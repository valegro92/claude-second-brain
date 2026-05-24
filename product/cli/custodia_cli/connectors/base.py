"""
Contratti comuni ai connettori sorgenti.

Definisce:
- ``SourceDocument``: unità di output di un connettore, consumata dall'extractor
  (U5). Immutabile (frozen dataclass + ``MappingProxyType`` su ``metadata``)
  per evitare modifiche accidentali durante il pipeline.
- ``Connector``: Protocol minimale che ogni connettore deve rispettare. Permette
  di scrivere extractor agnostici alla sorgente (Drive/FS/Outlook/...).
- ``ParserError``: eccezione tipata per fallimenti non-recuperabili dei parser.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Iterator, Mapping, Protocol, runtime_checkable


class ParserError(Exception):
    """Errore non-recuperabile durante il parsing di un file binario.

    I parser sollevano questa eccezione per condizioni che il connettore non
    può/non deve nascondere (es. file corrotto, libreria di parsing che lancia
    un'eccezione inattesa). I casi "recuperabili" (PDF password-protected,
    PDF image-only senza testo) ritornano invece stringa vuota senza errore.
    """


class ConnectorError(Exception):
    """Base per errori dei connettori (Outlook, FIC, futuri).

    Le sottoclassi permettono al chiamante (es. ``commands/scan.py``) di
    differenziare la gestione: auth → richiedi re-login; rate limit → suggerisci
    retry più tardi; API generico → log + abort della singola risorsa.
    """


class ConnectorAuthError(ConnectorError):
    """Errore di autenticazione: token mancante, scaduto o revocato."""


class ConnectorRateLimitError(ConnectorError):
    """Rate limit superato dopo l'esaurimento dei retry."""


class ConnectorAPIError(ConnectorError):
    """Errore generico API esterna (4xx non-retriable o 5xx persistente)."""


@dataclass(frozen=True)
class SourceDocument:
    """Documento sorgente estratto da un connettore, pronto per l'extractor.

    ``metadata`` è esposta come ``Mapping`` immutabile (``MappingProxyType``)
    per garantire che il pipeline downstream non possa mutarla accidentalmente,
    anche se ``frozen=True`` previene solo la sostituzione del campo.

    Attributes:
        source_id: identificatore univoco stabile fra rerun. Formato consigliato:
            ``"<connector_name>:<id>"`` (es. ``"gdrive:1AbCdEf"`` o
            ``"fs:<sha1>"``).
        source_path: path leggibile per l'utente (es.
            ``"/Drive/Commerciale/2024/preventivo.pdf"``).
        mime_type: MIME canonico (post-export per i Google-native).
        text: testo estratto. Stringa vuota se estrazione fallita ma non-fatale
            (es. PDF scansionato, file skippato in dry-run).
        metadata: campi extra per debug/audit (modified_time, drive_id,
            page_count, size_bytes, web_view_link, …). Esposta come mapping
            immutabile; default mapping vuoto.
    """

    source_id: str
    source_path: str
    mime_type: str
    text: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Wrappa ``metadata`` in ``MappingProxyType`` per immutabilità reale.

        Usiamo ``object.__setattr__`` perché la dataclass è ``frozen=True``.
        """
        # Materializziamo come dict (defensive copy) e poi proxy read-only.
        snapshot = dict(self.metadata) if self.metadata is not None else {}
        object.__setattr__(self, "metadata", MappingProxyType(snapshot))


@runtime_checkable
class Connector(Protocol):
    """Contratto comune a tutti i connettori sorgenti.

    Ogni connettore espone un nome stabile e produce uno stream di
    ``SourceDocument`` tramite ``iter_documents()``. Lo stream è "lazy": il
    consumer (tipicamente ``commands/scan.py``) chiama ``StateStore.add_document``
    file-by-file, così un crash a metà run lascia comunque persistito il lavoro
    fatto fino a quel punto.
    """

    name: str

    def iter_documents(self) -> Iterator[SourceDocument]:
        """Itera tutti i documenti della sorgente come stream."""
        ...


__all__ = [
    "Connector",
    "ConnectorAPIError",
    "ConnectorAuthError",
    "ConnectorError",
    "ConnectorRateLimitError",
    "ParserError",
    "SourceDocument",
]
