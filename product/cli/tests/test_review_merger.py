"""Test merge interattivo candidato + vault."""

from __future__ import annotations

from custodia_cli.review.merger import merge_body, merge_dicts


def test_merge_lists_union_dedupe() -> None:
    vault = {"prodotti": ["a", "b", "c"]}
    cand = {"prodotti": ["b", "c", "d"]}
    out = merge_dicts(vault, cand)
    assert out["prodotti"] == ["a", "b", "c", "d"]


def test_merge_dict_recursive() -> None:
    vault = {"cond": {"sconto": "12%", "termini": "60gg"}}
    cand = {"cond": {"sconto": "10%", "trasporto": "franco"}}
    out = merge_dicts(vault, cand)
    # sconto: conflict → policy candidato (no prompt) = "10%"
    assert out["cond"]["sconto"] == "10%"
    # termini: solo in vault → preservato
    assert out["cond"]["termini"] == "60gg"
    # trasporto: solo in candidato → aggiunto
    assert out["cond"]["trasporto"] == "franco"


def test_merge_scalar_conflict_default_candidate() -> None:
    out = merge_dicts({"x": 1}, {"x": 2})
    assert out["x"] == 2


def test_merge_scalar_conflict_with_prompt() -> None:
    def prompt(key, vault_v, cand_v):
        return vault_v  # always pick vault

    out = merge_dicts({"x": 1}, {"x": 2}, prompt=prompt)
    assert out["x"] == 1


def test_merge_strings_concat_with_separator() -> None:
    # Stringhe narrative (multiline) → concat con separator.
    out = merge_dicts(
        {"note": "Vecchia nota\ncon più righe."},
        {"note": "Nuova nota\nanche multilinea."},
        today_iso="2026-05-24",
    )
    assert "Vecchia nota" in out["note"]
    assert "Nuova nota" in out["note"]
    assert "2026-05-24" in out["note"]


def test_merge_short_string_conflict_uses_candidate() -> None:
    # Stringhe brevi → policy candidato (no concat).
    out = merge_dicts({"sconto": "12%"}, {"sconto": "10%"})
    assert out["sconto"] == "10%"


def test_merge_strings_idempotent_if_already_contained() -> None:
    out = merge_dicts(
        {"note": "Vecchia\nNuova\ncon multilinea"},
        {"note": "Nuova"},
    )
    # candidato già contenuto → vault inalterato
    assert "Vecchia" in out["note"]
    assert out["note"].count("Nuova") == 1


def test_merge_only_in_vault_preserved() -> None:
    out = merge_dicts({"a": 1, "b": 2}, {"a": 1})
    assert out["b"] == 2


def test_merge_only_in_candidate_added() -> None:
    out = merge_dicts({"a": 1}, {"a": 1, "c": 3})
    assert out["c"] == 3


def test_merge_body_append() -> None:
    out = merge_body("Vecchio body.", "Nuovo body.", today_iso="2026-05-24")
    assert "Vecchio body" in out
    assert "Nuovo body" in out
    assert "Aggiornamento 2026-05-24" in out
    assert "---" in out


def test_merge_body_identical_no_op() -> None:
    out = merge_body("Stesso body.", "Stesso body.")
    assert out == "Stesso body."


def test_merge_body_empty_candidate() -> None:
    out = merge_body("Vault body", "")
    assert out == "Vault body"
