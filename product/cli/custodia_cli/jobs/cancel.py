"""
CancelToken: meccanismo thread-safe per richiedere la cancellazione di un job.

Pattern di utilizzo: il job esegue una funzione long-running in un thread
worker; al chiamante esterno (CLI, web UI, MCP server) viene esposto un token
che può essere "settato" per chiedere la cancellazione. Il worker chiama
``raise_if_cancelled()`` a ogni unità di lavoro (file, item, batch) e l'eccezione
``CancelledError`` viene catturata dal :class:`JobRunner` che marca il run come
``cancelled``.
"""

from __future__ import annotations

import threading


class CancelledError(Exception):
    """Sollevata quando un job viene cancellato via :class:`CancelToken`."""


class CancelToken:
    """Token thread-safe per richiedere la cancellazione di un job.

    Wrapper minimo attorno a :class:`threading.Event`. La scelta di non usare
    direttamente ``Event`` rende l'API più esplicita (``is_cancelled``,
    ``raise_if_cancelled``) e permette eventuali estensioni future (es. motivo
    della cancellazione, propagazione a sub-token).
    """

    def __init__(self) -> None:
        self._event = threading.Event()

    def set_cancelled(self) -> None:
        """Marca il token come cancellato. Idempotente."""
        self._event.set()

    @property
    def is_cancelled(self) -> bool:
        """Ritorna ``True`` se ``set_cancelled`` è stato chiamato."""
        return self._event.is_set()

    def raise_if_cancelled(self) -> None:
        """Solleva :class:`CancelledError` se il token è cancellato.

        Chiamare a ogni file/item processato per garantire cancel responsivo.
        """
        if self._event.is_set():
            raise CancelledError("Job interrotto dal token di cancellazione.")
