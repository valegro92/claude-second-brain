"""
Gerarchia eccezioni per il layer LLMProvider.

Tutte le eccezioni ereditano da LLMError. Gli extractor catchano per classe e
decidono la policy (retry, skip, surface all'utente).
"""

from __future__ import annotations


class LLMError(Exception):
    """Errore base per tutti gli adapter LLMProvider."""


class LLMUnavailableError(LLMError):
    """API key mancante, network down, provider non raggiungibile."""


class LLMRateLimitError(LLMError):
    """Rate limit superato dopo tutti i retry interni (429/529)."""


class LLMValidationError(LLMError):
    """Output del modello non conforme allo schema richiesto."""
