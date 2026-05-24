"""Flush delle bozze approvate dal batch al vault + log delle decisioni.

Comportamento:
- Bozze APPROVED: spostate (o copiate) nella loro `target_path` derivata dal
  frontmatter. Se il target esiste si applica la `conflict_policy` scelta
  (skip / overwrite / rename / merge).
- Bozze EDITED: trattate come APPROVED ma con `edits` salvati nello stato.
- Bozze REJECTED: spostate in `_status/audit/rejected/<batch_id>/`.
- Ogni decisione appesa a `_status/audit/decisions.jsonl` (append-only).

L'append al log e' best-effort: una scrittura singola e' atomica su filesystem
POSIX per dimensioni ridotte come le nostre righe.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from categorizers._enums import StatoBozza

from . import drafts as drafts_mod
from . import state as state_mod

ConflictPolicy = Literal["skip", "overwrite", "rename", "merge"]


@dataclass
class FlushResult:
    """Esito sintetico della flush di un batch."""

    applied: list[dict[str, Any]]  # bozze approved spostate nel vault
    rejected: list[dict[str, Any]]  # bozze rejected archiviate
    skipped: list[dict[str, Any]]  # conflitti o errori
    decisions_log: Path

    def as_dict(self) -> dict[str, Any]:
        return {
            "applied": self.applied,
            "rejected": self.rejected,
            "skipped": self.skipped,
            "decisions_log": str(self.decisions_log),
            "n_applied": len(self.applied),
            "n_rejected": len(self.rejected),
            "n_skipped": len(self.skipped),
        }


def flush_batch(
    batch_dir: Path,
    status_dir: Path,
    vault_root: Path,
    *,
    user: str = "valentino",
    conflict_policy: ConflictPolicy = "skip",
) -> FlushResult:
    """Applica al vault tutte le bozze APPROVED/EDITED del batch e archivia le REJECTED.

    Parametri:
      batch_dir: cartella della singola batch (`_status/drafts/<batch_id>/`).
      status_dir: root di `_status/` (per audit + rejected).
      vault_root: root del vault (`vault/`).
      user: chi fa la flush (loggato).
      conflict_policy: cosa fare se il target esiste gia'.
    """
    batch_id = batch_dir.name
    state = state_mod.load_state(batch_dir)
    decisions_log = status_dir / "audit" / "decisions.jsonl"
    decisions_log.parent.mkdir(parents=True, exist_ok=True)
    rejected_dir = status_dir / "audit" / "rejected" / batch_id
    applied: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for draft in drafts_mod.list_drafts(batch_dir):
        entry = state.get(draft.name, {})
        stato = entry.get("stato", StatoBozza.PENDING.value)

        if stato in (StatoBozza.APPROVED.value, StatoBozza.EDITED.value):
            outcome = _apply_to_vault(
                draft=draft,
                edits=entry.get("edits"),
                vault_root=vault_root,
                conflict_policy=conflict_policy,
            )
            outcome_kind = outcome["outcome"]
            payload = {
                "ts": _now_iso(),
                "batch": batch_id,
                "draft": draft.name,
                "action": stato,
                "user": user,
                "edits": 1 if entry.get("edits") else 0,
                "applied_to": outcome.get("applied_to"),
                "outcome": outcome_kind,
                "conflict_policy": conflict_policy,
            }
            _append_decision(decisions_log, payload)
            if outcome_kind in ("skipped-no-target", "skipped-conflict", "error"):
                skipped.append(payload)
            else:
                applied.append(payload)

        elif stato == StatoBozza.REJECTED.value:
            archive_path = _archive_rejected(draft.path, rejected_dir)
            payload = {
                "ts": _now_iso(),
                "batch": batch_id,
                "draft": draft.name,
                "action": stato,
                "user": user,
                "archived_to": str(archive_path),
            }
            _append_decision(decisions_log, payload)
            rejected.append(payload)
        # PENDING e PARKED: skip senza log (resteranno per la prossima flush)

    return FlushResult(
        applied=applied, rejected=rejected, skipped=skipped, decisions_log=decisions_log
    )


def _apply_to_vault(
    *,
    draft: drafts_mod.DraftInfo,
    edits: str | None,
    vault_root: Path,
    conflict_policy: ConflictPolicy,
) -> dict[str, Any]:
    """Sposta la bozza nel vault. Ritorna dict con outcome + applied_to."""
    target_rel = draft.target_path
    if not target_rel:
        return {"outcome": "skipped-no-target", "applied_to": None}

    # `target_rel` puo' essere "vault/clienti/x/x.md" oppure "clienti/x/x.md"
    target = _resolve_target(vault_root, target_rel)
    target.parent.mkdir(parents=True, exist_ok=True)

    content = edits if edits is not None else draft.raw

    if target.exists():
        if conflict_policy == "skip":
            return {"outcome": "skipped-conflict", "applied_to": str(target)}
        if conflict_policy == "rename":
            target = _unique_path(target)
        elif conflict_policy == "merge":
            existing = target.read_text(encoding="utf-8")
            content = existing.rstrip() + "\n\n<!-- merge da batch UI -->\n\n" + content
        # overwrite: niente da fare, scriviamo sopra

    try:
        target.write_text(content, encoding="utf-8")
        # Rimuovi la bozza dal batch_dir (archiviazione implicita: la copia e' nel vault)
        try:
            draft.path.unlink()
        except OSError:
            pass
        return {"outcome": "applied", "applied_to": str(target)}
    except OSError as exc:
        return {"outcome": "error", "applied_to": str(target), "error": str(exc)}


def _resolve_target(vault_root: Path, target_rel: str) -> Path:
    """Risolve un target relativo accettando sia `vault/x/y.md` che `x/y.md`."""
    p = Path(target_rel)
    parts = p.parts
    if parts and parts[0] == "vault":
        return vault_root.joinpath(*parts[1:])
    return vault_root / p


def _unique_path(path: Path) -> Path:
    """Restituisce un path libero aggiungendo `-1`, `-2`, ... al nome."""
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    i = 1
    while True:
        candidate = parent / f"{stem}-{i}{suffix}"
        if not candidate.exists():
            return candidate
        i += 1


def _archive_rejected(src: Path, rejected_dir: Path) -> Path:
    """Sposta una bozza rejected nella cartella di audit."""
    rejected_dir.mkdir(parents=True, exist_ok=True)
    dest = rejected_dir / src.name
    if dest.exists():
        dest = _unique_path(dest)
    shutil.move(str(src), str(dest))
    return dest


def _append_decision(log_path: Path, payload: dict[str, Any]) -> None:
    """Append-only JSONL delle decisioni (audit)."""
    line = json.dumps(payload, ensure_ascii=False)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()
