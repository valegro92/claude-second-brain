"""E2E test del comando `custodia write` + verifica consumabilità MCP."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml
from typer.testing import CliRunner

from custodia_cli.commands.init import (
    run_init,
    state_db_path_for_vault,
)
from custodia_cli.main import app
from custodia_cli.state import StateStore

runner = CliRunner()


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Replica della parse_frontmatter dell'MCP server (per non importare il pkg)."""
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    fm_text = text[4:end]
    body = text[end + 5 :]
    try:
        fm = yaml.safe_load(fm_text) or {}
    except yaml.YAMLError:
        fm = {}
    return fm, body


def _setup_approved_entities(vault: Path) -> None:
    vault.mkdir(exist_ok=True)
    run_init(vault)
    db = state_db_path_for_vault(vault)
    with StateStore(db) as store:
        pk1 = store.upsert_entity(
            entity_type="cliente",
            entity_id="acme",
            frontmatter={"tipo": "cliente", "nome": "Acme SpA"},
            body_md="# Acme SpA\n\nNote.\n",
            source_doc_ids=[],
            confidence=0.9,
        )
        pk2 = store.upsert_entity(
            entity_type="cliente",
            entity_id="delta",
            frontmatter={"tipo": "cliente", "nome": "Delta SRL"},
            body_md="# Delta SRL\n",
            source_doc_ids=[],
            confidence=0.85,
        )
        pk3 = store.upsert_entity(
            entity_type="cliente",
            entity_id="rifiutato",
            frontmatter={"tipo": "cliente", "nome": "Skippato"},
            body_md="",
            source_doc_ids=[],
            confidence=0.5,
        )
        store.record_review_decision(entity_pk=pk1, decision="approved")
        store.record_review_decision(entity_pk=pk2, decision="approved")
        store.record_review_decision(entity_pk=pk3, decision="rejected")


def test_write_creates_md_files(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    _setup_approved_entities(vault)
    result = runner.invoke(app, ["write", "--vault", str(vault)])
    assert result.exit_code == 0, result.stdout
    assert (vault / "clienti" / "acme.md").exists()
    assert (vault / "clienti" / "delta.md").exists()
    # rejected non viene scritto
    assert not (vault / "clienti" / "rifiutato.md").exists()


def test_write_idempotent(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    _setup_approved_entities(vault)
    runner.invoke(app, ["write", "--vault", str(vault)])
    # Seconda chiamata: nulla da scrivere (written_at settato)
    result = runner.invoke(app, ["write", "--vault", str(vault)])
    assert result.exit_code == 0
    assert "nessuna entity" in result.stdout.lower()


def test_write_output_parseable_by_mcp(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    _setup_approved_entities(vault)
    runner.invoke(app, ["write", "--vault", str(vault)])
    text = (vault / "clienti" / "acme.md").read_text(encoding="utf-8")
    fm, body = _parse_frontmatter(text)
    assert fm["tipo"] == "cliente"
    assert fm["nome"] == "Acme SpA"
    assert "Acme SpA" in body


def _load_mcp_vault_class():
    """Carica la classe ``Vault`` dal file custodia_mcp.py via importlib,
    saltando l'import del modulo ``mcp`` (FastMCP) che potrebbe non essere
    installato nel venv del CLI. Estrae solo le funzioni/classi che ci
    servono per il check di consumabilità.

    Strategia: leggiamo il sorgente, isoliamo le definizioni di
    ``parse_frontmatter`` e ``Vault`` e le exec-uiamo in un namespace minimo.
    """
    mcp_path = (
        Path(__file__).resolve().parents[2] / "mcp-server" / "custodia_mcp.py"
    )
    src = mcp_path.read_text(encoding="utf-8")
    # Trova le definizioni di parse_frontmatter e Vault.
    pf_start = src.index("def parse_frontmatter")
    vault_start = src.index("class Vault")
    vault_end = src.index("\ndef build_server")
    snippet = src[pf_start:vault_end]
    ns: dict = {"__name__": "_mcp_vault_subset"}
    exec(
        "from __future__ import annotations\n"
        "import re\n"
        "from pathlib import Path\n"
        "from typing import Any\n"
        "import yaml\n"
        + snippet,
        ns,
    )
    return ns["Vault"]


def test_write_consumable_by_mcp_server_vault(tmp_path: Path) -> None:
    """Smoke E2E: il vault prodotto è consumabile da Vault.list_clients()."""
    Vault = _load_mcp_vault_class()

    vault = tmp_path / "vault"
    _setup_approved_entities(vault)
    runner.invoke(app, ["write", "--vault", str(vault)])

    mcp_vault = Vault(vault)
    clients = mcp_vault.list_clients()
    ids = sorted(c["id"] for c in clients)
    assert ids == ["acme", "delta"]
    detail = mcp_vault.get_client("acme")
    assert "error" not in detail
    assert detail["frontmatter"]["nome"] == "Acme SpA"


def test_write_no_backup_flag(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    _setup_approved_entities(vault)
    runner.invoke(app, ["write", "--vault", str(vault)])
    # Forza re-write con contenuto diverso aggiungendo nuova entity con
    # stesso path e contenuto diverso.
    db = state_db_path_for_vault(vault)
    with StateStore(db) as store:
        pk = store.upsert_entity(
            entity_type="cliente",
            entity_id="acme",  # stesso id → riscrittura
            frontmatter={"tipo": "cliente", "nome": "Acme NUOVO"},
            body_md="",
            source_doc_ids=[],
            confidence=0.9,
        )
        # upsert ha forzato status=pending. Approva e fai sì che written_at
        # sia NULL: upsert NON resetta written_at, ma lo status=pending
        # significa che NON apparirà in list_pending_writes finché non
        # ri-approvato. Approviamo e resetiamo written_at via SQL diretto.
        store.record_review_decision(entity_pk=pk, decision="approved")
        store._conn.execute(
            "UPDATE entities SET written_at = NULL WHERE id = ?", (pk,)
        )
        store._conn.commit()
    result = runner.invoke(
        app, ["write", "--vault", str(vault), "--no-backup"]
    )
    assert result.exit_code == 0
    backups_dir = vault / ".custodia-backups"
    # Non deve esistere alcun backup di acme (--no-backup attivo)
    if backups_dir.exists():
        backups = list(backups_dir.glob("acme_*.md"))
        assert backups == []


def test_write_no_approved_entities(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    run_init(vault)
    result = runner.invoke(app, ["write", "--vault", str(vault)])
    assert result.exit_code == 0
    assert "nessuna entity" in result.stdout.lower()


def test_write_missing_state_fails(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    result = runner.invoke(app, ["write", "--vault", str(vault)])
    assert result.exit_code == 1
    assert "init" in result.stdout.lower()
