"""
Validator del frontmatter prodotto dall'LLM contro lo schema canonical.

Usa `jsonschema.validate` ed espone gli errori tradotti in italiano per il
consulente in review (U6).
"""

from __future__ import annotations

from typing import Any

import jsonschema

from custodia_cli.extractor.schema import load_canonical_schema


def _format_error(err: jsonschema.ValidationError) -> str:
    """Trasforma un ValidationError jsonschema in stringa leggibile in italiano."""
    if err.absolute_path:
        path = ".".join(str(p) for p in err.absolute_path)
    else:
        path = "<root>"
    return f"campo {path!r}: {err.message}"


def validate_entity(
    frontmatter: dict[str, Any],
    entity_type: str,
) -> tuple[bool, list[str]]:
    """Valida un dict frontmatter contro lo schema canonical del tipo.

    Args:
        frontmatter: dict prodotto dall'LLM (o dal merger).
        entity_type: uno fra "cliente"|"fornitore"|"commessa"|"comunicazione".

    Returns:
        Tupla `(valid, errors)`. Se `valid=True`, `errors` è vuota.
        Errori sono stringhe italiane pronte per il display.
    """
    try:
        schema = load_canonical_schema(entity_type)
    except ValueError as exc:
        return False, [f"schema canonical non caricabile: {exc}"]

    validator_cls = jsonschema.Draft7Validator
    validator = validator_cls(schema)
    errors = sorted(validator.iter_errors(frontmatter), key=lambda e: list(e.path))
    if not errors:
        return True, []
    return False, [_format_error(e) for e in errors]


__all__ = ["validate_entity"]
