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
  * Eccezioni nel pipeline catturate e loggate, mai propagate (il watcher
    non deve mai morire per un singolo file rotto).
"""
from __future__ import annotations

import logging
import os
import signal
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from wiki.pipeline import run_pipeline_for_file

logger = logging.getLogger(__name__)


# Tipo del callback usato dal handler. Default: pipeline reale; nei test si
# inietta una funzione mock che registra le chiamate.
PipelineCallback = Callable[[Path, dict[str, Any], Path], Any]


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


class InboxHandler(FileSystemEventHandler):
    """Handler watchdog che invoca il pipeline su create/modify, con debounce."""

    def __init__(
        self,
        *,
        config: dict[str, Any],
        state_dir: Path,
        pipeline: PipelineCallback,
        debounce_s: float = 2.0,
    ) -> None:
        super().__init__()
        self.config = config
        self.state_dir = state_dir
        self.pipeline = pipeline
        self.debounce_s = debounce_s
        self._state = _DebounceState()

    # ----- dispatch ------------------------------------------------------

    def _dispatch(self, src_path: str) -> None:
        path = Path(src_path)
        if not path.exists() or not path.is_file():
            return
        # Ignora i tipici "file di lavoro" degli editor.
        name = path.name
        if name.startswith(".") or name.endswith("~") or name.endswith(".swp"):
            return
        if not self._state.should_process(src_path, self.debounce_s):
            logger.debug("Debounce: ignoro %s", src_path)
            return
        logger.info("Pipeline su %s", path.name)
        try:
            self.pipeline(path, self.config, self.state_dir)
        except Exception as exc:  # pragma: no cover - difensivo
            logger.exception("Pipeline fallita su %s: %s", path, exc)

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
        f"{os.getpid()}\n{datetime.now(timezone.utc).isoformat()}\n",
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
) -> Observer:
    """Avvia il watcher sulla `_inbox/<cliente>/`.

    Parametri:
      * ``inbox_dir``: directory da osservare (creata se non esiste).
      * ``config``: dict di config cliente (passato al pipeline).
      * ``state_dir``: path a `_status/` (per pidfile, drafts, ecc.).
      * ``pipeline``: override per i test. Default: pipeline reale.
      * ``block``: se True, attende SIGINT/SIGTERM. Se False, ritorna subito
        l'Observer (utile nei test per chiamare ``stop()`` manualmente).

    Ritorna l'Observer (utile soprattutto in modalità non-blocking).
    """
    inbox_dir.mkdir(parents=True, exist_ok=True)
    state_dir.mkdir(parents=True, exist_ok=True)

    handler = InboxHandler(
        config=config,
        state_dir=state_dir,
        pipeline=pipeline or run_pipeline_for_file,
        debounce_s=debounce_s,
    )
    observer = Observer()
    observer.schedule(handler, str(inbox_dir), recursive=True)
    observer.start()
    logger.info("Watcher avviato su %s (debounce=%.1fs)", inbox_dir, debounce_s)

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
