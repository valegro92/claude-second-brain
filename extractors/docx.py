"""Extractor DOCX. Primario: pandoc (gfm). Fallback: python-docx."""
from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

from ._base import ExtractionResult, Extractor

logger = logging.getLogger(__name__)


class DocxExtractor(Extractor):
    """DOCX → markdown.

    Strategia:
      1. ``pandoc -f docx -t gfm`` se il binario è nel PATH (qualità migliore, mantiene tabelle e link)
      2. Altrimenti fallback con ``python-docx`` (paragrafi + tabelle in GFM, niente immagini)
    """

    name = "docx"
    mimes = [
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ]
    extensions = [".docx"]

    def extract(self, file_path: Path) -> ExtractionResult:
        warnings: list[str] = []

        if _has_pandoc():
            try:
                md = _pandoc_convert(file_path)
                return ExtractionResult(
                    markdown=md.strip() or "_(documento vuoto)_",
                    metadata={"engine": "pandoc", "chars": len(md)},
                    warnings=warnings,
                    quality=1.0 if md.strip() else 0.1,
                )
            except subprocess.CalledProcessError as exc:
                warnings.append(
                    f"pandoc ha fallito (rc={exc.returncode}): {exc.stderr or ''}; "
                    "fallback a python-docx"
                )
            except Exception as exc:
                warnings.append(f"pandoc errore inatteso ({exc}); fallback a python-docx")
        else:
            warnings.append("pandoc non installato, uso python-docx (qualità minore)")

        return _python_docx_fallback(file_path, warnings)


def _has_pandoc() -> bool:
    return shutil.which("pandoc") is not None


def _pandoc_convert(file_path: Path) -> str:
    """Esegue pandoc e ritorna lo stdout markdown. Timeout 60s."""
    result = subprocess.run(
        ["pandoc", "-f", "docx", "-t", "gfm", str(file_path)],
        capture_output=True,
        text=True,
        timeout=60,
        check=True,
    )
    return result.stdout


def _python_docx_fallback(file_path: Path, warnings: list[str]) -> ExtractionResult:
    """Estrae paragrafi e tabelle nell'ordine logico del documento via XML body."""
    try:
        from docx import Document  # type: ignore[import-not-found]
        from docx.oxml.ns import qn  # type: ignore[import-not-found]
        from docx.table import Table  # type: ignore[import-not-found]
        from docx.text.paragraph import Paragraph  # type: ignore[import-not-found]
    except ImportError:
        warnings.append("python-docx non installato: estrazione vuota")
        return ExtractionResult(markdown="", metadata={"engine": "none"},
                                warnings=warnings, quality=0.0)

    try:
        doc = Document(str(file_path))
    except Exception as exc:
        warnings.append(f"python-docx non riesce ad aprire il file: {exc}")
        return ExtractionResult(markdown="", metadata={"engine": "python-docx"},
                                warnings=warnings, quality=0.0)

    parts: list[str] = []
    body = doc.element.body
    for child in body.iterchildren():
        tag = child.tag
        if tag == qn("w:p"):
            para = Paragraph(child, doc)
            md = _paragraph_to_md(para)
            if md:
                parts.append(md)
        elif tag == qn("w:tbl"):
            table = Table(child, doc)
            md = _table_to_md(table)
            if md:
                parts.append(md)

    markdown = "\n\n".join(parts).strip()
    return ExtractionResult(
        markdown=markdown or "_(documento vuoto)_",
        metadata={"engine": "python-docx", "chars": len(markdown)},
        warnings=warnings,
        quality=0.8 if markdown else 0.1,
    )


def _paragraph_to_md(paragraph) -> str:
    """Convertito approssimato: gestisce H1/H2/H3/H4 in base allo style."""
    text = paragraph.text.strip()
    if not text:
        return ""
    style_name = (paragraph.style.name or "").lower() if paragraph.style else ""
    if style_name.startswith("heading 1") or style_name == "title":
        return f"# {text}"
    if style_name.startswith("heading 2"):
        return f"## {text}"
    if style_name.startswith("heading 3"):
        return f"### {text}"
    if style_name.startswith("heading 4"):
        return f"#### {text}"
    if style_name.startswith("list") or style_name.startswith("bullet"):
        return f"- {text}"
    return text


def _table_to_md(table) -> str:
    """Tabella python-docx → markdown GFM."""
    rows = []
    for row in table.rows:
        cells = [
            cell.text.replace("|", "\\|").replace("\n", " ").strip() for cell in row.cells
        ]
        rows.append(cells)
    if not rows:
        return ""
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    header = rows[0]
    sep = ["---"] * width
    lines = ["| " + " | ".join(header) + " |", "| " + " | ".join(sep) + " |"]
    for row in rows[1:]:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)
