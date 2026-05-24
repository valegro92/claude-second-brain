"""
Test del sub-comando ``custodia scan fs`` (U4).
"""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from custodia_cli.commands.init import (
    run_init,
    state_db_path_for_vault,
)
from custodia_cli.main import app
from custodia_cli.state import StateStore

runner = CliRunner()


def test_scan_fs_end_to_end(tmp_path: Path, finto_drive_root: Path) -> None:
    """`custodia scan fs --vault ... --root finto-drive` deve:
    - exitare 0
    - registrare un run con status 'success'
    - persistere i documenti in StateStore
    """
    vault = tmp_path / "vault"
    vault.mkdir()
    run_init(vault)

    result = runner.invoke(
        app,
        [
            "scan",
            "fs",
            "--vault",
            str(vault),
            "--root",
            str(finto_drive_root),
        ],
    )
    assert result.exit_code == 0, result.output

    db_path = state_db_path_for_vault(vault)
    with StateStore(db_path) as store:
        docs = store.list_documents()
        # Almeno i 5 file noti del fixture devono essere persistiti.
        paths = {d["source_path"] for d in docs}
        expected_paths = {
            "Commerciale 2024/fattura-rossetto-001.pdf",
            "Commerciale 2024/offerta-bianchi-valvole.docx",
            "Commerciale 2024/listino-2024.xlsx",
            "Comunicazioni/email-torrelli-2024-03.txt",
            "README.md",
        }
        assert expected_paths.issubset(paths), (
            f"missing: {expected_paths - paths}"
        )

        # Verifica run registrato con status 'success'.
        runs = store._conn.execute(  # type: ignore[attr-defined]
            "SELECT command, status FROM runs ORDER BY id DESC LIMIT 1"
        ).fetchone()
        assert runs is not None
        assert runs["command"] == "scan fs"
        assert runs["status"] == "success"


def test_scan_fs_missing_state_db(tmp_path: Path, finto_drive_root: Path) -> None:
    """Senza `custodia init`, scan fs deve fallire con errore chiaro."""
    vault = tmp_path / "vault"
    vault.mkdir()
    # NON eseguiamo run_init.
    result = runner.invoke(
        app,
        [
            "scan",
            "fs",
            "--vault",
            str(vault),
            "--root",
            str(finto_drive_root),
        ],
    )
    assert result.exit_code != 0
    assert "State store non trovato" in result.output or "init" in result.output


def test_scan_fs_nonexistent_root(tmp_path: Path) -> None:
    """Root inesistente: exit 1 + messaggio chiaro."""
    vault = tmp_path / "vault"
    vault.mkdir()
    run_init(vault)
    result = runner.invoke(
        app,
        [
            "scan",
            "fs",
            "--vault",
            str(vault),
            "--root",
            str(tmp_path / "ghost"),
        ],
    )
    assert result.exit_code == 1
    assert "inesistente" in result.output.lower() or "non" in result.output.lower()


def test_scan_fs_custom_exclude(tmp_path: Path) -> None:
    """`--exclude` viene rispettato: i file .bak non finiscono nello store."""
    vault = tmp_path / "vault"
    vault.mkdir()
    run_init(vault)

    src = tmp_path / "src"
    src.mkdir()
    (src / "keep.md").write_text("# keep")
    (src / "old.bak").write_text("# skip")

    result = runner.invoke(
        app,
        [
            "scan",
            "fs",
            "--vault",
            str(vault),
            "--root",
            str(src),
            "--exclude",
            "*.bak",
        ],
    )
    assert result.exit_code == 0, result.output

    db_path = state_db_path_for_vault(vault)
    with StateStore(db_path) as store:
        paths = {d["source_path"] for d in store.list_documents()}
        assert "keep.md" in paths
        assert "old.bak" not in paths


def test_scan_fs_incremental_rescan(
    tmp_path: Path, finto_drive_root: Path
) -> None:
    """Secondo run su stesso vault/root: i source_id duplicati non aggiungono
    documenti nuovi (FIX B17: ancoriamo sullo state DB, non sull'output)."""
    vault = tmp_path / "vault"
    vault.mkdir()
    run_init(vault)
    args = ["scan", "fs", "--vault", str(vault), "--root", str(finto_drive_root)]
    r1 = runner.invoke(app, args)
    assert r1.exit_code == 0, r1.output

    db_path = state_db_path_for_vault(vault)
    with StateStore(db_path) as store:
        count_after_first = len(store.list_documents())
    assert count_after_first > 0

    r2 = runner.invoke(app, args)
    assert r2.exit_code == 0, r2.output

    with StateStore(db_path) as store:
        count_after_second = len(store.list_documents())
    # Nessun documento nuovo: il count deve essere identico.
    assert count_after_second == count_after_first


def test_scan_fs_keyboard_interrupt_marks_run_error(
    tmp_path: Path,
    finto_drive_root: Path,
    monkeypatch,
) -> None:
    """Ctrl+C durante scan → run chiuso con status='error' e summary
    descrittivo (FIX B14)."""
    vault = tmp_path / "vault"
    vault.mkdir()
    run_init(vault)

    # Patcha il connector così iter_documents solleva KeyboardInterrupt subito.
    from custodia_cli.connectors import filesystem as fs_mod

    real_iter = fs_mod.FilesystemConnector.iter_documents

    def fake_iter(self):  # type: ignore[no-untyped-def]
        # Restituisci un generator che solleva KeyboardInterrupt al primo next().
        def _gen():
            raise KeyboardInterrupt()
            yield  # pragma: no cover

        return _gen()

    monkeypatch.setattr(
        fs_mod.FilesystemConnector, "iter_documents", fake_iter
    )

    result = runner.invoke(
        app,
        [
            "scan",
            "fs",
            "--vault",
            str(vault),
            "--root",
            str(finto_drive_root),
        ],
    )
    # CliRunner cattura KeyboardInterrupt come exit_code != 0.
    assert result.exit_code != 0

    db_path = state_db_path_for_vault(vault)
    with StateStore(db_path) as store:
        row = store._conn.execute(  # type: ignore[attr-defined]
            "SELECT status, summary FROM runs ORDER BY id DESC LIMIT 1"
        ).fetchone()
    assert row is not None
    assert row["status"] == "error"
    assert "Interrotto" in (row["summary"] or "")


def test_scan_fs_dangerous_root_refused(tmp_path: Path) -> None:
    """Root path ``/`` rifiutato dal guardrail (FIX B2)."""
    vault = tmp_path / "vault"
    vault.mkdir()
    run_init(vault)
    result = runner.invoke(
        app,
        [
            "scan",
            "fs",
            "--vault",
            str(vault),
            "--root",
            "/",
        ],
    )
    assert result.exit_code != 0
    assert "troppo permissivo" in result.output


def test_scan_fs_integrity_error_other_than_dup_propagates(
    tmp_path: Path,
    finto_drive_root: Path,
    monkeypatch,
) -> None:
    """Una IntegrityError che NON è duplicato source_id deve far fallire lo
    scan (FIX B15)."""
    import sqlite3

    from custodia_cli.state.store import StateStore as Store

    vault = tmp_path / "vault"
    vault.mkdir()
    run_init(vault)

    real_add = Store.add_document

    def broken_add(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        raise sqlite3.IntegrityError(
            "NOT NULL constraint failed: documents.text"
        )

    monkeypatch.setattr(Store, "add_document", broken_add)

    result = runner.invoke(
        app,
        [
            "scan",
            "fs",
            "--vault",
            str(vault),
            "--root",
            str(finto_drive_root),
        ],
    )
    assert result.exit_code != 0
    # Il run deve risultare in stato error.
    db_path = state_db_path_for_vault(vault)
    with StateStore(db_path) as store:
        row = store._conn.execute(  # type: ignore[attr-defined]
            "SELECT status FROM runs ORDER BY id DESC LIMIT 1"
        ).fetchone()
    assert row["status"] == "error"
