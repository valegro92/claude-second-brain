"""
Parser PDF → testo via pypdf.

Edge case gestiti:
- PDF password-protected: ritorna stringa vuota + warning log (non fatale).
- PDF scansionato senza testo (image-only): ritorna stringa vuota senza errore.
- PDF corrotto / non-parsabile: solleva ``ParserError``.
"""

from __future__ import annotations

import io
import logging
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from custodia_cli.connectors.base import ParserError

logger = logging.getLogger(__name__)


def parse_pdf(content: bytes | Path) -> str:
    """Estrae il testo di un PDF concatenando pagina per pagina.

    Args:
        content: bytes del file o ``Path`` a un PDF su disco.

    Returns:
        Testo estratto. Stringa vuota se il PDF è cifrato (password-protected),
        scansionato (image-only) o realmente vuoto.

    Raises:
        ParserError: se ``pypdf`` non riesce a leggere il file (corrotto,
            formato non valido).
    """
    stream: io.BytesIO | object
    if isinstance(content, Path):
        stream = io.BytesIO(content.read_bytes())
    else:
        stream = io.BytesIO(content)

    try:
        reader = PdfReader(stream)
    except PdfReadError as exc:
        raise ParserError(f"PDF non leggibile: {exc}") from exc
    except Exception as exc:  # noqa: BLE001 — vogliamo tipizzare comunque
        raise ParserError(f"Errore inatteso aprendo PDF: {exc}") from exc

    if reader.is_encrypted:
        # Tentiamo password vuota (PDF "cifrati" senza password reale).
        try:
            if reader.decrypt("") == 0:
                logger.warning("⚠️  PDF cifrato senza password: testo non estraibile.")
                return ""
        except Exception:  # noqa: BLE001
            logger.warning("⚠️  PDF cifrato: decrypt fallito, testo non estraibile.")
            return ""

    parts: list[str] = []
    for idx, page in enumerate(reader.pages):
        try:
            page_text = page.extract_text() or ""
        except Exception as exc:  # noqa: BLE001 — pagine malformate non bloccano l'intero file
            logger.warning("⚠️  Errore estrazione pagina %d: %s", idx + 1, exc)
            page_text = ""
        if page_text:
            parts.append(page_text)
    return "\n".join(parts)


__all__ = ["parse_pdf"]
