"""Extractor passthrough per file di testo (.txt, .md) e tabelle CSV (.csv)."""

from __future__ import annotations

import csv
import logging
from io import StringIO
from pathlib import Path

from ._base import ExtractionResult, Extractor

logger = logging.getLogger(__name__)

# Soglia oltre la quale tronchiamo l'input testuale per evitare bozze enormi.
_MAX_CHARS = 200_000


class PlainExtractor(Extractor):
    """Passthrough per testo semplice e CSV.

    - .txt / .md: contenuto restituito tale quale (decodifica utf-8 con fallback latin-1).
    - .csv: prima riga = header, righe successive = tabella markdown.
    """

    name = "plain"
    mimes = ["text/plain", "text/csv", "text/markdown"]
    extensions = [".txt", ".csv", ".md", ".markdown"]

    def extract(self, file_path: Path) -> ExtractionResult:
        ext = file_path.suffix.lower()
        warnings: list[str] = []
        try:
            raw = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            warnings.append("Decodifica utf-8 fallita, fallback a latin-1")
            raw = file_path.read_text(encoding="latin-1", errors="replace")

        if ext == ".csv":
            markdown, csv_warnings = _csv_to_markdown(raw)
            warnings.extend(csv_warnings)
            quality = 0.9 if markdown.strip() else 0.2
            return ExtractionResult(
                markdown=markdown,
                metadata={"format": "csv", "chars": len(raw)},
                warnings=warnings,
                quality=quality,
            )

        # txt / md / markdown
        if len(raw) > _MAX_CHARS:
            warnings.append(f"File testuale grande ({len(raw)} char), troncato a {_MAX_CHARS}")
            raw = raw[:_MAX_CHARS]

        quality = 1.0 if raw.strip() else 0.1
        return ExtractionResult(
            markdown=raw,
            metadata={
                "format": "markdown" if ext in {".md", ".markdown"} else "text",
                "chars": len(raw),
            },
            warnings=warnings,
            quality=quality,
        )


def _csv_to_markdown(raw: str) -> tuple[str, list[str]]:
    """Converte una stringa CSV in una tabella markdown GFM."""
    warnings: list[str] = []
    try:
        # Sniff del dialect (separatore , o ;).
        sample = raw[:4096]
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        except csv.Error:
            dialect = csv.excel
        reader = csv.reader(StringIO(raw), dialect=dialect)
        rows = list(reader)
    except Exception as exc:  # pragma: no cover - difensivo
        warnings.append(f"Parsing CSV fallito: {exc}")
        return raw, warnings

    if not rows:
        return "", ["CSV vuoto"]

    header = [_md_cell(c) for c in rows[0]]
    sep = ["---"] * len(header)
    lines = ["| " + " | ".join(header) + " |", "| " + " | ".join(sep) + " |"]
    for row in rows[1:]:
        cells = [_md_cell(c) for c in row]
        # Normalizza la lunghezza riga sulla testata.
        if len(cells) < len(header):
            cells += [""] * (len(header) - len(cells))
        elif len(cells) > len(header):
            cells = cells[: len(header)]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines), warnings


def _md_cell(value: str) -> str:
    """Escape minimale per celle di tabella markdown."""
    if value is None:
        return ""
    return str(value).replace("|", "\\|").replace("\n", " ").strip()
