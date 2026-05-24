"""
Connettore Google Drive read-only.

Implementa il design doc D2.* (sezione "Componente 2"):
- OAuth desktop flow via ``custodia_cli.auth.google_oauth`` (D2.1).
- Scope ``drive.readonly`` (D2.2), traversal BFS limitato a una folder root
  esplicitamente indicata dal consulente (D2.3).
- Parsing locale per i tipi supportati (D2.4):
    * PDF, DOCX, XLSX nativi → ``files.get_media`` + parser dedicato.
    * Google Docs nativi → ``files.export`` come DOCX → ``parse_docx``.
    * Google Sheets nativi → ``files.export`` come XLSX → ``parse_xlsx``.
    * Google Slides, immagini, video, archivi → skip silenzioso/log warning.
- Skip per file >50MB, file in cestino, formati non supportati.
- Retry con backoff esponenziale su 403/429 (D2.6), max 3 tentativi.
- ``dry_run=True``: traversa ma non scarica/parsa, produce ``SourceDocument``
  con ``text=""`` per stima costi.
- Cache locale opzionale dei bytes scaricati per re-parse senza ri-download.

Decisione: NON esiste un parser ``gdoc.py`` separato. I Google-native files
vengono esportati come DOCX/XLSX dall'API Drive e poi parsati dai parser
canonici. Questo evita duplicazione di logica e tiene i parser focalizzati su
1 formato ciascuno.
"""

from __future__ import annotations

import io
import logging
import random
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Iterator, TypeVar

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload

from custodia_cli.auth.google_oauth import get_credentials
from custodia_cli.connectors.base import ParserError, SourceDocument
from custodia_cli.connectors.parsers import parse_docx, parse_pdf, parse_xlsx

if TYPE_CHECKING:
    from googleapiclient.discovery import Resource as DriveResource
else:  # alias runtime senza forzare import statico per future-proof
    DriveResource = Any  # type: ignore[misc, assignment]

logger = logging.getLogger(__name__)

DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

# Limite hard documenti grandi (design doc D2.6): skip + warning.
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB

# Parser signature canonica: bytes/Path → str.
ParserFunc = Callable[[bytes], str]

# Mapping MIME nativo Google → (export_mime, parser_func).
# I file Google-native non hanno "raw bytes": vanno esportati con files.export.
_GOOGLE_EXPORT_MAP: dict[str, tuple[str, ParserFunc]] = {
    "application/vnd.google-apps.document": (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        parse_docx,
    ),
    "application/vnd.google-apps.spreadsheet": (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        parse_xlsx,
    ),
}

# Mapping MIME binario nativo → parser per file scaricati con files.get_media.
_BINARY_PARSER_MAP: dict[str, ParserFunc] = {
    "application/pdf": parse_pdf,
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": parse_docx,
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": parse_xlsx,
}

# Prefissi MIME da skippare silenziosamente (non interessanti per Custodia v0.1).
_SKIP_MIME_PREFIXES = ("image/", "video/", "audio/", "application/zip")

# Backoff esponenziale per retry su 403/429: base 2s, max 3 tentativi.
_RETRY_MAX_ATTEMPTS = 3
_RETRY_BACKOFF_BASE = 2.0

# Reason codes Google che indicano rate limiting / quota, retriable.
_RETRIABLE_403_REASONS = frozenset(
    {
        "userratelimitexceeded",
        "ratelimitexceeded",
        "quotaexceeded",
        "backenderror",
    }
)

T = TypeVar("T")


def _sanitize_for_path(source_id: str) -> str:
    """Trasforma un source_id in un nome file safe per il filesystem."""
    return "".join(c if c.isalnum() or c in "._-" else "_" for c in source_id)


def _extract_http_error_reason(exc: HttpError) -> str:
    """Estrae il ``reason`` Google da un HttpError in modo robusto.

    Prova prima ``exc.error_details`` (lista di dict structured) e poi
    fallback al parsing della reason string. Tutto in lowercase.
    """
    # 1) googleapiclient espone error_details su versioni recenti.
    details = getattr(exc, "error_details", None)
    if isinstance(details, list):
        for d in details:
            if isinstance(d, dict):
                reason = d.get("reason")
                if isinstance(reason, str) and reason:
                    return reason.lower()
    # 2) fallback al campo top-level reason (httplib2 Response).
    reason = getattr(getattr(exc, "resp", None), "reason", None)
    if isinstance(reason, str):
        return reason.lower()
    return ""


def _is_retriable_http_error(exc: HttpError) -> bool:
    """Vero per 5xx, 429, e 403 con reason rate-limit/quota.

    Usa ``exc.error_details`` (campo structured) o ``resp.reason`` per il check,
    NON substring match sul messaggio (fragile e localizzato).
    """
    status = getattr(getattr(exc, "resp", None), "status", None)
    if status in (429, 500, 502, 503, 504):
        return True
    if status == 403:
        reason = _extract_http_error_reason(exc)
        # Match esatto contro il set di reason retriable.
        if reason in _RETRIABLE_403_REASONS:
            return True
        # Fallback difensivo: substring sul reason (non sul messaggio).
        return any(token in reason for token in ("ratelimit", "quota"))
    return False


def _with_retry(callable_no_args: Callable[[], T], *, what: str) -> T:
    """Esegue ``callable_no_args()`` con retry/backoff su errori transient."""
    attempt = 0
    while True:
        attempt += 1
        try:
            return callable_no_args()
        except HttpError as exc:
            if not _is_retriable_http_error(exc) or attempt >= _RETRY_MAX_ATTEMPTS:
                raise
            sleep_s = _RETRY_BACKOFF_BASE * (2 ** (attempt - 1)) + random.uniform(0, 0.5)
            logger.warning(
                "⚠️  HttpError transient su %s (tentativo %d/%d): %s — retry in %.1fs",
                what,
                attempt,
                _RETRY_MAX_ATTEMPTS,
                exc,
                sleep_s,
            )
            time.sleep(sleep_s)


class GoogleDriveConnector:
    """Connettore Google Drive read-only.

    Esempio d'uso::

        connector = GoogleDriveConnector(
            root_folder_id="1AbCdEf...",
            credentials_path=Path("/path/to/credentials.json"),
            token_cache_path=state_dir / "google_token.json",
        )
        for doc in connector.iter_documents():
            store.add_document(...)
    """

    name = "google_drive"

    def __init__(
        self,
        root_folder_id: str,
        *,
        credentials_path: Path | None = None,
        token_cache_path: Path | None = None,
        dry_run: bool = False,
        cache_dir: Path | None = None,
        service: DriveResource | None = None,
    ) -> None:
        """
        Args:
            root_folder_id: ID della folder Drive da cui partire (BFS verso le foglie).
            credentials_path: path al ``credentials.json`` OAuth desktop. Se None,
                si tenta la env ``CUSTODIA_GOOGLE_CREDENTIALS_JSON``.
            token_cache_path: dove cachare il token utente (refresh-token incluso).
                Default ``./google_token.json`` (consigliato passare il path nello
                state_dir).
            dry_run: se True, traversa ma non scarica/parsa; produce
                ``SourceDocument`` con ``text=""``. Utile per stima costi.
            cache_dir: directory opzionale dove salvare i raw bytes scaricati,
                per re-parse senza ri-download in run successivi.
            service: discovery client già costruito (per testing). Se passato,
                ``credentials_path`` e ``token_cache_path`` sono ignorati.
        """
        self.root_folder_id = root_folder_id
        self.credentials_path = credentials_path
        self.token_cache_path = (
            token_cache_path
            if token_cache_path is not None
            else Path("./google_token.json")
        )
        self.dry_run = dry_run
        self.cache_dir = cache_dir
        self._service: DriveResource | None = service
        self._stats: dict[str, int] = {
            "processed": 0,
            "skipped_size": 0,
            "skipped_mime": 0,
            "skipped_trashed": 0,
            "errors": 0,
        }

    # ------------------------------------------------------------------
    # API Connector
    # ------------------------------------------------------------------

    def iter_documents(self) -> Iterator[SourceDocument]:
        """Itera tutti i documenti supportati a partire dalla folder root."""
        service = self._get_service()
        for file_meta, folder_path in self._traverse(service, self.root_folder_id):
            doc = self._process_file(service, file_meta, folder_path)
            if doc is not None:
                yield doc

    @property
    def stats(self) -> dict[str, int]:
        """Counter di osservabilità: processed/skipped_size/.../errors."""
        return dict(self._stats)

    # ------------------------------------------------------------------
    # Auth + service
    # ------------------------------------------------------------------

    def _get_service(self) -> DriveResource:
        """Costruisce (o ritorna cached) il client Drive v3."""
        if self._service is not None:
            return self._service
        creds = get_credentials(
            credentials_path=self.credentials_path,
            token_cache_path=self.token_cache_path,
            scopes=DRIVE_SCOPES,
        )
        self._service = build("drive", "v3", credentials=creds, cache_discovery=False)
        return self._service

    # ------------------------------------------------------------------
    # Traversal BFS
    # ------------------------------------------------------------------

    def _fetch_folder_name(self, service: DriveResource, folder_id: str) -> str:
        """Recupera il nome di una folder Drive (per costruire i path gerarchici).

        Ritorna ``folder_id`` come fallback se la API fallisce o il nome è vuoto:
        evita di crashare l'intero scan per un metadata mancante sulla root.
        """
        def _do() -> dict[str, Any]:
            return (
                service.files()
                .get(fileId=folder_id, fields="id, name", supportsAllDrives=True)
                .execute()
            )

        try:
            meta = _with_retry(_do, what=f"files.get({folder_id})")
            name = meta.get("name") or folder_id
            return str(name)
        except HttpError as exc:
            logger.warning(
                "⚠️  Impossibile recuperare il nome della folder %s (%s); userò l'id come fallback.",
                folder_id,
                exc,
            )
            return folder_id
        except Exception as exc:  # pragma: no cover — difensivo
            logger.warning(
                "⚠️  Errore inatteso su files.get(%s) (%s); userò l'id come fallback.",
                folder_id,
                exc,
            )
            return folder_id

    def _traverse(
        self, service: DriveResource, root_folder_id: str
    ) -> Iterator[tuple[dict[str, Any], str]]:
        """BFS della folder root. Yield ``(file_meta, parent_folder_path)``.

        Filtra ``trashed=false`` sia lato query Drive sia client-side. Tiene
        traccia del path gerarchico di ogni folder per popolare ``source_path``.
        """
        # Recupera nome della root per costruire path leggibili.
        root_name = self._fetch_folder_name(service, root_folder_id)
        folder_paths: dict[str, str] = {root_folder_id: f"/{root_name}"}

        queue: list[str] = [root_folder_id]
        visited: set[str] = set()

        while queue:
            folder_id = queue.pop(0)
            if folder_id in visited:
                continue
            visited.add(folder_id)
            current_path = folder_paths.get(folder_id, f"/{folder_id}")

            page_token: str | None = None
            while True:
                # ``def`` nested al posto di lambda con closure su page_token/folder_id:
                # ogni iterazione cattura i valori correnti (no late-binding bug).
                fid = folder_id
                token_now = page_token

                def _do_list() -> dict[str, Any]:
                    return (
                        service.files()
                        .list(
                            q=f"'{fid}' in parents and trashed=false",
                            pageSize=100,
                            pageToken=token_now,
                            fields=(
                                "nextPageToken, files(id, name, mimeType, size, "
                                "modifiedTime, createdTime, trashed, parents, "
                                "md5Checksum, webViewLink)"
                            ),
                            supportsAllDrives=True,
                            includeItemsFromAllDrives=True,
                        )
                        .execute()
                    )

                response = _with_retry(_do_list, what=f"files.list({folder_id})")

                for f in response.get("files", []):
                    # Doppia difesa: anche se la query filtra, controlliamo client-side.
                    if f.get("trashed"):
                        self._stats["skipped_trashed"] += 1
                        logger.debug("⏭️  skip trashed: %s", f.get("name"))
                        continue
                    if f["mimeType"] == "application/vnd.google-apps.folder":
                        child_id = f["id"]
                        child_name = f.get("name") or child_id
                        folder_paths[child_id] = f"{current_path}/{child_name}"
                        queue.append(child_id)
                        continue
                    yield f, current_path
                page_token = response.get("nextPageToken")
                if page_token is None:
                    break

    # ------------------------------------------------------------------
    # Processing singolo file
    # ------------------------------------------------------------------

    def _process_file(
        self,
        service: DriveResource,
        file_meta: dict[str, Any],
        parent_folder_path: str,
    ) -> SourceDocument | None:
        """Decide come gestire un singolo file e ritorna eventuale SourceDocument.

        Cattura ``Exception`` (non ``BaseException``) per impedire che un singolo
        file rompa l'intero scan: errori di rete, parser bug, encoding fail, etc.
        vengono loggati e contati in ``stats['errors']``. ``KeyboardInterrupt``
        e ``SystemExit`` sono ``BaseException`` e propagano correttamente.
        """
        name = file_meta.get("name", "<unnamed>")
        mime = file_meta["mimeType"]
        file_id = file_meta["id"]
        size_str = file_meta.get("size")
        try:
            size_bytes = int(size_str) if size_str is not None else 0
        except (TypeError, ValueError):
            size_bytes = 0

        source_id = f"gdrive:{file_id}"
        # Path gerarchico: <root>/<sub>/.../<name>. Preserva la struttura Drive.
        source_path = f"{parent_folder_path}/{name}"

        # Skip mime non supportati.
        if any(mime.startswith(p) for p in _SKIP_MIME_PREFIXES):
            self._stats["skipped_mime"] += 1
            logger.info("⏭️  skip mime non supportato (%s): %s", mime, name)
            return None

        # Skip file troppo grandi (solo per binari nativi; google-native non hanno size affidabile).
        if size_bytes and size_bytes > MAX_FILE_SIZE_BYTES:
            self._stats["skipped_size"] += 1
            logger.warning(
                "⚠️  skip file >50MB (%.1fMB): %s",
                size_bytes / 1024 / 1024,
                name,
            )
            return None

        metadata: dict[str, Any] = {
            "drive_id": file_id,
            "name": name,
            "mime_type_original": mime,
            "modified_time": file_meta.get("modifiedTime"),
            "created_time": file_meta.get("createdTime"),
            "parents": file_meta.get("parents", []),
            "size_bytes": size_bytes,
            "web_view_link": file_meta.get("webViewLink"),
            "md5": file_meta.get("md5Checksum"),
        }

        # Dry-run: emetti placeholder senza scaricare/parsare.
        if self.dry_run:
            self._stats["processed"] += 1
            canonical_mime = self._canonical_mime(mime)
            return SourceDocument(
                source_id=source_id,
                source_path=source_path,
                mime_type=canonical_mime,
                text="",
                metadata=metadata,
            )

        # Decisione: google-native (export) vs binario nativo (get_media).
        # ``raw_bytes`` inizializzato esplicitamente: evita l'anti-pattern
        # ``'raw_bytes' in locals()``.
        raw_bytes: bytes | None = None
        text: str
        canonical_mime: str
        try:
            if mime in _GOOGLE_EXPORT_MAP:
                export_mime, parser = _GOOGLE_EXPORT_MAP[mime]
                raw_bytes = self._export_file(service, file_id, export_mime)
                text = parser(raw_bytes)
                canonical_mime = export_mime
            elif mime in _BINARY_PARSER_MAP:
                parser = _BINARY_PARSER_MAP[mime]
                raw_bytes = self._download_file(service, file_id)
                text = parser(raw_bytes)
                canonical_mime = mime
            elif mime == "application/vnd.google-apps.presentation":
                logger.warning("⚠️  Google Slides non supportati in v0.1: skip %s", name)
                self._stats["skipped_mime"] += 1
                return None
            else:
                logger.info("⏭️  skip mime non gestito (%s): %s", mime, name)
                self._stats["skipped_mime"] += 1
                return None
        except ParserError as exc:
            logger.error("❌  parser error su %s: %s", name, exc)
            self._stats["errors"] += 1
            return None
        except HttpError as exc:
            logger.error("❌  HttpError su %s: %s", name, exc)
            self._stats["errors"] += 1
            return None
        except Exception as exc:
            # Cattura ogni altro fail non-fatale per il singolo file:
            # socket.timeout, ConnectionResetError, ssl.SSLError, pypdf
            # DependencyError, MemoryError su file corrotti, etc.
            # NB: ``Exception`` esclude ``BaseException`` ⇒ KeyboardInterrupt/
            # SystemExit non vengono mai inghiottiti.
            logger.error(
                "❌  errore inatteso su %s (%s): %s",
                name,
                type(exc).__name__,
                exc,
            )
            self._stats["errors"] += 1
            return None

        # Cache opzionale dei raw bytes per re-parse offline.
        if self.cache_dir is not None and raw_bytes is not None:
            try:
                self.cache_dir.mkdir(parents=True, exist_ok=True)
                cache_path = self.cache_dir / _sanitize_for_path(source_id)
                # Evita riscrittura ad ogni rerun se il blob non è cambiato.
                if not cache_path.exists():
                    cache_path.write_bytes(raw_bytes)
                metadata["cached_at"] = str(cache_path)
            except OSError as exc:
                logger.warning("⚠️  cache scrittura fallita per %s: %s", name, exc)

        self._stats["processed"] += 1
        return SourceDocument(
            source_id=source_id,
            source_path=source_path,
            mime_type=canonical_mime,
            text=text,
            metadata=metadata,
        )

    @staticmethod
    def _canonical_mime(mime: str) -> str:
        """Mappa il mime native Google al mime di esportazione canonico (per dry-run)."""
        if mime in _GOOGLE_EXPORT_MAP:
            return _GOOGLE_EXPORT_MAP[mime][0]
        return mime

    # ------------------------------------------------------------------
    # Download / export
    # ------------------------------------------------------------------

    @staticmethod
    def _download_media_to_bytes(request: Any) -> bytes:
        """Scarica un MediaIoBaseDownload request in memoria."""
        buf = io.BytesIO()
        downloader = MediaIoBaseDownload(buf, request)
        done = False
        while not done:
            _status, done = downloader.next_chunk()
        return buf.getvalue()

    def _download_file(self, service: DriveResource, file_id: str) -> bytes:
        """Scarica i bytes nativi di un file binario tramite ``files.get_media``."""
        def _do() -> bytes:
            request = service.files().get_media(fileId=file_id, supportsAllDrives=True)
            return self._download_media_to_bytes(request)

        return _with_retry(_do, what=f"get_media({file_id})")

    def _export_file(
        self, service: DriveResource, file_id: str, export_mime: str
    ) -> bytes:
        """Esporta un file Google-native (Docs/Sheets) come DOCX/XLSX."""
        def _do() -> bytes:
            request = service.files().export_media(fileId=file_id, mimeType=export_mime)
            return self._download_media_to_bytes(request)

        return _with_retry(_do, what=f"export_media({file_id})")


__all__ = ["GoogleDriveConnector", "DRIVE_SCOPES", "MAX_FILE_SIZE_BYTES"]
