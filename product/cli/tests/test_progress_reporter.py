"""Test :class:`ProgressReporter` (coalescing + heartbeat)."""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

from custodia_cli.jobs.progress import ProgressReporter, ProgressSnapshot
from custodia_cli.state.store import StateStore


@pytest.fixture
def store() -> StateStore:
    return StateStore(":memory:")


@pytest.fixture
def run_id(store: StateStore) -> int:
    return store.register_run(command="test", args={})


def test_first_update_is_written(store: StateStore, run_id: int) -> None:
    reporter = ProgressReporter(store, run_id, min_interval_ms=200)
    reporter.update(ProgressSnapshot(status="running", current=1, total=10))
    snapshot = store.get_run_progress(run_id)
    assert snapshot is not None
    assert snapshot["progress"]["current"] == 1
    assert snapshot["progress"]["total"] == 10


def test_coalescing_drops_rapid_updates(run_id: int) -> None:
    """Update consecutivi entro la finestra di coalescing → solo il primo passa."""
    mock_store = MagicMock()
    reporter = ProgressReporter(mock_store, run_id, min_interval_ms=200)
    # Primo update passa (last_write_at=0, elapsed enorme).
    reporter.update(ProgressSnapshot(status="running", current=1))
    # I prossimi 5 update arrivano immediatamente → dovrebbero essere droppati.
    for i in range(2, 7):
        reporter.update(ProgressSnapshot(status="running", current=i))
    assert mock_store.update_run_progress.call_count == 1


def test_update_passes_after_interval(run_id: int) -> None:
    mock_store = MagicMock()
    reporter = ProgressReporter(mock_store, run_id, min_interval_ms=50)
    reporter.update(ProgressSnapshot(status="running", current=1))
    time.sleep(0.08)  # > 50ms
    reporter.update(ProgressSnapshot(status="running", current=2))
    assert mock_store.update_run_progress.call_count == 2


def test_flush_forces_next_update(run_id: int) -> None:
    mock_store = MagicMock()
    reporter = ProgressReporter(mock_store, run_id, min_interval_ms=10_000)
    reporter.update(ProgressSnapshot(status="running", current=1))
    # Subito un altro update senza flush → droppato.
    reporter.update(ProgressSnapshot(status="running", current=2))
    assert mock_store.update_run_progress.call_count == 1
    # Ora flush + update → passa anche sotto soglia.
    reporter.flush()
    reporter.update(ProgressSnapshot(status="running", current=3))
    assert mock_store.update_run_progress.call_count == 2


def test_heartbeat_calls_mark_heartbeat_only(run_id: int) -> None:
    mock_store = MagicMock()
    reporter = ProgressReporter(mock_store, run_id, min_interval_ms=200)
    reporter.heartbeat()
    mock_store.mark_run_heartbeat.assert_called_once_with(run_id)
    mock_store.update_run_progress.assert_not_called()


def test_snapshot_payload_roundtrip(store: StateStore, run_id: int) -> None:
    reporter = ProgressReporter(store, run_id, min_interval_ms=0)
    snap = ProgressSnapshot(
        status="running",
        current=42,
        total=100,
        current_item="/tmp/foo.pdf",
        throughput_per_sec=12.5,
        eta_seconds=4.6,
        skipped={"unchanged": 3, "excluded": 1},
        errors=2,
        extra={"connector": "filesystem"},
    )
    reporter.update(snap)
    out = store.get_run_progress(run_id)
    assert out is not None
    progress = out["progress"]
    assert progress["status"] == "running"
    assert progress["current"] == 42
    assert progress["total"] == 100
    assert progress["current_item"] == "/tmp/foo.pdf"
    assert progress["throughput_per_sec"] == 12.5
    assert progress["eta_seconds"] == 4.6
    assert progress["skipped"] == {"unchanged": 3, "excluded": 1}
    assert progress["errors"] == 2
    assert progress["extra"] == {"connector": "filesystem"}


def test_update_writes_heartbeat_alongside(store: StateStore, run_id: int) -> None:
    reporter = ProgressReporter(store, run_id, min_interval_ms=0)
    reporter.update(ProgressSnapshot(status="running"))
    out = store.get_run_progress(run_id)
    assert out is not None
    assert out["heartbeat_at"] is not None
