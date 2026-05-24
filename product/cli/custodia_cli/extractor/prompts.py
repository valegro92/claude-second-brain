"""
Template di prompt per la pipeline a 2 stadi (categorize → extract).

Prompt in italiano (D-open question del piano): output frontmatter è italiano,
la categorizzazione lavora su documenti italiani, il consulente legge il prompt
per debug. La struttura JSON-schema è language-agnostic e gestita altrove.
"""

from __future__ import annotations

import json
from typing import Any

from custodia_cli.extractor.schema import load_canonical_example


# Etichette user-facing per ogni entity_type (singolare/plurale).
_ENTITY_LABELS: dict[str, dict[str, str]] = {
    "cliente": {"singular": "cliente", "plural": "clienti"},
    "fornitore": {"singular": "fornitore", "plural": "fornitori"},
    "commessa": {"singular": "commessa", "plural": "commesse"},
    "comunicazione": {"singular": "comunicazione", "plural": "comunicazioni"},
}


# Schema JSON dell'output di categorize. Stabile fra entity_type.
CATEGORIZE_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "entities": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "hint": {"type": "string"},
                },
                "required": ["name"],
                "additionalProperties": True,
            },
        }
    },
    "required": ["entities"],
    "additionalProperties": False,
}


def _entity_label(entity_type: str, form: str = "singular") -> str:
    """Etichetta italiana per `entity_type`. Fallback all'identifier raw."""
    return _ENTITY_LABELS.get(entity_type, {}).get(form, entity_type)


def categorize_system_prompt(entity_type: str) -> str:
    """System prompt per lo stadio 1 (categorize, tier FAST)."""
    plural = _entity_label(entity_type, "plural")
    singular = _entity_label(entity_type, "singular")
    return (
        "Sei un assistente specializzato in analisi documentale per PMI italiane. "
        f"Riceverai il testo estratto da un singolo documento aziendale (può "
        "essere una fattura, un'offerta, un contratto, un'email, un foglio "
        "Excel). Il tuo compito è identificare se il documento parla di "
        f"{plural} (entità di tipo `{entity_type}`), e in caso affermativo "
        f"elencare i nomi delle {plural} menzionati.\n\n"
        "Regole:\n"
        f"- Restituisci JSON con shape `{{\"entities\": [{{\"name\": \"...\", \"hint\": \"...\"}}]}}`.\n"
        f"- Lista vuota se nessuna {singular} compare nel testo.\n"
        f"- NON inventare {plural} non presenti nel documento.\n"
        f"- `hint` è un riferimento breve al contesto in cui appare la {singular} "
        "(es. \"fattura del 2024-03\", \"oggetto email\").\n"
        f"- Per `comunicazione`: identifica le email/comunicazioni dirette "
        "presenti nel documento, non i partecipanti."
    )


def categorize_user_prompt(*, document_text: str, source_path: str) -> str:
    """User prompt categorize: source_path + testo."""
    return (
        f"Documento sorgente: `{source_path}`\n\n"
        f"--- Testo ---\n{document_text}\n--- Fine testo ---"
    )


def extract_system_prompt(entity_type: str) -> str:
    """System prompt per lo stadio 2 (extract, tier SMART)."""
    singular = _entity_label(entity_type, "singular")
    example = load_canonical_example(entity_type)
    example_json = json.dumps(example, ensure_ascii=False, indent=2, default=str)
    return (
        "Sei un assistente specializzato in estrazione strutturata da documenti "
        f"aziendali italiani. Ti viene chiesto di estrarre una scheda `{singular}` "
        "conforme allo schema canonical.\n\n"
        "Regole stringenti:\n"
        "- Compila solo i campi desumibili dai documenti forniti.\n"
        "- Campi non desumibili: lascia `null` per scalari, lista vuota per array.\n"
        "- Date: formato ISO 8601 (`YYYY-MM-DD`).\n"
        "- Importi: numero, senza simbolo valuta né separatore migliaia.\n"
        "- Sii fedele al documento: NON inventare valori (PIVA, fatturati, sedi).\n"
        "- `note_relazionali` e `body`/`note`: lascia stringa vuota o `null` — "
        "li compila il consulente in review.\n"
        "- `red_flag`: lascia array vuoto — è output del consulente.\n"
        "- `tipo`: deve essere esattamente la stringa "
        f"`{singular}`.\n\n"
        "Esempio completo (riferimento di stile e completezza):\n"
        f"```json\n{example_json}\n```\n\n"
        "Devi chiamare il tool `emit_structured_output` con i campi richiesti, "
        "uno per uno; nessun campo deve essere allucinato."
    )


def extract_user_prompt(
    *,
    entity_name: str,
    documents: list[dict[str, Any]],
) -> str:
    """User prompt extract.

    Args:
        entity_name: hint name dalla fase categorize.
        documents: lista di dict `{"source_path": str, "text": str}`.
    """
    blocks: list[str] = []
    for i, d in enumerate(documents, start=1):
        blocks.append(
            f"### Documento {i}: `{d.get('source_path', '<unknown>')}`\n"
            f"{d.get('text', '')}"
        )
    docs_section = "\n\n".join(blocks)
    return (
        f"Entità da estrarre: **{entity_name}**\n\n"
        "Documenti che la menzionano (può essere uno o più):\n\n"
        f"{docs_section}\n\n"
        "Compila il frontmatter della scheda chiamando il tool "
        "`emit_structured_output`."
    )


__all__ = [
    "CATEGORIZE_OUTPUT_SCHEMA",
    "categorize_system_prompt",
    "categorize_user_prompt",
    "extract_system_prompt",
    "extract_user_prompt",
]
