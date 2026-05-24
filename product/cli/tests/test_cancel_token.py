"""Test :class:`CancelToken`."""

from __future__ import annotations

import threading

import pytest

from custodia_cli.jobs.cancel import CancelledError, CancelToken


def test_new_token_is_not_cancelled() -> None:
    token = CancelToken()
    assert token.is_cancelled is False
    # raise_if_cancelled deve essere no-op.
    token.raise_if_cancelled()


def test_set_cancelled_makes_token_cancelled() -> None:
    token = CancelToken()
    token.set_cancelled()
    assert token.is_cancelled is True


def test_raise_if_cancelled_raises_after_set() -> None:
    token = CancelToken()
    token.set_cancelled()
    with pytest.raises(CancelledError):
        token.raise_if_cancelled()


def test_set_cancelled_is_idempotent() -> None:
    token = CancelToken()
    token.set_cancelled()
    token.set_cancelled()  # non deve esplodere
    token.set_cancelled()
    assert token.is_cancelled is True


def test_thread_safety_under_contention() -> None:
    """10 thread setters + 10 thread readers, nessuna race."""
    token = CancelToken()
    barrier = threading.Barrier(20)
    errors: list[BaseException] = []

    def setter() -> None:
        barrier.wait()
        try:
            token.set_cancelled()
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    def reader() -> None:
        barrier.wait()
        try:
            for _ in range(1000):
                _ = token.is_cancelled
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=setter) for _ in range(10)] + [
        threading.Thread(target=reader) for _ in range(10)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5)
    assert errors == []
    assert token.is_cancelled is True
