"""Astrazione provider LLM per wiki-toolkit (Step 3 — on-premise).

Punto di ingresso unico: :func:`get_llm_client`. I caller del toolkit
(categorizers, reconcilers) ricevono qui un client che espone la stessa
shape ``client.messages.create(...)`` dell'SDK Anthropic, indipendentemente
dal backend reale (API standard, Bedrock, on-premise futuri).

Esempio:

.. code-block:: python

    from pathlib import Path
    from wiki.llm import get_llm_client

    client = get_llm_client(config, state_dir=Path("_status"))
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1024,
        system="...",
        messages=[{"role": "user", "content": "..."}],
    )
    text = response.content[0].text

Provider supportati (``config.llm.provider``):

* ``anthropic_api`` (default): SDK Anthropic standard, richiede
  ``ANTHROPIC_API_KEY``.
* ``bedrock``: AWS Bedrock dell'account cliente, richiede
  ``config.llm.bedrock.region`` e credenziali AWS standard.

Wrapper privacy:

* Se ``config.llm.redact_pii: true``, il client torna wrappato in
  :class:`SafeModeClient` (redact pre-call, de-redact post-call,
  mappa in ``_status/audit/redact-map.json``).

Vedi ``_brief/04-step-2-tech-plan.md`` sezione 8 e ``docs/08-on-premise.md``
per la matrice decisionale on-premise.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from ._base import LLMClient
from .anthropic_api import AnthropicApiClient
from .bedrock import BedrockClient
from .safe_mode import RedactMap, SafeModeClient, redact_text, unredact_text

logger = logging.getLogger(__name__)


def _get(d: dict, key: str, default: Any = None) -> Any:
    """``d.get(key, default)`` ma tollera ``d`` non-dict."""
    if not isinstance(d, dict):
        return default
    return d.get(key, default)


def get_llm_client(
    config: dict[str, Any] | None = None,
    *,
    state_dir: Path | None = None,
) -> LLMClient:
    """Costruisce e ritorna il client LLM secondo configurazione.

    Args:
        config: dict di configurazione (caricato da
            ``bootstrap/clients/<slug>/config.yml``). Chiave rilevante:
            ``llm.provider`` (``anthropic_api`` | ``bedrock``);
            sub-sezioni opzionali per provider e per ``redact_pii``.
            Se ``None`` o vuoto, default = ``anthropic_api`` senza redact
            (comportamento Step 2).
        state_dir: cartella ``_status/`` del cliente. Necessaria per
            persistere la redact-map quando ``redact_pii: true``.

    Returns:
        Istanza di :class:`LLMClient` (eventualmente wrappata in
        :class:`SafeModeClient`).

    Raises:
        ValueError: se ``provider`` non è uno tra quelli supportati.
        RuntimeError: se mancano credenziali o SDK del provider scelto.
    """
    llm_cfg = _get(config or {}, "llm", {}) or {}
    provider = _get(llm_cfg, "provider", "anthropic_api")

    inner: LLMClient
    if provider == "anthropic_api":
        api_cfg = _get(llm_cfg, "anthropic_api", {}) or {}
        inner = AnthropicApiClient(
            model_overrides=_get(api_cfg, "model_overrides"),
        )
    elif provider == "bedrock":
        bedrock_cfg = _get(llm_cfg, "bedrock", {}) or {}
        region = _get(bedrock_cfg, "region")
        if not region:
            raise RuntimeError(
                "Provider 'bedrock' richiede config.llm.bedrock.region (es. 'eu-west-1')."
            )
        inner = BedrockClient(
            region=region,
            aws_profile=_get(bedrock_cfg, "aws_profile"),
            model_overrides=_get(bedrock_cfg, "model_overrides"),
        )
    else:
        raise ValueError(
            f"Provider LLM sconosciuto: {provider!r}. Valori ammessi: 'anthropic_api', 'bedrock'."
        )

    if _get(llm_cfg, "redact_pii", False):
        logger.info("safe-mode attivo: PII verranno mascherate prima del modello")
        return SafeModeClient(inner, state_dir=state_dir)

    return inner


__all__ = [
    "AnthropicApiClient",
    "BedrockClient",
    "LLMClient",
    "RedactMap",
    "SafeModeClient",
    "get_llm_client",
    "redact_text",
    "unredact_text",
]
