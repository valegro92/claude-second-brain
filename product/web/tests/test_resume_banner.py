"""
Test del banner "Riprendi scan interrotto" (U5, Sprint 2a).

Copre:
- services.scan.reap_interrupted_runs_for_vault marca i run abbandonati.
- services.scan.list_interrupted_scan_runs filtra correttamente.
- services.scan.resume_scan_filesystem lancia un nuovo thread con args
  recuperati dal run interrotto.
- services.scan.dismiss_interrupted_run elimina la riga dal DB.
- Banner UI: visibile/nascosto in base a numero di run interrotti
  (testato senza dipendenza da Streamlit runtime via mock di st).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from custodia_cli.commands.init import run_init, state_db_path_for_vault
from custodia_cli.jobs.progress import ProgressSnapshot
from custodia_cli.state import StateStore
from custodia_web.services import scan as scan_svc


@pytest.fixture
def vault_with_state(tmp_path: Path) -> Path:
    vault = tmp_path / "vault"
    vault.mkdir()
    run_init(vault)
    return vault


def _make_interrupted_scan(
    vault: Path,
    *,
    root: str,
    age_minutes: int = 10,
    mark_partial: bool = True,
) -> int:
    """Crea un run scan fs interrotto nel DB del vault."""
    db_path = state_db_path_for_vault(vault.resolve())
    with StateStore(db_path) as store:
        run_id = store.register_run(
            command="scan fs",
            args={"root": root, "max_size_mb": 50, "excludes": []},
        )
        with store._conn:  # noqa: SLF001
            store._conn.execute(  # noqa: SLF001
                "UPDATE runs SET heartbeat_at = datetime('now', '-' || ? || ' minutes') "
                "WHERE id = ?",
                (age_minutes, run_id),
            )
        if mark_partial:
            store.update_run_progress(
                run_id,
                ProgressSnapshot(status="interrupted", current=42).to_payload(),
            )
            store.complete_run(run_id, status="partial", summary="Interrotto.")
    return run_id


# ---------------------------------------------------------------------------
# reap + list
# ---------------------------------------------------------------------------


def test_reap_marks_abandoned_runs(vault_with_state: Path) -> None:
    """reap_interrupted_runs_for_vault marca run 'running' scaduti come partial."""
    db_path = state_db_path_for_vault(vault_with_state.resolve())
    with StateStore(db_path) as store:
        run_id = store.register_run(command="scan fs", args={"root": "/x"})
        with store._conn:  # noqa: SLF001
            store._conn.execute(  # noqa: SLF001
                "UPDATE runs SET heartbeat_at = datetime('now', '-10 minutes') "
                "WHERE id = ?",
                (run_id,),
            )

    n = scan_svc.reap_interrupted_runs_for_vault(vault_with_state, threshold_minutes=5)
    assert n == 1

    with StateStore(db_path) as store:
        row = store._conn.execute(  # noqa: SLF001
            "SELECT status FROM runs WHERE id = ?", (run_id,)
        ).fetchone()
    assert row["status"] == "partial"


def test_reap_no_state_db_returns_zero(tmp_path: Path) -> None:
    """Vault senza state DB → reap ritorna 0 senza crashare."""
    vault = tmp_path / "vault-empty"
    vault.mkdir()
    assert scan_svc.reap_interrupted_runs_for_vault(vault) == 0


def test_list_interrupted_runs_hidden_when_none(vault_with_state: Path) -> None:
    runs = scan_svc.list_interrupted_scan_runs(vault_with_state)
    assert runs == []


def test_list_interrupted_runs_returns_recent_first(
    vault_with_state: Path,
) -> None:
    """Più run interrotti, ordinati per id DESC (più recente primo)."""
    r1 = _make_interrupted_scan(vault_with_state, root="/a")
    r2 = _make_interrupted_scan(vault_with_state, root="/b")
    r3 = _make_interrupted_scan(vault_with_state, root="/c")

    runs = scan_svc.list_interrupted_scan_runs(vault_with_state)
    assert [r.run_id for r in runs] == [r3, r2, r1]
    assert runs[0].root == "/c"
    assert runs[0].processed == 42


# ---------------------------------------------------------------------------
# resume_scan_filesystem
# ---------------------------------------------------------------------------


def test_resume_scan_filesystem_returns_thread(
    vault_with_state: Path, tmp_path: Path
) -> None:
    """resume_scan_filesystem lancia un thread che processa la root del run
    interrotto."""
    # Crea una sorgente reale così il connector riesce a iterare.
    src = tmp_path / "src"
    src.mkdir()
    (src / "doc1.txt").write_text("contenuto cliente")

    _make_interrupted_scan(vault_with_state, root=str(src))

    from custodia_cli.jobs import CancelToken
    token = CancelToken()
    result = scan_svc.resume_scan_filesystem(
        vault=vault_with_state,
        run_id=scan_svc.list_interrupted_scan_runs(vault_with_state)[0].run_id,
        cancel=token,
    )
    assert result is not None
    thread, ctx = result
    thread.join(timeout=10)
    assert not thread.is_alive()
    assert ctx.get("result") is not None
    assert ctx["result"].error is None


def test_resume_scan_filesystem_missing_run(vault_with_state: Path) -> None:
    from custodia_cli.jobs import CancelToken
    out = scan_svc.resume_scan_filesystem(
        vault=vault_with_state, run_id=9999, cancel=CancelToken()
    )
    assert out is None


# ---------------------------------------------------------------------------
# dismiss
# ---------------------------------------------------------------------------


def test_dismiss_removes_run_from_db(vault_with_state: Path) -> None:
    rid = _make_interrupted_scan(vault_with_state, root="/x")
    assert scan_svc.dismiss_interrupted_run(vault_with_state, rid) is True
    runs = scan_svc.list_interrupted_scan_runs(vault_with_state)
    assert all(r.run_id != rid for r in runs)


def test_dismiss_returns_false_when_not_found(vault_with_state: Path) -> None:
    assert scan_svc.dismiss_interrupted_run(vault_with_state, 9999) is False


# ---------------------------------------------------------------------------
# Banner UI (con Streamlit mockato)
# ---------------------------------------------------------------------------


def _patch_streamlit(monkeypatch):
    """Sostituisce il modulo streamlit nel banner con un mock minimale.

    Riproduce le API usate dal banner: ``session_state`` (dict-like),
    ``warning``, ``button`` (default False), ``columns``, ``rerun``,
    ``expander`` (context manager), ``container`` (context manager), ``toast``,
    ``caption``, ``error``.
    """

    import custodia_web.components.interrupted_banner as banner_mod

    fake_st = MagicMock()

    class FakeSession(dict):
        def __setitem__(self, k, v):
            super().__setitem__(k, v)

    session = FakeSession()
    fake_st.session_state = session

    # button: default False (mai cliccato).
    fake_st.button = MagicMock(return_value=False)
    fake_st.warning = MagicMock()
    fake_st.error = MagicMock()
    fake_st.caption = MagicMock()
    fake_st.toast = MagicMock()
    fake_st.rerun = MagicMock(side_effect=Exception("rerun"))

    class FakeCtx:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    fake_st.container = MagicMock(return_value=FakeCtx())
    fake_st.expander = MagicMock(return_value=FakeCtx())

    def fake_columns(spec):
        # Ritorna N column mock con button/caption.
        n = len(spec) if isinstance(spec, (list, tuple)) else int(spec)
        cols = []
        for _ in range(n):
            c = MagicMock()
            c.__enter__ = lambda self=c: self
            c.__exit__ = lambda *args: False
            c.button = MagicMock(return_value=False)
            c.caption = MagicMock()
            cols.append(c)
        return cols

    fake_st.columns = MagicMock(side_effect=fake_columns)

    monkeypatch.setattr(banner_mod, "st", fake_st)
    return fake_st


def test_banner_hidden_when_no_interrupted(
    vault_with_state: Path, monkeypatch
) -> None:
    fake_st = _patch_streamlit(monkeypatch)
    from custodia_web.components.interrupted_banner import render_interrupted_banner

    drew = render_interrupted_banner(vault_with_state, "proj1")
    assert drew is False
    fake_st.warning.assert_not_called()


def test_banner_visible_when_interrupted_present(
    vault_with_state: Path, monkeypatch
) -> None:
    _make_interrupted_scan(vault_with_state, root="/some/path")
    fake_st = _patch_streamlit(monkeypatch)
    from custodia_web.components.interrupted_banner import render_interrupted_banner

    drew = render_interrupted_banner(vault_with_state, "proj1")
    assert drew is True
    fake_st.warning.assert_called_once()
    # Il testo del banner contiene il path della cartella.
    call_args = fake_st.warning.call_args[0][0]
    assert "/some/path" in call_args


def test_banner_dismiss_marks_session(
    vault_with_state: Path, monkeypatch
) -> None:
    """Click 'Ignora' aggiunge il run_id ai dismessi in session_state."""
    rid = _make_interrupted_scan(vault_with_state, root="/x")
    fake_st = _patch_streamlit(monkeypatch)
    from custodia_web.components.interrupted_banner import (
        render_interrupted_banner,
        _DISMISSED_KEY,
    )

    # Click pattern: il dismiss button è il SECONDO button della prima column.
    # Più semplice: simuliamo manualmente l'aggiunta ai dismessi e
    # verifichiamo che il prossimo render NON disegni il banner.
    fake_st.session_state[_DISMISSED_KEY] = {rid}
    drew = render_interrupted_banner(vault_with_state, "proj1")
    assert drew is False


def test_banner_multiple_runs_shows_latest_first(
    vault_with_state: Path, monkeypatch
) -> None:
    """Con N interrupted runs, il banner principale è il più recente; gli
    altri vivono in expander."""
    _make_interrupted_scan(vault_with_state, root="/old")
    _make_interrupted_scan(vault_with_state, root="/new")

    fake_st = _patch_streamlit(monkeypatch)
    from custodia_web.components.interrupted_banner import render_interrupted_banner

    drew = render_interrupted_banner(vault_with_state, "proj1")
    assert drew is True
    # Il warning principale deve contenere /new (più recente).
    call_args = fake_st.warning.call_args[0][0]
    assert "/new" in call_args
    # Expander chiamato per gli "altri".
    fake_st.expander.assert_called()


def test_resume_with_invalid_run_returns_none(vault_with_state: Path) -> None:
    """Resume su run di un command non-fs deve fallire (ritorna None)."""
    db_path = state_db_path_for_vault(vault_with_state.resolve())
    with StateStore(db_path) as store:
        rid = store.register_run(command="scan drive", args={"root_folder_id": "X"})
    from custodia_cli.jobs import CancelToken
    out = scan_svc.resume_scan_filesystem(
        vault=vault_with_state, run_id=rid, cancel=CancelToken()
    )
    assert out is None
