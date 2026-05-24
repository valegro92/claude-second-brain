"""
Schema loader canonical: legge una scheda demo dal vault e ne deriva un JSON
Schema utilizzabile per (a) prompting LLM, (b) validazione, (c) review.

Source-of-truth è il filesystem `product/vault-demo/`: questo rende la scheda
demo "canone vivo" — se il consulente arricchisce la scheda Rossetto con un
nuovo campo, il prompt e il validator si aggiornano automaticamente.

Strategy: parsing YAML frontmatter, type inference per ogni chiave, schema
JSON con solo `nome` e `tipo` required (gli altri sono optional ma desiderati).
"""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import Any

import yaml


# Path canonical per ogni entity_type. Risolto al runtime relativamente al
# package (così funziona sia in dev install che da wheel installato).
_REPO_ROOT = Path(__file__).resolve().parents[3]
_VAULT_DEMO = _REPO_ROOT / "vault-demo"

_CANONICAL_FILES: dict[str, Path] = {
    "cliente": _VAULT_DEMO / "clienti" / "rossetto-laminazioni.md",
    "fornitore": _VAULT_DEMO / "fornitori" / "template-fornitore.md",
    "commessa": _VAULT_DEMO / "commesse" / "template-commessa.md",
    "comunicazione": _VAULT_DEMO / "inbox" / "2026-05-21-bianchi-richiesta-sconto.md",
}

_SUPPORTED_TYPES: tuple[str, ...] = tuple(_CANONICAL_FILES.keys())


def _parse_frontmatter(text: str) -> dict[str, Any]:
    """Estrae il blocco YAML frontmatter delimitato da `---` ... `---`.

    Solleva ValueError se il file non ha un frontmatter ben formato.
    """
    if not text.startswith("---"):
        raise ValueError("File senza frontmatter (manca apertura ---).")
    # Splitta sul secondo "---" (escludendo il primo all'inizio).
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise ValueError("Frontmatter non chiuso (manca seconda riga ---).")
    yaml_block = parts[1]
    data = yaml.safe_load(yaml_block)
    if not isinstance(data, dict):
        raise ValueError("Frontmatter non è un mapping YAML valido.")
    return data


def _infer_type(value: Any, *, nullable: bool = True) -> dict[str, Any]:
    """Inferenza tipo JSON-Schema da un sample value Python.

    Mappa:
    - bool → boolean
    - int → integer
    - float → number
    - str / date / datetime → string
    - list → array (items inferito dal primo elemento, se presente)
    - dict → object (proprietà inferite ricorsivamente, nessun required)
    - None → tipo permissivo (nessun constraint) — viene scritto come {} per
      compatibilità con jsonschema.validate (sempre valido).

    Args:
        nullable: se True, il tipo è "<inferred> | null" (default).
            Permette all'LLM di tornare null per campi non desumibili dai
            documenti senza far fallire la validazione.
    """
    if value is None:
        return {}  # nessun constraint
    if isinstance(value, bool):
        types: list[str] = ["boolean"]
    elif isinstance(value, int):
        types = ["integer"]
    elif isinstance(value, float):
        types = ["number"]
    elif isinstance(value, (str, datetime.date, datetime.datetime)):
        types = ["string"]
    elif isinstance(value, list):
        node: dict[str, Any] = {"type": "array"}
        if value:
            node["items"] = _infer_type(value[0], nullable=True)
        if nullable:
            node["type"] = ["array", "null"]
        return node
    elif isinstance(value, dict):
        props: dict[str, Any] = {}
        for k, v in value.items():
            props[str(k)] = _infer_type(v, nullable=True)
        node = {"type": "object", "properties": props}
        if nullable:
            node["type"] = ["object", "null"]
        return node
    else:
        types = ["string"]

    if nullable:
        types.append("null")
    return {"type": types if len(types) > 1 else types[0]}


def _build_schema(frontmatter: dict[str, Any]) -> dict[str, Any]:
    """Costruisce uno schema JSON dal frontmatter canonical.

    Convention:
    - tutti i campi presenti nel sample diventano proprietà
    - required: solo `nome` e `tipo` (gli altri possono essere null/missing)
    - additionalProperties: True (l'LLM può aggiungere campi se trova info utili)
    - i required NON sono nullable; tutti gli altri sì (LLM può tornare null)
    """
    required_keys = {"tipo", "nome"}
    properties: dict[str, Any] = {}
    for key, value in frontmatter.items():
        nullable = key not in required_keys
        properties[str(key)] = _infer_type(value, nullable=nullable)

    schema: dict[str, Any] = {
        "type": "object",
        "properties": properties,
        "required": [k for k in ("tipo", "nome") if k in properties],
        "additionalProperties": True,
    }
    return schema


def load_canonical_schema(entity_type: str) -> dict[str, Any]:
    """Carica lo schema JSON canonical per un entity_type.

    Args:
        entity_type: uno fra "cliente" | "fornitore" | "commessa" | "comunicazione".

    Returns:
        dict JSON Schema compatibile con jsonschema.validate.

    Raises:
        ValueError: se entity_type non è supportato o se il file canonical
            manca/è malformato.
    """
    if entity_type not in _CANONICAL_FILES:
        raise ValueError(
            f"entity_type {entity_type!r} non supportato. "
            f"Supportati: {_SUPPORTED_TYPES}."
        )

    path = _CANONICAL_FILES[entity_type]
    if not path.is_file():
        raise ValueError(
            f"Scheda canonical per {entity_type!r} mancante: {path}. "
            "Verifica che product/vault-demo/ sia presente e popolato."
        )
    text = path.read_text(encoding="utf-8")
    frontmatter = _parse_frontmatter(text)
    return _build_schema(frontmatter)


def load_canonical_example(entity_type: str) -> dict[str, Any]:
    """Ritorna il frontmatter raw della scheda canonical (per few-shot prompt)."""
    if entity_type not in _CANONICAL_FILES:
        raise ValueError(
            f"entity_type {entity_type!r} non supportato. "
            f"Supportati: {_SUPPORTED_TYPES}."
        )
    path = _CANONICAL_FILES[entity_type]
    text = path.read_text(encoding="utf-8")
    return _parse_frontmatter(text)


__all__ = [
    "load_canonical_schema",
    "load_canonical_example",
]
