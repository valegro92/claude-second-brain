"""Registry mime/estensione → extractor.

Uso tipico::

    from extractors._registry import get_extractor
    ext = get_extractor(record.mime, Path(record.path).suffix)
    if ext is None:
        logger.info("nessun extractor per %s (%s)", record.path, record.mime)
        return
    result = ext.extract(file_path)
"""

from __future__ import annotations

import logging
from pathlib import Path

from ._base import Extractor
from .docx import DocxExtractor
from .eml import EmlExtractor
from .pdf import PdfExtractor
from .pdf_ocr import PdfOcrExtractor
from .plain import PlainExtractor
from .xlsx import XlsxExtractor

logger = logging.getLogger(__name__)

# Ordine: il primario per ciascun mime va per primo. ``pdf_ocr`` è esplicitamente
# escluso dal lookup automatico: viene selezionato in modo deliberato (post-dispatch
# quando ``meta['needs_ocr']`` è True) o dal CLI con flag specifico.
_PRIMARY_EXTRACTORS: list[Extractor] = [
    PdfExtractor(),
    DocxExtractor(),
    XlsxExtractor(),
    EmlExtractor(),
    PlainExtractor(),
]

# Mappe costruite una volta.
_BY_MIME: dict[str, Extractor] = {}
_BY_EXT: dict[str, Extractor] = {}
for _ext in _PRIMARY_EXTRACTORS:
    for _m in _ext.mimes:
        _BY_MIME.setdefault(_m, _ext)
    for _e in _ext.extensions:
        _BY_EXT.setdefault(_e.lower(), _ext)

# OCR esposto via lookup esplicito.
_OCR = PdfOcrExtractor()


def get_extractor(mime: str | None, extension: str) -> Extractor | None:
    """Ritorna l'extractor primario per il mime; fallback su estensione.

    Restituisce ``None`` se nessuno gestisce il tipo (caller può loggare skip).
    """
    if mime:
        ext = _BY_MIME.get(mime.lower())
        if ext is not None:
            return ext
    ext_key = (extension or "").lower()
    if not ext_key.startswith(".") and ext_key:
        ext_key = "." + ext_key
    ext = _BY_EXT.get(ext_key)
    if ext is None:
        logger.info("Nessun extractor per mime=%r ext=%r — file verrà saltato", mime, extension)
    return ext


def get_ocr_extractor() -> Extractor:
    """Restituisce l'extractor OCR (esplicito, non parte del lookup automatico)."""
    return _OCR


def supported_mimes() -> list[str]:
    """Mime supportati dal registry primario (utile per la dashboard)."""
    return sorted(_BY_MIME.keys())


def supported_extensions() -> list[str]:
    """Estensioni supportate dal registry primario."""
    return sorted(_BY_EXT.keys())


def extractor_for_path(path: Path, mime: str | None = None) -> Extractor | None:
    """Helper: data una path, sceglie l'extractor."""
    return get_extractor(mime, path.suffix)
