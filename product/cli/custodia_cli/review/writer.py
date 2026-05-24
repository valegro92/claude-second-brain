"""
Writer del vault: materializza le entity approved come file `.md`.

Idempotente:
- Se il file esiste e ha lo stesso contenuto del candidato → no-op (skipped).
- Se il file esiste con contenuto diverso → backup in `.custodia-backups/`
  (a meno che ``backup=False``), poi sovrascrive.
- Se non esiste → scrive.

Il formato output è esattamente quello consumato da
``product/mcp-server/custodia_mcp.py::parse_frontmatter``: ``---\\n<yaml>---\\n<body>``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from custodia_cli.review.yaml_io import (
    ENTITY_TYPE_PLURAL,
    dump_frontmatter,
    ordered_keys_for_type,
)


@dataclass
class WriteResult:
    """Riepilogo di un'invocazione di :func:`write_entities`."""

    written: list[Path] = field(default_factory=list)
    skipped: list[Path] = field(default_factory=list)
    backups: list[Path] = field(default_factory=list)
    errors: list[tuple[str, str]] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.written) + len(self.skipped)


def _now_compact() -> str:
    """Timestamp UTC compatto per nomi file backup."""
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def render_markdown(
    frontmatter: dict[str, Any],
    body_md: str,
    entity_type: str,
) -> str:
    """Serializza ``(frontmatter, body) → markdown completo con YAML front."""
    ordered = ordered_keys_for_type(entity_type)
    fm_text = dump_frontmatter(frontmatter, ordered)
    body = body_md.rstrip("\n")
    if body:
        body = body + "\n"
    return f"---\n{fm_text}---\n{body}"


def _target_path(
    vault_root: Path,
    entity_type: str,
    entity_id: str,
) -> Path:
    """Path di destinazione `<vault>/<plural>/<entity_id>.md`."""
    subdir = ENTITY_TYPE_PLURAL.get(entity_type, entity_type + "i")
    return vault_root / subdir / f"{entity_id}.md"


def _write_with_backup(
    target: Path,
    content: str,
    *,
    vault_root: Path,
    backup: bool,
) -> tuple[bool, Path | None]:
    """Scrive ``content`` in ``target`` con backup opzionale.

    Returns:
        Tuple ``(wrote, backup_path_or_None)``. ``wrote=False`` se il
        contenuto era identico a quello esistente.
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        existing = target.read_text(encoding="utf-8")
        if existing == content:
            return False, None
        backup_path: Path | None = None
        if backup:
            backups_dir = vault_root / ".custodia-backups"
            backups_dir.mkdir(parents=True, exist_ok=True)
            backup_path = backups_dir / f"{target.stem}_{_now_compact()}.md"
            backup_path.write_text(existing, encoding="utf-8")
        target.write_text(content, encoding="utf-8")
        return True, backup_path
    target.write_text(content, encoding="utf-8")
    return True, None


def write_entities(
    entities: list[dict[str, Any]],
    vault_root: Path,
    *,
    backup: bool = True,
) -> WriteResult:
    """Materializza una lista di entity nel vault Obsidian.

    Args:
        entities: lista di dict (output di ``StateStore.list_pending_writes``).
            Ogni dict deve avere ``entity_type``, ``entity_id``, ``frontmatter``,
            ``body_md``.
        vault_root: directory radice del vault.
        backup: se True, salva backup dei file esistenti prima di sovrascrivere.

    Returns:
        :class:`WriteResult` con riepilogo dei file scritti, saltati, backup.
    """
    vault_root = vault_root.expanduser().resolve()
    vault_root.mkdir(parents=True, exist_ok=True)
    result = WriteResult()

    for ent in entities:
        try:
            target = _target_path(
                vault_root, ent["entity_type"], ent["entity_id"]
            )
            content = render_markdown(
                ent.get("frontmatter") or {},
                ent.get("body_md") or "",
                ent["entity_type"],
            )
            wrote, backup_path = _write_with_backup(
                target, content, vault_root=vault_root, backup=backup
            )
            if wrote:
                result.written.append(target)
            else:
                result.skipped.append(target)
            if backup_path is not None:
                result.backups.append(backup_path)
        except OSError as exc:
            result.errors.append((str(ent.get("entity_id", "?")), str(exc)))
    return result


__all__ = ["write_entities", "WriteResult", "render_markdown"]
