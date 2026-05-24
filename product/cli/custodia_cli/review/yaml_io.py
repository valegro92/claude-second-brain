"""
Serializzazione YAML deterministica per i file `.md` del vault.

Caratteristiche:
- ``sort_keys=False``: l'ordine delle chiavi rispetta lo schema canonical.
- Block style ``|`` automatico per stringhe multilinea (note_relazionali ecc.).
- Allow unicode (italiani con accenti restano leggibili).
- Line ending Unix.

L'ordine canonical per ogni ``entity_type`` è definito esplicitamente qui:
single source of truth allineata con `product/vault-demo/clienti/rossetto-laminazioni.md`.
"""

from __future__ import annotations

from typing import Any

import yaml

# Ordine canonical chiavi frontmatter per tipo entità.
# Allineato con product/vault-demo/clienti/rossetto-laminazioni.md.
_ORDERED_KEYS: dict[str, list[str]] = {
    "cliente": [
        "tipo",
        "nome",
        "piva",
        "settore",
        "sede",
        "referente_principale",
        "ruolo_referente",
        "email_referente",
        "telefono",
        "relazione_dal",
        "stato_relazione",
        "ultimo_contatto",
        "prossima_azione",
        "condizioni_commerciali",
        "eccezioni_concordate",
        "prodotti_ricorrenti",
        "fatturato_2024",
        "fatturato_2025_ytd",
        "note_relazionali",
        "red_flag",
    ],
    "fornitore": [
        "tipo",
        "nome",
        "piva",
        "settore",
        "sede",
        "referente_principale",
        "ruolo_referente",
        "email_referente",
        "telefono",
        "relazione_dal",
        "stato_relazione",
        "ultimo_contatto",
        "prossima_azione",
        "condizioni_commerciali",
        "prodotti_forniti",
        "note_relazionali",
        "red_flag",
    ],
    "commessa": [
        "tipo",
        "nome",
        "cliente",
        "stato",
        "data_inizio",
        "data_fine_prevista",
        "valore",
        "responsabile",
        "milestone",
        "note_relazionali",
    ],
    "comunicazione": [
        "tipo",
        "data",
        "da",
        "a",
        "oggetto",
        "cliente_collegato",
        "stato",
        "allegati",
    ],
}


# Plurali per il path della cartella del vault.
ENTITY_TYPE_PLURAL: dict[str, str] = {
    "cliente": "clienti",
    "fornitore": "fornitori",
    "commessa": "commesse",
    "comunicazione": "inbox",
}


def ordered_keys_for_type(entity_type: str) -> list[str]:
    """Ritorna l'ordine canonical delle chiavi per ``entity_type``.

    Tipi sconosciuti ritornano lista vuota (= ordine di inserimento del dict).
    """
    return list(_ORDERED_KEYS.get(entity_type, []))


def _reorder_dict(d: dict[str, Any], ordered_keys: list[str]) -> dict[str, Any]:
    """Ritorna un nuovo dict con chiavi in ``ordered_keys`` prima, altre dopo.

    Le chiavi di ``ordered_keys`` assenti da ``d`` vengono saltate. Le chiavi
    di ``d`` non in ``ordered_keys`` vengono appese in coda nell'ordine in cui
    compaiono nel dict originale.
    """
    if not ordered_keys:
        return dict(d)
    out: dict[str, Any] = {}
    for k in ordered_keys:
        if k in d:
            out[k] = d[k]
    for k, v in d.items():
        if k not in out:
            out[k] = v
    return out


class _CustodiaDumper(yaml.SafeDumper):
    """Dumper che forza block style ``|`` per stringhe multilinea."""


def _str_representer(dumper: yaml.SafeDumper, data: str) -> Any:
    if "\n" in data:
        return dumper.represent_scalar(
            "tag:yaml.org,2002:str", data, style="|"
        )
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


_CustodiaDumper.add_representer(str, _str_representer)


def dump_frontmatter(
    frontmatter: dict[str, Any],
    ordered_keys: list[str] | None = None,
) -> str:
    """Serializza un dict frontmatter in YAML deterministico.

    Args:
        frontmatter: dict da serializzare. Può essere vuoto.
        ordered_keys: ordine top-level desiderato; se None usa l'ordine di
            inserimento del dict (Python 3.7+).

    Returns:
        Stringa YAML (senza i delimitatori ``---``), line ending Unix,
        senza newline finale superfluo.
    """
    if not frontmatter:
        return ""
    payload = _reorder_dict(frontmatter, ordered_keys or [])
    text = yaml.dump(
        payload,
        Dumper=_CustodiaDumper,
        sort_keys=False,
        default_flow_style=False,
        allow_unicode=True,
        width=120,
    )
    # yaml.dump appende sempre '\n' finale; lo manteniamo per consistenza.
    return text


__all__ = [
    "dump_frontmatter",
    "ordered_keys_for_type",
    "ENTITY_TYPE_PLURAL",
]
