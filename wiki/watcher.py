"""File watcher per la `_inbox/` del cliente.

Usa ``watchdog`` per intercettare `on_created` e `on_modified`, applica un
debounce per evitare il doppio trigger tipico degli editor che fanno
write-temp + rename, e chiama :func:`wiki.pipeline.run_pipeline_for_file` su
ogni file stabilizzato.

Robustezza:
  * Debounce per path (2s default).
  * Graceful shutdown su SIGINT/SIGTERM.
  * Health check: scrive `_status/watcher.pid` (PID + timestamp), aggiornato
    ogni 60s da un thread di heartbeat.
  * Idempotenza delegata al pipeline (skip se sha già visto).
  * Backoff + retry: se il pipeline crasha su un file, il watcher aspetta
    ``retry_backoff_s`` secondi e ritenta fino a ``max_retries`` volte.
    Al superamento del limite, il file viene copiato in
    ``_status/dead-letter/<sha12>/`` insieme a un ``error.log`` (DLQ).
  * Logging strutturato: ``log_format="json"`` produce una riga JSON per
    evento, comoda da ingestare in osservabilità (loki/elastic) quando il
    watcher gira su una macchina del cliente; default ``text``.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import signal
import threading
import time
import traceback
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from wiki.pipeline import run_pipeline_for_file

logger = logging.getLogger(__name__)


# Tipo del callback usato dal handler. Default: pipeline reale; nei test si
# inietta una funzione mock che registra le chiamate.
PipelineCallback = Callable[[Path, dict[str, Any], Path], Any]


# --- logging strutturato --------------------------------------------------


class _JsonFormatter(logging.Formatter):
    """Formatter che serializza i log come una riga JSON.

    Include i campi standard (ts, level, logger, msg) + tutti gli ``extra``
    passati al record (``logger.info(..., extra={"path": "..."})``).
    """

    _RESERVED = {
        "name",
        "msg",
        "args",
        "levelname",
        "levelno",
        "pathname",
        "filename",
        "module",
        "exc_info",
        "exc_text",
        "stack_info",
        "lineno",
        "funcName",
        "created",
        "msecs",
        "relativeCreated",
        "thread",
        "threadName",
        "processName",
        "process",
        "message",
        "taskName",
    }

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        # Aggiungi campi `extra` non-standard
        for key, value in record.__dict__.items():
            if key in self._RESERVED or key.startswith("_"):
                continue
            try:
                json.dumps(value)
            except (TypeError, ValueError):
                value = repr(value)
            payload[key] = value
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(log_format: str = "text", level: int = logging.INFO) -> None:
    """Configura il root logger per il watcher.

    Args:
        log_format: ``text`` (default) o ``json``.
        level: livello minimo di logging.

    Idempotente sull'handler del root logger del modulo ``wiki``: rimuove
    handler precedenti per evitare doppia stampa.
    """
    fmt = log_format.lower()
    if fmt not in {"text", "json"}:
        raise ValueError(f"log_format sconosciuto: {log_format!r}. Usa 'text' o 'json'.")
    root = logging.getLogger()
    # Rimuove eventuali handler già installati (es. da un precedente
    # ``configure_logging``), per non duplicare l'output.
    for h in list(root.handlers):
        root.removeHandler(h)
    handler = logging.StreamHandler()
    if fmt == "json":
        handler.setFormatter(_JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s %(name)s: %(message)s",
                datefmt="%H:%M:%S",
            )
        )
    root.addHandler(handler)
    root.setLevel(level)


# ----- handler con debounce ----------------------------------------------


@dataclass
class _DebounceState:
    """Stato per file (path → ultimo evento) usato dal handler."""

    last_seen: dict[str, float] = field(default_factory=dict)
    lock: threading.Lock = field(default_factory=threading.Lock)

    def should_process(self, path: str, debounce_s: float) -> bool:
        """True se è passato più di ``debounce_s`` dall'ultimo trigger su ``path``."""
        now = time.monotonic()
        with self.lock:
            last = self.last_seen.get(path, 0.0)
            if now - last < debounce_s:
                return False
            self.last_seen[path] = now
            return True


# ----- dead-letter queue --------------------------------------------------


def _sha12_for_path(path: Path) -> str:
    """SHA dei primi 256KB del file: identifica univocamente il payload nella DLQ.

    Non usiamo l'hash completo del file (che per DLQ può essere troppo costoso
    su file grandi). Per la deduplicazione delle DLQ basta una firma "buona
    abbastanza"; in ogni caso il path resta nel manifest.
    """
    h = hashlib.sha256()
    try:
        with path.open("rb") as f:
            chunk = f.read(256 * 1024)
            h.update(chunk)
    except OSError:
        # Se non posso leggere, hash del path stesso (deterministico).
        h.update(str(path).encode("utf-8"))
    h.update(str(path).encode("utf-8"))
    return h.hexdigest()[:12]


def _write_dead_letter(
    state_dir: Path,
    file_path: Path,
    attempts: int,
    last_error: BaseException,
) -> Path:
    """Copia il file nella DLQ e scrive un ``error.log`` con stacktrace e meta.

    Ritorna la cartella della DLQ creata.
    """
    sha12 = _sha12_for_path(file_path)
    dlq_dir = state_dir / "dead-letter" / sha12
    dlq_dir.mkdir(parents=True, exist_ok=True)
    # Salvataggio del file originale (best-effort).
    try:
        shutil.copy2(file_path, dlq_dir / file_path.name)
    except OSError as exc:
        # Logga, ma scrivi comunque l'error.log per non perdere info.
        logger.warning(
            "DLQ: impossibile copiare %s in %s: %s",
            file_path,
            dlq_dir,
            exc,
            extra={"path": str(file_path), "dlq": str(dlq_dir)},
        )
    # Stacktrace + meta.
    tb = "".join(traceback.format_exception(type(last_error), last_error, last_error.__traceback__))
    manifest = {
        "ts": datetime.now(UTC).isoformat(),
        "original_path": str(file_path),
        "attempts": attempts,
        "error_type": type(last_error).__name__,
        "error": str(last_error),
    }
    (dlq_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (dlq_dir / "error.log").write_text(tb, encoding="utf-8")
    return dlq_dir


# ----- handler -----------------------------------------------------------


class InboxHandler(FileSystemEventHandler):
    """Handler watchdog che invoca il pipeline su create/modify, con debounce.

    Robustezza ulteriore (Step 3 hardening):
      * Retry con backoff sulle eccezioni del pipeline (default 3 tentativi,
        5s di pausa fra uno e l'altro).
      * Al superamento del limite, il file viene messo in
        ``_status/dead-letter/<sha12>/``.
    """

    def __init__(
        self,
        *,
        config: dict[str, Any],
        state_dir: Path,
        pipeline: PipelineCallback,
        debounce_s: float = 2.0,
        max_retries: int = 3,
        retry_backoff_s: float = 5.0,
    ) -> None:
        super().__init__()
        self.config = config
        self.state_dir = state_dir
        self.pipeline = pipeline
        self.debounce_s = debounce_s
        self.max_retries = max_retries
        self.retry_backoff_s = retry_backoff_s
        self._state = _DebounceState()

    # ----- dispatch ------------------------------------------------------

    def _run_with_retries(self, path: Path) -> None:
        """Invoca il pipeline e ritenta in caso di eccezione, con backoff.

        Numero massimo di tentativi: ``self.max_retries`` (inclusi i retry).
        Se tutti falliscono, il file finisce nella DLQ.
        """
        attempts = 0
        last_exc: BaseException | None = None
        while attempts < self.max_retries:
            attempts += 1
            try:
                self.pipeline(path, self.config, self.state_dir)
                if attempts > 1:
                    logger.info(
                        "Pipeline OK al tentativo %d/%d su %s",
                        attempts,
                        self.max_retries,
                        path.name,
                        extra={"path": str(path), "attempts": attempts},
                    )
                return
            except Exception as exc:  # pragma: no cover - difensivo
                last_exc = exc
                logger.warning(
                    "Pipeline fallita (tentativo %d/%d) su %s: %s",
                    attempts,
                    self.max_retries,
                    path,
                    exc,
                    extra={
                        "path": str(path),
                        "attempts": attempts,
                        "error_type": type(exc).__name__,
                    },
                )
                if attempts < self.max_retries:
                    time.sleep(self.retry_backoff_s)
        # Esauriti i tentativi: dead-letter.
        if last_exc is not None:
            try:
                dlq_dir = _write_dead_letter(self.state_dir, path, attempts, last_exc)
                logger.error(
                    "Dead-letter: %s archiviato in %s dopo %d tentativi",
                    path,
                    dlq_dir,
                    attempts,
                    extra={"path": str(path), "dlq": str(dlq_dir), "attempts": attempts},
                )
            except OSError as exc:  # pragma: no cover - difensivo
                logger.exception(
                    "Impossibile scrivere DLQ per %s: %s",
                    path,
                    exc,
                    extra={"path": str(path)},
                )

    def _dispatch(self, src_path: str) -> None:
        path = Path(src_path)
        if not path.exists() or not path.is_file():
            return
        # Ignora i tipici "file di lavoro" degli editor.
        name = path.name
        if name.startswith(".") or name.endswith("~") or name.endswith(".swp"):
            return
        if not self._state.should_process(src_path, self.debounce_s):
            logger.debug("Debounce: ignoro %s", src_path, extra={"path": src_path})
            return
        logger.info("Pipeline su %s", path.name, extra={"path": str(path)})
        self._run_with_retries(path)

    # ----- eventi watchdog -----------------------------------------------

    def on_created(self, event: FileSystemEvent) -> None:  # type: ignore[override]
        if event.is_directory:
            return
        self._dispatch(event.src_path)

    def on_modified(self, event: FileSystemEvent) -> None:  # type: ignore[override]
        if event.is_directory:
            return
        self._dispatch(event.src_path)


# ----- health check ------------------------------------------------------


def _write_pidfile(state_dir: Path) -> Path:
    """Scrive `_status/watcher.pid` con PID + timestamp ISO."""
    state_dir.mkdir(parents=True, exist_ok=True)
    pid_path = state_dir / "watcher.pid"
    pid_path.write_text(
        f"{os.getpid()}\n{datetime.now(UTC).isoformat()}\n",
        encoding="utf-8",
    )
    return pid_path


def _heartbeat_loop(state_dir: Path, stop_event: threading.Event, period_s: float = 60.0) -> None:
    """Thread che ri-scrive il pidfile periodicamente fino a stop_event."""
    while not stop_event.is_set():
        try:
            _write_pidfile(state_dir)
        except OSError as exc:  # pragma: no cover - difensivo
            logger.warning("Heartbeat scrittura pidfile fallita: %s", exc)
        stop_event.wait(period_s)


# ----- API principale ----------------------------------------------------


def start_watcher(
    inbox_dir: Path,
    config: dict[str, Any],
    state_dir: Path,
    *,
    pipeline: PipelineCallback | None = None,
    debounce_s: float = 2.0,
    heartbeat_s: float = 60.0,
    install_signal_handlers: bool = True,
    block: bool = True,
    max_retries: int = 3,
    retry_backoff_s: float = 5.0,
    log_format: str | None = None,
) -> Observer:
    """Avvia il watcher sulla `_inbox/<cliente>/`.

    Parametri:
      * ``inbox_dir``: directory da osservare (creata se non esiste).
      * ``config``: dict di config cliente (passato al pipeline).
      * ``state_dir``: path a `_status/` (per pidfile, drafts, DLQ ecc.).
      * ``pipeline``: override per i test. Default: pipeline reale.
      * ``block``: se True, attende SIGINT/SIGTERM. Se False, ritorna subito
        l'Observer (utile nei test per chiamare ``stop()`` manualmente).
      * ``max_retries``: tentativi totali (incluso il primo) prima di mandare
        il file in DLQ. Default 3.
      * ``retry_backoff_s``: pausa fra un tentativo e il successivo. Default 5s.
      * ``log_format``: se valorizzato (``"text"`` o ``"json"``), riconfigura
        il root logger con quel formato. Se ``None`` lascia inalterata la
        config corrente (utile da test per non interferire con caplog).

    Ritorna l'Observer (utile soprattutto in modalità non-blocking).
    """
    if log_format is not None:
        configure_logging(log_format)

    inbox_dir.mkdir(parents=True, exist_ok=True)
    state_dir.mkdir(parents=True, exist_ok=True)

    handler = InboxHandler(
        config=config,
        state_dir=state_dir,
        pipeline=pipeline or run_pipeline_for_file,
        debounce_s=debounce_s,
        max_retries=max_retries,
        retry_backoff_s=retry_backoff_s,
    )
    observer = Observer()
    observer.schedule(handler, str(inbox_dir), recursive=True)
    observer.start()
    logger.info(
        "Watcher avviato su %s (debounce=%.1fs, retries=%d)",
        inbox_dir,
        debounce_s,
        max_retries,
        extra={
            "inbox": str(inbox_dir),
            "debounce_s": debounce_s,
            "max_retries": max_retries,
        },
    )

    # Heartbeat in thread separato
    stop_event = threading.Event()
    heartbeat = threading.Thread(
        target=_heartbeat_loop,
        args=(state_dir, stop_event, heartbeat_s),
        name="wiki-watcher-heartbeat",
        daemon=True,
    )
    heartbeat.start()
    _write_pidfile(state_dir)

    def _shutdown(signum: int | None = None, frame: Any | None = None) -> None:
        logger.info("Watcher: shutdown richiesto (signal=%s)", signum)
        stop_event.set()
        observer.stop()

    if install_signal_handlers:
        try:
            signal.signal(signal.SIGINT, _shutdown)
            signal.signal(signal.SIGTERM, _shutdown)
        except (ValueError, OSError):  # pragma: no cover - thread non-main
            logger.debug("Signal handler non installabile (non-main thread)")

    if not block:
        return observer

    try:
        while observer.is_alive():
            observer.join(timeout=1.0)
    except KeyboardInterrupt:  # pragma: no cover - segnali coperti sopra
        _shutdown(signal.SIGINT)
    finally:
        stop_event.set()
        observer.stop()
        observer.join()
        # Pulizia pidfile alla fine: indica che il watcher non è più attivo.
        pid_path = state_dir / "watcher.pid"
        if pid_path.exists():
            try:
                pid_path.unlink()
            except OSError:  # pragma: no cover
                pass

    return observer
