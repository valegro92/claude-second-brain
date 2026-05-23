"""Provider LLM: Claude via API Anthropic standard.

Default del toolkit. Comportamento identico a quello dello Step 2:
istanzia ``anthropic.Anthropic(api_key=...)`` e fa passare le chiamate.

Variabili d'ambiente:

* ``ANTHROPIC_API_KEY`` (obbligatoria): API key Anthropic.

Modelli di default (alias logici → model id):

* ``fast`` → ``claude-haiku-4-5``
* ``smart`` → ``claude-sonnet-4-5``

Override possibile via ``config.llm.anthropic_api.model_overrides``.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from ._base import AnthropicCompatibleMixin, LLMClient

logger = logging.getLogger(__name__)


_DEFAULT_MODELS: dict[str, str] = {
    "fast": "claude-haiku-4-5",
    "smart": "claude-sonnet-4-5",
}


class AnthropicApiClient(AnthropicCompatibleMixin, LLMClient):
    """Implementazione di :class:`LLMClient` che usa l'SDK Anthropic standard."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model_overrides: dict[str, str] | None = None,
        sdk_client: Any | None = None,
    ) -> None:
        """Inizializza il client.

        Args:
            api_key: API key Anthropic. Se ``None``, legge da
                ``ANTHROPIC_API_KEY``.
            model_overrides: dict ``alias -> model id`` per sovrascrivere
                i default.
            sdk_client: client SDK già istanziato (utile per i test).
        """
        self.models = dict(_DEFAULT_MODELS)
        if model_overrides:
            self.models.update(model_overrides)

        if sdk_client is not None:
            self._sdk = sdk_client
            return

        try:
            import anthropic  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover - dipende dall'install
            raise RuntimeError(
                "Il pacchetto `anthropic` non è installato. Aggiungilo via uv."
            ) from exc

        key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY non impostata: imposta la variabile d'ambiente "
                "o passa api_key esplicito."
            )
        self._sdk = anthropic.Anthropic(api_key=key)

    def complete(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        max_tokens: int = 1024,
        **kwargs: Any,
    ) -> tuple[str, dict[str, int]]:
        """Wrappa ``self._sdk.messages.create(...)``."""
        resolved_model = self.resolve_model(model)
        call_kwargs: dict[str, Any] = {
            "model": resolved_model,
            "max_tokens": max_tokens,
            "messages": messages,
        }
        # ``system`` è opzionale (Anthropic lo vuole come kwarg top-level).
        if "system" in kwargs:
            call_kwargs["system"] = kwargs.pop("system")
        call_kwargs.update(kwargs)

        response = self._sdk.messages.create(**call_kwargs)
        text = _extract_text(response)
        usage = _extract_usage(response)
        return text, usage

    def vision(
        self,
        image_path: Path,
        prompt: str,
        model: str | None = None,
        **kwargs: Any,
    ) -> tuple[str, dict[str, int]]:
        """Chiamata vision: invia immagine + prompt al modello.

        Usa il modello ``smart`` di default (vision richiede capacità Sonnet+).
        """
        import base64
        import mimetypes

        resolved_model = self.resolve_model(model or "smart")
        mime, _ = mimetypes.guess_type(str(image_path))
        mime = mime or "image/png"
        with image_path.open("rb") as f:
            b64 = base64.standard_b64encode(f.read()).decode("ascii")

        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": mime,
                            "data": b64,
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ]
        return self.complete(
            messages=messages,
            model=resolved_model,
            max_tokens=kwargs.pop("max_tokens", 2048),
            **kwargs,
        )


# Estrazione robusta (replicata da categorizers/claude.py per evitare
# import circolari) ----------------------------------------------------------
def _extract_text(response: Any) -> str:
    content = getattr(response, "content", None)
    if content is None and isinstance(response, dict):
        content = response.get("content")
    if isinstance(content, list) and content:
        block = content[0]
        text = getattr(block, "text", None)
        if text is None and isinstance(block, dict):
            text = block.get("text")
        if text is not None:
            return str(text)
    if isinstance(content, str):
        return content
    return ""


def _extract_usage(response: Any) -> dict[str, int]:
    usage = getattr(response, "usage", None)
    if usage is None and isinstance(response, dict):
        usage = response.get("usage")
    if usage is None:
        return {"input_tokens": 0, "output_tokens": 0}
    in_tok = getattr(usage, "input_tokens", None)
    out_tok = getattr(usage, "output_tokens", None)
    if in_tok is None and isinstance(usage, dict):
        in_tok = usage.get("input_tokens", 0)
        out_tok = usage.get("output_tokens", 0)
    try:
        return {
            "input_tokens": int(in_tok or 0),
            "output_tokens": int(out_tok or 0),
        }
    except (TypeError, ValueError):
        return {"input_tokens": 0, "output_tokens": 0}


__all__ = ["AnthropicApiClient"]
