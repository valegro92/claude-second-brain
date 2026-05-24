"""
Test dell'AnthropicProvider con SDK stub-ato (nessuna chiamata di rete).

Strategia: iniettiamo un fake client via parametro `client=` del costruttore,
costruito con SimpleNamespace per imitare la shape della response dell'SDK
(content come lista di blocchi con attributi `type`, `text`, `name`, `input`;
usage con `input_tokens`/`output_tokens`).
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from custodia_cli.llm import Message, ModelTier
from custodia_cli.llm.anthropic_provider import (
    _PRICING_USD,
    _TIER_TO_MODEL,
    AnthropicProvider,
)
from custodia_cli.llm.exceptions import (
    LLMRateLimitError,
    LLMUnavailableError,
    LLMValidationError,
)


# --- Helpers per costruire fake response Anthropic-like -----------------------------


def _make_text_response(text: str, *, tokens_in: int = 100, tokens_out: int = 50) -> Any:
    """Fake response Anthropic con un singolo blocco di tipo text."""
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text=text)],
        usage=SimpleNamespace(input_tokens=tokens_in, output_tokens=tokens_out),
        stop_reason="end_turn",
    )


def _make_tool_use_response(
    tool_name: str,
    tool_input: dict,
    *,
    tokens_in: int = 200,
    tokens_out: int = 80,
) -> Any:
    """Fake response Anthropic con un blocco tool_use."""
    return SimpleNamespace(
        content=[
            SimpleNamespace(
                type="tool_use",
                name=tool_name,
                input=tool_input,
                id="tool_use_id_fake",
            )
        ],
        usage=SimpleNamespace(input_tokens=tokens_in, output_tokens=tokens_out),
        stop_reason="tool_use",
    )


def _make_end_turn_no_tool_response() -> Any:
    """Response in cui il modello NON chiama il tool (es. end_turn diretto)."""
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text="non ho strumenti")],
        usage=SimpleNamespace(input_tokens=50, output_tokens=10),
        stop_reason="end_turn",
    )


class _FakeRateLimitError(Exception):
    """Mock di RateLimitError dell'SDK Anthropic (basato su status_code)."""

    def __init__(self, message: str = "rate limited") -> None:
        super().__init__(message)
        self.status_code = 429


class _FakeMessagesAPI:
    """Imita client.messages con .create()."""

    def __init__(self, responses: list[Any]) -> None:
        self._responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> Any:
        """Ritorna (o solleva) il prossimo elemento dalla queue."""
        self.calls.append(kwargs)
        if not self._responses:
            raise RuntimeError("Fake API: queue di risposte esaurita.")
        nxt = self._responses.pop(0)
        if isinstance(nxt, BaseException):
            raise nxt
        return nxt


class _FakeAnthropicClient:
    """Minimo client che espone .messages.create()."""

    def __init__(self, responses: list[Any]) -> None:
        self.messages = _FakeMessagesAPI(responses)


# --- Test ------------------------------------------------------------------------


def test_complete_happy_path() -> None:
    """complete ritorna testo e logga usage."""
    client = _FakeAnthropicClient([_make_text_response("Ciao, sono Claude.")])
    provider = AnthropicProvider(api_key="fake", client=client)

    result = provider.complete(
        messages=[Message(role="user", content="Salutami")],
        system="Sei cortese",
        tier=ModelTier.FAST,
    )

    assert result == "Ciao, sono Claude."
    assert len(provider.usage_log) == 1
    log = provider.usage_log[0]
    assert log.provider == "anthropic"
    assert log.model == "claude-haiku-4-5"
    assert log.operation == "complete"
    assert log.input_tokens == 100
    assert log.output_tokens == 50
    assert log.cost_eur_estimate > 0


def test_complete_passes_system_and_model() -> None:
    """complete inoltra system prompt e mappa correttamente il tier."""
    client = _FakeAnthropicClient([_make_text_response("ok")])
    provider = AnthropicProvider(api_key="fake", client=client)

    provider.complete(
        messages=[Message(role="user", content="x")],
        system="prompt sistema",
        tier=ModelTier.SMART,
    )

    call = client.messages.calls[0]
    assert call["model"] == "claude-sonnet-4-6"
    assert call["system"] == "prompt sistema"
    assert call["messages"] == [{"role": "user", "content": "x"}]


def test_extract_structured_happy_path() -> None:
    """extract_structured ritorna il dict dal blocco tool_use."""
    expected = {"nome": "Rossetto SRL", "partita_iva": "01234567890"}
    client = _FakeAnthropicClient(
        [_make_tool_use_response("emit_structured_output", expected)]
    )
    provider = AnthropicProvider(api_key="fake", client=client)

    result = provider.extract_structured(
        messages=[Message(role="user", content="estrai i dati")],
        schema={"type": "object", "properties": {"nome": {"type": "string"}}},
        system="estrattore",
        tier=ModelTier.SMART,
    )

    assert result == expected

    # Verifica che il tool sia stato passato correttamente
    call = client.messages.calls[0]
    assert call["tool_choice"] == {
        "type": "tool",
        "name": "emit_structured_output",
    }
    assert call["tools"][0]["name"] == "emit_structured_output"
    assert call["tools"][0]["input_schema"] == {
        "type": "object",
        "properties": {"nome": {"type": "string"}},
    }


def test_extract_structured_no_tool_use_raises_validation_error() -> None:
    """Se il modello non chiama il tool, solleva LLMValidationError."""
    client = _FakeAnthropicClient([_make_end_turn_no_tool_response()])
    provider = AnthropicProvider(api_key="fake", client=client)

    with pytest.raises(LLMValidationError, match="emit_structured_output"):
        provider.extract_structured(
            messages=[Message(role="user", content="x")],
            schema={"type": "object"},
        )


def test_retry_on_rate_limit_then_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Un 429 al primo tentativo viene retried e si arriva al successo."""
    # Patch time.sleep per non rallentare i test
    monkeypatch.setattr("custodia_cli.llm.anthropic_provider.time.sleep", lambda _s: None)

    client = _FakeAnthropicClient(
        [
            _FakeRateLimitError("first attempt 429"),
            _make_text_response("recovered"),
        ]
    )
    provider = AnthropicProvider(api_key="fake", client=client)

    result = provider.complete(messages=[Message(role="user", content="x")])

    assert result == "recovered"
    assert len(client.messages.calls) == 2


def test_retry_exhausted_raises_rate_limit_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tre 429 consecutivi sollevano LLMRateLimitError."""
    monkeypatch.setattr("custodia_cli.llm.anthropic_provider.time.sleep", lambda _s: None)

    client = _FakeAnthropicClient(
        [
            _FakeRateLimitError("1"),
            _FakeRateLimitError("2"),
            _FakeRateLimitError("3"),
        ]
    )
    provider = AnthropicProvider(api_key="fake", client=client)

    with pytest.raises(LLMRateLimitError, match="3 tentativi"):
        provider.complete(messages=[Message(role="user", content="x")])

    assert len(client.messages.calls) == 3


def test_missing_api_key_raises_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    """Senza API key e senza client, _get_client solleva LLMUnavailableError."""
    monkeypatch.delenv("CUSTODIA_ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    provider = AnthropicProvider()  # nessun api_key, nessun client

    with pytest.raises(LLMUnavailableError, match="API key Anthropic"):
        provider.complete(messages=[Message(role="user", content="x")])


def test_count_tokens_fallback_estimate(monkeypatch: pytest.MonkeyPatch) -> None:
    """Senza API key, count_tokens cade su stima len//4."""
    monkeypatch.delenv("CUSTODIA_ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    provider = AnthropicProvider()

    assert provider.count_tokens("x" * 400) == 100
    assert provider.count_tokens("") == 1  # max(1, ...)


def test_count_tokens_via_sdk_when_available() -> None:
    """Se client.messages.count_tokens esiste, viene usato."""

    class _Counter:
        def count_tokens(self, **_kwargs: Any) -> Any:
            return SimpleNamespace(input_tokens=42)

        def create(self, **_kwargs: Any) -> Any:  # noqa: D401
            """Stub non chiamato in questo test."""
            raise RuntimeError("not used")

    client = SimpleNamespace(messages=_Counter())
    provider = AnthropicProvider(api_key="fake", client=client)

    assert provider.count_tokens("qualunque testo") == 42
    assert len(provider.usage_log) == 1
    assert provider.usage_log[0].operation == "count_tokens"


def test_tier_mapping_reasoning() -> None:
    """Tier REASONING mappa a claude-opus-4-7."""
    client = _FakeAnthropicClient([_make_text_response("ok")])
    provider = AnthropicProvider(api_key="fake", client=client)
    provider.complete(
        messages=[Message(role="user", content="x")],
        tier=ModelTier.REASONING,
    )
    assert client.messages.calls[0]["model"] == "claude-opus-4-7"


@pytest.mark.parametrize("tier", list(ModelTier))
def test_all_tier_models_have_pricing(tier: ModelTier) -> None:
    """Ogni modello mappato da _TIER_TO_MODEL DEVE essere in _PRICING_USD."""
    model = _TIER_TO_MODEL[tier]
    assert model in _PRICING_USD, (
        f"Modello {model} (tier={tier.value}) manca in _PRICING_USD. "
        f"Aggiornare la tabella prezzi."
    )


def test_retry_backoff_delays_with_jitter(monkeypatch: pytest.MonkeyPatch) -> None:
    """I delay di backoff sono [2.0+jitter, 4.0+jitter] tra i 3 tentativi (2 sleep)."""
    sleeps: list[float] = []
    monkeypatch.setattr(
        "custodia_cli.llm.anthropic_provider.time.sleep",
        lambda s: sleeps.append(s),
    )
    # Stub jitter a 0 per asserzione deterministica
    monkeypatch.setattr(
        "custodia_cli.llm.anthropic_provider.random.uniform",
        lambda _a, _b: 0.0,
    )

    client = _FakeAnthropicClient(
        [
            _FakeRateLimitError("1"),
            _FakeRateLimitError("2"),
            _make_text_response("ok finalmente"),
        ]
    )
    provider = AnthropicProvider(api_key="fake", client=client)
    result = provider.complete(messages=[Message(role="user", content="x")])

    assert result == "ok finalmente"
    # Esattamente 2 sleep tra 3 tentativi, con backoff (2.0, 4.0)
    assert sleeps == [2.0, 4.0]


def test_retry_backoff_jitter_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    """Con jitter random, ogni sleep e' in [base, base+0.5)."""
    sleeps: list[float] = []
    monkeypatch.setattr(
        "custodia_cli.llm.anthropic_provider.time.sleep",
        lambda s: sleeps.append(s),
    )
    client = _FakeAnthropicClient(
        [
            _FakeRateLimitError("1"),
            _FakeRateLimitError("2"),
            _make_text_response("ok"),
        ]
    )
    provider = AnthropicProvider(api_key="fake", client=client)
    provider.complete(messages=[Message(role="user", content="x")])

    assert len(sleeps) == 2
    assert 2.0 <= sleeps[0] < 2.5
    assert 4.0 <= sleeps[1] < 4.5


def test_keyboard_interrupt_propagates(monkeypatch: pytest.MonkeyPatch) -> None:
    """KeyboardInterrupt durante sleep NON viene catturata come retry-able."""

    def _raise_kbi(_s: float) -> None:
        raise KeyboardInterrupt()

    monkeypatch.setattr("custodia_cli.llm.anthropic_provider.time.sleep", _raise_kbi)

    client = _FakeAnthropicClient(
        [
            _FakeRateLimitError("1"),  # forza retry -> sleep -> KBI
            _make_text_response("never reached"),
        ]
    )
    provider = AnthropicProvider(api_key="fake", client=client)

    with pytest.raises(KeyboardInterrupt):
        provider.complete(messages=[Message(role="user", content="x")])


def test_extract_structured_validates_required(monkeypatch: pytest.MonkeyPatch) -> None:
    """Schema con required: input senza il campo solleva LLMValidationError."""
    schema = {
        "type": "object",
        "properties": {
            "nome": {"type": "string"},
            "piva": {"type": "string"},
        },
        "required": ["nome", "piva"],
    }
    # input manca 'piva'
    client = _FakeAnthropicClient(
        [_make_tool_use_response("emit_structured_output", {"nome": "X"})]
    )
    provider = AnthropicProvider(api_key="fake", client=client)

    with pytest.raises(LLMValidationError, match="schema"):
        provider.extract_structured(
            messages=[Message(role="user", content="x")],
            schema=schema,
        )


def test_extract_structured_validates_type() -> None:
    """Tipo sbagliato (string invece di int) solleva LLMValidationError."""
    schema = {
        "type": "object",
        "properties": {"count": {"type": "integer"}},
        "required": ["count"],
    }
    client = _FakeAnthropicClient(
        [_make_tool_use_response("emit_structured_output", {"count": "not-an-int"})]
    )
    provider = AnthropicProvider(api_key="fake", client=client)

    with pytest.raises(LLMValidationError, match="schema"):
        provider.extract_structured(
            messages=[Message(role="user", content="x")],
            schema=schema,
        )


def test_extract_structured_validates_happy_path_with_required() -> None:
    """Schema con required tutti presenti e tipi corretti: pass."""
    schema = {
        "type": "object",
        "properties": {
            "nome": {"type": "string"},
            "piva": {"type": "string"},
        },
        "required": ["nome", "piva"],
    }
    expected = {"nome": "X SRL", "piva": "1234567890"}
    client = _FakeAnthropicClient(
        [_make_tool_use_response("emit_structured_output", expected)]
    )
    provider = AnthropicProvider(api_key="fake", client=client)

    result = provider.extract_structured(
        messages=[Message(role="user", content="estrai")],
        schema=schema,
    )
    assert result == expected


def test_cost_estimate_haiku() -> None:
    """Cost estimate per Haiku 4.5 e' coerente con la tabella prezzi."""
    client = _FakeAnthropicClient(
        [_make_text_response("ok", tokens_in=1_000_000, tokens_out=1_000_000)]
    )
    provider = AnthropicProvider(api_key="fake", client=client)
    provider.complete(
        messages=[Message(role="user", content="x")],
        tier=ModelTier.FAST,
    )
    # Haiku: 0.80 + 4.00 = 4.80 USD per 1M+1M token
    # * 0.92 EUR/USD = 4.416 EUR
    cost = provider.usage_log[0].cost_eur_estimate
    assert 4.3 < cost < 4.5
