"""
Test del helper ``custodia_cli.connectors._http.request_with_retry``.

Strategia: ``_FakeSession`` programmabile + ``time.sleep`` stubbato per
verificare il comportamento di retry/backoff/Retry-After senza wall clock.
"""

from __future__ import annotations

import logging
from typing import Any

import pytest
import requests

from custodia_cli.connectors._http import request_with_retry


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class _FakeResponse:
    def __init__(
        self,
        *,
        status_code: int = 200,
        json_data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self._json = json_data or {}
        self.headers = headers or {}

    def json(self) -> dict[str, Any]:
        return self._json

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}", response=self)  # type: ignore[arg-type]


class _FakeSession:
    """Session che ritorna risposte (o raise pre-programmati) da una coda."""

    def __init__(self, items: list[Any]) -> None:
        self.items = list(items)
        self.calls = 0

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        timeout: float | int = 30,
    ) -> _FakeResponse:
        self.calls += 1
        if not self.items:
            return _FakeResponse(status_code=200)
        item = self.items.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def _stub_sleep(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    sleeps: list[float] = []
    monkeypatch.setattr(
        "custodia_cli.connectors._http.time.sleep",
        lambda s: sleeps.append(s),
    )
    return sleeps


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_happy_path_200_first_try() -> None:
    """200 al primo tentativo → ritorna response senza sleep."""
    session = _FakeSession([_FakeResponse(status_code=200, json_data={"ok": True})])
    resp = request_with_retry(session, "GET", "https://x.test/y")
    assert resp.status_code == 200
    assert session.calls == 1


def test_429_then_200(monkeypatch: pytest.MonkeyPatch) -> None:
    """429 al primo, 200 al secondo → success al secondo tentativo."""
    sleeps = _stub_sleep(monkeypatch)
    session = _FakeSession([
        _FakeResponse(status_code=429, headers={"Retry-After": "1"}),
        _FakeResponse(status_code=200, json_data={"ok": 1}),
    ])
    resp = request_with_retry(session, "GET", "https://x.test/y")
    assert resp.status_code == 200
    assert session.calls == 2
    assert sleeps == [1.0]


def test_429_x3_raises_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """429 × max_attempts → HTTPError dopo l'ultimo sleep."""
    _stub_sleep(monkeypatch)
    session = _FakeSession([
        _FakeResponse(status_code=429),
        _FakeResponse(status_code=429),
        _FakeResponse(status_code=429),
    ])
    with pytest.raises(requests.HTTPError):
        request_with_retry(session, "GET", "https://x.test/y", max_attempts=3)
    assert session.calls == 3


def test_retry_after_capped_at_max(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Retry-After: 999 → sleep al max 60.0 + warning."""
    sleeps = _stub_sleep(monkeypatch)
    session = _FakeSession([
        _FakeResponse(status_code=429, headers={"Retry-After": "999"}),
        _FakeResponse(status_code=200),
    ])
    with caplog.at_level(logging.WARNING, logger="custodia_cli.connectors._http"):
        request_with_retry(session, "GET", "https://x.test/y")
    assert sleeps == [60.0]
    assert any("eccede il cap" in r.message for r in caplog.records)


def test_retry_after_negative_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """Retry-After negativo → fallback al backoff esponenziale."""
    sleeps = _stub_sleep(monkeypatch)
    session = _FakeSession([
        _FakeResponse(status_code=429, headers={"Retry-After": "-5"}),
        _FakeResponse(status_code=200),
    ])
    request_with_retry(session, "GET", "https://x.test/y")
    # Backoff base 2s + jitter <= 0.5.
    assert sleeps and 2.0 <= sleeps[0] <= 2.5


def test_retry_after_http_date_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """Retry-After: HTTP-date format → ValueError catch, fallback backoff."""
    sleeps = _stub_sleep(monkeypatch)
    session = _FakeSession([
        _FakeResponse(
            status_code=503,
            headers={"Retry-After": "Wed, 21 Oct 2026 07:28:00 GMT"},
        ),
        _FakeResponse(status_code=200),
    ])
    request_with_retry(session, "GET", "https://x.test/y")
    assert sleeps and 2.0 <= sleeps[0] <= 2.5


def test_request_exception_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    """RequestException (ConnectionError) → retry, poi re-raise dopo max."""
    _stub_sleep(monkeypatch)
    session = _FakeSession([
        requests.ConnectionError("dns fail"),
        requests.ConnectionError("dns fail"),
        requests.ConnectionError("dns fail"),
    ])
    with pytest.raises(requests.ConnectionError):
        request_with_retry(session, "GET", "https://x.test/y", max_attempts=3)
    assert session.calls == 3


def test_request_exception_then_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """ConnectionError al primo, 200 al secondo → success."""
    _stub_sleep(monkeypatch)
    session = _FakeSession([
        requests.ConnectionError("transient"),
        _FakeResponse(status_code=200, json_data={"ok": True}),
    ])
    resp = request_with_retry(session, "GET", "https://x.test/y")
    assert resp.status_code == 200


def test_keyboard_interrupt_during_sleep_propagates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """KeyboardInterrupt durante sleep si propaga (non viene catturato)."""
    def _interrupt(_s: float) -> None:
        raise KeyboardInterrupt
    monkeypatch.setattr("custodia_cli.connectors._http.time.sleep", _interrupt)
    session = _FakeSession([
        _FakeResponse(status_code=429),
        _FakeResponse(status_code=200),
    ])
    with pytest.raises(KeyboardInterrupt):
        request_with_retry(session, "GET", "https://x.test/y")


@pytest.mark.parametrize("status", [500, 502, 503, 504])
def test_5xx_retriable(status: int, monkeypatch: pytest.MonkeyPatch) -> None:
    """Tutti i 5xx in default set sono retriable."""
    _stub_sleep(monkeypatch)
    session = _FakeSession([
        _FakeResponse(status_code=status),
        _FakeResponse(status_code=200),
    ])
    resp = request_with_retry(session, "GET", "https://x.test/y")
    assert resp.status_code == 200
    assert session.calls == 2


def test_404_not_retriable(monkeypatch: pytest.MonkeyPatch) -> None:
    """HTTP 404 non è retriable → raise immediato senza retry."""
    _stub_sleep(monkeypatch)
    session = _FakeSession([_FakeResponse(status_code=404)])
    with pytest.raises(requests.HTTPError):
        request_with_retry(session, "GET", "https://x.test/y")
    assert session.calls == 1
