"""
Connettori sorgenti per Custodia CLI.

Espone l'astrazione comune ``Connector`` + dataclass ``SourceDocument``
condivisa fra Google Drive (U3), filesystem locale (U4) e futuri connettori.
"""

from __future__ import annotations

from custodia_cli.connectors.base import (
    Connector,
    ParserError,
    SourceDocument,
)

__all__ = ["Connector", "ParserError", "SourceDocument"]
