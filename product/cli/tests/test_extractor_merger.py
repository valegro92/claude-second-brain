"""Test del merger di EntityCandidate."""

from __future__ import annotations

import pytest

from custodia_cli.extractor.extractor import EntityCandidate
from custodia_cli.extractor.merger import merge_entity_candidates


def _make(**kw):
    """Helper per costruire EntityCandidate con default sensati."""
    defaults = dict(
        entity_type="cliente",
        entity_id="rossetto",
        frontmatter={},
        body_md="",
        source_doc_ids=[],
        confidence=1.0,
    )
    defaults.update(kw)
    return EntityCandidate(**defaults)  # type: ignore[arg-type]


def test_merge_single_candidate_returns_itself() -> None:
    """Singolo candidato → nessuna modifica."""
    c = _make(frontmatter={"nome": "X"}, source_doc_ids=[1])
    merged = merge_entity_candidates([c])
    assert merged is c


def test_merge_empty_list_raises() -> None:
    """Lista vuota → ValueError."""
    with pytest.raises(ValueError):
        merge_entity_candidates([])


def test_merge_heterogeneous_entity_ids_raises() -> None:
    """entity_id diversi → ValueError."""
    a = _make(entity_id="rossetto")
    b = _make(entity_id="bianchi")
    with pytest.raises(ValueError, match="eterogenei"):
        merge_entity_candidates([a, b])


def test_merge_scalar_prefer_non_null() -> None:
    """Campo scalare: preferisce non-null all'altro vuoto."""
    a = _make(frontmatter={"piva": None, "nome": "Rossetto"}, confidence=0.8)
    b = _make(frontmatter={"piva": "12345", "nome": "Rossetto"}, confidence=0.6)
    merged = merge_entity_candidates([a, b])
    assert merged.frontmatter["piva"] == "12345"


def test_merge_scalar_conflict_higher_confidence_wins() -> None:
    """Conflitto su scalare → vince la confidence più alta."""
    a = _make(frontmatter={"sede": "Vicenza", "nome": "X"}, confidence=0.9)
    b = _make(frontmatter={"sede": "Verona", "nome": "X"}, confidence=0.5)
    merged = merge_entity_candidates([a, b])
    assert merged.frontmatter["sede"] == "Vicenza"


def test_merge_lists_union_dedupe() -> None:
    """Liste: union + dedupe, preserva ordine."""
    a = _make(frontmatter={"prodotti_ricorrenti": ["A", "B"], "nome": "X"})
    b = _make(frontmatter={"prodotti_ricorrenti": ["B", "C"], "nome": "X"})
    merged = merge_entity_candidates([a, b])
    assert merged.frontmatter["prodotti_ricorrenti"] == ["A", "B", "C"]


def test_merge_dicts_recursive() -> None:
    """Dict: merge ricorsivo."""
    a = _make(
        frontmatter={
            "condizioni_commerciali": {"sconto_listino": "12%"},
            "nome": "X",
        },
        confidence=0.9,
    )
    b = _make(
        frontmatter={
            "condizioni_commerciali": {"termini_pagamento": "60gg"},
            "nome": "X",
        },
        confidence=0.7,
    )
    merged = merge_entity_candidates([a, b])
    cc = merged.frontmatter["condizioni_commerciali"]
    assert cc["sconto_listino"] == "12%"
    assert cc["termini_pagamento"] == "60gg"


def test_merge_long_form_concat_with_separator() -> None:
    """note_relazionali: concat con separator markdown."""
    a = _make(frontmatter={"note_relazionali": "Prima nota.", "nome": "X"})
    b = _make(frontmatter={"note_relazionali": "Seconda nota.", "nome": "X"})
    merged = merge_entity_candidates([a, b])
    assert "Prima nota." in merged.frontmatter["note_relazionali"]
    assert "Seconda nota." in merged.frontmatter["note_relazionali"]
    assert "---" in merged.frontmatter["note_relazionali"]


def test_merge_source_doc_ids_union() -> None:
    """source_doc_ids vengono uniti dedupe."""
    a = _make(source_doc_ids=[1, 2])
    b = _make(source_doc_ids=[2, 3])
    merged = merge_entity_candidates([a, b])
    assert sorted(merged.source_doc_ids) == [1, 2, 3]


def test_merge_three_candidates_fold_left() -> None:
    """Fold left-to-right con 3 candidati."""
    a = _make(frontmatter={"nome": "X", "prodotti_ricorrenti": ["A"]})
    b = _make(frontmatter={"nome": "X", "prodotti_ricorrenti": ["B"]})
    c = _make(frontmatter={"nome": "X", "prodotti_ricorrenti": ["C"]})
    merged = merge_entity_candidates([a, b, c])
    assert sorted(merged.frontmatter["prodotti_ricorrenti"]) == ["A", "B", "C"]
    # confidence è media: (1 + 1)/2 = 1, poi (1 + 1)/2 = 1
    assert merged.confidence == 1.0


def test_merge_unhashable_list_items() -> None:
    """Items dict (es. eccezioni_concordate) si fondono senza esplodere."""
    a = _make(
        frontmatter={
            "nome": "X",
            "eccezioni_concordate": [
                {"data": "2023-09-15", "contesto": "ordine A"},
            ],
        }
    )
    b = _make(
        frontmatter={
            "nome": "X",
            "eccezioni_concordate": [
                {"data": "2024-11-02", "contesto": "ordine B"},
            ],
        }
    )
    merged = merge_entity_candidates([a, b])
    assert len(merged.frontmatter["eccezioni_concordate"]) == 2
