"""Enum condivisi tra categorizer, reconciler, batch UI, watcher."""
from __future__ import annotations

from enum import Enum


class Categoria(str, Enum):
    """Le 5 categorie operative per ogni file scandagliato (vedi docs/05-manuale-custode.md Fase 2)."""

    VIVO = "vivo"
    DA_CONSULTARE = "da-consultare"
    ARCHIVIO = "archivio"
    CESTINO = "cestino"
    DA_CHIARIRE = "da-chiarire"


class StatoBozza(str, Enum):
    """Stato di una bozza nel batch approval UI."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EDITED = "edited"
    PARKED = "parked"
