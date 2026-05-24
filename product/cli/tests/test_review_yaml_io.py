"""Test serializzazione YAML deterministica per i file `.md` del vault."""

from __future__ import annotations

import yaml

from custodia_cli.review.yaml_io import (
    ENTITY_TYPE_PLURAL,
    dump_frontmatter,
    ordered_keys_for_type,
)


def test_dump_empty_dict() -> None:
    assert dump_frontmatter({}) == ""


def test_dump_preserves_order_with_explicit_keys() -> None:
    payload = {"settore": "metal", "tipo": "cliente", "nome": "Acme"}
    keys = ordered_keys_for_type("cliente")
    out = dump_frontmatter(payload, keys)
    lines = [ln for ln in out.splitlines() if ":" in ln]
    # `tipo` deve precedere `nome` deve precedere `settore` (ordine canonical).
    assert lines[0].startswith("tipo:")
    assert lines[1].startswith("nome:")
    assert lines[2].startswith("settore:")


def test_dump_multiline_string_uses_block_style() -> None:
    payload = {"note_relazionali": "riga1\nriga2\nriga3"}
    out = dump_frontmatter(payload)
    # Forma block: `note_relazionali: |`
    assert "note_relazionali: |" in out
    assert "riga1" in out
    assert "riga2" in out


def test_dump_unicode_preserved() -> None:
    payload = {"nome": "Società Italiana à è ò"}
    out = dump_frontmatter(payload)
    assert "Società Italiana à è ò" in out


def test_roundtrip_yaml_safe_load() -> None:
    payload = {
        "tipo": "cliente",
        "nome": "Test",
        "lista": ["a", "b", "c"],
        "nested": {"k": 1, "k2": [1, 2]},
        "note_relazionali": "riga1\nriga2",
        "nullo": None,
    }
    out = dump_frontmatter(payload, ordered_keys_for_type("cliente"))
    parsed = yaml.safe_load(out)
    assert parsed == payload


def test_dump_keys_not_in_ordered_appended_last() -> None:
    payload = {"nome": "X", "campo_custom": "y", "tipo": "cliente"}
    keys = ordered_keys_for_type("cliente")
    out = dump_frontmatter(payload, keys)
    lines = [ln.split(":", 1)[0] for ln in out.splitlines() if ":" in ln]
    # tipo e nome sono in canonical, campo_custom no → appended in coda
    assert lines.index("tipo") < lines.index("nome")
    assert lines.index("campo_custom") > lines.index("nome")


def test_ordered_keys_known_types() -> None:
    assert ordered_keys_for_type("cliente")[0] == "tipo"
    assert "nome" in ordered_keys_for_type("fornitore")
    assert ordered_keys_for_type("ignoto") == []


def test_entity_type_plural_map() -> None:
    assert ENTITY_TYPE_PLURAL["cliente"] == "clienti"
    assert ENTITY_TYPE_PLURAL["fornitore"] == "fornitori"
    assert ENTITY_TYPE_PLURAL["comunicazione"] == "inbox"
