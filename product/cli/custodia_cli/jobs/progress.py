"""
ProgressReporter: invia snapshot di progresso al :class:`StateStore` con
coalescing temporale.

Motivazione: SAM scan / build possono emettere update molto frequenti (uno per
file). Scrivere ogni update sul DB sarebbe costoso e inutile per la UI, che
campiona via polling. Quindi accodiamo l'ultimo snapshot e scriviamo al massimo
ogni ``min_interval_ms`` (default 200ms). Il metodo :meth:`flush` forza la
scrittura immediata, indispensabile alla fine del job per chiudere la corsa
con lo snapshot finale.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any

from custodia_cli.state.store import StateStore


@dataclass
class ProgressSnapshot:
    """Snapshot dello stato corrente di un job.

    Campi tutti opzionali tranne ``status``: il reporter accetta qualsiasi
    livello di dettaglio. Serializzato in JSON nel campo
    ``runs.progress_json``.
    """

    status: str  # "running" | "success" | "error" | "cancelled" | "interrupted"
    current: int = 0
    total: int | None = None
    current_item: str | None = None
    throughput_per_sec: float = 0.0
    eta_seconds: float | None = None
    skipped: dict[str, int] = field(default_factory=dict)
    errors: int = 0
    extra: dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        """Converte in dict serializzabile per il DB."""
        return {
            "status": self.status,
            "current": self.current,
            "total": self.total,
            "current_item": self.current_item,
            "throughput_per_sec": self.throughput_per_sec,
            "eta_seconds": self.eta_seconds,
            "skipped": dict(self.skipped),
            "errors": self.errors,
            "extra": dict(self.extra),
        }


class ProgressReporter:
    """Riporta progresso al :class:`StateStore` con coalescing.

    Thread-safe: può essere chiamato dal worker thread mentre il main thread
    legge tramite :meth:`StateStore.get_run_progress`.
    """

    def __init__(
        self,
        store: StateStore,
        run_id: int,
        *,
        min_interval_ms: int = 200,
    ) -> None:
        self._store = store
        self._run_id = run_id
        self._min_interval_s = min_interval_ms / 1000.0
        self._last_write_at: float = 0.0
        self._force_next: bool = False
        self._lock = threading.Lock()

    def update(self, snapshot: ProgressSnapshot) -> None:
        """Aggiorna lo snapshot.

        Scrive nel DB solo se è passato ``min_interval_ms`` dall'ultima
        scrittura, oppure se :meth:`flush` ha forzato il prossimo write.
        """
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_write_at
            should_write = self._force_next or elapsed >= self._min_interval_s
            if not should_write:
                return
            self._store.update_run_progress(self._run_id, snapshot.to_payload())
            self._last_write_at = now
            self._force_next = False

    def flush(self) -> None:
        """Forza il prossimo :meth:`update` a passare anche se sotto soglia."""
        with self._lock:
            self._force_next = True

    def heartbeat(self) -> None:
        """Scrive solo il ``heartbeat_at``, senza toccare ``progress_json``.

        Da chiamare in idle, quando il job sta facendo I/O lento senza
        cambiamenti di stato osservabili.
        """
        self._store.mark_run_heartbeat(self._run_id)
