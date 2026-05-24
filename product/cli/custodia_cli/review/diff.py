"""
Diff visuale fra una entity candidata e il file `.md` esistente nel vault.

Restituisce ``rich`` renderable: i campi nuovi sono verdi, i modificati gialli,
i campi persi (presenti nel vault ma non nel candidato) rossi.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.text import Text


def _parse_existing_vault_file(path: Path) -> tuple[dict[str, Any], str]:
    """Legge un file `.md` del vault e ritorna ``(frontmatter, body)``.

    Frontmatter mancante ⇒ dict vuoto. Errori di parse YAML degradano in dict
    vuoto (consistente con la logica di `parse_frontmatter` dell'MCP server).
    """
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    fm_text = text[4:end]
    body = text[end + 5 :]
    try:
        fm = yaml.safe_load(fm_text) or {}
    except yaml.YAMLError:
        fm = {}
    return fm, body


def _format_value(value: Any) -> str:
    """Rappresentazione one-line compatta di un valore per il diff."""
    if isinstance(value, (dict, list)):
        try:
            text = yaml.safe_dump(
                value, allow_unicode=True, default_flow_style=True, width=200
            ).strip()
        except Exception:
            text = repr(value)
        if len(text) > 80:
            text = text[:77] + "..."
        return text
    if value is None:
        return "∅"
    text = str(value)
    if "\n" in text:
        first = text.splitlines()[0]
        return f"{first} ⏎ ({len(text.splitlines())} righe)"
    return text


def diff_frontmatter(
    candidate: dict[str, Any],
    existing: dict[str, Any],
) -> list[tuple[str, str, str]]:
    """Confronta due frontmatter; ritorna lista di tuple ``(status, key, repr)``.

    Status:
        - ``"new"``     : campo nuovo nel candidato (non presente in vault)
        - ``"changed"`` : campo modificato (valore diverso)
        - ``"same"``    : campo invariato
        - ``"lost"``    : campo presente nel vault ma non nel candidato
    """
    out: list[tuple[str, str, str]] = []
    all_keys = list(candidate.keys()) + [
        k for k in existing.keys() if k not in candidate
    ]
    for key in all_keys:
        if key in candidate and key not in existing:
            out.append(("new", key, _format_value(candidate[key])))
        elif key in candidate and key in existing:
            if candidate[key] == existing[key]:
                out.append(("same", key, _format_value(candidate[key])))
            else:
                vault_repr = _format_value(existing[key])
                cand_repr = _format_value(candidate[key])
                out.append(("changed", key, f"{vault_repr} → {cand_repr}"))
        else:
            out.append(("lost", key, _format_value(existing[key])))
    return out


_STATUS_STYLE: dict[str, str] = {
    "new": "green",
    "changed": "yellow",
    "same": "dim",
    "lost": "red",
}

_STATUS_GLYPH: dict[str, str] = {
    "new": "+",
    "changed": "~",
    "same": "·",
    "lost": "-",
}


def render_diff(
    candidate: dict[str, Any],
    existing_path: Path | None,
) -> RenderableType:
    """Renderable Rich per il pannello destro del REPL review.

    Se ``existing_path`` è None o non esistente, mostra "[Nuova entità]".
    Altrimenti calcola il diff campo-per-campo e lo rende colored.
    """
    if existing_path is None or not existing_path.exists():
        return Panel(
            Text("[Nuova entità — nessun file nel vault]", style="bold green"),
            title="vault",
            border_style="green",
        )

    existing_fm, _ = _parse_existing_vault_file(existing_path)
    rows = diff_frontmatter(candidate, existing_fm)

    if not rows or all(s == "same" for s, _, _ in rows):
        return Panel(
            Text("Nessun cambiamento rispetto al vault.", style="dim"),
            title=f"vault: {existing_path.name}",
            border_style="dim",
        )

    lines: list[Text] = []
    for status, key, repr_value in rows:
        style = _STATUS_STYLE.get(status, "white")
        glyph = _STATUS_GLYPH.get(status, " ")
        line = Text()
        line.append(f"{glyph} ", style=style)
        line.append(f"{key}: ", style=f"bold {style}")
        line.append(repr_value, style=style)
        lines.append(line)

    return Panel(
        Group(*lines),
        title=f"vault: {existing_path.name}",
        border_style="blue",
    )


def existing_vault_path(
    vault_root: Path,
    entity_type: str,
    entity_id: str,
) -> Path:
    """Path atteso del file `.md` per l'entity nel vault (anche se non esiste)."""
    from custodia_cli.review.yaml_io import ENTITY_TYPE_PLURAL

    subdir = ENTITY_TYPE_PLURAL.get(entity_type, entity_type + "i")
    return vault_root / subdir / f"{entity_id}.md"


__all__ = [
    "diff_frontmatter",
    "render_diff",
    "existing_vault_path",
]
