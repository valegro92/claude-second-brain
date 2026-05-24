"""Test del FakeLLMProvider deterministico."""

from __future__ import annotations

from pathlib import Path

import pytest

from custodia_cli.llm import Message, ModelTier
from custodia_cli.llm.fakes import FakeLLMProvider


FIXTURE_PATH = (
    Path(__file__).parent / "fixtures" / "llm" / "sample_responses.yaml"
)


def test_complete_matches_prefix() -> None:
    """complete ritorna la stringa associata al primo match_prefix."""
    provider = FakeLLMProvider(fixture_path=FIXTURE_PATH)
    result = provider.complete(
        messages=[Message(role="user", content="Categorizza questo cliente.")],
        system="Sei un classificatore PMI italiane.",
        tier=ModelTier.FAST,
    )
    assert result == "Categoria: cliente_attivo"


def test_complete_logs_usage() -> None:
    """Ogni chiamata complete appende un record a usage_log."""
    provider = FakeLLMProvider(fixture_path=FIXTURE_PATH)
    provider.complete(
        messages=[Message(role="user", content="test")],
        system="Sei un classificatore PMI italiane.",
    )
    assert len(provider.usage_log) == 1
    log = provider.usage_log[0]
    assert log.provider == "fake"
    assert log.operation == "complete"
    assert log.input_tokens == 120
    assert log.output_tokens == 8


def test_extract_structured_returns_dict() -> None:
    """extract_structured ritorna il dict associato."""
    provider = FakeLLMProvider(fixture_path=FIXTURE_PATH)
    result = provider.extract_structured(
        messages=[Message(role="user", content="dati qui")],
        schema={"type": "object"},
        system="Estrai i dati cliente",
    )
    assert isinstance(result, dict)
    assert result["nome"] == "Rossetto Laminazioni SRL"
    assert result["partita_iva"] == "01234567890"


def test_no_match_raises_keyerror() -> None:
    """KeyError diagnostico se nessun prefix matcha."""
    provider = FakeLLMProvider(fixture_path=FIXTURE_PATH)
    with pytest.raises(KeyError, match="nessuna response"):
        provider.complete(
            messages=[Message(role="user", content="random")],
            system="System prompt che non matcha nulla nella fixture",
        )


def test_missing_fixture_raises() -> None:
    """File fixture inesistente solleva FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        FakeLLMProvider(fixture_path="/tmp/nonexistent-custodia-fixture.yaml")


def test_operation_filter() -> None:
    """Un prefix con operation 'extract_structured' non risponde a complete."""
    provider = FakeLLMProvider(fixture_path=FIXTURE_PATH)
    # "Estrai i dati cliente" e' registrato solo come extract_structured
    with pytest.raises(KeyError):
        provider.complete(
            messages=[Message(role="user", content="dati")],
            system="Estrai i dati cliente",
        )


def test_count_tokens_estimate() -> None:
    """count_tokens ritorna una stima >=1."""
    provider = FakeLLMProvider(fixture_path=FIXTURE_PATH)
    assert provider.count_tokens("ciao") >= 1
    assert provider.count_tokens("x" * 400) == 100


def test_empty_messages_raises_value_error() -> None:
    """complete con messages vuoto solleva ValueError."""
    provider = FakeLLMProvider(fixture_path=FIXTURE_PATH)
    with pytest.raises(ValueError, match="vuoto"):
        provider.complete(messages=[], system="qualunque")


def test_empty_messages_extract_structured_raises_value_error() -> None:
    """extract_structured con messages vuoto solleva ValueError."""
    provider = FakeLLMProvider(fixture_path=FIXTURE_PATH)
    with pytest.raises(ValueError, match="vuoto"):
        provider.extract_structured(messages=[], schema={"type": "object"})


def test_keyerror_lists_available_prefixes() -> None:
    """Il KeyError include la lista dei prefix disponibili (diagnostica)."""
    provider = FakeLLMProvider(fixture_path=FIXTURE_PATH)
    with pytest.raises(KeyError, match="Prefix disponibili"):
        provider.complete(
            messages=[Message(role="user", content="random")],
            system="System prompt che non matcha nulla nella fixture",
        )
