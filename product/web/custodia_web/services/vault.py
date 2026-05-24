"""
Helper read-only sul vault Markdown e sullo state DB.

Tutta la logica usata dalle pagine Dashboard/Vault/Review per query veloci
(metriche, tree dei file .md, ultimi run, list pending entities).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from custodia_cli.commands.init import state_db_path_for_vault
from custodia_cli.state import StateStore


VAULT_SUBDIRS = ("clienti", "fornitori", "commesse", "inbox")


@dataclass
class VaultStats:
    """Snapshot delle metriche di un vault per la dashboard."""

    docs_total: int = 0
    docs_pending: int = 0
    entities_by_status: dict[str, int] = None  # type: ignore[assignment]
    entities_by_type: dict[str, int] = None  # type: ignore[assignment]
    md_by_subdir: dict[str, int] = None  # type: ignore[assignment]
    last_run: dict[str, Any] | None = None
    state_db_exists: bool = False

    def __post_init__(self) -> None:
        if self.entities_by_status is None:
            self.entities_by_status = {}
        if self.entities_by_type is None:
            self.entities_by_type = {}
        if self.md_by_subdir is None:
            self.md_by_subdir = {}


def count_md_files(vault: Path) -> dict[str, int]:
    """Conta file .md per ogni sottocartella canonica del vault."""
    vault = Path(vault).expanduser()
    counts = {sub: 0 for sub in VAULT_SUBDIRS}
    if not vault.exists():
        return counts
    for sub in VAULT_SUBDIRS:
        base = vault / sub
        if base.exists():
            counts[sub] = sum(1 for _ in base.rglob("*.md") if _.is_file())
    return counts


def list_vault_files(vault: Path, subdir: str | None = None) -> list[Path]:
    """Lista i file .md del vault (eventualmente sotto un subdir)."""
    vault = Path(vault).expanduser()
    base = vault / subdir if subdir else vault
    if not base.exists():
        return []
    return sorted(p for p in base.rglob("*.md") if p.is_file())


def parse_md(path: Path) -> tuple[dict[str, Any], str]:
    """Parsing minimale di frontmatter YAML + body markdown."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    fm_text = text[4:end]
    body = text[end + 5:]
    try:
        fm = yaml.safe_load(fm_text) or {}
    except yaml.YAMLError:
        fm = {}
    return fm, body


def search_vault(vault: Path, query: str, *, limit: int = 50) -> list[tuple[Path, str]]:
    """Full-text search naive sui file .md. Ritorna (path, snippet)."""
    if not query.strip():
        return []
    q = query.lower()
    out: list[tuple[Path, str]] = []
    for path in list_vault_files(vault):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        lower = text.lower()
        idx = lower.find(q)
        if idx == -1:
            continue
        start = max(0, idx - 60)
        end = min(len(text), idx + len(query) + 60)
        snippet = text[start:end].replace("\n", " ")
        out.append((path, snippet))
        if len(out) >= limit:
            break
    return out


def vault_stats(vault: Path) -> VaultStats:
    """Calcola metriche per la dashboard."""
    vault = Path(vault).expanduser().resolve()
    stats = VaultStats(md_by_subdir=count_md_files(vault))

    db_path = state_db_path_for_vault(vault)
    stats.state_db_exists = db_path.exists()
    if not stats.state_db_exists:
        return stats

    with StateStore(db_path) as store:
        docs = store.list_documents()
        stats.docs_total = len(docs)
        stats.docs_pending = sum(1 for d in docs if d["status"] == "pending")

        # entities by status / type (query diretta al DB, evita N+1)
        rows = store._conn.execute(
            "SELECT entity_type, status, COUNT(*) AS n FROM entities GROUP BY entity_type, status"
        ).fetchall()
        for r in rows:
            et = r["entity_type"]
            st = r["status"]
            stats.entities_by_type[et] = stats.entities_by_type.get(et, 0) + r["n"]
            stats.entities_by_status[st] = stats.entities_by_status.get(st, 0) + r["n"]

        last = store._conn.execute(
            "SELECT * FROM runs ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if last is not None:
            stats.last_run = dict(last)

    return stats


def list_recent_runs(vault: Path, *, limit: int = 10) -> list[dict[str, Any]]:
    """Ultimi N run registrati nello state DB."""
    db_path = state_db_path_for_vault(Path(vault).expanduser().resolve())
    if not db_path.exists():
        return []
    with StateStore(db_path) as store:
        rows = store._conn.execute(
            "SELECT id, command, status, summary, started_at, completed_at "
            "FROM runs ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


def list_pending_entities(vault: Path, entity_type: str | None = None) -> list[dict[str, Any]]:
    """Entity pending nello state DB del vault."""
    db_path = state_db_path_for_vault(Path(vault).expanduser().resolve())
    if not db_path.exists():
        return []
    with StateStore(db_path) as store:
        return store.list_pending_entities(entity_type)


def get_entity_by_pk(vault: Path, entity_pk: int) -> dict[str, Any] | None:
    """Carica una singola entity per primary key."""
    db_path = state_db_path_for_vault(Path(vault).expanduser().resolve())
    if not db_path.exists():
        return None
    with StateStore(db_path) as store:
        row = store._conn.execute(
            "SELECT * FROM entities WHERE id = ?", (entity_pk,)
        ).fetchone()
        if row is None:
            return None
        return store._entity_row_to_dict(row)


def record_decision(
    vault: Path,
    *,
    entity_pk: int,
    decision: str,
    edited_frontmatter: dict[str, Any] | None = None,
) -> None:
    """Wrap di `record_review_decision` con apertura/chiusura store."""
    db_path = state_db_path_for_vault(Path(vault).expanduser().resolve())
    with StateStore(db_path) as store:
        store.record_review_decision(
            entity_pk=entity_pk,
            decision=decision,
            edited_frontmatter=edited_frontmatter,
        )


def existing_md_for_entity(vault: Path, entity_type: str, entity_id: str) -> Path | None:
    """Path del .md esistente nel vault corrispondente a (entity_type, entity_id), se esiste."""
    from custodia_cli.review.yaml_io import ENTITY_TYPE_PLURAL

    subdir = ENTITY_TYPE_PLURAL.get(entity_type)
    if not subdir:
        return None
    candidate = Path(vault).expanduser() / subdir / f"{entity_id}.md"
    return candidate if candidate.exists() else None


__all__ = [
    "VaultStats",
    "VAULT_SUBDIRS",
    "count_md_files",
    "list_vault_files",
    "parse_md",
    "search_vault",
    "vault_stats",
    "list_recent_runs",
    "list_pending_entities",
    "get_entity_by_pk",
    "record_decision",
    "existing_md_for_entity",
]
