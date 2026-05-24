"""Lettura bozze markdown e generazione HTML del diff viewer.

Una bozza e' un file `.md` in `_status/drafts/<batch_id>/`. Il frontmatter YAML
opzionale fornisce metadati per la flush nel vault (tipo, slug, target_path).

Il diff viewer e' HTML statico (no JS) con classi CSS che evidenziano:
- `.draft-content` base
- `.todo-marker` per linee con TODO
- `.warning-marker` per linee di warning
- `.generated` per contenuto sotto frontmatter `generato-da:`
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)


@dataclass
class DraftInfo:
    """Riassunto di una bozza: nome, path, frontmatter, confidence, target."""

    name: str
    path: Path
    frontmatter: dict[str, Any] = field(default_factory=dict)
    body: str = ""
    raw: str = ""

    @property
    def confidence(self) -> float | None:
        """Confidence dichiarata nel frontmatter (se presente)."""
        c = self.frontmatter.get("confidence") or self.frontmatter.get("conf")
        if c is None:
            return None
        try:
            return float(c)
        except (TypeError, ValueError):
            return None

    @property
    def tipo(self) -> str | None:
        return self.frontmatter.get("tipo")

    @property
    def slug(self) -> str | None:
        return self.frontmatter.get("slug")

    @property
    def target_path(self) -> str | None:
        """Target esplicito (frontmatter `target`) oppure derivato da tipo+slug."""
        explicit = self.frontmatter.get("target") or self.frontmatter.get("target_path")
        if explicit:
            return str(explicit)
        return derive_target_path(self.tipo, self.slug)


def derive_target_path(tipo: str | None, slug: str | None) -> str | None:
    """Deriva il path nel vault da `tipo` e `slug` del frontmatter.

    Convenzioni minime (estendibili a piacere):
      scheda-cliente   -> vault/clienti/<slug>/<slug>.md
      scheda-fornitore -> vault/fornitori/<slug>/<slug>.md
      scheda-commessa  -> vault/commesse/<slug>/<slug>.md
      persona          -> vault/references/persone.md (append)
      decisione        -> vault/decisioni/<slug>.md
    """
    if not tipo or not slug:
        return None
    t = tipo.lower().strip()
    s = slug.strip()
    mapping = {
        "scheda-cliente": f"vault/clienti/{s}/{s}.md",
        "scheda-fornitore": f"vault/fornitori/{s}/{s}.md",
        "scheda-commessa": f"vault/commesse/{s}/{s}.md",
        "decisione": f"vault/decisioni/{s}.md",
        "persona": "vault/references/persone.md",
    }
    return mapping.get(t)


def parse_frontmatter(raw: str) -> tuple[dict[str, Any], str]:
    """Estrae frontmatter YAML (--- ... ---) restituendo (dict, body).

    Parser minimale (no PyYAML necessario per le chiavi semplici tipo/slug/confidence/warnings).
    Supporta `key: value` su una sola riga e liste con `- item`.
    """
    m = _FRONTMATTER_RE.match(raw)
    if not m:
        return {}, raw
    block = m.group(1)
    body = raw[m.end() :]
    data: dict[str, Any] = {}
    current_key: str | None = None
    for line in block.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("- ") and current_key:
            # Item di lista appartenente alla chiave precedente
            data.setdefault(current_key, []).append(stripped[2:].strip())
            continue
        if ":" in stripped:
            key, _, val = stripped.partition(":")
            key = key.strip()
            val = val.strip()
            if not val:
                # Lista o blocco vuoto: prepara per items
                data[key] = []
                current_key = key
            else:
                data[key] = _coerce_scalar(val)
                current_key = key
    return data, body


def _coerce_scalar(v: str) -> Any:
    """Conversione minimale (numeri, bool, stringhe)."""
    v = v.strip().strip('"').strip("'")
    if v.lower() in ("true", "yes"):
        return True
    if v.lower() in ("false", "no"):
        return False
    try:
        if "." in v:
            return float(v)
        return int(v)
    except ValueError:
        return v


def list_batches(drafts_root: Path) -> list[str]:
    """Elenca i batch (sottocartelle di `_status/drafts/`) in ordine alfabetico."""
    if not drafts_root.exists():
        return []
    return sorted(
        p.name for p in drafts_root.iterdir() if p.is_dir() and not p.name.startswith("_")
    )


def list_drafts(batch_dir: Path) -> list[DraftInfo]:
    """Carica tutte le bozze `.md` di un batch (ordinate per nome)."""
    if not batch_dir.exists():
        return []
    out: list[DraftInfo] = []
    for path in sorted(batch_dir.glob("*.md")):
        out.append(load_draft(path))
    return out


def load_draft(path: Path) -> DraftInfo:
    """Legge una singola bozza e ne estrae frontmatter + body."""
    raw = path.read_text(encoding="utf-8")
    fm, body = parse_frontmatter(raw)
    return DraftInfo(name=path.name, path=path, frontmatter=fm, body=body, raw=raw)


def render_diff_viewer(draft: DraftInfo) -> str:
    """Genera HTML del diff viewer per una bozza.

    Non e' un vero "diff" Git: e' una vista del contenuto con highlighting
    semantico (TODO/warning/generato) per facilitare la review umana.

    Quando la bozza ha una sezione `## Generato` o frontmatter `generato-da:`,
    il contenuto dopo quel marker e' incapsulato in `.generated`.
    """
    lines = draft.raw.splitlines()
    out_lines: list[str] = ['<div class="draft-content">']
    in_generated_section = bool(draft.frontmatter.get("generato-da"))
    in_warnings_block = False
    in_frontmatter = False
    fm_seen = 0

    for raw_line in lines:
        line = raw_line.rstrip("\n")
        escaped = html.escape(line)
        classes: list[str] = []

        # Tracking frontmatter (--- ... ---)
        if line.strip() == "---":
            fm_seen += 1
            in_frontmatter = fm_seen == 1
            out_lines.append(f'<pre class="fm-marker">{escaped}</pre>')
            if fm_seen >= 2:
                in_frontmatter = False
            continue

        # Dentro al frontmatter: rileva blocchi warnings:
        if in_frontmatter:
            stripped = line.strip()
            if stripped.startswith("warnings:"):
                in_warnings_block = True
                out_lines.append(f'<pre class="warning-marker">{escaped}</pre>')
                continue
            if in_warnings_block:
                if stripped.startswith("- "):
                    out_lines.append(f'<pre class="warning-marker">{escaped}</pre>')
                    continue
                in_warnings_block = False
            out_lines.append(f'<pre class="fm-line">{escaped}</pre>')
            continue

        # Body
        upper = line.upper()
        if "TODO" in upper:
            classes.append("todo-marker")
        if "WARNING" in upper or line.strip().lower().startswith("> warning"):
            classes.append("warning-marker")
        # Heading "## Generato" attiva la sezione
        if line.strip().lower().startswith("## generato"):
            in_generated_section = True
            classes.append("generated")
            classes.append("section-header")
        elif in_generated_section and line.strip().startswith("## "):
            # Nuovo H2 chiude la sezione generato (a meno che sia "Generato" stesso)
            in_generated_section = False
        elif in_generated_section:
            classes.append("generated")

        css = (" ".join(classes)).strip()
        if css:
            out_lines.append(f'<pre class="{css}">{escaped}</pre>')
        else:
            out_lines.append(f"<pre>{escaped}</pre>")

    out_lines.append("</div>")
    return "\n".join(out_lines)
