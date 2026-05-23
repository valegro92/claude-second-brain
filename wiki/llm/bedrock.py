"""Provider LLM: Claude su AWS Bedrock (account cliente).

Usato per clienti regolamentati che vogliono il modello dentro al proprio
perimetro AWS (data residency EU, conformità con BAA/HIPAA-like, ecc.).

L'SDK Anthropic espone una classe ``AnthropicBedrock`` che, sotto il cofano,
firma le richieste con AWS SigV4 e parla con l'endpoint Bedrock della region
indicata. La shape API (``messages.create``) è identica a quella standard,
quindi questo provider riusa la stessa logica del provider ``anthropic_api``.

Differenze rilevanti:

* I model id su Bedrock hanno il prefisso ``anthropic.`` e un suffisso
  versione, es. ``anthropic.claude-haiku-4-5-20251001-v1:0``. I default qui
  sono placeholder ragionevoli ma vanno **sempre** validati con
  ``config.llm.bedrock.model_overrides`` per il cliente specifico (i model
  id Bedrock cambiano con le release).
* Le credenziali vengono dalla normale catena AWS (env, profile, IAM role).
* La region è obbligatoria: ``config.llm.bedrock.region``.

Setup richiesto lato cliente — vedi ``docs/08-on-premise.md``.
"""
from __future__ import annotations

import logging
import os
from typing import Any

from ._base import AnthropicCompatibleMixin, LLMClient
from .anthropic_api import _extract_text, _extract_usage

logger = logging.getLogger(__name__)


# Placeholder: i model id Bedrock vanno confermati dalla console AWS.
_DEFAULT_BEDROCK_MODELS: dict[str, str] = {
    "fast": "anthropic.claude-haiku-4-5-20251001-v1:0",
    "smart": "anthropic.claude-sonnet-4-5-20251022-v2:0",
}


class BedrockClient(AnthropicCompatibleMixin, LLMClient):
    """Implementazione di :class:`LLMClient` su AWS Bedrock."""

    def __init__(
        self,
        *,
        region: str,
        aws_profile: str | None = None,
        model_overrides: dict[str, str] | None = None,
        sdk_client: Any | None = None,
    ) -> None:
        """Inizializza il client Bedrock.

        Args:
            region: AWS region (es. ``"eu-west-1"``, ``"us-east-1"``).
            aws_profile: profilo AWS della catena di credenziali. Se ``None``,
                usa la catena standard (env, default profile, IAM role).
            model_overrides: dict ``alias -> model id Bedrock``. Consigliato
                sempre passarlo: i model id Bedrock cambiano spesso.
            sdk_client: client SDK già istanziato (per i test).
        """
        self.models = dict(_DEFAULT_BEDROCK_MODELS)
        if model_overrides:
            self.models.update(model_overrides)
        self._region = region
        self._aws_profile = aws_profile

        if sdk_client is not None:
            self._sdk = sdk_client
            return

        try:
            import anthropic  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover - dipende dall'install
            raise RuntimeError(
                "Il pacchetto `anthropic` non è installato. Aggiungilo via uv."
            ) from exc

        # Imposta AWS_PROFILE solo se richiesto: rispetta variabili esistenti.
        if aws_profile and "AWS_PROFILE" not in os.environ:
            os.environ["AWS_PROFILE"] = aws_profile

        try:
            self._sdk = anthropic.AnthropicBedrock(aws_region=region)
        except AttributeError as exc:  # pragma: no cover - sdk troppo vecchio
            raise RuntimeError(
                "`anthropic.AnthropicBedrock` non disponibile: aggiorna il "
                "pacchetto anthropic (>=0.40 con extras bedrock)."
            ) from exc

    def complete(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        max_tokens: int = 1024,
        **kwargs: Any,
    ) -> tuple[str, dict[str, int]]:
        """Identica firma a ``AnthropicApiClient.complete``."""
        resolved_model = self.resolve_model(model)
        call_kwargs: dict[str, Any] = {
            "model": resolved_model,
            "max_tokens": max_tokens,
            "messages": messages,
        }
        if "system" in kwargs:
            call_kwargs["system"] = kwargs.pop("system")
        call_kwargs.update(kwargs)

        response = self._sdk.messages.create(**call_kwargs)
        return _extract_text(response), _extract_usage(response)


__all__ = ["BedrockClient"]
