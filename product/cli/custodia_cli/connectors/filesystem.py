"""
Connettore filesystem locale per Custodia v0.1.

Legge ricorsivamente una cartella locale (o mount POSIX/NAS) e produce
``SourceDocument`` con stesso contratto del connettore Google Drive (U3).
Riusa interamente i parser di U3 (PDF/DOCX/XLSX) e aggiunge il supporto
nativo per file plaintext (``.txt``, ``.md``, ``.csv``, ``.log``).

Design choices:
- Skip silenzioso per file binari non testuali (immagini, video, audio,
  archivi): non interessano per Custodia v0.1.
- Skip silenzioso per file temporanei Office (``~$*``) e metadata di sistema
  (``.DS_Store``, ``Thumbs.db``).
- Skip esplicito (con warning loggato) per file > ``max_file_size_mb``:
  protegge da OOM su dump corposi.
- ``source_path`` è SEMPRE relativo a ``root_path``, così il vault è
  portabile fra macchine.
- ``source_id`` è ``fs:<sha1_path_assoluto>[:16]``: stabile fra rerun finché
  il file non si sposta.
- Glob exclude patterns: ``fnmatch`` style, applicato sia al filename che a
  qualunque componente intermedio del path (cosicché ``.git`` escluda tutta
  la sottocartella).
- Traversal sicuro: usa ``os.walk(followlinks=False)``. Symlink loops e
  symlink-escape (link che puntano fuori dalla root) sono ignorati di default;
  ``follow_symlinks=True`` riabilita il follow ma applica comunque la difesa
  di canonicalizzazione (skip se il path resolved esce dalla root).
- Guardrail su root troppo permissivi (``/``, ``$HOME``, ``/etc`` …): solleva
  ``ValueError`` salvo override esplicito ``allow_dangerous_root=True``.
"""

from __future__ import annotations

import fnmatch
import hashlib
import logging
import mimetypes
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterator

if TYPE_CHECKING:
    from custodia_cli.state.store import StateStore

from custodia_cli.connectors.base import ParserError, SourceDocument
from custodia_cli.connectors.parsers import (
    ParserPool,
    mime_matches_extension,
    parse_docx,
    parse_pdf,
    parse_xlsx,
)

logger = logging.getLogger(__name__)

# Default exclude patterns (glob-style, applicato a ogni componente del path).
_DEFAULT_EXCLUDES: list[str] = [
    # Sistema / metadata classici (già in v0.1).
    ".git",
    ".obsidian",
    "__pycache__",
    ".custodia-state",
    "*.tmp",
    "~$*",
    ".DS_Store",
    "Thumbs.db",
]

# U3 — Smart excludes estesi: pattern di sottocartella che non hanno mai
# valore per Custodia (build dir, virtualenv, cache, lock di pacchetti).
# Match via ``_path_matches_any`` su qualunque componente del path.
#
# NOTA: gli pattern *di estensione* NON vanno qui ma in ``_SKIP_EXTENSIONS``,
# così la stat ``skipped_ext`` resta semanticamente corretta (skipped_excluded
# è per directory/path-component matches, non per estensioni mediali).
_SMART_EXCLUDES_EXTENDED: list[str] = [
    # Build/lib directory (node, python, java, rust)
    "node_modules",
    ".next",
    "dist",
    "build",
    "target",
    ".gradle",
    ".m2",
    ".cargo",
    ".venv",
    "venv",
    "env",
    "site-packages",
    ".pytest_cache",
    ".tox",
    ".mypy_cache",
    ".ruff_cache",
    # macOS cache/library system (parziale: Library da sola NON è esclusa,
    # vedi ``_is_under_excluded_library_subdir`` per la logica fine).
    ".Trash",
    ".cache",
    # Photos.app library: pseudo-cartella opaca.
    "*.photoslibrary",
    # Streamlit
    ".streamlit",
    # Lock files (qui matchano come *filename* via fnmatch).
    "*.lock",
    "Pipfile.lock",
    "package-lock.json",
    "yarn.lock",
    "poetry.lock",
    "uv.lock",
]

# Sottocartelle di ``~/Library`` (macOS) sempre senza valore di scansione.
# ``Library`` da solo NON va escluso perché può contenere mailbox utenti
# (es. ``~/Library/Mail``) che il consulente vuole davvero indicizzare.
# Match in forma "componenti consecutivi": ``parts[i] == "Library" and
# parts[i+1] in _LIBRARY_USELESS_SUBDIRS``.
_LIBRARY_USELESS_SUBDIRS: frozenset[str] = frozenset(
    {
        "Caches",
        "Application Support",
        "Logs",
        "Containers",
        "Mobile Documents",  # iCloud Drive staging
    }
)

# Estensioni → parser binario dedicato.
_BINARY_PARSER_BY_EXT = {
    ".pdf": parse_pdf,
    ".docx": parse_docx,
    ".xlsx": parse_xlsx,
}

# Estensioni testuali lette in raw con cascade encoding (UTF-8 → cp1252 → latin-1).
_PLAINTEXT_EXTENSIONS: set[str] = {
    ".txt",
    ".md",
    ".csv",
    ".log",
    ".tsv",
    ".json",
    ".yaml",
    ".yml",
    ".ini",
    ".cfg",
}

# Estensioni esplicitamente skippate (mediali / archivi / eseguibili / DB
# binari). Skip silenzioso, counter ``skipped_ext``.
_SKIP_EXTENSIONS: set[str] = {
    # Immagini
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".bmp",
    ".tiff",
    ".svg",
    # Foto fotocamera high-res (no OCR in v0.1)
    ".heic",
    ".heif",
    ".raw",
    ".cr2",
    ".nef",
    ".arw",
    ".dng",
    # Video (no transcription in v0.1)
    ".mp4",
    ".mov",
    ".avi",
    ".mkv",
    ".webm",
    ".flv",
    # Audio (no transcription in v0.1)
    ".mp3",
    ".wav",
    ".flac",
    ".aac",
    ".m4a",
    ".ogg",
    # Archivi compressi
    ".zip",
    ".tar",
    ".tgz",
    ".gz",
    ".bz2",
    ".7z",
    ".rar",
    # Eseguibili / librerie / installer
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".app",
    ".dmg",
    ".pkg",
    ".deb",
    ".rpm",
    ".iso",
    ".msi",
    # Database / blob binari di sistema
    ".sqlite",
    ".sqlite3",
    ".db-journal",
    ".db-shm",
    ".db-wal",
    ".dat",
    ".bin",
}

# Root path "troppo permissivi" da rifiutare a meno di override esplicito.
# Match per uguaglianza canonicalizzata su ``Path.resolve()``.
def _dangerous_root_paths() -> set[Path]:
    """Set dei root path considerati pericolosi sul sistema corrente.

    Calcolato lazily per onorare ``Path.home()`` del consulente runtime.
    """
    candidates: set[Path] = {
        Path("/"),
        Path("/Users"),
        Path("/home"),
        Path("/etc"),
        Path("/var"),
        Path("/private"),
        Path("/tmp"),
        Path("/usr"),
        Path("/bin"),
        Path("/sbin"),
        Path("/opt"),
        Path("/System"),  # macOS
        Path("/Library"),  # macOS system
    }
    # Windows-style (no-op su POSIX, utile per cross-platform).
    candidates.add(Path("C:\\"))
    candidates.add(Path("C:\\Users"))
    try:
        candidates.add(Path.home())
    except (RuntimeError, OSError):
        pass
    # Resolved variants per match canonico.
    resolved: set[Path] = set()
    for c in candidates:
        try:
            resolved.add(c.resolve())
        except (OSError, RuntimeError):
            resolved.add(c)
    return resolved


def _is_under_excluded_library_subdir(path: Path) -> bool:
    """True se ``path`` contiene un segmento ``Library`` seguito da uno dei
    nomi noti come ``Caches``/``Application Support``/``Logs``/``Containers``/
    ``Mobile Documents``.

    Logica fine pensata per macOS: ``~/Library`` da sola NON va esclusa
    (può contenere ``Mail``, ``Calendars`` o altre cartelle effettivamente
    rilevanti), ma le sottocartelle di sistema sopra elencate sono sempre
    rumore. Match case-sensitive perché sono nomi canonici.
    """
    parts = path.parts
    for i, part in enumerate(parts):
        if part == "Library" and i + 1 < len(parts):
            if parts[i + 1] in _LIBRARY_USELESS_SUBDIRS:
                return True
    return False


def _path_matches_any(path: Path, patterns: list[str], root: Path) -> bool:
    """True se ``path`` matcha qualche pattern, su filename O su qualunque
    componente intermedio relativo a ``root``.

    Esempio: ``.git/HEAD`` con pattern ``.git`` → True (perché ``.git`` è uno
    dei componenti relativi).
    """
    name = path.name
    if any(fnmatch.fnmatch(name, pat) for pat in patterns):
        return True
    try:
        rel = path.relative_to(root)
    except ValueError:
        return False
    for part in rel.parts:
        if any(fnmatch.fnmatch(part, pat) for pat in patterns):
            return True
    return False


def _sha1_path(absolute_path: str) -> str:
    """Hash SHA1 stabile del path assoluto, troncato a 16 char."""
    return hashlib.sha1(absolute_path.encode("utf-8")).hexdigest()[:16]


# Soglia di hashing per il manifest: SHA1 dei primi 1MB del file. Sufficiente
# per change detection (la probabilità che due file con stessi primi 1MB E
# stessa mtime E stessa size siano effettivamente diversi è astronomica), e
# limita l'I/O su file di grosse dimensioni durante il pre-check.
_MANIFEST_HASH_MAX_BYTES = 1024 * 1024


def _compute_content_hash(path: Path) -> bytes:
    """SHA1 dei primi 1MB del file, troncato a 16 byte (128 bit).

    Solleva ``OSError``/``PermissionError`` che il chiamante deve catturare.
    """
    hasher = hashlib.sha1()
    with path.open("rb") as fh:
        chunk = fh.read(_MANIFEST_HASH_MAX_BYTES)
        hasher.update(chunk)
    return hasher.digest()[:16]


def _decode_plaintext(raw_bytes: bytes, path: Path) -> str:
    """Decodifica plaintext con cascade UTF-8 → cp1252 → latin-1.

    Loga il fallback scelto a livello warning, perché tipicamente segnala
    file Windows italiani salvati senza dichiarare l'encoding.
    """
    try:
        return raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        pass
    try:
        text = raw_bytes.decode("cp1252")
        logger.warning("⚠️  fallback encoding cp1252 su %s", path)
        return text
    except UnicodeDecodeError:
        pass
    # latin-1 non solleva mai: ultima rete di sicurezza.
    text = raw_bytes.decode("latin-1")
    logger.warning("⚠️  fallback encoding latin-1 su %s", path)
    return text


class FilesystemConnector:
    """Connettore per filesystem locale o mount POSIX.

    Esempio d'uso::

        connector = FilesystemConnector(
            root_path=Path("/clienti/acme/dump"),
            exclude_patterns=["*.bak"],
            max_file_size_mb=50,
        )
        for doc in connector.iter_documents():
            store.add_document(...)
    """

    name = "filesystem"

    def __init__(
        self,
        root_path: Path,
        *,
        exclude_patterns: list[str] | None = None,
        max_file_size_mb: int = 50,
        follow_symlinks: bool = False,
        allow_dangerous_root: bool = False,
        parser_workers: int | None = None,
        smart_excludes: bool = True,
        state_store: "StateStore | None" = None,
        manifest_run_id: int | None = None,
        force_rescan: bool = False,
    ) -> None:
        """
        Args:
            root_path: directory radice da scansionare ricorsivamente.
            exclude_patterns: pattern glob aggiuntivi rispetto ai default.
                I default (``.git``, ``__pycache__``, ``~$*`` …) vengono
                sempre uniti a quelli passati.
            max_file_size_mb: soglia oltre la quale i file vengono skippati
                con warning loggato. Default 50 MB.
            follow_symlinks: se ``False`` (default) i symlink NON sono seguiti
                (difesa contro loop e escape). Se ``True`` vengono seguiti, ma
                ogni file viene verificato con canonicalizzazione: i path che
                risolvono fuori da ``root_path`` sono skippati.
            allow_dangerous_root: bypassa il guardrail su root path troppo
                permissivi (``/``, ``$HOME``, ``/etc`` …). Default ``False``:
                proteggere il consulente da scansioni accidentali dell'intero
                filesystem. Se ``True``, l'utente si assume la responsabilità.
            parser_workers: numero di worker thread del ``ParserPool``. Se
                ``None`` (default) viene calcolato da ``_default_max_workers``
                (env ``CUSTODIA_PARSER_WORKERS`` o ``cpu_count - 1``).
            smart_excludes: se ``True`` (default), applica
                ``_SMART_EXCLUDES_EXTENDED`` (node_modules/, dist/, build/,
                .Trash/, *.photoslibrary/, lock files, ecc.) in aggiunta ai
                ``_DEFAULT_EXCLUDES``. Settabile a ``False`` per scan
                "permissive" da debug.

        Raises:
            FileNotFoundError: ``root_path`` non esiste.
            NotADirectoryError: ``root_path`` esiste ma non è una directory.
            ValueError: ``root_path`` è uno dei dangerous root e
                ``allow_dangerous_root`` è ``False``.
        """
        resolved = root_path.expanduser().resolve()

        # Validazione esistenza + tipo (deve essere directory esistente).
        if not resolved.exists():
            raise FileNotFoundError(
                f"root_path inesistente: {resolved}"
            )
        if not resolved.is_dir():
            raise NotADirectoryError(
                f"root_path non è una directory: {resolved}"
            )

        # Guardrail su root pericolosi.
        if not allow_dangerous_root and resolved in _dangerous_root_paths():
            raise ValueError(
                f"Root path '{resolved}' troppo permissivo. "
                "Indica una sottocartella specifica del cliente "
                "oppure passa allow_dangerous_root=True per forzare."
            )

        self.root_path = resolved
        self.follow_symlinks = follow_symlinks
        self.exclude_patterns = list(_DEFAULT_EXCLUDES)
        if smart_excludes:
            self.exclude_patterns.extend(_SMART_EXCLUDES_EXTENDED)
        if exclude_patterns:
            self.exclude_patterns.extend(exclude_patterns)
        self.smart_excludes = smart_excludes
        self.max_file_size_bytes = max_file_size_mb * 1024 * 1024
        self._parser_workers = parser_workers
        # Manifest: lo state_store è opzionale per backward compat coi test
        # esistenti che istanziano il connector senza store. Se assente,
        # l'incremental skip è disabilitato (= comportamento pre-U2).
        self._state_store: StateStore | None = state_store
        self.manifest_run_id: int | None = manifest_run_id
        self.force_rescan: bool = force_rescan
        self._stats: dict[str, int] = {
            "processed": 0,
            "skipped_excluded": 0,
            "skipped_size": 0,
            "skipped_ext": 0,
            "skipped_unknown": 0,
            "skipped_escape": 0,
            "skipped_magic_mismatch": 0,
            "skipped_unchanged": 0,
            "renamed_detected": 0,
            "errors": 0,
        }

    # ------------------------------------------------------------------
    # API Connector
    # ------------------------------------------------------------------

    def iter_documents(self) -> Iterator[SourceDocument]:
        """Itera tutti i file supportati sotto ``root_path``.

        Usa ``os.walk(followlinks=self.follow_symlinks)`` con ``onerror``
        callback che logga e continua, evitando loop su symlink e crash su
        permessi negati di sottocartelle.

        Strategia U3:
        - Fase 1 (sequenziale): walk + filter + plaintext inline yield;
          i path binari (PDF/DOCX/XLSX) vengono accumulati in batch.
        - Fase 2 (parallelo): ogni batch viene sottomesso al ``ParserPool``
          e i ``SourceDocument`` sono yielded appena pronti (ordine non
          deterministico all'interno del batch).
        """

        def _on_walk_error(exc: OSError) -> None:
            logger.warning("⚠️  errore traversal (continuo): %s", exc)
            self._stats["errors"] += 1

        # Batch size: trade-off fra parallelismo (pool saturo) e memoria
        # (i risultati attendono il yield del batch corrente). 50 = ~50
        # PDF in memoria max → ~50MB testo nel peggior caso.
        BATCH_SIZE = 50
        pending_binary: list[tuple[Path, dict[str, Any], str, str]] = []

        def _flush_batch() -> Iterator[SourceDocument]:
            """Drena ``pending_binary`` attraverso il ``ParserPool``."""
            if not pending_binary:
                return
            paths_only = [item[0] for item in pending_binary]
            # Lookup metadata-precomputato per ricostruire il SourceDocument
            # appena il pool ritorna il testo per quel path.
            by_path = {item[0]: item[1:] for item in pending_binary}

            with ParserPool(max_workers=self._parser_workers) as pool:
                for path, result in pool.parse_batch(paths_only):
                    metadata, relative_path, source_id = by_path[path]
                    parse_failed = isinstance(result, Exception)
                    if parse_failed:
                        logger.warning(
                            "⚠️  parser error su %s: %s", path, result
                        )
                        self._stats["errors"] += 1
                        metadata = {
                            **metadata,
                            "parser_error": str(result),
                        }
                        text = ""
                    else:
                        text = result
                    self._stats["processed"] += 1
                    canonical_mime = metadata.get(
                        "_canonical_mime", "application/octet-stream"
                    )
                    # Manifest update solo per parse riusciti: file mascherato
                    # o corrotto NON deve finire come "visto" nel manifest,
                    # così che un rerun ritenti.
                    if not parse_failed:
                        self._manifest_record_processed(
                            source_id=source_id,
                            content_hash=metadata.get("_manifest_content_hash"),
                            modified_iso=metadata.get(
                                "_manifest_modified_iso"
                            ),
                            size_bytes=metadata.get("size_bytes", 0),
                            path=path,
                        )
                    yield SourceDocument(
                        source_id=source_id,
                        source_path=relative_path,
                        mime_type=canonical_mime,
                        text=text,
                        metadata={
                            k: v for k, v in metadata.items()
                            if not k.startswith("_")
                        },
                    )
            pending_binary.clear()

        for dirpath, dirnames, filenames in os.walk(
            self.root_path,
            followlinks=self.follow_symlinks,
            onerror=_on_walk_error,
        ):
            # Pruning delle sottocartelle escluse: evita di entrarci proprio.
            # Modifichiamo ``dirnames`` in-place come previsto da os.walk.
            pruned: list[str] = []
            for d in dirnames:
                sub = Path(dirpath) / d
                if _path_matches_any(sub, self.exclude_patterns, self.root_path):
                    self._stats["skipped_excluded"] += 1
                    logger.debug("⏭️  skip excluded dir: %s", sub)
                    continue
                if _is_under_excluded_library_subdir(sub):
                    self._stats["skipped_excluded"] += 1
                    logger.debug("⏭️  skip Library system subdir: %s", sub)
                    continue
                pruned.append(d)
            dirnames[:] = pruned

            for fname in filenames:
                path = Path(dirpath) / fname
                outcome = self._prepare_path(path)
                if outcome is None:
                    continue
                kind, payload = outcome
                if kind == "doc":
                    yield payload  # type: ignore[misc]
                else:
                    # ("binary", (path, metadata, relative_path, source_id))
                    pending_binary.append(payload)  # type: ignore[arg-type]
                    if len(pending_binary) >= BATCH_SIZE:
                        yield from _flush_batch()

        # Drain finale.
        yield from _flush_batch()

    @property
    def stats(self) -> dict[str, int]:
        """Counter osservabilità: processed/skipped_*/errors."""
        return dict(self._stats)

    def _manifest_record_processed(
        self,
        *,
        source_id: str,
        content_hash: bytes | None,
        modified_iso: str | None,
        size_bytes: int,
        path: Path,
    ) -> None:
        """Aggiorna il manifest dopo un parsing riuscito.

        No-op se ``state_store`` è None (modalità senza manifest), oppure se
        non abbiamo potuto calcolare ``content_hash``/``modified_iso``
        (parsing best-effort: meglio non sporcare il manifest con dati parziali
        che farebbero saltare il prossimo rerun unchanged-check).
        """
        if (
            self._state_store is None
            or content_hash is None
            or modified_iso is None
        ):
            return
        try:
            self._state_store.manifest_upsert(
                connector_name=self.name,
                source_id=source_id,
                content_hash_sha1_16=content_hash,
                mtime_iso=modified_iso,
                file_size=size_bytes,
                run_id=self.manifest_run_id,
            )
        except Exception as exc:  # noqa: BLE001 — non blocchiamo lo scan
            logger.warning("⚠️  manifest upsert fallito su %s: %s", path, exc)

    # ------------------------------------------------------------------
    # Processing singolo path
    # ------------------------------------------------------------------

    def _prepare_path(
        self, path: Path
    ) -> tuple[str, Any] | None:
        """Pre-elabora un path e decide come gestirlo.

        Returns:
            ``None`` se il path va scartato.
            ``("doc", SourceDocument)`` se è gestibile inline (plaintext o
            parser-error con metadati pronti).
            ``("binary", (path, metadata, relative_path, source_id))`` se va
            sottomesso al ``ParserPool`` per estrazione testo asincrona.
        """
        # Exclude pattern (su filename o componenti intermedi).
        if _path_matches_any(path, self.exclude_patterns, self.root_path):
            self._stats["skipped_excluded"] += 1
            logger.debug("⏭️  skip excluded: %s", path)
            return None
        # macOS Library: skip sottocartelle di sistema (Caches, Logs, etc.)
        # ma NON ``Library`` da sola (può contenere Mail/Calendars).
        if _is_under_excluded_library_subdir(path):
            self._stats["skipped_excluded"] += 1
            logger.debug("⏭️  skip Library system subdir file: %s", path)
            return None

        # Difesa anti symlink-escape: canonicalizza e verifica contenimento
        # in root. Applichiamo SEMPRE, anche quando follow_symlinks=False, per
        # gestire i casi limite (junction Windows, bind-mount).
        try:
            resolved = path.resolve()
        except (OSError, RuntimeError) as exc:
            logger.warning("⚠️  resolve fallito su %s: %s", path, exc)
            self._stats["errors"] += 1
            return None
        try:
            resolved.relative_to(self.root_path)
        except ValueError:
            logger.warning(
                "⚠️  skip path che esce dalla root via symlink/junction: %s → %s",
                path,
                resolved,
            )
            self._stats["skipped_escape"] += 1
            return None

        # Stat per size + mtime. Catch permission errors. ``follow_symlinks``
        # qui agisce sul singolo stat: di default NON seguiamo (lo skip è
        # gestito dal ``os.walk(followlinks=False)``).
        try:
            stat = path.stat()
        except PermissionError as exc:
            logger.warning("⚠️  permission denied su %s: %s", path, exc)
            self._stats["errors"] += 1
            return None
        except OSError as exc:
            logger.warning("⚠️  stat fallita su %s: %s", path, exc)
            self._stats["errors"] += 1
            return None

        # Verifica che sia un file regolare (no dir, no symlink → dir, no FIFO).
        try:
            if not path.is_file():
                return None
        except OSError as exc:
            logger.warning("⚠️  is_file fallita su %s: %s", path, exc)
            self._stats["errors"] += 1
            return None

        size_bytes = stat.st_size
        if size_bytes > self.max_file_size_bytes:
            self._stats["skipped_size"] += 1
            logger.warning(
                "⚠️  skip file >%dMB (%.1fMB): %s",
                self.max_file_size_bytes // (1024 * 1024),
                size_bytes / 1024 / 1024,
                path,
            )
            return None

        ext = path.suffix.lower()

        # Estensioni esplicitamente skippate (mediali/archivi).
        if ext in _SKIP_EXTENSIONS:
            self._stats["skipped_ext"] += 1
            logger.debug("⏭️  skip ext mediale/archivio (%s): %s", ext, path)
            return None

        absolute_path = str(resolved)
        try:
            relative_path = str(path.relative_to(self.root_path))
        except ValueError:
            # Fallback: prova a calcolare la relativa dal resolved
            try:
                relative_path = str(resolved.relative_to(self.root_path))
            except ValueError:
                relative_path = path.name

        mime_type, _ = mimetypes.guess_type(absolute_path)
        if mime_type is None:
            mime_type = "application/octet-stream"

        # modified_time tollerante a timestamp fuori range (es. file con mtime
        # corrotto da metadata import). Fallback a None.
        modified_iso: str | None = None
        try:
            modified_iso = datetime.fromtimestamp(
                stat.st_mtime, tz=timezone.utc
            ).isoformat()
        except (OverflowError, OSError, ValueError) as exc:
            logger.warning(
                "⚠️  mtime fuori range su %s (raw=%r): %s — fallback a None",
                path,
                stat.st_mtime,
                exc,
            )
            modified_iso = None

        metadata: dict[str, Any] = {
            "absolute_path": absolute_path,
            "size_bytes": size_bytes,
            "modified_time": modified_iso,
            "extension": ext,
        }

        source_id = f"fs:{_sha1_path(absolute_path)}"

        # ----- Manifest pre-check (Sprint 2a, U2) -----
        # Step 1: lookup by source_id. Se entry esiste e (mtime, size) coincide
        # → unchanged: skippa parsing e ritorna None. Aggiorniamo comunque
        # ``last_seen_at`` per tracciare "visto in questo run".
        manifest_entry: dict[str, Any] | None = None
        content_hash: bytes | None = None
        if (
            self._state_store is not None
            and not self.force_rescan
            and modified_iso is not None
        ):
            manifest_entry = self._state_store.manifest_lookup_by_source(
                self.name, source_id
            )
            if (
                manifest_entry is not None
                and manifest_entry["mtime_iso"] == modified_iso
                and manifest_entry["file_size"] == size_bytes
            ):
                # Unchanged. Refresh manifest (last_seen_at + run_id) e skippa.
                try:
                    self._state_store.manifest_upsert(
                        connector_name=self.name,
                        source_id=source_id,
                        content_hash_sha1_16=manifest_entry["content_hash"],
                        mtime_iso=modified_iso,
                        file_size=size_bytes,
                        run_id=self.manifest_run_id,
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "⚠️  manifest refresh fallito su %s: %s", path, exc
                    )
                self._stats["skipped_unchanged"] += 1
                logger.debug("⏭️  skip unchanged (manifest): %s", path)
                return None

            # Step 2: compute content hash per detection rinomine/spostamenti.
            # Solo se manifest abilitato e file non skippato come unchanged.
            try:
                content_hash = _compute_content_hash(path)
            except (OSError, PermissionError) as exc:
                logger.warning(
                    "⚠️  hash content fallito su %s: %s", path, exc
                )
                # Procedi senza manifest update: il parsing classico continuerà.
                content_hash = None

            if content_hash is not None:
                # Lookup by hash: se stesso content è già in manifest con un
                # source_id DIVERSO, è un file rinominato/spostato. Riusiamo
                # quel source_id come canonical per evitare doppione in
                # ``documents`` (che è UNIQUE su source_id).
                hash_match = self._state_store.manifest_lookup_by_hash(
                    self.name, content_hash
                )
                if (
                    hash_match is not None
                    and hash_match["source_id"] != source_id
                ):
                    logger.info(
                        "ℹ️  rename/move detected: %s → riusa source_id=%s",
                        path,
                        hash_match["source_id"],
                    )
                    self._stats["renamed_detected"] += 1
                    source_id = hash_match["source_id"]

        # Espone content_hash al post-parse update (vedi iter_documents per
        # i binari, e routing inline per i plaintext).
        metadata["_manifest_content_hash"] = content_hash
        metadata["_manifest_modified_iso"] = modified_iso

        # Routing: parser binario (deferred al pool), plaintext (inline),
        # oppure skip sconosciuto.
        if ext in _BINARY_PARSER_BY_EXT:
            # Magic-bytes prefilter: se l'estensione promette PDF/DOCX/XLSX
            # ma i magic bytes dicono "altro", skip con counter dedicato.
            # Evita di lanciare il parser su file mascherati (= spreco CPU)
            # e ci protegge da estensioni "ingannevoli" (.pdf che è testo).
            if not mime_matches_extension(path):
                self._stats["skipped_magic_mismatch"] += 1
                logger.warning(
                    "⚠️  skip %s: magic bytes non coerenti con estensione",
                    path,
                )
                return None
            # Mime canonico per i tipi parsati (lo applichiamo qui per averlo
            # disponibile quando il pool ritorna il testo).
            canonical_mime = mime_type
            if ext == ".pdf":
                canonical_mime = "application/pdf"
            elif ext == ".docx":
                canonical_mime = (
                    "application/vnd.openxmlformats-officedocument."
                    "wordprocessingml.document"
                )
            elif ext == ".xlsx":
                canonical_mime = (
                    "application/vnd.openxmlformats-officedocument."
                    "spreadsheetml.sheet"
                )
            metadata["_canonical_mime"] = canonical_mime
            return (
                "binary",
                (path, metadata, relative_path, source_id),
            )

        if ext in _PLAINTEXT_EXTENSIONS:
            try:
                raw = path.read_bytes()
                text = _decode_plaintext(raw, path)
                if mime_type == "application/octet-stream":
                    # Forziamo text/plain per estensioni testuali.
                    mime_type = "text/plain"
            except PermissionError as exc:
                logger.warning("⚠️  permission denied leggendo %s: %s", path, exc)
                self._stats["errors"] += 1
                return None
            except OSError as exc:
                logger.warning("⚠️  read fallita su %s: %s", path, exc)
                self._stats["errors"] += 1
                return None

            self._stats["processed"] += 1
            # Manifest update post-parse plaintext (Sprint 2a, U2).
            self._manifest_record_processed(
                source_id=source_id,
                content_hash=content_hash,
                modified_iso=modified_iso,
                size_bytes=size_bytes,
                path=path,
            )
            return (
                "doc",
                SourceDocument(
                    source_id=source_id,
                    source_path=relative_path,
                    mime_type=mime_type,
                    text=text,
                    metadata={
                        k: v for k, v in metadata.items()
                        if not k.startswith("_")
                    },
                ),
            )

        # Estensione sconosciuta / non gestita: skip con debug (non warning).
        self._stats["skipped_unknown"] += 1
        logger.debug("⏭️  skip ext sconosciuta (%s): %s", ext, path)
        return None


__all__ = [
    "FilesystemConnector",
    "_DEFAULT_EXCLUDES",
    "_dangerous_root_paths",
]
