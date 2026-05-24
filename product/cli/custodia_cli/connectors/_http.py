"""
Helper per richieste HTTP con retry e backoff, condiviso fra connettori che
parlano con API REST esterne (Outlook, Fatture in Cloud, eventuali altri
futuri).

Caratteristiche:
- Retry su set configurabile di status code transient (default: 429 + 5xx).
- Backoff esponenziale + jitter random(0, 0.5) come fallback.
- Header ``Retry-After`` rispettato, *cappato* a ``retry_after_max`` (default
  60s) per evitare DoS di noi stessi se il server sbaglia. Valori negativi o
  non-numerici (es. HTTP-date) → fallback al backoff calcolato.
- ``requests.RequestException`` (connection error, timeout) trattata come
  retriable.
- ``KeyboardInterrupt`` durante ``time.sleep`` propaga senza catturare.
- Dopo l'ultimo tentativo, ``raise_for_status()`` propaga l'errore HTTP al
  chiamante; per ``RequestException`` esauste l'eccezione originale re-raise.

Non gestisce qui la traduzione in eccezioni custom (``ConnectorAuthError`` &
co.): è responsabilità del chiamante mappare ``HTTPError.response.status_code``
sull'eccezione semantica appropriata, perché lo stesso ``401`` significa cose
diverse fra Outlook e FIC.
"""

from __future__ import annotations

import logging
import random
import time
from typing import Any

import requests

logger = logging.getLogger(__name__)

_DEFAULT_RETRY_STATUSES: frozenset[int] = frozenset({429, 500, 502, 503, 504})
_DEFAULT_MAX_ATTEMPTS = 3
_DEFAULT_BACKOFF_SECONDS: tuple[float, ...] = (2.0, 4.0, 8.0)
_DEFAULT_RETRY_AFTER_MAX = 60.0


def request_with_retry(
    session: requests.Session,
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
    timeout: float = 30.0,
    retriable_statuses: frozenset[int] = _DEFAULT_RETRY_STATUSES,
    max_attempts: int = _DEFAULT_MAX_ATTEMPTS,
    backoff_seconds: tuple[float, ...] = _DEFAULT_BACKOFF_SECONDS,
    retry_after_max: float = _DEFAULT_RETRY_AFTER_MAX,
) -> requests.Response:
    """Esegue una request HTTP con retry su status code transient.

    Args:
        session: ``requests.Session`` (per connection pooling).
        method: verbo HTTP (``GET``, ``POST``, ...).
        url: URL completo.
        headers: header opzionali.
        params: query params opzionali.
        json_body: body JSON opzionale (per POST/PUT).
        timeout: timeout per singola request (default 30s).
        retriable_statuses: status code che triggherano retry.
        max_attempts: numero massimo di tentativi (incluso il primo).
        backoff_seconds: sequenza base di sleep per i retry (l'ultimo valore
            viene riusato se gli attempt eccedono).
        retry_after_max: cap massimo (secondi) per il rispetto di
            ``Retry-After`` server-side. Evita di bloccarsi per ore se il
            server invia valori assurdi.

    Returns:
        ``requests.Response`` con status < 400 (o status non-retriable: in tal
        caso ``raise_for_status`` è già stato chiamato e ha sollevato).

    Raises:
        requests.HTTPError: per status non-retriable o retriable esauriti.
        requests.RequestException: per errori di rete esauriti.
    """
    last_exc: requests.RequestException | None = None
    for attempt in range(max_attempts):
        try:
            response = session.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json_body,
                timeout=timeout,
            )
        except requests.RequestException as exc:
            last_exc = exc
            if attempt >= max_attempts - 1:
                raise
            sleep_s = _compute_backoff(
                None, attempt, backoff_seconds, retry_after_max
            )
            logger.warning(
                "⚠️  Errore di rete su %s (tentativo %d/%d): %s. Retry in %.1fs.",
                url,
                attempt + 1,
                max_attempts,
                exc,
                sleep_s,
            )
            time.sleep(sleep_s)
            continue

        if response.status_code not in retriable_statuses:
            response.raise_for_status()
            return response

        if attempt >= max_attempts - 1:
            response.raise_for_status()
            return response  # pragma: no cover — raise_for_status l'ha già fatto

        retry_after = response.headers.get("Retry-After")
        sleep_s = _compute_backoff(
            retry_after, attempt, backoff_seconds, retry_after_max
        )
        logger.warning(
            "⚠️  HTTP %d su %s (tentativo %d/%d). Retry in %.1fs.",
            response.status_code,
            url,
            attempt + 1,
            max_attempts,
            sleep_s,
        )
        time.sleep(sleep_s)

    # Unreachable in pratica: gli ultimi rami sopra raise o return.
    if last_exc is not None:  # pragma: no cover
        raise last_exc
    raise RuntimeError("request_with_retry: stato inaspettato")  # pragma: no cover


def _compute_backoff(
    retry_after: str | None,
    attempt: int,
    backoff_seconds: tuple[float, ...],
    max_value: float,
) -> float:
    """Calcola lo sleep per il prossimo retry.

    Priorità:
    1. ``Retry-After`` numerico positivo → ``min(value, max_value)``. Se il
       server invia un valore assurdo (es. 3600) cappato a ``max_value`` per
       non bloccare lo scan e log warning.
    2. ``Retry-After`` non parsabile (HTTP-date, negativo, non numerico) →
       fallback al backoff esponenziale.
    3. Nessun ``Retry-After`` → backoff esponenziale da ``backoff_seconds`` +
       jitter ``random(0, 0.5)``.
    """
    if retry_after is not None:
        try:
            value = float(retry_after)
        except ValueError:
            # HTTP-date format o stringa garbage: fallback.
            value = -1.0
        if value > 0:
            if value > max_value:
                logger.warning(
                    "⚠️  Retry-After=%.1fs eccede il cap %.1fs; cappo.",
                    value,
                    max_value,
                )
                return max_value
            return value
    base = backoff_seconds[min(attempt, len(backoff_seconds) - 1)]
    return base + random.uniform(0, 0.5)


__all__ = ["request_with_retry"]
