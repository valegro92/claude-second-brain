"""
Wrapper della webapp attorno al writer del vault (`custodia write`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from custodia_cli.commands.init import state_db_path_for_vault
from custodia_cli.review import write_entities
from custodia_cli.state import StateStore


@dataclass
class WriteSummary:
    """Esito del write end-to-end visto dalla webapp."""

    written: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    backups: list[str] = field(default_factory=list)
    errors: list[tuple[str, str]] = field(default_factory=list)
    pending_count: int = 0
    error: str | None = None


def write_pending(*, vault: Path, backup: bool = True) -> WriteSummary:
    """Scrive nel vault tutte le entity approved-non-written."""
    vault = Path(vault).expanduser().resolve()
    db_path = state_db_path_for_vault(vault)
    if not db_path.exists():
        return WriteSummary(error=f"State DB non trovato: {db_path}")

    summary = WriteSummary()
    try:
        with StateStore(db_path) as store:
            pending = store.list_pending_writes()
            summary.pending_count = len(pending)
            if not pending:
                return summary

            res = write_entities(pending, vault, backup=backup)
            error_ids = {eid for eid, _ in res.errors}
            for ent in pending:
                if str(ent["entity_id"]) in error_ids:
                    continue
                store.mark_entity_written(ent["id"])

            summary.written = [str(p) for p in res.written]
            summary.skipped = [str(p) for p in res.skipped]
            summary.backups = [str(p) for p in res.backups]
            summary.errors = list(res.errors)
    except Exception as exc:  # noqa: BLE001
        summary.error = str(exc)

    return summary


__all__ = ["WriteSummary", "write_pending"]
