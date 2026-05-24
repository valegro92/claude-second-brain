"""
Merger di EntityCandidate multipli (stesso entity_id) provenienti da chunk
diversi o da più documenti che parlano della stessa entità.

Regole (D5 del piano Sprint 1):
- Scalari (str/int/float/bool/None): preferisci valore non-null. Conflitto →
  scegli quello dal candidato con confidence maggiore; pari merito → primo.
- Liste: UNION + dedupe preservando ordine di prima apparizione.
- Dict (es. condizioni_commerciali): merge ricorsivo applicando le stesse regole.
- Stringhe "long-form" (es. note_relazionali): concat con separator markdown.
- confidence finale: media (semplice, senza pesi — sufficiente per v0.1).
- source_doc_ids: union.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


# Chiavi che contengono prose "long-form": meglio appenderle invece di
# discriminare per confidence (informazione complementare, non conflittuale).
_LONG_FORM_KEYS: frozenset[str] = frozenset(
    {"note_relazionali", "note", "body", "descrizione"}
)

_LONG_FORM_SEPARATOR: str = "\n\n---\n\n"


def _is_empty(value: Any) -> bool:
    """True se il valore è None, stringa vuota/whitespace, lista o dict vuoto."""
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    if isinstance(value, (list, dict)):
        return len(value) == 0
    return False


def _merge_scalars(
    *,
    key: str,
    a_value: Any,
    a_conf: float,
    b_value: Any,
    b_conf: float,
) -> Any:
    """Scegli fra due scalari preferendo non-null e confidence più alta."""
    if _is_empty(a_value):
        return b_value
    if _is_empty(b_value):
        return a_value
    if a_value == b_value:
        return a_value
    # Conflitto reale.
    if a_conf >= b_conf:
        winner = a_value
    else:
        winner = b_value
    logger.warning(
        "merger: conflitto sul campo %r — a=%r (conf=%.2f) vs b=%r (conf=%.2f) → tengo %r",
        key,
        a_value,
        a_conf,
        b_value,
        b_conf,
        winner,
    )
    return winner


def _union_lists(a: list[Any], b: list[Any]) -> list[Any]:
    """Union dedupe preservando ordine. Items hashable: usa set; altrimenti compara per uguaglianza."""
    result: list[Any] = []
    seen_hashable: set[Any] = set()
    seen_unhashable: list[Any] = []
    for item in list(a) + list(b):
        try:
            if item in seen_hashable:
                continue
            seen_hashable.add(item)
            result.append(item)
        except TypeError:
            # Item non-hashable (dict, list): fallback su compare list.
            if item in seen_unhashable:
                continue
            seen_unhashable.append(item)
            result.append(item)
    return result


def _merge_long_form(a: str, b: str) -> str:
    """Concat di stringhe long-form con separator markdown.

    Se uno dei due è vuoto, ritorna l'altro intatto.
    """
    a_s = (a or "").strip()
    b_s = (b or "").strip()
    if not a_s:
        return b_s
    if not b_s:
        return a_s
    if a_s == b_s:
        return a_s
    return a_s + _LONG_FORM_SEPARATOR + b_s


def _merge_dicts(
    *,
    a: dict[str, Any],
    a_conf: float,
    b: dict[str, Any],
    b_conf: float,
) -> dict[str, Any]:
    """Merge ricorsivo di due dict (es. condizioni_commerciali)."""
    result: dict[str, Any] = {}
    keys = set(a.keys()) | set(b.keys())
    for key in keys:
        a_val = a.get(key)
        b_val = b.get(key)
        result[key] = _merge_field(
            key=key, a_value=a_val, a_conf=a_conf, b_value=b_val, b_conf=b_conf
        )
    return result


def _merge_field(
    *,
    key: str,
    a_value: Any,
    a_conf: float,
    b_value: Any,
    b_conf: float,
) -> Any:
    """Dispatch del merge in base al tipo del campo.

    Determina il tipo da `a_value` se non-empty, altrimenti da `b_value`.
    """
    # Long-form override.
    if key in _LONG_FORM_KEYS:
        return _merge_long_form(
            str(a_value) if a_value is not None else "",
            str(b_value) if b_value is not None else "",
        )

    # Se uno è empty, fallback al non-empty (semplifica i casi misti).
    if _is_empty(a_value):
        return b_value
    if _is_empty(b_value):
        return a_value

    # Stesso tipo composito.
    if isinstance(a_value, list) and isinstance(b_value, list):
        return _union_lists(a_value, b_value)
    if isinstance(a_value, dict) and isinstance(b_value, dict):
        return _merge_dicts(a=a_value, a_conf=a_conf, b=b_value, b_conf=b_conf)

    # Tipi diversi (es. lista vs scalare): scegli per confidence.
    return _merge_scalars(
        key=key, a_value=a_value, a_conf=a_conf, b_value=b_value, b_conf=b_conf
    )


def merge_entity_candidates(candidates: list[Any]) -> Any:
    """Merge di N EntityCandidate con stesso entity_type/entity_id.

    Args:
        candidates: lista non vuota. Tutti devono avere lo stesso
            (entity_type, entity_id). Il chiamante è responsabile del grouping.

    Returns:
        Un singolo EntityCandidate aggregato. Type-hint è `Any` per evitare
        ciclo di import con extractor.extractor.

    Raises:
        ValueError: lista vuota o entity_id/entity_type non omogenei.
    """
    if not candidates:
        raise ValueError("merge_entity_candidates: lista candidati vuota.")
    # Verifica omogeneità.
    et = candidates[0].entity_type
    eid = candidates[0].entity_id
    for c in candidates[1:]:
        if c.entity_type != et or c.entity_id != eid:
            raise ValueError(
                "merge_entity_candidates: candidati eterogenei "
                f"({et}/{eid} vs {c.entity_type}/{c.entity_id})."
            )

    if len(candidates) == 1:
        return candidates[0]

    # Fold left-to-right.
    from custodia_cli.extractor.extractor import EntityCandidate  # late import per evitare ciclo

    acc = candidates[0]
    acc_conf = acc.confidence
    for nxt in candidates[1:]:
        merged_fm: dict[str, Any] = {}
        keys = set(acc.frontmatter.keys()) | set(nxt.frontmatter.keys())
        for key in keys:
            merged_fm[key] = _merge_field(
                key=key,
                a_value=acc.frontmatter.get(key),
                a_conf=acc_conf,
                b_value=nxt.frontmatter.get(key),
                b_conf=nxt.confidence,
            )

        merged_body = _merge_long_form(acc.body_md, nxt.body_md)
        merged_ids = _union_lists(list(acc.source_doc_ids), list(nxt.source_doc_ids))
        # Media semplice (D5 v0.1).
        new_conf = (acc_conf + nxt.confidence) / 2.0

        acc = EntityCandidate(
            entity_type=et,
            entity_id=eid,
            frontmatter=merged_fm,
            body_md=merged_body,
            source_doc_ids=merged_ids,
            confidence=new_conf,
        )
        acc_conf = new_conf

    return acc


__all__ = ["merge_entity_candidates"]
