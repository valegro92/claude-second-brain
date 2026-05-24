"""Test per i moduli helper Wave 1: errors, _atomic, _retry, _subprocess."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from wiki import __version__
from wiki._atomic import (
    append_jsonl,
    atomic_write_bytes,
    atomic_write_json,
    atomic_write_text,
)
from wiki._retry import retry_on
from wiki._subprocess import run_with_timeout, which_or_none
from wiki.errors import (
    ConfigError,
    ExtractError,
    LLMError,
    PipelineError,
    SubprocessError,
    ValidationError,
    WikiError,
)


# --- version --------------------------------------------------------------


def test_version_set() -> None:
    assert __version__
    assert __version__.count(".") >= 1


# --- errors ---------------------------------------------------------------


def test_error_hierarchy() -> None:
    """Tutte le custom exception ereditano da WikiError."""
    for cls in (ConfigError, ExtractError, LLMError, PipelineError, SubprocessError, ValidationError):
        assert issubclass(cls, WikiError)


def test_wiki_error_raises_and_catches() -> None:
    with pytest.raises(WikiError):
        raise ConfigError("test")


# --- _atomic --------------------------------------------------------------


def test_atomic_write_text(tmp_path: Path) -> None:
    target = tmp_path / "out.txt"
    atomic_write_text(target, "ciao mondo")
    assert target.read_text(encoding="utf-8") == "ciao mondo"


def test_atomic_write_text_overwrite(tmp_path: Path) -> None:
    target = tmp_path / "out.txt"
    atomic_write_text(target, "v1")
    atomic_write_text(target, "v2")
    assert target.read_text(encoding="utf-8") == "v2"


def test_atomic_write_text_creates_parent(tmp_path: Path) -> None:
    target = tmp_path / "sub" / "deep" / "out.txt"
    atomic_write_text(target, "x")
    assert target.exists()


def test_atomic_write_bytes(tmp_path: Path) -> None:
    target = tmp_path / "blob.bin"
    atomic_write_bytes(target, b"\x00\x01\x02")
    assert target.read_bytes() == b"\x00\x01\x02"


def test_atomic_write_json(tmp_path: Path) -> None:
    target = tmp_path / "data.json"
    atomic_write_json(target, {"a": 1, "b": [2, 3]})
    assert json.loads(target.read_text(encoding="utf-8")) == {"a": 1, "b": [2, 3]}


def test_atomic_no_tmp_leftover_after_success(tmp_path: Path) -> None:
    target = tmp_path / "out.txt"
    atomic_write_text(target, "ok")
    leftovers = [p for p in tmp_path.iterdir() if p.suffix == ".tmp"]
    assert leftovers == []


def test_append_jsonl(tmp_path: Path) -> None:
    target = tmp_path / "log.jsonl"
    append_jsonl(target, {"a": 1})
    append_jsonl(target, {"b": 2})
    lines = target.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0]) == {"a": 1}
    assert json.loads(lines[1]) == {"b": 2}


# --- _retry ---------------------------------------------------------------


def test_retry_success_at_first() -> None:
    calls = {"n": 0}

    @retry_on(ValueError, attempts=3, initial_delay=0.01)
    def f() -> str:
        calls["n"] += 1
        return "ok"

    assert f() == "ok"
    assert calls["n"] == 1


def test_retry_success_at_third() -> None:
    calls = {"n": 0}

    @retry_on(ValueError, attempts=3, initial_delay=0.01, backoff=1.0)
    def f() -> str:
        calls["n"] += 1
        if calls["n"] < 3:
            raise ValueError("not yet")
        return "ok"

    assert f() == "ok"
    assert calls["n"] == 3


def test_retry_exhausted_raises() -> None:
    @retry_on(ValueError, attempts=2, initial_delay=0.01)
    def f() -> str:
        raise ValueError("always fail")

    with pytest.raises(ValueError):
        f()


def test_retry_unrelated_exception_not_caught() -> None:
    @retry_on(ValueError, attempts=3, initial_delay=0.01)
    def f() -> str:
        raise TypeError("wrong type")

    with pytest.raises(TypeError):
        f()


def test_retry_backoff_timing(monkeypatch: pytest.MonkeyPatch) -> None:
    sleeps: list[float] = []
    monkeypatch.setattr(time, "sleep", lambda s: sleeps.append(s))

    @retry_on(ValueError, attempts=4, initial_delay=1.0, backoff=2.0, max_delay=10.0)
    def f() -> None:
        raise ValueError("fail")

    with pytest.raises(ValueError):
        f()
    # 3 sleep tra 4 tentativi: 1.0, 2.0, 4.0
    assert sleeps == [1.0, 2.0, 4.0]


# --- _subprocess ----------------------------------------------------------


def test_run_with_timeout_success() -> None:
    result = run_with_timeout(["echo", "hello"], timeout=5)
    assert result.returncode == 0
    assert b"hello" in result.stdout


def test_run_with_timeout_binary_not_found() -> None:
    with pytest.raises(SubprocessError, match="non trovato"):
        run_with_timeout(["binario-inesistente-xyz"], timeout=5)


def test_run_with_timeout_nonzero_exit() -> None:
    with pytest.raises(SubprocessError, match="exit code"):
        run_with_timeout(["false"], timeout=5)


def test_run_with_timeout_no_check() -> None:
    result = run_with_timeout(["false"], timeout=5, check=False)
    assert result.returncode != 0


def test_run_with_timeout_expires() -> None:
    with pytest.raises(SubprocessError, match="Timeout"):
        run_with_timeout(["sleep", "5"], timeout=0.1)


def test_which_or_none_existing() -> None:
    assert which_or_none("ls") is not None


def test_which_or_none_missing() -> None:
    assert which_or_none("binario-non-esiste-xyz") is None
