"""Decoratore di retry con backoff esponenziale.

Usato per chiamate I/O potenzialmente flaky:
  - API Anthropic / Bedrock (rate limit, network blip)
  - API Google Drive / Microsoft Graph
  - I/O su NAS (timeout di rete)

Esempio:
    @retry_on((NetworkError, RateLimitError), attempts=3, backoff=2.0)
    def fetch(url): ...
"""

from __future__ import annotations

import functools
import logging
import time
from collections.abc import Callable
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def retry_on(
    exceptions: type[BaseException] | tuple[type[BaseException], ...],
    attempts: int = 3,
    backoff: float = 2.0,
    max_delay: float = 30.0,
    initial_delay: float = 1.0,
) -> Callable[[F], F]:
    """Decoratore: ritenta la funzione su exception specifiche con backoff esponenziale.

    Args:
        exceptions: eccezione o tuple di eccezioni che triggerano il retry.
        attempts: numero massimo di tentativi totali (incluso il primo).
        backoff: moltiplicatore del delay tra tentativi (2.0 = raddoppia ogni volta).
        max_delay: cap sul delay tra retry, in secondi.
        initial_delay: delay del primo retry (dopo il primo fallimento).

    Returns:
        Decoratore che wrappa la funzione.

    Raises:
        L'ultima eccezione catturata se tutti i tentativi falliscono.
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            delay = initial_delay
            last_exc: BaseException | None = None
            for attempt in range(1, attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    last_exc = exc
                    if attempt >= attempts:
                        logger.warning(
                            "Retry esauriti per %s dopo %d tentativi: %s",
                            func.__name__,
                            attempt,
                            exc,
                        )
                        raise
                    logger.info(
                        "Tentativo %d/%d fallito per %s (%s) — retry in %.1fs",
                        attempt,
                        attempts,
                        func.__name__,
                        type(exc).__name__,
                        delay,
                    )
                    time.sleep(delay)
                    delay = min(delay * backoff, max_delay)
            # Unreachable, ma per il type checker
            assert last_exc is not None  # noqa: S101
            raise last_exc

        return wrapper  # type: ignore[return-value]

    return decorator
