"""
Test estesi per ``custodia_web.services.scan`` con focus sul worker
background U4 (Sprint 2a): progress live + cancel mid-flight + manifest
incremental skip.

I test esistenti sullo scan sincrono restano in ``test_services.py``; qui
copriamo solo la parte nuova.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest

from custodia_cli.commands.init import state_db_path_for_vault
from custodia_cli.jobs import CancelToken
from custodia_cli.state import StateStore
from custodia_web.services import scan as scan_svc


@pytest.fixture
def sample_vault(tmp_path: Path) -> Path:
    vault = tmp_path / "vault"
    for sub in ("clienti", "fornitori", "commesse", "inbox"):
        (vault / sub).mkdir(parents=True)
    return vault


@pytest.fixture
def populated_source(tmp_path: Path) -> Path:
    """Crea una sorgente con 10 file txt."""
    src = tmp_path / "src"
    src.mkdir()
    for i in range(10):
        (src / f"nota_{i:02d}.txt").write_text(
            f"Cliente {i}: ordine #{i*100} per Acme SRL."
        )
    return src


# ---------------------------------------------------------------------------
# _estimate_file_count
# ---------------------------------------------------------------------------


def test_estimate_file_count_counts_files(populated_source: Path) -> None:
    token = CancelToken()
    count = scan_svc._estimate_file_count(populated_source, None, token)
    assert count == 10


def test_estimate_file_count_respects_excludes(populated_source: Path) -> None:
    token = CancelToken()
    # esclude tutti i .txt
    count = scan_svc._estimate_file_count(populated_source, ["*.txt"], token)
    assert count == 0


def test_estimate_file_count_handles_missing_root(tmp_path: Path) -> None:
    token = CancelToken()
    missing = tmp_path / "does-not-exist"
    # os.walk su path inesistente ritorna iter vuoto → count = 0 (None solo se
    # timeout o cap_files); accettiamo 0.
    count = scan_svc._estimate_file_count(missing, None, token)
    assert count == 0


# ---------------------------------------------------------------------------
# scan_filesystem_with_progress sincrono (chiamato senza thread)
# ---------------------------------------------------------------------------


def test_scan_with_progress_happy_path(
    sample_vault: Path, populated_source: Path
) -> None:
    """Chiamata diretta del worker: deve completare, scrivere docs, marcare
    run come success e pubblicare snapshot finale."""
    token = CancelToken()
    captured_run_id: dict[str, int] = {}

    def _cb(rid: int) -> None:
        captured_run_id["run_id"] = rid

    result = scan_svc.scan_filesystem_with_progress(
        vault=sample_vault,
        root=populated_source,
        cancel=token,
        run_id_callback=_cb,
    )
    assert result.error is None
    assert result.new_docs == 10
    assert result.duplicates == 0
    assert "run_id" in captured_run_id

    # Verifica snapshot finale nel DB.
    db_path = state_db_path_for_vault(sample_vault.resolve())
    with StateStore(db_path) as store:
        snap = store.get_run_progress(captured_run_id["run_id"])
    assert snap is not None
    prog = snap["progress"]
    assert prog["status"] == "success"
    assert prog["current"] == 10  # n_new + n_dup
    assert prog.get("total") == 10
    # snapshot finale ha eta None o 0; deve almeno avere skipped breakdown
    assert "skipped" in prog
    assert int(prog["skipped"].get("processed", 0)) == 10


def test_scan_with_progress_cancel_midflight(
    sample_vault: Path, tmp_path: Path
) -> None:
    """Cancel attivo prima dello scan → 0 doc nuovi, status cancelled."""
    # Sorgente piccola: 5 file
    src = tmp_path / "src_cancel"
    src.mkdir()
    for i in range(5):
        (src / f"f_{i}.txt").write_text(f"contenuto {i}")

    token = CancelToken()
    token.set_cancelled()  # già cancellato prima della partenza

    captured: dict[str, int] = {}

    def _cb(rid: int) -> None:
        captured["run_id"] = rid

    result = scan_svc.scan_filesystem_with_progress(
        vault=sample_vault,
        root=src,
        cancel=token,
        run_id_callback=_cb,
    )
    # Non rilancia, ritorna ScanResult con error=None ma 0 doc
    assert result.error is None
    assert result.new_docs == 0
    assert result.duplicates == 0

    db_path = state_db_path_for_vault(sample_vault.resolve())
    with StateStore(db_path) as store:
        snap = store.get_run_progress(captured["run_id"])
    assert snap is not None
    assert snap["progress"]["status"] == "cancelled"
    # Il run nel DB è marcato 'partial'
    assert snap["status"] == "partial"


def test_scan_with_progress_invalid_root(sample_vault: Path) -> None:
    token = CancelToken()
    result = scan_svc.scan_filesystem_with_progress(
        vault=sample_vault,
        root=Path("/nope/does/not/exist"),
        cancel=token,
    )
    assert result.error is not None


def test_scan_with_progress_rerun_uses_manifest(
    sample_vault: Path, populated_source: Path
) -> None:
    """Secondo scan sulla stessa root → tutti gli unchanged sono skippati,
    e non ci sono né nuovi né duplicati (perché l'add_document non viene
    nemmeno chiamato)."""
    token = CancelToken()
    r1 = scan_svc.scan_filesystem_with_progress(
        vault=sample_vault, root=populated_source, cancel=token
    )
    assert r1.new_docs == 10

    token2 = CancelToken()
    r2 = scan_svc.scan_filesystem_with_progress(
        vault=sample_vault, root=populated_source, cancel=token2
    )
    # Niente nuovi e niente duplicati: il manifest ha skippato tutto.
    assert r2.new_docs == 0
    assert r2.duplicates == 0
    # stats deve riportare skipped_unchanged = 10
    assert r2.stats.get("skipped_unchanged") == 10


# ---------------------------------------------------------------------------
# launch_scan_filesystem_thread (lancio in thread)
# ---------------------------------------------------------------------------


def test_launch_scan_thread_completes(
    sample_vault: Path, populated_source: Path
) -> None:
    token = CancelToken()
    thread, ctx = scan_svc.launch_scan_filesystem_thread(
        vault=sample_vault,
        root=populated_source,
        exclude_patterns=None,
        max_size_mb=50,
        follow_symlinks=False,
        allow_dangerous_root=True,
        force_rescan=False,
        cancel=token,
    )
    assert isinstance(thread, threading.Thread)
    # Aspetta che il worker termini (max 10s)
    thread.join(timeout=10.0)
    assert not thread.is_alive(), "Thread scan non è terminato in 10s"
    assert ctx["run_id"] is not None
    assert ctx["result"] is not None
    assert ctx["result"].new_docs == 10


def test_launch_scan_thread_cancel(
    sample_vault: Path, tmp_path: Path
) -> None:
    """Lancia in thread, cancella subito; il worker termina pulitamente."""
    src = tmp_path / "src_cancel_thread"
    src.mkdir()
    # 50 file così c'è margine perché il cancel arrivi mid-flight
    for i in range(50):
        (src / f"f_{i:03d}.txt").write_text(f"contenuto {i}" * 100)

    token = CancelToken()
    # Cancel subito (prima ancora che il worker entri nel loop)
    token.set_cancelled()

    thread, ctx = scan_svc.launch_scan_filesystem_thread(
        vault=sample_vault,
        root=src,
        exclude_patterns=None,
        max_size_mb=50,
        follow_symlinks=False,
        allow_dangerous_root=True,
        force_rescan=False,
        cancel=token,
    )
    thread.join(timeout=10.0)
    assert not thread.is_alive()
    assert ctx["result"] is not None
    # Cancel ⇒ pochissimi file processati (di solito 0)
    assert ctx["result"].new_docs <= 5
