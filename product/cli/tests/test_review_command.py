"""E2E test del comando `custodia review` (focus su --yes auto-accept)."""

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


def _setup_vault_with_candidates(tmp_path: Path) -> Path:
    """Crea vault + state store con 2 candidati pending."""
    vault = tmp_path / "vault"
    vault.mkdir()
    run_init(vault)
    db = state_db_path_for_vault(vault)
    with StateStore(db) as store:
        store.upsert_entity(
            entity_type="cliente",
            entity_id="acme",
            frontmatter={"tipo": "cliente", "nome": "Acme SpA"},
            body_md="# Acme SpA\n\nNote.\n",
            source_doc_ids=[],
            confidence=0.9,
        )
        store.upsert_entity(
            entity_type="cliente",
            entity_id="delta",
            frontmatter={"tipo": "cliente", "nome": "Delta SRL"},
            body_md="# Delta SRL\n",
            source_doc_ids=[],
            confidence=0.85,
        )
    return vault


def test_review_yes_accepts_all(tmp_path: Path) -> None:
    vault = _setup_vault_with_candidates(tmp_path)
    result = runner.invoke(
        app, ["review", "--vault", str(vault), "--yes"]
    )
    assert result.exit_code == 0, result.stdout
    db = state_db_path_for_vault(vault)
    with StateStore(db) as store:
        pending = store.list_pending_entities()
        assert pending == []
        writes = store.list_pending_writes()
        assert len(writes) == 2
        ids = sorted(e["entity_id"] for e in writes)
        assert ids == ["acme", "delta"]


def test_review_no_pending_prints_message(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    run_init(vault)
    result = runner.invoke(
        app, ["review", "--vault", str(vault), "--yes"]
    )
    assert result.exit_code == 0
    assert "nessun candidato" in result.stdout.lower()


def test_review_missing_state_fails(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    # no init
    result = runner.invoke(
        app, ["review", "--vault", str(vault), "--yes"]
    )
    assert result.exit_code == 1
    assert "init" in result.stdout.lower()


def test_review_invalid_entity_type(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    run_init(vault)
    result = runner.invoke(
        app,
        [
            "review",
            "--vault",
            str(vault),
            "--entity-type",
            "bogus",
            "--yes",
        ],
    )
    assert result.exit_code == 1


def test_review_filter_by_entity_type(tmp_path: Path) -> None:
    vault = _setup_vault_with_candidates(tmp_path)
    db = state_db_path_for_vault(vault)
    with StateStore(db) as store:
        store.upsert_entity(
            entity_type="fornitore",
            entity_id="omega",
            frontmatter={"tipo": "fornitore", "nome": "Omega"},
            body_md="",
            source_doc_ids=[],
            confidence=0.8,
        )
    result = runner.invoke(
        app,
        [
            "review",
            "--vault",
            str(vault),
            "--entity-type",
            "cliente",
            "--yes",
        ],
    )
    assert result.exit_code == 0
    with StateStore(db) as store:
        # fornitore omega rimane pending; clienti sono approved
        pending = store.list_pending_entities()
        assert len(pending) == 1
        assert pending[0]["entity_id"] == "omega"
