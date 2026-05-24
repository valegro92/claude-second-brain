"""
Factory per ottenere un LLMProvider concreto dato un nome.

v0.1 supporta:
- "anthropic": AnthropicProvider (produzione)
- "fake": FakeLLMProvider (test/dogfood)

Placeholder futuro: "sovrano" (provider OpenAI-compatible self-hosted), non
ancora implementato. Solleva ValueError chiaro per nomi sconosciuti.
"""

from __future__ import annotations

import os
from typing import Any

from custodia_cli.llm.anthropic_provider import AnthropicProvider
from custodia_cli.llm.base import LLMProvider
from custodia_cli.llm.fakes import FakeLLMProvider


_SUPPORTED_PROVIDERS: tuple[str, ...] = ("anthropic", "fake")
_FUTURE_PROVIDERS: tuple[str, ...] = ("sovrano",)


def get_provider(name: str | None = None, **config: Any) -> LLMProvider:
    """
    Ritorna un LLMProvider concreto.

    Precedenza:
    1. argomento `name` esplicito
    2. variabile d'ambiente CUSTODIA_LLM_PROVIDER
    3. default "anthropic"

    Per "fake" e' obbligatorio passare `fixture_path` in config.
    """
    resolved = name or os.environ.get("CUSTODIA_LLM_PROVIDER") or "anthropic"
    resolved = resolved.lower().strip()

    if resolved == "anthropic":
        return AnthropicProvider(
            api_key=config.get("api_key"),
            client=config.get("client"),
        )

    if resolved == "fake":
        fixture_path = config.get("fixture_path")
        if fixture_path is None:
            raise ValueError(
                "Provider 'fake' richiede l'argomento `fixture_path` (path al file YAML di canned responses)."
            )
        return FakeLLMProvider(fixture_path=fixture_path)

    if resolved in _FUTURE_PROVIDERS:
        raise ValueError(
            f"Provider '{resolved}' non ancora implementato in v0.1 "
            f"(placeholder futuro per OpenAI-compatible self-hosted). "
            f"Supportati oggi: {_SUPPORTED_PROVIDERS}."
        )

    raise ValueError(
        f"Provider LLM sconosciuto: {resolved!r}. Supportati: {_SUPPORTED_PROVIDERS}. "
        f"Placeholder futuri: {_FUTURE_PROVIDERS}."
    )
