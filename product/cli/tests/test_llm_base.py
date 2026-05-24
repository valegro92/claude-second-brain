"""Test del Protocol LLMProvider e dei tipi di base."""

from __future__ import annotations

from pathlib import Path

import pytest

from custodia_cli.llm import (
    LLMProvider,
    LLMUsage,
    Message,
    ModelTier,
    get_provider,
)
from custodia_cli.llm.anthropic_provider import AnthropicProvider
from custodia_cli.llm.fakes import FakeLLMProvider


FIXTURE_PATH = (
    Path(__file__).parent / "fixtures" / "llm" / "sample_responses.yaml"
)


def test_model_tier_values() -> None:
    """ModelTier ha esattamente tre valori canonici."""
    assert ModelTier.FAST.value == "fast"
    assert ModelTier.SMART.value == "smart"
    assert ModelTier.REASONING.value == "reasoning"


def test_message_is_frozen_dataclass() -> None:
    """Message e' immutabile e ha role/content."""
    msg = Message(role="user", content="ciao")
    assert msg.role == "user"
    assert msg.content == "ciao"
    with pytest.raises(Exception):
        msg.content = "altro"  # type: ignore[misc]


def test_llm_usage_fields() -> None:
    """LLMUsage espone tutti i campi richiesti."""
    usage = LLMUsage(
        provider="anthropic",
        model="claude-haiku-4-5",
        input_tokens=100,
        output_tokens=50,
        cost_eur_estimate=0.001,
        operation="complete",
        timestamp="2026-05-24T10:00:00+00:00",
    )
    assert usage.provider == "anthropic"
    assert usage.input_tokens == 100


def test_llm_usage_is_frozen() -> None:
    """LLMUsage e' immutabile: una mutazione post-init solleva FrozenInstanceError."""
    from dataclasses import FrozenInstanceError

    usage = LLMUsage(
        provider="anthropic",
        model="claude-haiku-4-5",
        input_tokens=100,
        output_tokens=50,
        cost_eur_estimate=0.001,
        operation="complete",
        timestamp="2026-05-24T10:00:00+00:00",
    )
    with pytest.raises(FrozenInstanceError):
        usage.input_tokens = 999  # type: ignore[misc]


def test_anthropic_provider_is_llm_provider() -> None:
    """AnthropicProvider e' istanza runtime del Protocol LLMProvider."""
    provider = AnthropicProvider(api_key="fake-key-for-protocol-check")
    assert isinstance(provider, LLMProvider)
    assert provider.name == "anthropic"
    assert provider.usage_log == []


def test_fake_provider_is_llm_provider() -> None:
    """FakeLLMProvider e' istanza runtime del Protocol LLMProvider."""
    provider = FakeLLMProvider(fixture_path=FIXTURE_PATH)
    assert isinstance(provider, LLMProvider)
    assert provider.name == "fake"
    assert provider.usage_log == []


def test_get_provider_default_anthropic(monkeypatch: pytest.MonkeyPatch) -> None:
    """get_provider() ritorna AnthropicProvider di default."""
    monkeypatch.delenv("CUSTODIA_LLM_PROVIDER", raising=False)
    monkeypatch.setenv("CUSTODIA_ANTHROPIC_API_KEY", "fake-key")
    provider = get_provider()
    assert isinstance(provider, AnthropicProvider)


def test_get_provider_fake_requires_fixture() -> None:
    """get_provider('fake') senza fixture_path solleva ValueError."""
    with pytest.raises(ValueError, match="fixture_path"):
        get_provider("fake")


def test_get_provider_fake_with_fixture() -> None:
    """get_provider('fake', fixture_path=...) ritorna un FakeLLMProvider."""
    provider = get_provider("fake", fixture_path=FIXTURE_PATH)
    assert isinstance(provider, FakeLLMProvider)


def test_get_provider_sovrano_placeholder() -> None:
    """get_provider('sovrano') solleva ValueError con messaggio chiaro su placeholder."""
    with pytest.raises(ValueError, match="sovrano"):
        get_provider("sovrano")


def test_get_provider_unknown() -> None:
    """get_provider con nome sconosciuto solleva ValueError."""
    with pytest.raises(ValueError, match="sconosciuto"):
        get_provider("nonexistent-provider")
