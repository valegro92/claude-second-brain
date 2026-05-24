"""
Astrazione LLMProvider per Custodia CLI.

Espone:
- LLMProvider: Protocol comune a tutti gli adapter
- ModelTier: enum dei tier semantici (FAST, SMART, REASONING)
- Message: dataclass per messaggi conversazionali
- LLMUsage: record di utilizzo (token, costo, operazione)
- get_provider: factory per ottenere un adapter concreto
- Gerarchia eccezioni: LLMError, LLMUnavailableError, LLMRateLimitError, LLMValidationError
"""

from __future__ import annotations

from custodia_cli.llm.base import LLMProvider, LLMUsage, Message, ModelTier
from custodia_cli.llm.exceptions import (
    LLMError,
    LLMRateLimitError,
    LLMUnavailableError,
    LLMValidationError,
)
from custodia_cli.llm.registry import get_provider

__all__ = [
    "LLMProvider",
    "LLMUsage",
    "Message",
    "ModelTier",
    "LLMError",
    "LLMRateLimitError",
    "LLMUnavailableError",
    "LLMValidationError",
    "get_provider",
]
