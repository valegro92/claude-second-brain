"""Test del CLI ``wiki``.

Usa ``CliRunner`` di click per smoke test (--help su ogni comando) e per
verificare il routing con una fixture di config minima.
"""

from __future__ import annotations

import json
from datetime import UTC
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from wiki import cli as cli_module
from wiki.cli import main

# --- fixture --------------------------------------------------------------


@pytest.fixture
def isolated_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Repo finto: redirige tutte le costanti del CLI a tmp_path."""
    clients_dir = tmp_path / "bootstrap" / "clients"
    clients_dir.mkdir(parents=True)
    state_dir = tmp_path / "_status"
    state_dir.mkdir()
    inbox_dir = tmp_path / "_inbox"
    inbox_dir.mkdir()
    # Copia il template reale, così write_config lo trova
    real_template = Path(__file__).resolve().parents[1] / "bootstrap" / "config.template.yml"
    template_path = tmp_path / "bootstrap" / "config.template.yml"
    template_path.write_text(real_template.read_text(encoding="utf-8"), encoding="utf-8")

    monkeypatch.setattr(cli_module, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(cli_module, "CLIENTS_DIR", clients_dir)
    monkeypatch.setattr(cli_module, "DEFAULT_STATE_DIR", state_dir)
    monkeypatch.setattr(cli_module, "DEFAULT_INBOX_DIR", inbox_dir)
    monkeypatch.setattr(cli_module, "TEMPLATE_PATH", template_path)
    return tmp_path


def _make_client(repo: Path, slug: str = "acme") -> Path:
    """Crea un cliente con config minimo (tutte sorgenti disattivate)."""
    cdir = repo / "bootstrap" / "clients" / slug
    cdir.mkdir(parents=True, exist_ok=True)
    config = {
        "cliente": {"slug": slug, "nome": "Acme Srl", "custode": "AC", "owner": "VG"},
        "sorgenti": {
            "gdrive": {"enabled": False},
            "m365": {"enabled": False},
            "email": {"enabled": False},
            "nas": {"enabled": False},
            "server": {"enabled": False},
        },
        "filtri_globali": {"max_file_mb": 50, "exclude_extensions": [], "exclude_paths_glob": []},
        "privacy": {"modalita": "safe"},
        "batch": {"size": 50, "cost_alert_eur": 50, "cost_hard_stop_eur": 200},
    }
    (cdir / "config.yml").write_text(yaml.dump(config), encoding="utf-8")
    (repo / "_status" / slug).mkdir(parents=True, exist_ok=True)
    return cdir


# --- smoke: --help on every command ---------------------------------------


@pytest.mark.parametrize(
    "args",
    [
        ["--help"],
        ["init", "--help"],
        ["scan", "--help"],
        ["extract", "--help"],
        ["categorize", "--help"],
        ["reconcile", "--help"],
        ["approve", "--help"],
        ["watch", "--help"],
        ["status", "--help"],
    ],
)
def test_help_smoke(args: list[str]) -> None:
    runner = CliRunner()
    result = runner.invoke(main, args)
    assert result.exit_code == 0, result.output
    assert "Usage:" in result.output or "usage:" in result.output.lower()


def test_version() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


# --- init -----------------------------------------------------------------


def test_init_full_flow(isolated_repo: Path) -> None:
    """`wiki init` con input simulato deve creare config + cartelle."""
    runner = CliRunner()
    # 6 risposte: slug, nome, custode, owner, sorgenti, privacy
    user_input = "acme\nAcme Srl\nAC\nVG\nnas\nsafe\n"
    result = runner.invoke(main, ["init"], input=user_input)
    assert result.exit_code == 0, result.output
    assert "Config scritto" in result.output
    config_path = isolated_repo / "bootstrap" / "clients" / "acme" / "config.yml"
    assert config_path.exists()
    cfg = yaml.safe_load(config_path.read_text())
    assert cfg["cliente"]["slug"] == "acme"
    assert cfg["sorgenti"]["nas"]["enabled"] is True
    assert cfg["sorgenti"]["gdrive"]["enabled"] is False
    assert (isolated_repo / "_inbox" / "acme").exists()
    assert (isolated_repo / "_status").exists()


# --- status ---------------------------------------------------------------


def test_status_empty_client(isolated_repo: Path) -> None:
    _make_client(isolated_repo, "acme")
    runner = CliRunner()
    result = runner.invoke(main, ["status", "--client", "acme"])
    assert result.exit_code == 0, result.output
    assert "acme" in result.output
    assert "Estratti: 0" in result.output


def test_status_no_clients(isolated_repo: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["status"])
    assert result.exit_code != 0
    assert "Nessun cliente" in result.output


def test_status_multiple_clients_needs_flag(isolated_repo: Path) -> None:
    _make_client(isolated_repo, "acme")
    _make_client(isolated_repo, "globex")
    runner = CliRunner()
    result = runner.invoke(main, ["status"])
    assert result.exit_code != 0
    assert "Più clienti" in result.output


# --- scan -----------------------------------------------------------------


def test_scan_no_active_sources(isolated_repo: Path) -> None:
    """Senza sorgenti attive il comando esce pulito con messaggio."""
    _make_client(isolated_repo, "acme")
    runner = CliRunner()
    result = runner.invoke(main, ["scan", "--client", "acme"])
    assert result.exit_code == 0, result.output
    assert "Nessuna sorgente attiva" in result.output


def test_scan_invalid_client(isolated_repo: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["scan", "--client", "non-esiste"])
    assert result.exit_code != 0


# --- extract / categorize / reconcile su inventory vuoto ------------------


def test_extract_empty_inventory(isolated_repo: Path) -> None:
    _make_client(isolated_repo, "acme")
    runner = CliRunner()
    result = runner.invoke(main, ["extract", "--client", "acme"])
    assert result.exit_code == 0
    assert "Nessun inventory" in result.output


def test_categorize_empty_inventory(isolated_repo: Path) -> None:
    _make_client(isolated_repo, "acme")
    runner = CliRunner()
    result = runner.invoke(main, ["categorize", "--client", "acme"])
    assert result.exit_code == 0
    assert "Nessun inventory" in result.output


def test_reconcile_empty_inventory(isolated_repo: Path) -> None:
    _make_client(isolated_repo, "acme")
    runner = CliRunner()
    result = runner.invoke(main, ["reconcile", "--client", "acme"])
    assert result.exit_code == 0
    assert "Nessun inventory" in result.output


# --- categorize con record reali nell'inventory ---------------------------


def test_categorize_counts_real_records(isolated_repo: Path) -> None:
    _make_client(isolated_repo, "acme")
    inv_dir = isolated_repo / "_status" / "acme" / "inventory"
    inv_dir.mkdir(parents=True, exist_ok=True)
    # Costruiamo 2 record validi
    from datetime import datetime

    from scanners._base import FileRecord

    r1 = FileRecord(
        source="nas",
        source_id="a",
        path="commerciale/x.pdf",
        name="x.pdf",
        size=1000,
        mtime=datetime.now(UTC),
        sha256="a" * 64,
    )
    r2 = FileRecord(
        source="nas",
        source_id="b",
        path="vecchio/y.pdf",
        name="y.pdf",
        size=1000,
        mtime=datetime(2010, 1, 1, tzinfo=UTC),
        sha256="b" * 64,
    )
    (inv_dir / "nas.jsonl").write_text(
        r1.to_jsonl() + "\n" + r2.to_jsonl() + "\n", encoding="utf-8"
    )
    runner = CliRunner()
    result = runner.invoke(main, ["categorize", "--client", "acme"])
    assert result.exit_code == 0, result.output
    assert "Categorizzati: 2" in result.output
    summary = json.loads(
        (isolated_repo / "_status" / "acme" / "audit" / "categorize.summary.json").read_text()
    )
    assert summary["total"] == 2


# --- approve: senza batch_ui deve fallire con messaggio chiaro ------------


def test_approve_without_batch_ui_module(
    isolated_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`wiki approve` deve dire chiaramente se batch_ui.cli manca."""
    _make_client(isolated_repo, "acme")
    # Forza l'import a fallire
    import sys as _sys

    monkeypatch.setitem(_sys.modules, "batch_ui.cli", None)
    runner = CliRunner()
    result = runner.invoke(main, ["approve", "--client", "acme"])
    # Può fallire perché batch_ui.cli non esiste come modulo:
    # il test verifica che il messaggio sia leggibile, non il successo.
    assert result.exit_code != 0
    assert "batch_ui" in result.output or "Modulo" in result.output
