"""
Tipi di base per il layer LLMProvider.

Contiene il Protocol LLMProvider e i dataclass leggeri usati da tutti gli adapter
(Message, LLMUsage, ModelTier).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Literal, Protocol, runtime_checkable


def now_iso() -> str:
    """Timestamp ISO 8601 UTC con microsecondi (per audit puntuale)."""
    return datetime.now(timezone.utc).isoformat()


class ModelTier(str, Enum):
    """Tier semantico richiesto dal caller. Ogni adapter lo mappa al modello concreto."""

    FAST = "fast"  # categorizzazione, dedup, classificazione binaria
    SMART = "smart"  # estrazione strutturata, generazione frontmatter
    REASONING = "reasoning"  # ragionamento esteso (raro in v0.1)


@dataclass(frozen=True)
class Message:
    """Messaggio conversazionale. Solo ruoli user/assistant; il system prompt è separato."""

    role: Literal["user", "assistant"]
    content: str


@dataclass(frozen=True)
class LLMUsage:
    """Record di una singola chiamata al provider. Aggregato in usage_log dell'adapter."""

    provider: str  # "anthropic" | "sovrano" | "fake"
    model: str  # nome modello effettivo usato
    input_tokens: int
    output_tokens: int
    cost_eur_estimate: float
    operation: str  # "complete" | "extract_structured" | "count_tokens"
    timestamp: str  # ISO 8601 UTC


@runtime_checkable
class LLMProvider(Protocol):
    """
    Interfaccia comune a tutti gli adapter LLM.

    Tre primitive: complete (testo libero), extract_structured (output dict
    conforme a JSON schema), count_tokens (stima/conta token).

    Ogni implementazione DEVE esporre attributi `name` e `usage_log`.
    """

    name: str
    usage_log: list[LLMUsage]

    def complete(
        self,
        messages: list[Message],
        *,
        system: str = "",
        tier: ModelTier = ModelTier.SMART,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> str:
        """Genera testo libero dato uno scambio di messaggi. Ritorna la stringa di risposta."""
        ...

    def extract_structured(
        self,
        messages: list[Message],
        *,
        schema: dict,
        system: str = "",
        tier: ModelTier = ModelTier.SMART,
    ) -> dict:
        """
        Estrae un dict conforme allo schema JSON fornito.

        Implementazioni tipiche: tool-use (Anthropic), JSON mode (OpenAI),
        structured output (Sovrano). Solleva LLMValidationError se il modello
        non produce output strutturato valido.
        """
        ...

    def count_tokens(self, text: str) -> int:
        """Conta i token di una stringa secondo il tokenizer del provider (può essere stima)."""
        ...
