"""
Connettore Outlook 365 / Microsoft Graph read-only.

Replica il pattern del Google Drive connector (D2.*):
- OAuth desktop flow via ``custodia_cli.auth.microsoft_oauth`` (PublicClient
  + MSAL token cache serializzata su file 0o600).
- Scope ``Mail.Read`` (read-only, minimum necessary).
- Itera i messaggi di una folder (default: ``inbox``) via Microsoft Graph
  ``/me/mailFolders/{id}/messages`` con paginazione ``@odata.nextLink``.
- Per ogni messaggio produce un ``SourceDocument`` con:
    * mime_type = ``message/rfc822``
    * text = header testuale (Da/A/Cc/Data/Oggetto) + body plain
      (conversione HTML → text via ``html2text``).
    * metadata = from/to/cc, received_at, has_attachments, folder, ...
- Retry con backoff esponenziale su 429/500/502/503/504, rispettando
  ``Retry-After`` (cappato a 60s) — implementato in ``_http.request_with_retry``.
- ``dry_run=True``: scarica solo headers + bodyPreview troncato (no body
  completo).
- Cache opzionale: salva il raw JSON di ogni messaggio in
  ``<cache_dir>/<id>.json`` con permessi 0o600 per replay offline.
- ``since``: filtra ``receivedDateTime ge ...`` lato Graph (server-side).
- ``max_messages``: hard stop dopo N messaggi (utile per smoke test).

Uso preferito (context manager, chiude la session a fine scope)::

    with OutlookConnector(...) as connector:
        for doc in connector.iter_documents():
            store.add_document(...)
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from types import TracebackType
from typing import Any, Iterator

import requests

from custodia_cli.auth.microsoft_oauth import get_access_token
from custodia_cli.connectors._http import request_with_retry
from custodia_cli.connectors.base import (
    ConnectorAPIError,
    ConnectorAuthError,
    ConnectorRateLimitError,
    SourceDocument,
)

try:
    import html2text
except ImportError as exc:  # pragma: no cover — dipendenza dichiarata in pyproject
    raise RuntimeError(
        "Manca dipendenza 'html2text'. Esegui: pip install html2text"
    ) from exc

logger = logging.getLogger(__name__)

GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
GRAPH_SCOPES = ["Mail.Read"]

# Campi minimi richiesti per costruire un SourceDocument completo.
_SELECT_FIELDS = (
    "id,subject,from,toRecipients,ccRecipients,receivedDateTime,"
    "body,bodyPreview,hasAttachments,parentFolderId"
)
_PAGE_SIZE = 50

# Retry config — allineato al pattern Google.
_RETRY_MAX_ATTEMPTS = 3
_RETRIABLE_STATUSES = frozenset({429, 500, 502, 503, 504})

# Cap massimo per Retry-After: se il server invia 999s ci proteggiamo.
_RETRY_AFTER_MAX = 60.0

# Safety net contro loop infiniti su @odata.nextLink ciclico/buggato.
_MAX_PAGES = 1000

# Limite dimensione bodyPreview per dry_run (truncato per evitare blow-up DB).
_DRY_RUN_PREVIEW_MAX = 500


def _sanitize_for_path(value: str) -> str:
    """Trasforma una stringa in un nome file safe per il filesystem."""
    return "".join(c if c.isalnum() or c in "._-" else "_" for c in value)


def _format_recipients(recipients: list[dict[str, Any]] | None) -> list[str]:
    """Estrae ``email`` da una lista di recipient Graph (toRecipients/ccRecipients)."""
    if not recipients:
        return []
    out: list[str] = []
    for r in recipients:
        addr = (r or {}).get("emailAddress") or {}
        email = addr.get("address")
        if isinstance(email, str) and email:
            out.append(email)
    return out


def _format_sender(from_field: dict[str, Any] | None) -> tuple[str, str]:
    """Ritorna ``(email, display_name)`` dal campo ``from`` di un messaggio Graph."""
    if not from_field:
        return "", ""
    addr = (from_field or {}).get("emailAddress") or {}
    return str(addr.get("address") or ""), str(addr.get("name") or "")


def _build_message_text(
    *,
    from_email: str,
    from_name: str,
    to_emails: list[str],
    cc_emails: list[str],
    received_at: str,
    subject: str,
    body_text: str,
) -> str:
    """Costruisce il testo finale del SourceDocument: header + body."""
    header_lines = [
        f"Da: {from_name or from_email} <{from_email}>",
        f"A: {', '.join(to_emails) if to_emails else '-'}",
    ]
    if cc_emails:
        header_lines.append(f"Cc: {', '.join(cc_emails)}")
    header_lines.append(f"Data: {received_at}")
    header_lines.append(f"Oggetto: {subject}")
    return "\n".join(header_lines) + "\n\n" + body_text


def _write_cache_json(cache_path: Path, payload: dict[str, Any]) -> None:
    """Scrive ``payload`` come JSON in ``cache_path`` con permessi 0o600.

    Pattern atomic via ``os.open`` (no finestra TOCTOU tra create e chmod).
    Parent dir creata con 0o700 best-effort.
    """
    parent = cache_path.parent
    parent.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(parent, 0o700)
    except OSError as exc:  # pragma: no cover — best effort (es. Windows)
        logger.debug("Impossibile chmod 0o700 su %s: %s", parent, exc)
    fd = os.open(
        str(cache_path),
        os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
        0o600,
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False)
    except Exception:
        # fdopen ha già chiuso il fd via context manager; in caso di errore
        # prima dell'apertura, chiudiamo qui (raro ma sicuro).
        try:
            os.close(fd)
        except OSError:
            pass
        raise


class OutlookConnector:
    """Connettore Outlook 365 / Microsoft Graph read-only.

    Esempio d'uso (raccomandato: context manager)::

        with OutlookConnector(
            folder_id=None,
            credentials_path=Path("/path/to/ms_credentials.json"),
            token_cache_path=state_dir / "microsoft_token.json",
            since=datetime(2026, 1, 1, tzinfo=timezone.utc),
        ) as connector:
            for doc in connector.iter_documents():
                store.add_document(...)

    Se non si usa il ``with``, chiamare ``connector.close()`` esplicitamente
    al termine per chiudere la ``requests.Session`` sottostante.
    """

    name = "outlook"

    # html2text è stateless una volta configurato → istanza shared per
    # evitare ricostruzione ad ogni messaggio.
    _html_converter: html2text.HTML2Text | None = None

    def __init__(
        self,
        *,
        folder_id: str | None = None,
        credentials_path: Path | None = None,
        token_cache_path: Path | None = None,
        cache_dir: Path | None = None,
        dry_run: bool = False,
        max_messages: int | None = None,
        since: datetime | None = None,
        access_token: str | None = None,
        session: requests.Session | None = None,
    ) -> None:
        """
        Args:
            folder_id: ID (o well-known name come ``"inbox"``, ``"sentitems"``)
                della folder da scansionare. Default ``None`` → ``"inbox"``.
            credentials_path: path al credentials JSON (client_id + tenant_id).
            token_cache_path: dove cachare il token MSAL. Default
                ``./microsoft_token.json``.
            cache_dir: directory opzionale dove salvare il raw JSON di ogni
                messaggio (per re-parse senza ri-chiamare Graph).
            dry_run: se True, scarica solo headers + bodyPreview troncato, no
                body completo. Utile per stima costi.
            max_messages: limite hard al numero di messaggi prodotti.
            since: filtra ``receivedDateTime >= since`` lato server.
            access_token: token già acquisito (per testing). Se passato,
                ``credentials_path`` e ``token_cache_path`` sono ignorati.
            session: ``requests.Session`` da iniettare (per testing).
        """
        self.folder_id = folder_id or "inbox"
        self.credentials_path = credentials_path
        self.token_cache_path = (
            token_cache_path
            if token_cache_path is not None
            else Path("./microsoft_token.json")
        )
        self.cache_dir = cache_dir
        self.dry_run = dry_run
        self.max_messages = max_messages
        self.since = since
        self._access_token = access_token
        self._session = session or requests.Session()
        # Indica se la session è "nostra" (creata qui) o iniettata: chiudiamo
        # solo quelle nostre per non sabotare chiamanti che riusano la stessa.
        self._owns_session = session is None
        self._closed = False
        self._stats: dict[str, int] = {
            "processed": 0,
            "skipped_since": 0,
            "skipped_max": 0,
            "errors": 0,
        }

    # ------------------------------------------------------------------
    # Context manager / cleanup
    # ------------------------------------------------------------------

    def __enter__(self) -> "OutlookConnector":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        """Chiude la session HTTP sottostante (idempotente)."""
        if self._closed:
            return
        if self._owns_session:
            try:
                self._session.close()
            except Exception as exc:  # noqa: BLE001 - best effort cleanup
                logger.debug("session.close() ha sollevato: %s", exc)
        self._closed = True

    # ------------------------------------------------------------------
    # API Connector
    # ------------------------------------------------------------------

    @property
    def stats(self) -> dict[str, int]:
        """Counter di osservabilità."""
        return dict(self._stats)

    def iter_documents(self) -> Iterator[SourceDocument]:
        """Itera tutti i messaggi della folder."""
        token = self._get_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }
        folder_name = self._resolve_folder_name(headers)
        url: str | None
        params: dict[str, str] | None
        url, params = self._build_initial_request()

        produced = 0
        seen_next_links: set[str] = set()
        page_count = 0
        while url is not None:
            page_count += 1
            if page_count > _MAX_PAGES:
                logger.warning(
                    "⚠️  Outlook: cap _MAX_PAGES=%d raggiunto, scansione interrotta.",
                    _MAX_PAGES,
                )
                return
            try:
                response = self._request(url, headers, params)
            except requests.HTTPError as exc:
                self._stats["errors"] += 1
                self._raise_for_http_error(exc)
                return  # pragma: no cover — _raise_for_http_error sempre raise
            except Exception as exc:  # noqa: BLE001
                # Errore non recuperabile sulla LISTA (network, ecc): contiamo
                # errore globale e usciamo.
                logger.error(
                    "❌  Errore fatale su Graph list (%s): %s",
                    type(exc).__name__,
                    exc,
                )
                self._stats["errors"] += 1
                raise ConnectorAPIError(
                    f"Errore fatale su Graph list: {type(exc).__name__}: {exc}"
                ) from exc

            data: dict[str, Any] = response.json()
            for msg in data.get("value", []):
                if self.max_messages is not None and produced >= self.max_messages:
                    self._stats["skipped_max"] += 1
                    return
                doc = self._process_message(msg, folder_name)
                if doc is not None:
                    produced += 1
                    yield doc

            # Paginazione: next link è URL completo. Reset params (sono già
            # encodati dentro nextLink).
            next_link = data.get("@odata.nextLink")
            if next_link is not None:
                if next_link in seen_next_links:
                    logger.warning(
                        "⚠️  Loop pagination rilevato su %s — scansione interrotta.",
                        next_link,
                    )
                    return
                seen_next_links.add(next_link)
            url = next_link
            params = None

    # ------------------------------------------------------------------
    # Auth + request setup
    # ------------------------------------------------------------------

    def _get_access_token(self) -> str:
        """Ritorna token cached o ne acquisisce uno nuovo."""
        if self._access_token is not None:
            return self._access_token
        try:
            self._access_token = get_access_token(
                credentials_path=self.credentials_path,
                token_cache_path=self.token_cache_path,
                scopes=GRAPH_SCOPES,
            )
        except Exception as exc:  # noqa: BLE001 - normalizziamo a ConnectorAuthError
            raise ConnectorAuthError(
                f"Impossibile ottenere access token Microsoft: {exc}"
            ) from exc
        return self._access_token

    def _build_initial_request(self) -> tuple[str, dict[str, str]]:
        """Costruisce URL e query params per la prima pagina di messaggi."""
        url = f"{GRAPH_BASE_URL}/me/mailFolders/{self.folder_id}/messages"
        params: dict[str, str] = {
            "$select": _SELECT_FIELDS,
            "$top": str(_PAGE_SIZE),
            "$orderby": "receivedDateTime desc",
        }
        if self.since is not None:
            # Graph richiede UTC ISO8601 con suffisso Z.
            since_utc = (
                self.since.astimezone(timezone.utc)
                if self.since.tzinfo
                else self.since.replace(tzinfo=timezone.utc)
            )
            params["$filter"] = (
                f"receivedDateTime ge {since_utc.strftime('%Y-%m-%dT%H:%M:%SZ')}"
            )
        return url, params

    def _resolve_folder_name(self, headers: dict[str, str]) -> str:
        """Recupera il display name della folder (per costruire source_path).

        Best effort: se la chiamata fallisce ritorna ``folder_id`` come fallback,
        senza interrompere lo scan.
        """
        url = f"{GRAPH_BASE_URL}/me/mailFolders/{self.folder_id}"
        try:
            response = self._request(
                url, headers, params={"$select": "displayName"}
            )
            data = response.json()
            name = data.get("displayName") or self.folder_id
            return str(name)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "⚠️  Impossibile recuperare il nome della folder %s (%s); userò l'id.",
                self.folder_id,
                exc,
            )
            return self.folder_id

    # ------------------------------------------------------------------
    # Retry / network
    # ------------------------------------------------------------------

    def _request(
        self,
        url: str,
        headers: dict[str, str],
        params: dict[str, str] | None,
    ) -> requests.Response:
        """GET wrapper sul helper condiviso ``request_with_retry``."""
        return request_with_retry(
            self._session,
            "GET",
            url,
            headers=headers,
            params=params,
            timeout=30.0,
            retriable_statuses=_RETRIABLE_STATUSES,
            max_attempts=_RETRY_MAX_ATTEMPTS,
            retry_after_max=_RETRY_AFTER_MAX,
        )

    @staticmethod
    def _raise_for_http_error(exc: requests.HTTPError) -> None:
        """Mappa ``HTTPError`` in eccezioni semantiche del connector."""
        response = exc.response
        status = getattr(response, "status_code", None)
        if status in (401, 403):
            raise ConnectorAuthError(
                f"Token Microsoft non valido o senza permessi (HTTP {status})."
            ) from exc
        if status == 429:
            raise ConnectorRateLimitError(
                "Rate limit Microsoft Graph superato (HTTP 429)."
            ) from exc
        raise ConnectorAPIError(
            f"Errore Graph API (HTTP {status})."
        ) from exc

    # ------------------------------------------------------------------
    # HTML → text
    # ------------------------------------------------------------------

    @classmethod
    def _get_html_converter(cls) -> html2text.HTML2Text:
        """Lazy singleton di ``html2text.HTML2Text`` (configurato una volta)."""
        if cls._html_converter is None:
            conv = html2text.HTML2Text()
            conv.ignore_images = True
            conv.ignore_links = False
            conv.body_width = 0  # no wrapping
            # unicode_snob=True preserva caratteri come ``caffè``, ``€``,
            # apostrofo tipografico anziché degradarli a ASCII (importante per
            # corpus italiano).
            conv.unicode_snob = True
            cls._html_converter = conv
        return cls._html_converter

    @classmethod
    def _html_to_text(cls, html: str) -> str:
        """Converte HTML in plain text via ``html2text`` (istanza shared)."""
        return cls._get_html_converter().handle(html).strip()

    # ------------------------------------------------------------------
    # Per-message processing
    # ------------------------------------------------------------------

    def _process_message(
        self,
        msg: dict[str, Any],
        folder_name: str,
    ) -> SourceDocument | None:
        """Trasforma un messaggio Graph in un SourceDocument.

        Per-message errors sono isolati: se il parsing di un singolo messaggio
        fallisce, log warning + incremento ``stats['errors']`` + continua.
        """
        try:
            msg_id = msg.get("id")
            if not isinstance(msg_id, str) or not msg_id:
                raise ValueError("messaggio senza id valido")

            subject = str(msg.get("subject") or "(senza oggetto)")
            received_at = str(msg.get("receivedDateTime") or "")
            has_attachments = bool(msg.get("hasAttachments"))
            from_email, from_name = _format_sender(msg.get("from"))
            to_emails = _format_recipients(msg.get("toRecipients"))
            cc_emails = _format_recipients(msg.get("ccRecipients"))
            body_preview = str(msg.get("bodyPreview") or "")

            # Body: html → text se necessario.
            if self.dry_run:
                body_text = body_preview[:_DRY_RUN_PREVIEW_MAX]
            else:
                body_obj = msg.get("body") or {}
                content_type = str(body_obj.get("contentType") or "text").lower()
                raw_content = str(body_obj.get("content") or "")
                if content_type == "html":
                    body_text = self._html_to_text(raw_content)
                else:
                    body_text = raw_content

            source_id = f"outlook:{msg_id}"
            # Disambiguazione: due email con stesso subject troncato avrebbero
            # source_path identico → aggiungiamo prefisso id (primi 8 char).
            id_suffix = _sanitize_for_path(msg_id)[:8] or "noid"
            source_path = (
                f"/Outlook/{folder_name}/{_sanitize_for_path(subject)[:80]}-{id_suffix}"
            )

            text = _build_message_text(
                from_email=from_email,
                from_name=from_name,
                to_emails=to_emails,
                cc_emails=cc_emails,
                received_at=received_at,
                subject=subject,
                body_text=body_text,
            )

            metadata: dict[str, Any] = {
                "message_id": msg_id,
                "folder": folder_name,
                "from_email": from_email,
                "from_name": from_name,
                "to_emails": to_emails,
                "cc_emails": cc_emails,
                "received_at": received_at,
                "has_attachments": has_attachments,
                "body_preview": body_preview[:_DRY_RUN_PREVIEW_MAX],
            }

            # Cache raw JSON opzionale (chmod 0o600).
            if self.cache_dir is not None and not self.dry_run:
                try:
                    cache_path = self.cache_dir / f"{_sanitize_for_path(source_id)}.json"
                    if not cache_path.exists():
                        _write_cache_json(cache_path, msg)
                    metadata["cached_at"] = str(cache_path)
                except OSError as exc:
                    logger.warning(
                        "⚠️  Cache scrittura fallita per %s: %s", msg_id, exc
                    )

            self._stats["processed"] += 1
            return SourceDocument(
                source_id=source_id,
                source_path=source_path,
                mime_type="message/rfc822",
                text=text,
                metadata=metadata,
            )
        except Exception as exc:  # noqa: BLE001
            # NB: ``Exception`` esclude ``BaseException`` ⇒ KeyboardInterrupt
            # e SystemExit propagano correttamente.
            # NON loggare il body in clear: solo id + tipo errore.
            msg_id_safe = msg.get("id", "<no-id>") if isinstance(msg, dict) else "<malformed>"
            logger.error(
                "❌  errore parsing messaggio %s (%s): %s",
                msg_id_safe,
                type(exc).__name__,
                exc,
            )
            self._stats["errors"] += 1
            return None


__all__ = ["OutlookConnector", "GRAPH_SCOPES", "GRAPH_BASE_URL"]
