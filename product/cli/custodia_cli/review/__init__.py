"""
Modulo review: REPL human-in-the-loop e writer del vault Custodia.

Espone:
- :func:`run_review_repl` — REPL principale richiamato da `custodia review`.
- :func:`write_entities` — scrittura idempotente delle entity nel vault.
- :func:`dump_frontmatter` — serializzazione YAML deterministico.
"""

from __future__ import annotations

from custodia_cli.review.interactive import run_review_repl
from custodia_cli.review.writer import WriteResult, write_entities
from custodia_cli.review.yaml_io import dump_frontmatter, ordered_keys_for_type

__all__ = [
    "run_review_repl",
    "write_entities",
    "WriteResult",
    "dump_frontmatter",
    "ordered_keys_for_type",
]
