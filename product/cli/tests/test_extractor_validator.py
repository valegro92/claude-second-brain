"""Test del validator del frontmatter vs schema canonical."""

from __future__ import annotations

from custodia_cli.extractor.validator import validate_entity


def test_validate_cliente_minimal_valid() -> None:
    """Frontmatter con solo i campi required → valido."""
    fm = {"tipo": "cliente", "nome": "Esempio SRL"}
    valid, errors = validate_entity(fm, "cliente")
    assert valid is True
    assert errors == []


def test_validate_cliente_missing_nome() -> None:
    """Manca `nome` → invalido."""
    fm = {"tipo": "cliente"}
    valid, errors = validate_entity(fm, "cliente")
    assert valid is False
    assert any("nome" in e for e in errors)


def test_validate_cliente_wrong_type_for_piva() -> None:
    """`piva` deve essere string; passandola come int → invalido."""
    fm = {
        "tipo": "cliente",
        "nome": "X",
        "piva": 12345,
    }
    valid, errors = validate_entity(fm, "cliente")
    assert valid is False
    assert any("piva" in e for e in errors)


def test_validate_cliente_complete_frontmatter() -> None:
    """Un frontmatter completo con tutti i campi tipo della scheda canonical."""
    fm = {
        "tipo": "cliente",
        "nome": "Rossetto Laminazioni SRL",
        "piva": "03421560289",
        "settore": "metalmeccanica",
        "sede": "Vicenza",
        "referente_principale": "Marco Rossetto",
        "condizioni_commerciali": {"sconto_listino": "12%"},
        "eccezioni_concordate": [],
        "prodotti_ricorrenti": ["lamiere"],
        "red_flag": [],
    }
    valid, errors = validate_entity(fm, "cliente")
    assert valid is True, errors


def test_validate_unknown_entity_type() -> None:
    """Entity type sconosciuto → invalido con messaggio diagnostico."""
    valid, errors = validate_entity({}, "alieno")
    assert valid is False
    assert any("schema canonical" in e for e in errors)


def test_validate_fornitore_minimal() -> None:
    """Schema fornitore richiede tipo+nome."""
    fm = {"tipo": "fornitore", "nome": "Esempio Fornitore SRL"}
    valid, errors = validate_entity(fm, "fornitore")
    assert valid is True, errors


def test_validate_commessa_minimal() -> None:
    """Schema commessa richiede tipo+nome."""
    fm = {"tipo": "commessa", "nome": "Commessa X 2026"}
    valid, errors = validate_entity(fm, "commessa")
    assert valid is True, errors
