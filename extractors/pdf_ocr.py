"""Extractor OCR per PDF scansionati. Usa pytesseract + Pillow se disponibili.

In v1 non chiamiamo Claude vision: se Tesseract non è installato l'extractor
restituisce un ExtractionResult con quality=0.0 e un warning chiaro, senza
sollevare eccezioni (così la pipeline può continuare).
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from ._base import ExtractionResult, Extractor

logger = logging.getLogger(__name__)

# Lingue richieste a Tesseract. Italiano primario, inglese fallback.
_LANGS = "ita+eng"


class PdfOcrExtractor(Extractor):
    """OCR di PDF scansionati con Tesseract italiano.

    Richiede:
      - pacchetti Python ``pytesseract`` + ``Pillow`` (extras ``ocr``)
      - binario di sistema ``tesseract`` con language pack ``ita`` installato
      - utility per rasterizzare il PDF: tenta ``pdf2image`` (Poppler) o, in fallback,
        ``pdfplumber`` (page.to_image, richiede comunque Poppler/ghostscript)

    Quando i prerequisiti mancano: quality=0.0, warning, niente crash.
    """

    name = "pdf_ocr"
    # Stesso mime del PDF testuale: il registry sceglie pdf.py come primario,
    # il dispatcher (Sprint 4) decide se passare a pdf_ocr in base a needs_ocr.
    mimes = ["application/pdf"]
    extensions = [".pdf"]

    def extract(self, file_path: Path) -> ExtractionResult:
        warnings: list[str] = []

        if not _has_tesseract():
            warnings.append("Tesseract non installato, OCR saltato — vedi bootstrap/INSTALL.md")
            return ExtractionResult(
                markdown="_(OCR non eseguito: Tesseract assente)_",
                metadata={"engine": "none", "ocr_skipped": True},
                warnings=warnings,
                quality=0.0,
            )

        try:
            import pytesseract  # type: ignore[import-not-found]
            from PIL import Image  # noqa: F401 - verifica disponibilità
        except ImportError:
            warnings.append("pytesseract/Pillow non installati (extras 'ocr') — OCR saltato")
            return ExtractionResult(
                markdown="_(OCR non eseguito: librerie Python mancanti)_",
                metadata={"engine": "none", "ocr_skipped": True},
                warnings=warnings,
                quality=0.0,
            )

        images = _rasterize_pdf(file_path, warnings)
        if not images:
            warnings.append(
                "Impossibile rasterizzare il PDF (manca Poppler/pdf2image o pdfplumber). "
                "Vedi bootstrap/INSTALL.md per installare 'poppler-utils'."
            )
            return ExtractionResult(
                markdown="_(OCR non eseguito: rasterizzazione fallita)_",
                metadata={"engine": "none", "ocr_skipped": True},
                warnings=warnings,
                quality=0.0,
            )

        sections: list[str] = []
        total_chars = 0
        for idx, img in enumerate(images, start=1):
            try:
                text = pytesseract.image_to_string(img, lang=_LANGS)
            except pytesseract.TesseractError as exc:
                warnings.append(f"Pagina {idx}: tesseract ha fallito ({exc})")
                text = ""
            except Exception as exc:  # pragma: no cover - difensivo
                warnings.append(f"Pagina {idx}: errore inatteso ({exc})")
                text = ""
            sections.append(f"## Pagina {idx}\n\n{text.strip()}")
            total_chars += len(text)

        n_pages = len(images)
        quality = _ocr_quality(total_chars, n_pages)
        return ExtractionResult(
            markdown="\n\n".join(sections).strip() or "_(OCR non ha prodotto testo)_",
            metadata={
                "engine": "tesseract",
                "lang": _LANGS,
                "pages": n_pages,
                "chars": total_chars,
            },
            warnings=warnings,
            quality=quality,
        )


def _has_tesseract() -> bool:
    """True se il binario ``tesseract`` è nel PATH."""
    return shutil.which("tesseract") is not None


def _rasterize_pdf(file_path: Path, warnings: list[str]) -> list:
    """Prova ``pdf2image`` (Poppler) → ``pdfplumber.page.to_image``. Lista vuota se nessuno disponibile."""
    # Tentativo 1: pdf2image (più robusto).
    try:
        from pdf2image import convert_from_path  # type: ignore[import-not-found]

        return list(convert_from_path(str(file_path)))
    except ImportError:
        pass
    except Exception as exc:
        warnings.append(f"pdf2image ha fallito: {exc}")

    # Tentativo 2: pdfplumber.to_image (anch'esso si appoggia a ghostscript/poppler).
    try:
        import pdfplumber
        from PIL import Image  # noqa: F401

        out = []
        with pdfplumber.open(str(file_path)) as pdf:
            for page in pdf.pages:
                try:
                    pil = page.to_image(resolution=200).original
                    out.append(pil)
                except Exception as exc:
                    warnings.append(f"pdfplumber.to_image fallito: {exc}")
                    return []
        return out
    except ImportError:
        return []
    except Exception as exc:
        warnings.append(f"Rasterizzazione fallita: {exc}")
        return []


def _ocr_quality(chars: int, pages: int) -> float:
    """OCR è di norma più rumoroso del testo nativo: soglia più permissiva."""
    if pages <= 0:
        return 0.0
    ratio = chars / (200 * pages)
    return max(0.0, min(1.0, ratio))
