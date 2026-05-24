"""
JobRunner: esegue job in un :class:`ThreadPoolExecutor`, traccia stato sul
:class:`StateStore`, supporta cancel via :class:`CancelToken` e reaping dei
run interrotti (es. dopo crash del processo).

Architettura: single-user locale, AsyncIO + threading in-process. Niente Redis
o Celery: ogni job vive in un worker thread del pool. Il :meth:`submit` accetta
una callable ``fn(*args, progress, **kwargs)`` che riceve come parametro
keyword ``progress`` un :class:`ProgressReporter` già configurato sul
``run_id``; la callable può anche accettare ``cancel`` come keyword per
controllare il :class:`CancelToken` (best practice: passarlo a ogni iterazione
e chiamare ``cancel.raise_if_cancelled()``).
"""

from __future__ import annotations

import logging
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable

from custodia_cli.jobs.cancel import CancelledError, CancelToken
from custodia_cli.jobs.progress import ProgressReporter, ProgressSnapshot
from custodia_cli.state.store import StateStore

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    """Stato di un job nel ciclo di vita."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
    CANCELLED = "cancelled"
    INTERRUPTED = "interrupted"


# Mappa JobStatus → status accettato da StateStore.complete_run.
# StateStore accetta solo "success" | "error" | "partial"; mappiamo gli stati
# terminali aggiuntivi su "error"/"partial" per compatibilità con lo schema
# esistente, mentre lo stato "vero" è già in progress_json.status.
_STATUS_TO_STORE: dict[JobStatus, str] = {
    JobStatus.SUCCESS: "success",
    JobStatus.ERROR: "error",
    JobStatus.CANCELLED: "partial",
    JobStatus.INTERRUPTED: "partial",
}


@dataclass
class Job:
    """Handle di un job in esecuzione o terminato."""

    id: int
    name: str
    status: JobStatus
    started_at: datetime
    completed_at: datetime | None
    summary: str | None
    cancel_token: CancelToken
    future: Future = field(repr=False)


class JobRunner:
    """Esegue job in thread pool con progress, cancel e heartbeat.

    Usage::

        runner = JobRunner(store, max_workers=2)

        def my_scan(path, *, progress, cancel):
            for f in walk(path):
                cancel.raise_if_cancelled()
                progress.update(ProgressSnapshot(status="running", current=...))

        job = runner.submit(my_scan, "/tmp/vault", name="scan")
        ...
        runner.cancel_job(job.id)
        runner.shutdown()
    """

    def __init__(self, store: StateStore, *, max_workers: int = 2) -> None:
        self._store = store
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="custodia-job",
        )
        self._jobs: dict[int, Job] = {}
        self._lock = threading.Lock()
        self._max_workers = max_workers

    # ------------------------------------------------------------------
    # submit / state
    # ------------------------------------------------------------------

    def submit(
        self,
        fn: Callable[..., Any],
        *args: Any,
        name: str,
        cancel_token: CancelToken | None = None,
        **kwargs: Any,
    ) -> Job:
        """Sottomette un job al thread pool.

        La callable ``fn`` viene invocata come ``fn(*args, progress=...,
        cancel=..., **kwargs)``. Le chiavi ``progress`` e ``cancel`` sono
        riservate al runner: se ``fn`` non le accetta, vengono ignorate
        introspezionando la firma — ma il pattern raccomandato è accettarle
        sempre come keyword-only.
        """
        token = cancel_token if cancel_token is not None else CancelToken()
        run_id = self._store.register_run(command=name, args={})
        reporter = ProgressReporter(self._store, run_id)
        # Inizializza progress + heartbeat appena registrato il run.
        reporter.flush()
        reporter.update(ProgressSnapshot(status="running"))

        started_at = datetime.now(timezone.utc)
        future: Future = self._executor.submit(
            self._run_wrapper,
            fn,
            args,
            kwargs,
            reporter,
            token,
            run_id,
            name,
        )
        job = Job(
            id=run_id,
            name=name,
            status=JobStatus.RUNNING,
            started_at=started_at,
            completed_at=None,
            summary=None,
            cancel_token=token,
            future=future,
        )
        with self._lock:
            self._jobs[run_id] = job
        future.add_done_callback(lambda _f: self._on_done(run_id))
        return job

    def _run_wrapper(
        self,
        fn: Callable[..., Any],
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
        reporter: ProgressReporter,
        cancel_token: CancelToken,
        run_id: int,
        name: str,
    ) -> Any:
        """Esegue ``fn`` catturando cancellation/errors e aggiornando lo stato."""
        # Inietta progress/cancel come kwargs se non già presenti.
        call_kwargs = dict(kwargs)
        call_kwargs.setdefault("progress", reporter)
        call_kwargs.setdefault("cancel", cancel_token)
        try:
            result = fn(*args, **call_kwargs)
        except CancelledError:
            logger.info("Job %s (run_id=%s) cancellato", name, run_id)
            self._finalize_run(
                run_id, reporter, JobStatus.CANCELLED, "Cancellato dall'utente."
            )
            return None
        except Exception as exc:  # noqa: BLE001 - vogliamo prendere tutto
            logger.exception("Job %s (run_id=%s) fallito", name, run_id)
            self._finalize_run(
                run_id, reporter, JobStatus.ERROR, f"Errore: {exc}"
            )
            raise
        self._finalize_run(run_id, reporter, JobStatus.SUCCESS, "OK")
        return result

    def _finalize_run(
        self,
        run_id: int,
        reporter: ProgressReporter,
        status: JobStatus,
        summary: str,
    ) -> None:
        """Scrive snapshot finale + chiude il run nel DB."""
        reporter.flush()
        reporter.update(ProgressSnapshot(status=status.value))
        store_status = _STATUS_TO_STORE[status]
        try:
            self._store.complete_run(run_id, status=store_status, summary=summary)
        except Exception:  # noqa: BLE001
            logger.exception("complete_run fallita per run_id=%s", run_id)

    def _on_done(self, run_id: int) -> None:
        """Aggiorna l'in-memory Job dopo che il Future ha terminato."""
        with self._lock:
            job = self._jobs.get(run_id)
            if job is None:
                return
            job.completed_at = datetime.now(timezone.utc)
            if job.cancel_token.is_cancelled and not job.future.exception():
                # Il worker ha visto cancel e ha terminato pulitamente.
                job.status = JobStatus.CANCELLED
                job.summary = "Cancellato dall'utente."
            elif job.future.exception() is not None:
                exc = job.future.exception()
                if isinstance(exc, CancelledError):
                    job.status = JobStatus.CANCELLED
                    job.summary = "Cancellato dall'utente."
                else:
                    job.status = JobStatus.ERROR
                    job.summary = f"Errore: {exc}"
            else:
                job.status = JobStatus.SUCCESS
                job.summary = "OK"

    def get_job(self, job_id: int) -> Job | None:
        """Ritorna l'handle del job o ``None``."""
        with self._lock:
            return self._jobs.get(job_id)

    def cancel_job(self, job_id: int) -> bool:
        """Richiede cancellazione. Ritorna ``True`` se il job esiste.

        Idempotente: cancel su un job già terminato è no-op (ritorna True se
        il job è ancora tracciato).
        """
        with self._lock:
            job = self._jobs.get(job_id)
        if job is None:
            return False
        job.cancel_token.set_cancelled()
        return True

    # ------------------------------------------------------------------
    # interrupted runs reaping
    # ------------------------------------------------------------------

    def reap_interrupted_runs(self, threshold_minutes: int = 5) -> int:
        """Allo startup, marca come ``interrupted`` i run con heartbeat scaduto.

        Da chiamare una sola volta all'avvio del processo, prima di
        sottomettere nuovi job. Identifica run la cui ``status='running'`` ma
        ``heartbeat_at`` è più vecchio di ``threshold_minutes`` minuti — sintomo
        di un crash del processo precedente.

        Returns:
            numero di run marcati come interrotti.
        """
        rows = self._store.find_interrupted_runs(threshold_minutes=threshold_minutes)
        count = 0
        for row in rows:
            run_id = int(row["id"])
            try:
                # Aggiorna sia progress (status='interrupted') sia colonna runs.status.
                self._store.update_run_progress(
                    run_id,
                    ProgressSnapshot(status="interrupted").to_payload(),
                )
                self._store.complete_run(
                    run_id,
                    status="partial",
                    summary="Interrotto: heartbeat scaduto.",
                )
                count += 1
            except Exception:  # noqa: BLE001
                logger.exception("reap fallita per run_id=%s", run_id)
        return count

    # ------------------------------------------------------------------
    # shutdown
    # ------------------------------------------------------------------

    def shutdown(self, wait: bool = True) -> None:
        """Spegne il thread pool.

        Args:
            wait: se ``True`` aspetta che i job in flight terminino. Se
                ``False`` chiama ``shutdown(wait=False)`` sull'executor: i
                worker thread continuano in background ma il pool non accetta
                nuovi submit. Nota: i thread workers sono daemon=False per
                default in ThreadPoolExecutor; se il processo termina con job
                pendenti, Python aspetterà comunque la loro fine.
        """
        self._executor.shutdown(wait=wait)
