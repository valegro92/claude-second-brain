"""Test writer del vault: idempotenza, backup, formato MCP-compatibile."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

from custodia_cli.review.writer import (
    WriteResult,
    render_markdown,
    write_entities,
)


# Riproduco la logica di parse_frontmatter dell'MCP server per non importare
# il package mcp-server (path con trattino non importabile direttamente).
def _parse_frontmatter(text: str) -> tuple[dict, str]:
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


def _entity(
    entity_id: str = "acme",
    entity_type: str = "cliente",
    frontmatter: dict | None = None,
    body_md: str = "# Acme\n\nNote.\n",
) -> dict:
    return {
        "id": 1,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "frontmatter": frontmatter or {"tipo": entity_type, "nome": "Acme"},
        "body_md": body_md,
        "status": "approved",
    }


def test_render_markdown_mcp_compatible() -> None:
    md = render_markdown({"tipo": "cliente", "nome": "X"}, "Body", "cliente")
    fm, body = _parse_frontmatter(md)
    assert fm == {"tipo": "cliente", "nome": "X"}
    assert body.strip() == "Body"


def test_write_creates_file(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    result = write_entities([_entity()], vault)
    target = vault / "clienti" / "acme.md"
    assert target.exists()
    assert len(result.written) == 1
    assert not result.skipped
    assert not result.backups
    # parsable da MCP-style parser
    fm, body = _parse_frontmatter(target.read_text(encoding="utf-8"))
    assert fm["nome"] == "Acme"
    assert "Note" in body


def test_write_idempotent_no_backup_when_unchanged(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    write_entities([_entity()], vault)
    # Seconda esecuzione: contenuto identico → skipped, no backup
    result = write_entities([_entity()], vault)
    assert not result.written
    assert len(result.skipped) == 1
    assert not result.backups


def test_write_creates_backup_on_change(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    write_entities([_entity()], vault)
    ent2 = _entity(frontmatter={"tipo": "cliente", "nome": "Acme NUOVO"})
    result = write_entities([ent2], vault)
    assert len(result.written) == 1
    assert len(result.backups) == 1
    backup = result.backups[0]
    assert backup.exists()
    assert "Acme" in backup.read_text(encoding="utf-8")
    # Il file vault ora contiene il valore nuovo.
    target = vault / "clienti" / "acme.md"
    assert "Acme NUOVO" in target.read_text(encoding="utf-8")


def test_write_no_backup_flag(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    write_entities([_entity()], vault)
    ent2 = _entity(frontmatter={"tipo": "cliente", "nome": "Y"})
    result = write_entities([ent2], vault, backup=False)
    assert len(result.written) == 1
    assert len(result.backups) == 0


def test_write_multiple_entity_types(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    ents = [
        _entity("acme", "cliente"),
        _entity(
            "delta",
            "fornitore",
            frontmatter={"tipo": "fornitore", "nome": "Delta"},
        ),
    ]
    result = write_entities(ents, vault)
    assert (vault / "clienti" / "acme.md").exists()
    assert (vault / "fornitori" / "delta.md").exists()
    assert len(result.written) == 2


def test_write_target_path_uses_canonical_plural(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    ent = _entity("e1", "comunicazione", frontmatter={"tipo": "comunicazione"})
    write_entities([ent], vault)
    assert (vault / "inbox" / "e1.md").exists()


def test_write_handles_missing_frontmatter_and_body(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    ent = {
        "id": 1,
        "entity_type": "cliente",
        "entity_id": "vuoto",
        "frontmatter": {},
        "body_md": "",
        "status": "approved",
    }
    result = write_entities([ent], vault)
    assert len(result.written) == 1
    text = (vault / "clienti" / "vuoto.md").read_text(encoding="utf-8")
    assert text.startswith("---\n")
