"""
Adapter Anthropic per LLMProvider.

Usa l'SDK ufficiale `anthropic` (>=0.40). Espone:
- complete: messages.create classico, ritorna text
- extract_structured: tool-use forzato con tool sintetico `emit_structured_output`,
  con validazione dell'output contro lo schema fornito (jsonschema).
- count_tokens: usa client.messages.count_tokens se disponibile, altrimenti stima

Retry: max 3 tentativi su 429/529 con backoff esponenziale (2s, 4s) + jitter,
per un totale di 2 sleep tra i 3 tentativi.

Configurazione via env:
- CUSTODIA_ANTHROPIC_API_KEY (preferita) / ANTHROPIC_API_KEY: chiave API.
- CUSTODIA_USD_TO_EUR (opzionale): override del cambio per cost estimate.
"""

from __future__ import annotations

import logging
import os
import random
import time
from typing import Any

import jsonschema

from custodia_cli.llm.base import LLMProvider, LLMUsage, Message, ModelTier, now_iso
from custodia_cli.llm.exceptions import (
    LLMRateLimitError,
    LLMUnavailableError,
    LLMValidationError,
)

logger = logging.getLogger(__name__)


# Mapping tier -> model id Anthropic (modelli 2026)
_TIER_TO_MODEL: dict[ModelTier, str] = {
    ModelTier.FAST: "claude-haiku-4-5",
    ModelTier.SMART: "claude-sonnet-4-6",
    ModelTier.REASONING: "claude-opus-4-7",
}

# Pricing USD per milione di token (input, output). Tabella 2026.
# Ultimo aggiornamento: 2026-05-24. Refresh trimestrale (ogni cambio listino Anthropic).
_PRICING_USD: dict[str, tuple[float, float]] = {
    "claude-haiku-4-5": (0.80, 4.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-opus-4-7": (15.00, 75.00),
}

# Cambio EUR/USD di default. Ultimo aggiornamento: 2026-05-24.
# Override possibile via env CUSTODIA_USD_TO_EUR (utile per stime piu accurate).
_USD_TO_EUR_DEFAULT: float = 0.92


def _get_usd_to_eur() -> float:
    """Ritorna il cambio EUR/USD da env CUSTODIA_USD_TO_EUR o default."""
    raw = os.environ.get("CUSTODIA_USD_TO_EUR")
    if not raw:
        return _USD_TO_EUR_DEFAULT
    try:
        return float(raw)
    except ValueError:
        logger.warning(
            "CUSTODIA_USD_TO_EUR non e' un float valido (%r); uso default %.3f",
            raw,
            _USD_TO_EUR_DEFAULT,
        )
        return _USD_TO_EUR_DEFAULT


# Nome del tool sintetico usato per extract_structured (tool-use forzato).
_STRUCTURED_TOOL_NAME: str = "emit_structured_output"

# Retry policy su rate limit / overload (D1.6 del design doc).
# 3 tentativi totali con 2 sleep in mezzo (2s, 4s) + jitter random fino a +0.5s.
_RETRY_MAX_ATTEMPTS: int = 3
_RETRY_BACKOFF_SECONDS: tuple[float, ...] = (2.0, 4.0)
_RETRY_JITTER_MAX_SECONDS: float = 0.5


def _estimate_cost_eur(model: str, tokens_in: int, tokens_out: int) -> float:
    """Stima costo in EUR data una coppia (tokens_in, tokens_out) per il modello.

    Se il modello non e' nella tabella prezzi, logga warning e ritorna 0.0.
    """
    if model not in _PRICING_USD:
        logger.warning(
            "Modello %r non in tabella prezzi _PRICING_USD: costo stimato = 0.0", model
        )
        return 0.0
    price_in_usd, price_out_usd = _PRICING_USD[model]
    cost_usd = (tokens_in / 1_000_000.0) * price_in_usd + (
        tokens_out / 1_000_000.0
    ) * price_out_usd
    return cost_usd * _get_usd_to_eur()


class AnthropicProvider:
    """
    Adapter LLMProvider per Anthropic Claude.

    L'API key è letta da `CUSTODIA_ANTHROPIC_API_KEY` (preferita) con fallback a
    `ANTHROPIC_API_KEY`. Se nessuna è settata, viene sollevata LLMUnavailableError
    al primo utilizzo.
    """

    name: str = "anthropic"

    def __init__(self, api_key: str | None = None, client: Any | None = None) -> None:
        """
        Costruisce l'adapter.

        Parametri:
            api_key: override esplicito dell'API key (utile in test). Se None, legge env.
            client: client Anthropic gia istanziato (utile per dependency injection in test).
        """
        self.usage_log: list[LLMUsage] = []
        self._api_key: str | None = api_key or os.environ.get(
            "CUSTODIA_ANTHROPIC_API_KEY"
        ) or os.environ.get("ANTHROPIC_API_KEY")
        self._client: Any | None = client

    def _get_client(self) -> Any:
        """Lazy init del client Anthropic. Solleva LLMUnavailableError se manca API key."""
        if self._client is not None:
            return self._client
        if not self._api_key:
            raise LLMUnavailableError(
                "API key Anthropic mancante. Setta CUSTODIA_ANTHROPIC_API_KEY o "
                "ANTHROPIC_API_KEY nell'ambiente."
            )
        try:
            import anthropic
        except ImportError as exc:
            raise LLMUnavailableError(
                "Pacchetto `anthropic` non installato. Installa con `pip install anthropic>=0.40`."
            ) from exc
        self._client = anthropic.Anthropic(api_key=self._api_key)
        return self._client

    @staticmethod
    def _is_rate_limit_error(exc: BaseException) -> bool:
        """True se l'eccezione e un 429 o 529 (overload) dall'SDK Anthropic."""
        # Anthropic SDK espone classi con `status_code`. Fallback su nome per robustezza.
        status = getattr(exc, "status_code", None)
        if status in (429, 529):
            return True
        name = type(exc).__name__
        return name in {"RateLimitError", "OverloadedError"}

    def _call_with_retry(self, fn, *args, **kwargs):  # type: ignore[no-untyped-def]
        """Esegue fn con retry su 429/529. Solleva LLMRateLimitError dopo i tentativi.

        Nota: catturiamo solo `Exception` (non `BaseException`) per non intercettare
        `KeyboardInterrupt` e `SystemExit` — devono propagare per permettere all'utente
        di interrompere il processo. Errori non-rate-limit vengono re-sollevati.
        """
        last_exc: Exception | None = None
        for attempt in range(_RETRY_MAX_ATTEMPTS):
            try:
                return fn(*args, **kwargs)
            except Exception as exc:  # noqa: BLE001 — dispatch su rate-limit detection
                if not self._is_rate_limit_error(exc):
                    raise
                last_exc = exc
                if attempt < _RETRY_MAX_ATTEMPTS - 1:
                    delay = _RETRY_BACKOFF_SECONDS[attempt] + random.uniform(
                        0.0, _RETRY_JITTER_MAX_SECONDS
                    )
                    time.sleep(delay)
        raise LLMRateLimitError(
            f"Rate limit Anthropic superato dopo {_RETRY_MAX_ATTEMPTS} tentativi: {last_exc}"
        )

    @staticmethod
    def _messages_to_anthropic(messages: list[Message]) -> list[dict[str, str]]:
        """Converte Message dataclass nel formato dict atteso dall'SDK Anthropic."""
        return [{"role": m.role, "content": m.content} for m in messages]

    def _log_usage(
        self,
        *,
        model: str,
        tokens_in: int,
        tokens_out: int,
        operation: str,
    ) -> None:
        """Appende un record LLMUsage in self.usage_log con timestamp ISO."""
        self.usage_log.append(
            LLMUsage(
                provider=self.name,
                model=model,
                input_tokens=tokens_in,
                output_tokens=tokens_out,
                cost_eur_estimate=_estimate_cost_eur(model, tokens_in, tokens_out),
                operation=operation,
                timestamp=now_iso(),
            )
        )

    def complete(
        self,
        messages: list[Message],
        *,
        system: str = "",
        tier: ModelTier = ModelTier.SMART,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> str:
        """Chiamata messages.create classica. Ritorna il testo del primo blocco di response."""
        client = self._get_client()
        model = _TIER_TO_MODEL[tier]

        kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": self._messages_to_anthropic(messages),
        }
        if system:
            kwargs["system"] = system

        response = self._call_with_retry(client.messages.create, **kwargs)

        # Estrai testo dal primo blocco di tipo "text"
        text_parts: list[str] = []
        for block in getattr(response, "content", []):
            block_type = getattr(block, "type", None)
            if block_type == "text":
                text_parts.append(getattr(block, "text", ""))
        text = "".join(text_parts)

        usage = getattr(response, "usage", None)
        tokens_in = int(getattr(usage, "input_tokens", 0) or 0)
        tokens_out = int(getattr(usage, "output_tokens", 0) or 0)
        self._log_usage(
            model=model,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            operation="complete",
        )
        return text

    def extract_structured(
        self,
        messages: list[Message],
        *,
        schema: dict,
        system: str = "",
        tier: ModelTier = ModelTier.SMART,
    ) -> dict:
        """
        Estrae output strutturato via tool-use forzato.

        Definisce un tool sintetico (emit_structured_output) con input_schema=schema,
        forza il modello a chiamarlo via tool_choice. Ritorna block.input come dict.

        Solleva LLMValidationError se il modello non chiama il tool (es. end_turn).
        """
        client = self._get_client()
        model = _TIER_TO_MODEL[tier]

        tool_def = {
            "name": _STRUCTURED_TOOL_NAME,
            "description": (
                "Restituisce l'output strutturato richiesto. Devi sempre chiamare "
                "questo tool con i campi richiesti."
            ),
            "input_schema": schema,
        }

        kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": 4096,
            "temperature": 0.0,
            "messages": self._messages_to_anthropic(messages),
            "tools": [tool_def],
            "tool_choice": {"type": "tool", "name": _STRUCTURED_TOOL_NAME},
        }
        if system:
            kwargs["system"] = system

        response = self._call_with_retry(client.messages.create, **kwargs)

        usage = getattr(response, "usage", None)
        tokens_in = int(getattr(usage, "input_tokens", 0) or 0)
        tokens_out = int(getattr(usage, "output_tokens", 0) or 0)
        self._log_usage(
            model=model,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            operation="extract_structured",
        )

        # Cerca il primo blocco tool_use con il nome atteso
        for block in getattr(response, "content", []):
            block_type = getattr(block, "type", None)
            if block_type == "tool_use" and getattr(block, "name", None) == _STRUCTURED_TOOL_NAME:
                tool_input = getattr(block, "input", None)
                if not isinstance(tool_input, dict):
                    raise LLMValidationError(
                        "Tool-use ha ritornato input non-dict per emit_structured_output."
                    )
                # Valida l'input contro lo schema fornito: il modello puo' violarlo
                # (campi required mancanti, tipi sbagliati, ecc.).
                try:
                    jsonschema.validate(instance=tool_input, schema=schema)
                except jsonschema.ValidationError as exc:
                    raise LLMValidationError(
                        f"Output del tool non conforme allo schema: {exc.message}"
                    ) from exc
                return tool_input

        stop_reason = getattr(response, "stop_reason", "unknown")
        raise LLMValidationError(
            f"Il modello non ha chiamato il tool {_STRUCTURED_TOOL_NAME} "
            f"(stop_reason={stop_reason}). Output strutturato non disponibile."
        )

    def count_tokens(self, text: str) -> int:
        """
        Conta i token. Usa client.messages.count_tokens se disponibile, fallback len//4.

        Il fallback `len(text) // 4` e una stima grossolana ma accettabile per
        cost estimation; il design doc D1.2 lo prevede esplicitamente.
        """
        # Fallback semplice se non c'e API key (utile in test offline)
        if not self._api_key and self._client is None:
            return max(1, len(text) // 4)

        try:
            client = self._get_client()
        except LLMUnavailableError:
            return max(1, len(text) // 4)

        count_fn = getattr(getattr(client, "messages", None), "count_tokens", None)
        if count_fn is None:
            return max(1, len(text) // 4)

        try:
            result = count_fn(
                model=_TIER_TO_MODEL[ModelTier.SMART],
                messages=[{"role": "user", "content": text}],
            )
            tokens = int(getattr(result, "input_tokens", 0) or 0)
            self._log_usage(
                model=_TIER_TO_MODEL[ModelTier.SMART],
                tokens_in=tokens,
                tokens_out=0,
                operation="count_tokens",
            )
            return tokens if tokens > 0 else max(1, len(text) // 4)
        except (AttributeError, ValueError, TypeError) as exc:
            logger.warning("count_tokens fallback su stima len//4: %s", exc)
            return max(1, len(text) // 4)
        except Exception as exc:  # noqa: BLE001 — SDK puo' sollevare classi proprie
            # Catturiamo Exception (non BaseException) per non bloccare KeyboardInterrupt.
            # Il fallback su stima e' sempre piu utile di un crash.
            logger.warning("count_tokens errore SDK, fallback su stima: %s", exc)
            return max(1, len(text) // 4)
