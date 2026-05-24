"""Stress test fixtures: corpus sintetico per benchmark Sprint 2a.

Esposto solo lo helper di generazione; il corpus reale vive in una cartella tmp
(default: ``$TMPDIR/custodia-stress-corpus``) per evitare di inquinare la repo.
"""

from __future__ import annotations

from tests.fixtures.stress.generate import generate_corpus

__all__ = ["generate_corpus"]
