"""
Helper per aprire ``$EDITOR`` su un frontmatter YAML temporaneo.

Flusso:
1. Serializza il frontmatter con :func:`dump_frontmatter`.
2. Scrive su un file temp `<state_dir>/edit_<entity_pk>.yaml`.
3. Lancia ``$EDITOR`` (default: ``vi``) bloccando fino al return.
4. Rilegge, parse YAML, ritorna il dict editato.

Errori di parse vengono restituiti come ``EditorError`` e il chiamante può
decidere se ri-editare.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

import yaml

from custodia_cli.review.yaml_io import dump_frontmatter, ordered_keys_for_type


class EditorError(RuntimeError):
    """Sollevata quando l'editor ritorna contenuto non valido (YAML invalido)."""


def open_in_editor(
    frontmatter: dict[str, Any],
    *,
    entity_type: str,
    state_dir: Path,
    entity_pk: int,
    editor: str | None = None,
) -> dict[str, Any]:
    """Apre ``$EDITOR`` su una rappresentazione YAML del frontmatter.

    Args:
        frontmatter: dict da editare.
        entity_type: usato per ordinare le chiavi nel template.
        state_dir: directory dove scrivere il file temp.
        entity_pk: identificativo numerico per il nome file temp.
        editor: override esplicito; default = $EDITOR o "vi".

    Returns:
        Dict editato dall'utente.

    Raises:
        EditorError: se l'output non è YAML valido o non è un mapping.
    """
    state_dir.mkdir(parents=True, exist_ok=True)
    temp_path = state_dir / f"edit_{entity_pk}.yaml"
    keys = ordered_keys_for_type(entity_type)
    temp_path.write_text(dump_frontmatter(frontmatter, keys), encoding="utf-8")

    editor_cmd = editor or os.environ.get("EDITOR") or "vi"
    try:
        subprocess.run([editor_cmd, str(temp_path)], check=True)
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        raise EditorError(f"editor {editor_cmd!r} fallito: {exc}") from exc

    raw = temp_path.read_text(encoding="utf-8")
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        raise EditorError(f"YAML invalido: {exc}") from exc
    if data is None:
        # File vuoto: trattalo come "nessun cambio".
        return dict(frontmatter)
    if not isinstance(data, dict):
        raise EditorError(
            f"frontmatter atteso come mapping, ricevuto {type(data).__name__}"
        )
    return data


__all__ = ["open_in_editor", "EditorError"]
