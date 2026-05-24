"""
Merge interattivo fra frontmatter candidato e frontmatter del vault esistente.

Politica di default (D7-compatibile):
- Liste: union dedupe preservando l'ordine vault-prima-candidato.
- Dict scalari (es. condizioni_commerciali): merge per chiave; in caso di
  conflitto su un valore atomico il prompt chiede ``[v]ault / [c]andidato / [m]anual``.
  Quando non interattivo, default = candidato.
- Stringhe (incluse ``note_relazionali``): concat con separator timestampato.
- Body markdown: append candidato body al vault body con separator
  ``\\n\\n---\\n*Aggiornamento {data}*\\n\\n``.

In modalità non interattiva (``prompt=None``) le decisioni di conflitto
adottano la policy *candidato vince*: questo è il comportamento usato dal
flag ``--yes`` e dai test E2E.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Callable, Iterable

# Tipo del callback usato per chiedere all'utente come risolvere un conflitto
# scalare. Riceve (chiave, valore_vault, valore_candidato) e ritorna il valore
# scelto. Se None, default policy = candidato.
ConflictPrompt = Callable[[str, Any, Any], Any]


def _dedupe_preserve_order(items: Iterable[Any]) -> list[Any]:
    """Rimuove duplicati conservando l'ordine. Confronto via ``repr`` per dict."""
    seen: list[str] = []
    out: list[Any] = []
    for item in items:
        key = repr(item)
        if key in seen:
            continue
        seen.append(key)
        out.append(item)
    return out


def _merge_strings(
    key: str,
    vault_value: str,
    candidate_value: str,
    today_iso: str,
) -> str:
    """Concat di stringhe con separator timestampato.

    Se ``vault_value`` contiene già ``candidate_value`` ritorna ``vault_value``
    inalterato (idempotenza).
    """
    if vault_value == candidate_value:
        return vault_value
    if candidate_value in vault_value:
        return vault_value
    sep = f"\n\n— aggiornamento {today_iso} —\n"
    return f"{vault_value}{sep}{candidate_value}"


def merge_dicts(
    vault: dict[str, Any],
    candidate: dict[str, Any],
    *,
    prompt: ConflictPrompt | None = None,
    today_iso: str | None = None,
) -> dict[str, Any]:
    """Merge campo-per-campo di due dict (ricorsivo sulle sottostrutture).

    Args:
        vault: frontmatter esistente nel vault.
        candidate: frontmatter prodotto dall'extractor.
        prompt: callback per risolvere conflitti scalari interattivamente.
            Se None applica policy candidato.
        today_iso: data ISO per il separator delle stringhe; default = oggi.

    Returns:
        Nuovo dict mergiato. Non muta gli input.
    """
    today_iso = today_iso or date.today().isoformat()
    out: dict[str, Any] = {}
    keys = list(vault.keys()) + [k for k in candidate.keys() if k not in vault]
    for key in keys:
        if key in vault and key not in candidate:
            out[key] = vault[key]
            continue
        if key in candidate and key not in vault:
            out[key] = candidate[key]
            continue
        v_val = vault[key]
        c_val = candidate[key]
        if v_val == c_val:
            out[key] = v_val
            continue
        # Conflitto.
        if isinstance(v_val, list) and isinstance(c_val, list):
            out[key] = _dedupe_preserve_order(list(v_val) + list(c_val))
        elif isinstance(v_val, dict) and isinstance(c_val, dict):
            out[key] = merge_dicts(
                v_val, c_val, prompt=prompt, today_iso=today_iso
            )
        elif isinstance(v_val, str) and isinstance(c_val, str):
            # Stringhe narrative (multiline o lunghe) → concat con separator.
            # Stringhe brevi (es. "12%", "60gg") → comportamento da scalare:
            # prompt se interattivo, altrimenti candidato vince.
            is_narrative = (
                "\n" in v_val or "\n" in c_val or len(v_val) > 80 or len(c_val) > 80
            )
            if is_narrative:
                out[key] = _merge_strings(key, v_val, c_val, today_iso)
            elif prompt is not None:
                out[key] = prompt(key, v_val, c_val)
            else:
                out[key] = c_val
        else:
            # Scalari atomici (numeri, bool, mismatch di tipo): prompt.
            if prompt is not None:
                out[key] = prompt(key, v_val, c_val)
            else:
                out[key] = c_val  # policy candidato
    return out


def merge_body(
    vault_body: str,
    candidate_body: str,
    *,
    today_iso: str | None = None,
) -> str:
    """Append del body candidato al body del vault con separator.

    Se i body sono identici o il candidato è vuoto, ritorna ``vault_body``.
    """
    today_iso = today_iso or date.today().isoformat()
    if not candidate_body.strip():
        return vault_body
    if vault_body.strip() == candidate_body.strip():
        return vault_body
    return (
        f"{vault_body.rstrip()}\n\n---\n*Aggiornamento {today_iso}*\n\n"
        f"{candidate_body.lstrip()}"
    )


__all__ = [
    "merge_dicts",
    "merge_body",
    "ConflictPrompt",
]
