"""Gerarchia eccezioni custom del toolkit.

Tutte le eccezioni custom ereditano da ``WikiError``. I caller possono
catturare ``WikiError`` per gestire qualunque errore del toolkit; le
sottoclassi permettono gestione mirata (es. distinguere config invalido
da fallimento estrazione).
"""

from __future__ import annotations


class WikiError(Exception):
    """Eccezione base per tutti gli errori del toolkit."""


class ConfigError(WikiError):
    """Config YAML mancante, malformato o invalido (validazione semantica fallita)."""


class ScanError(WikiError):
    """Errore durante lo scandagliamento di una sorgente (auth, rete, permessi)."""


class ExtractError(WikiError):
    """Errore durante l'estrazione di un file (formato corrotto, tool mancante, timeout)."""


class CategorizeError(WikiError):
    """Errore durante la categorizzazione (LLM unreachable, parsing risposta)."""


class ReconcileError(WikiError):
    """Errore durante la riconciliazione (dedup, generazione schede, persone)."""


class LLMError(WikiError):
    """Errore di comunicazione con il provider LLM (Anthropic API o Bedrock)."""


class PipelineError(WikiError):
    """Errore generico del pipeline orchestrator. Avvolge gli errori di stage."""


class SubprocessError(WikiError):
    """Errore di esecuzione subprocess (pandoc, tesseract). Include timeout."""


class ValidationError(WikiError):
    """Input utente invalido (slug malformato, path traversal, ecc.)."""
