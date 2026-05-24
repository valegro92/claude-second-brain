"""Test del comando `custodia init`."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from custodia_cli.commands.init import state_db_path_for_vault
from custodia_cli.main import app
from custodia_cli.state import SCHEMA_VERSION, StateStore

runner = CliRunner()


def test_init_creates_state_db(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()

    result = runner.invoke(app, ["init", "--vault", str(vault)])
    assert result.exit_code == 0, result.stdout
    assert "inizializzato" in result.stdout.lower()

    db_path = state_db_path_for_vault(vault)
    assert db_path.exists()
    assert db_path.parent.name == ".custodia-state"
    # Lo stato deve stare fuori dal vault
    assert db_path.parent.parent == vault.parent


def test_init_idempotent(tmp_path: Path) -> None:
    """FIX G: la seconda init non deve distruggere il DB esistente.

    Inseriamo un run reale fra le due chiamate e verifichiamo che sopravviva.
    """
    vault = tmp_path / "vault"
    vault.mkdir()

    first = runner.invoke(app, ["init", "--vault", str(vault)])
    assert first.exit_code == 0

    db_path = state_db_path_for_vault(vault)
    with StateStore(db_path) as store:
        run_id = store.register_run(command="test", args={"k": "v"})
        assert run_id >= 1

    second = runner.invoke(app, ["init", "--vault", str(vault)])
    assert second.exit_code == 0
    assert "già presente" in second.stdout.lower() or "no-op" in second.stdout.lower() \
        or "nessuna modifica" in second.stdout.lower()

    # Il run inserito prima della seconda init deve essere ancora presente.
    with StateStore(db_path) as store:
        rows = store._conn.execute("SELECT * FROM runs").fetchall()
        assert len(rows) == 1
        assert rows[0]["command"] == "test"
        assert store.schema_version == SCHEMA_VERSION


def test_init_missing_vault_flag() -> None:
    result = runner.invoke(app, ["init"])
    assert result.exit_code != 0
