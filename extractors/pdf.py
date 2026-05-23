"""Extractor per PDF testuali. Primario: pdfplumber. Fallback: pypdf."""
from __future__ import annotations

import logging
from pathlib import Path

from ._base import ExtractionResult, Extractor

logger = logging.getLogger(__name__)

# Soglia minima di char/pagine per considerare l'estrazione "testuale": sotto si marca OCR.
_MIN_CHARS_FOR_TEXT = 100
_MIN_PAGES_FOR_OCR_FLAG = 5


class PdfExtractor(Extractor):
    """PDF testuali: una sezione H2 per pagina, tabelle in markdown.

    Quality = char_estratti / (50 * pagine), clampato. Se quality < 0.5 e ci sono
    molte pagine ma testo scarso, viene marcato per OCR fallback (metadata['needs_ocr']).
    """

    name = "pdf"
    mimes = ["application/pdf"]
    extensions = [".pdf"]

    def extract(self, file_path: Path) -> ExtractionResult:
        warnings: list[str] = []
        try:
            import pdfplumber
        except ImportError:  # pragma: no cover - dipendenza dichiarata
            warnings.append("pdfplumber non installato, uso pypdf come fallback")
            return _extract_pypdf(file_path, warnings)

        sections: list[str] = []
        total_chars = 0
        n_pages = 0
        try:
            with pdfplumber.open(str(file_path)) as pdf:
                n_pages = len(pdf.pages)
                for idx, page in enumerate(pdf.pages, start=1):
                    page_md = _render_page(page, idx, warnings)
                    sections.append(page_md)
                    total_chars += len(page_md)
        except Exception as exc:
            warnings.append(f"pdfplumber ha sollevato eccezione: {exc}; fallback a pypdf")
            return _extract_pypdf(file_path, warnings)

        markdown = "\n\n".join(sections).strip()
        quality = _quality(total_chars, n_pages)
        metadata = {"pages": n_pages, "chars": total_chars, "engine": "pdfplumber"}

        if quality < 0.5 and n_pages > _MIN_PAGES_FOR_OCR_FLAG and total_chars < _MIN_CHARS_FOR_TEXT:
            metadata["needs_ocr"] = True
            warnings.append(
                f"Testo estratto scarso ({total_chars} char su {n_pages} pagine): "
                "probabilmente PDF scansionato, candidato per pdf_ocr"
            )

        return ExtractionResult(
            markdown=markdown or "_(nessun testo estratto)_",
            metadata=metadata,
            warnings=warnings,
            quality=quality,
        )


def _render_page(page, idx: int, warnings: list[str]) -> str:
    """Rende una pagina come ``## Pagina N`` + testo + tabelle markdown."""
    parts: list[str] = [f"## Pagina {idx}"]
    try:
        text = page.extract_text() or ""
    except Exception as exc:
        warnings.append(f"Pagina {idx}: extract_text fallito ({exc})")
        text = ""
    if text.strip():
        parts.append(text.strip())

    try:
        tables = page.extract_tables() or []
    except Exception as exc:
        warnings.append(f"Pagina {idx}: extract_tables fallito ({exc})")
        tables = []
    for t_idx, table in enumerate(tables, start=1):
        md_table = _table_to_markdown(table)
        if md_table:
            parts.append(f"### Tabella {idx}.{t_idx}\n\n{md_table}")
    return "\n\n".join(parts)


def _table_to_markdown(table: list[list]) -> str:
    """Tabella `list[list[str|None]]` → markdown GFM."""
    rows = [[("" if cell is None else str(cell)).replace("|", "\\|").replace("\n", " ").strip()
             for cell in row] for row in table if row]
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


def _quality(chars: int, pages: int) -> float:
    """Heuristic: ~50 char/pagina è già piuttosto scarso, 500+ è ricco."""
    if pages <= 0:
        return 0.0
    ratio = chars / (50 * pages)
    return max(0.0, min(1.0, ratio))


def _extract_pypdf(file_path: Path, warnings: list[str]) -> ExtractionResult:
    """Fallback minimale con pypdf."""
    try:
        from pypdf import PdfReader
    except ImportError:  # pragma: no cover
        warnings.append("Né pdfplumber né pypdf disponibili: estrazione vuota")
        return ExtractionResult(markdown="", metadata={"engine": "none"},
                                warnings=warnings, quality=0.0)
    try:
        reader = PdfReader(str(file_path))
    except Exception as exc:
        warnings.append(f"pypdf non riesce ad aprire il file: {exc}")
        return ExtractionResult(markdown="", metadata={"engine": "pypdf"},
                                warnings=warnings, quality=0.0)

    sections = []
    total_chars = 0
    for idx, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception as exc:
            warnings.append(f"pypdf pagina {idx}: {exc}")
            text = ""
        sections.append(f"## Pagina {idx}\n\n{text.strip()}")
        total_chars += len(text)
    n_pages = len(reader.pages)
    quality = _quality(total_chars, n_pages)
    metadata = {"pages": n_pages, "chars": total_chars, "engine": "pypdf"}
    if quality < 0.5 and n_pages > _MIN_PAGES_FOR_OCR_FLAG and total_chars < _MIN_CHARS_FOR_TEXT:
        metadata["needs_ocr"] = True
        warnings.append("Testo scarso anche con pypdf: candidato OCR")
    return ExtractionResult(
        markdown="\n\n".join(sections).strip() or "_(nessun testo estratto)_",
        metadata=metadata,
        warnings=warnings,
        quality=quality,
    )
