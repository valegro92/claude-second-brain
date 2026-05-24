"""Test :class:`JobRunner` (submit, cancel, reap, heartbeat, shutdown)."""

from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path

import pytest

from custodia_cli.jobs.cancel import CancelToken
from custodia_cli.jobs.progress import ProgressReporter, ProgressSnapshot
from custodia_cli.jobs.runner import JobRunner, JobStatus
from custodia_cli.state.store import StateStore


@pytest.fixture
def store(tmp_path: Path) -> StateStore:
    """StateStore su file (non in-memory) per testare cross-thread access."""
    db = tmp_path / "state.db"
    return StateStore(db)


@pytest.fixture
def runner(store: StateStore) -> JobRunner:
    r = JobRunner(store, max_workers=2)
    yield r
    r.shutdown(wait=True)


def _wait_for_status(
    runner: JobRunner,
    job_id: int,
    target: JobStatus,
    timeout: float = 3.0,
) -> bool:
    """Poll fino a che il job raggiunge ``target`` o scade il timeout."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        job = runner.get_job(job_id)
        if job is not None and job.status == target:
            return True
        time.sleep(0.02)
    return False


def test_submit_happy_path(runner: JobRunner) -> None:
    def work(*, progress: ProgressReporter, cancel: CancelToken) -> str:
        progress.update(ProgressSnapshot(status="running", current=1, total=1))
        return "done"

    job = runner.submit(work, name="happy")
    assert _wait_for_status(runner, job.id, JobStatus.SUCCESS)
    final = runner.get_job(job.id)
    assert final is not None
    assert final.status == JobStatus.SUCCESS
    assert final.summary == "OK"
    assert job.future.result() == "done"


def test_submit_job_that_raises_marks_error(runner: JobRunner) -> None:
    def boom(*, progress: ProgressReporter, cancel: CancelToken) -> None:
        raise RuntimeError("boom-test")

    job = runner.submit(boom, name="explosive")
    assert _wait_for_status(runner, job.id, JobStatus.ERROR)
    final = runner.get_job(job.id)
    assert final is not None
    assert final.status == JobStatus.ERROR
    assert final.summary is not None
    assert "boom-test" in final.summary


def test_cancel_mid_flight(runner: JobRunner) -> None:
    started = threading.Event()

    def long_running(*, progress: ProgressReporter, cancel: CancelToken) -> None:
        started.set()
        for _ in range(200):
            cancel.raise_if_cancelled()
            time.sleep(0.02)

    job = runner.submit(long_running, name="long")
    assert started.wait(timeout=2), "il job non è partito"
    time.sleep(0.05)
    assert runner.cancel_job(job.id) is True
    assert _wait_for_status(runner, job.id, JobStatus.CANCELLED, timeout=2)


def test_cancel_returns_false_for_unknown_job(runner: JobRunner) -> None:
    assert runner.cancel_job(99999) is False


def test_heartbeat_is_updated_by_progress(
    runner: JobRunner, store: StateStore
) -> None:
    heartbeats_seen: list[str] = []

    def beating(*, progress: ProgressReporter, cancel: CancelToken) -> None:
        for i in range(4):
            progress.heartbeat()
            time.sleep(0.05)

    job = runner.submit(beating, name="beat")
    # Aspetta che il job sia partito e abbia chiamato heartbeat almeno una volta.
    time.sleep(0.15)
    snap = store.get_run_progress(job.id)
    assert snap is not None
    assert snap["heartbeat_at"] is not None
    _wait_for_status(runner, job.id, JobStatus.SUCCESS, timeout=3)


def test_reap_interrupted_runs(tmp_path: Path) -> None:
    """Run con heartbeat scaduto deve essere marcato partial/interrupted."""
    db = tmp_path / "state.db"
    store = StateStore(db)
    # Inserisce manualmente un run con heartbeat vecchio.
    run_id = store.register_run(command="ghost", args={})
    # Forza heartbeat_at a 10 minuti fa via SQL diretto (bypassa il metodo).
    with store._conn:  # noqa: SLF001
        store._conn.execute(  # noqa: SLF001
            "UPDATE runs SET heartbeat_at = datetime('now', '-10 minutes') "
            "WHERE id = ?",
            (run_id,),
        )
    runner = JobRunner(store, max_workers=1)
    try:
        count = runner.reap_interrupted_runs(threshold_minutes=5)
        assert count == 1
        # Verifica che il run sia stato chiuso.
        row = store._conn.execute(  # noqa: SLF001
            "SELECT status FROM runs WHERE id = ?", (run_id,)
        ).fetchone()
        assert row["status"] == "partial"
        snap = store.get_run_progress(run_id)
        assert snap is not None
        assert snap["progress"] is not None
        assert snap["progress"]["status"] == "interrupted"
    finally:
        runner.shutdown(wait=True)
        store.close()


def test_reap_skips_recent_runs(tmp_path: Path) -> None:
    db = tmp_path / "state.db"
    store = StateStore(db)
    run_id = store.register_run(command="fresh", args={})
    store.mark_run_heartbeat(run_id)
    runner = JobRunner(store, max_workers=1)
    try:
        count = runner.reap_interrupted_runs(threshold_minutes=5)
        assert count == 0
    finally:
        runner.shutdown(wait=True)
        store.close()


def test_parallel_jobs_no_progress_crosstalk(
    runner: JobRunner, store: StateStore
) -> None:
    """Due job paralleli non devono inquinarsi a vicenda il progress_json."""
    def make_work(tag: str):
        def work(*, progress: ProgressReporter, cancel: CancelToken) -> None:
            for i in range(5):
                progress.update(
                    ProgressSnapshot(
                        status="running",
                        current=i,
                        total=5,
                        extra={"tag": tag},
                    )
                )
                # min_interval_ms=200; per garantire scritture multiple usiamo flush.
                progress.flush()
                time.sleep(0.03)
        return work

    job_a = runner.submit(make_work("alpha"), name="a")
    job_b = runner.submit(make_work("beta"), name="b")
    assert _wait_for_status(runner, job_a.id, JobStatus.SUCCESS)
    assert _wait_for_status(runner, job_b.id, JobStatus.SUCCESS)
    snap_a = store.get_run_progress(job_a.id)
    snap_b = store.get_run_progress(job_b.id)
    assert snap_a is not None and snap_b is not None
    # Lo status finale di entrambi è "success" (impostato in _finalize_run).
    assert snap_a["progress"]["status"] == "success"
    assert snap_b["progress"]["status"] == "success"


def test_shutdown_wait_true_blocks_until_done(store: StateStore) -> None:
    runner = JobRunner(store, max_workers=1)
    done = threading.Event()

    def slow(*, progress: ProgressReporter, cancel: CancelToken) -> None:
        time.sleep(0.15)
        done.set()

    runner.submit(slow, name="slow")
    runner.shutdown(wait=True)
    assert done.is_set()


def test_max_workers_one_serializes_jobs(store: StateStore) -> None:
    runner = JobRunner(store, max_workers=1)
    sequence: list[str] = []
    lock = threading.Lock()

    def stamp(tag: str):
        def work(*, progress: ProgressReporter, cancel: CancelToken) -> None:
            with lock:
                sequence.append(f"start-{tag}")
            time.sleep(0.1)
            with lock:
                sequence.append(f"end-{tag}")
        return work

    job_a = runner.submit(stamp("A"), name="A")
    job_b = runner.submit(stamp("B"), name="B")
    runner.shutdown(wait=True)
    # Job B non può partire prima che A finisca (max_workers=1).
    assert sequence == ["start-A", "end-A", "start-B", "end-B"]


def test_job_without_progress_or_cancel_kwargs_still_runs(
    runner: JobRunner,
) -> None:
    """Una funzione che accetta **kwargs deve girare senza esplodere."""
    def work(**kwargs) -> int:
        return 42

    job = runner.submit(work, name="kwargs-only")
    assert _wait_for_status(runner, job.id, JobStatus.SUCCESS)
    assert job.future.result() == 42
