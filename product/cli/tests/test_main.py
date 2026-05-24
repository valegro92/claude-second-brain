"""Test smoke sull'entry point CLI: struttura comandi e stub."""

from __future__ import annotations

from typer.testing import CliRunner

from custodia_cli.main import app

runner = CliRunner()


def test_help_lists_all_subcommands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    out = result.stdout
    for cmd in ("init", "scan", "build", "review", "write"):
        assert cmd in out, f"comando {cmd!r} mancante in --help:\n{out}"


def test_scan_help_lists_drive_and_fs() -> None:
    result = runner.invoke(app, ["scan", "--help"])
    assert result.exit_code == 0
    assert "drive" in result.stdout
    assert "fs" in result.stdout


def test_build_help_lists_subcommands() -> None:
    result = runner.invoke(app, ["build", "--help"])
    assert result.exit_code == 0
    for sub in ("clients", "fornitori", "commesse", "communications"):
        assert sub in result.stdout, f"sub {sub!r} mancante in build --help"


def test_scan_drive_help_is_documented() -> None:
    """Dopo U3, `scan drive` non è più uno stub: ha opzioni reali documentate."""
    result = runner.invoke(app, ["scan", "drive", "--help"])
    assert result.exit_code == 0
    out = result.stdout.lower()
    # Le opzioni reali del comando devono essere presenti nell'help.
    assert "--root-folder-id" in out
    assert "--vault" in out
    assert "dry-run" in out


def test_scan_fs_help_is_documented() -> None:
    """Dopo U4, `scan fs` non è più uno stub: ha opzioni reali documentate."""
    result = runner.invoke(app, ["scan", "fs", "--help"])
    assert result.exit_code == 0
    out = result.stdout.lower()
    assert "--root" in out
    assert "--vault" in out
    assert "--exclude" in out


def test_build_clients_requires_vault_option() -> None:
    """U5 implemented: `build clients` ora richiede --vault e non è più uno stub."""
    result = runner.invoke(app, ["build", "clients"])
    # Manca --vault → exit non-zero da Typer (usage error).
    assert result.exit_code != 0


def test_review_requires_vault_option() -> None:
    """U6 implemented: `review` ora richiede --vault e non è più uno stub."""
    result = runner.invoke(app, ["review"])
    # Manca --vault → exit non-zero da Typer (usage error).
    assert result.exit_code != 0


def test_write_requires_vault_option() -> None:
    """U6 implemented: `write` ora richiede --vault e non è più uno stub."""
    result = runner.invoke(app, ["write"])
    assert result.exit_code != 0
