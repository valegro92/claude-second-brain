"""
Gestione job in background per la webapp Streamlit.

Streamlit re-renderizza la pagina a ogni interazione/rerun: per evitare di
ri-lanciare il job a ogni rerun, lo stato del job attivo vive in
``st.session_state['active_jobs']`` come dict ``{project_id: ActiveJob}``.

Il pattern è:

1. L'utente clicca "Scan" → si crea un :class:`CancelToken`, si lancia un
   thread worker e si registra :class:`ActiveJob` in session_state.
2. Streamlit rerun → la pagina vede ``active_jobs[project.id]`` e rende
   layout "polling".
3. Ogni 500ms ri-legge ``store.get_run_progress(run_id)`` e ri-renderizza.
4. Cancel button chiama ``token.set_cancelled()``: il worker vede il flag al
   prossimo ``raise_if_cancelled()`` e termina.
5. Quando lo status diventa terminale (success/error/cancelled/interrupted),
   si mostra il summary e si pulisce l'entry.

NOTA SU JOBRUNNER: il :class:`JobRunner` del CLI prende uno ``store`` al
costruttore, gestisce un unico thread pool e auto-crea il :class:`ProgressReporter`.
Per la webapp questo è scomodo (store cambia per progetto, runner globale dovrebbe
essere singleton, ma store no). La scelta qui è di NON usare JobRunner: lanciamo
i worker direttamente con :class:`threading.Thread` (daemon=True) e teniamo solo
il :class:`CancelToken` per cancel + il ``run_id`` per polling del progress
tramite ``StateStore.get_run_progress``. Il worker apre il proprio StateStore
nel thread (la connessione SQLite non è thread-safe).
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any

import streamlit as st

from custodia_cli.jobs import CancelToken


_ACTIVE_JOBS_KEY = "active_jobs"


@dataclass
class ActiveJob:
    """Handle di un job background associato a un progetto.

    Attributes:
        run_id: id del run nel ``StateStore``, usato per polling progress.
        token: :class:`CancelToken` settato dal cancel button.
        kind: ``"scan"`` o ``"build"`` — discrimina layout polling.
        thread: thread worker. Daemon=True così non blocca l'exit del processo.
        result: popolato dal worker alla fine. ``None`` finché il job è running.
        label: stringa human readable per intestazione progress (es.
            "Scan filesystem", "Build cliente").
    """

    run_id: int
    token: CancelToken
    kind: str
    thread: threading.Thread
    label: str
    result: Any = None


def get_active_jobs() -> dict[str, ActiveJob]:
    """Ritorna il dict job-attivi-per-progetto, creandolo se necessario."""
    if _ACTIVE_JOBS_KEY not in st.session_state:
        st.session_state[_ACTIVE_JOBS_KEY] = {}
    return st.session_state[_ACTIVE_JOBS_KEY]


def set_active_job(project_id: str, job: ActiveJob) -> None:
    """Associa un :class:`ActiveJob` a un progetto."""
    jobs = get_active_jobs()
    jobs[project_id] = job


def get_active_job(project_id: str) -> ActiveJob | None:
    """Ritorna il job attivo per il progetto, ``None`` se non c'è."""
    return get_active_jobs().get(project_id)


def clear_active_job(project_id: str) -> None:
    """Rimuove l'entry job-attivo del progetto. No-op se non presente."""
    jobs = get_active_jobs()
    jobs.pop(project_id, None)


def has_active_job(project_id: str, kind: str | None = None) -> bool:
    """Vero se c'è un job attivo per il progetto (opzionalmente di un kind)."""
    job = get_active_job(project_id)
    if job is None:
        return False
    if kind is None:
        return True
    return job.kind == kind


__all__ = [
    "ActiveJob",
    "clear_active_job",
    "get_active_job",
    "get_active_jobs",
    "has_active_job",
    "set_active_job",
]
