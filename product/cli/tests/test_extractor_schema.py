"""Test del loader di schema canonical per Custodia v2 U5."""

from __future__ import annotations

import pytest

from custodia_cli.extractor.schema import (
    load_canonical_example,
    load_canonical_schema,
)


def test_load_canonical_schema_cliente() -> None:
    """Lo schema per `cliente` deriva da rossetto-laminazioni.md."""
    schema = load_canonical_schema("cliente")
    assert schema["type"] == "object"
    assert "tipo" in schema["required"]
    assert "nome" in schema["required"]
    props = schema["properties"]
    # Campi essenziali presenti.
    for key in (
        "tipo",
        "nome",
        "piva",
        "settore",
        "sede",
        "referente_principale",
        "stato_relazione",
        "condizioni_commerciali",
        "eccezioni_concordate",
        "red_flag",
    ):
        assert key in props, f"campo {key!r} mancante nello schema"
    # condizioni_commerciali è un oggetto nidificato (nullable).
    assert "object" in props["condizioni_commerciali"]["type"]
    # eccezioni_concordate è array (nullable).
    assert "array" in props["eccezioni_concordate"]["type"]
    # red_flag è array (nullable).
    assert "array" in props["red_flag"]["type"]


def test_load_canonical_schema_fornitore() -> None:
    """Lo schema per `fornitore` deriva dal template fornitore."""
    schema = load_canonical_schema("fornitore")
    props = schema["properties"]
    for key in ("tipo", "nome", "piva", "prodotti_forniti", "condizioni_commerciali"):
        assert key in props
    assert "nome" in schema["required"]


def test_load_canonical_schema_commessa() -> None:
    """Lo schema per `commessa` deriva dal template commessa."""
    schema = load_canonical_schema("commessa")
    props = schema["properties"]
    for key in ("tipo", "nome", "cliente_collegato", "valore", "stato"):
        assert key in props


def test_load_canonical_schema_comunicazione() -> None:
    """Lo schema per `comunicazione` deriva dalla mail Bianchi."""
    schema = load_canonical_schema("comunicazione")
    props = schema["properties"]
    # `comunicazione` ha schema diverso (mail), niente `nome` ma `oggetto`.
    for key in ("tipo", "da", "data", "oggetto", "stato"):
        assert key in props
    # `tipo` resta required; `nome` non c'è.
    assert "tipo" in schema["required"]


def test_load_canonical_schema_unknown_type() -> None:
    """Tipo non supportato → ValueError chiaro."""
    with pytest.raises(ValueError, match="non supportato"):
        load_canonical_schema("alieno")


def test_load_canonical_example_returns_dict() -> None:
    """load_canonical_example ritorna il frontmatter raw dal vault demo."""
    example = load_canonical_example("cliente")
    assert example["nome"] == "Rossetto Laminazioni SRL"
    assert example["piva"] == "03421560289"
    assert isinstance(example["eccezioni_concordate"], list)
