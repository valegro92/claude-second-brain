"""
Parser file binari → testo per i connettori Custodia.

I parser sono "puri": prendono ``bytes`` o ``Path``, ritornano ``str``. Sono
riusati da U3 (Google Drive, dopo download/export) e U4 (filesystem locale).

Nota Google Docs/Sheets: NON esiste un ``parse_gdoc`` dedicato. Il connettore
Drive esporta i file nativi Google come DOCX/XLSX via API, poi delega a
``parse_docx``/``parse_xlsx``. Questo evita duplicazione di logica.

Security note: all'import del modulo invochiamo ``defusedxml.defuse_stdlib()``
una volta, che mette in sicurezza i parser XML stdlib (``xml.etree.*``,
``xml.sax.*``, ``xml.dom.*``) contro XXE, billion-laughs e DTD esterno. Le
librerie ``python-docx`` e ``openpyxl`` usano ``lxml``: ``defusedxml`` non
intercetta direttamente ``lxml``, ma i nostri parser difendono comunque con
controllo uncompressed-size sul ZIP a monte (vedi ``check_zip_uncompressed_size``).
"""

from __future__ import annotations

import logging
import zipfile
from pathlib import Path
from typing import Union

import defusedxml

from custodia_cli.connectors.base import ParserError

logger = logging.getLogger(__name__)

# Difesa XXE/billion-laughs sui parser XML stdlib. Idempotente.
try:
    defusedxml.defuse_stdlib()
except Exception:  # noqa: BLE001 — non bloccare l'import se già patched
    logger.debug("defusedxml.defuse_stdlib() già applicato o non applicabile")


# Soglia uncompressed massima per archivi DOCX/XLSX (sono ZIP container).
# 200 MB: ampiamente sufficiente per offerte/listini reali, ma blocca
# zip-bomb classiche da kilobyte → gigabyte.
MAX_UNCOMPRESSED_BYTES: int = 200 * 1024 * 1024


def check_zip_uncompressed_size(
    content: Union[bytes, Path],
    *,
    max_uncompressed_bytes: int | None = None,
) -> None:
    """Verifica che la dimensione *uncompressed* del file ZIP non superi la soglia.

    Args:
        content: bytes del file o Path all'archivio ZIP (DOCX/XLSX).
        max_uncompressed_bytes: soglia di sicurezza. ``None`` (default) usa
            ``MAX_UNCOMPRESSED_BYTES`` letto al momento della chiamata, così i
            test possono monkeypatchare la costante a runtime.

    Raises:
        ParserError: se il file non è uno ZIP valido o supera la soglia
            (possibile zip-bomb).
    """
    if max_uncompressed_bytes is None:
        # Lookup dinamico per supportare monkeypatching nei test.
        import sys as _sys
        _mod = _sys.modules[__name__]
        max_uncompressed_bytes = _mod.MAX_UNCOMPRESSED_BYTES
    try:
        if isinstance(content, Path):
            zf = zipfile.ZipFile(content)
        else:
            import io

            zf = zipfile.ZipFile(io.BytesIO(content))
    except zipfile.BadZipFile as exc:
        raise ParserError(f"Archivio ZIP non valido: {exc}") from exc

    try:
        total = sum(info.file_size for info in zf.infolist())
    finally:
        zf.close()

    if total > max_uncompressed_bytes:
        raise ParserError(
            f"Possibile zip-bomb: uncompressed size {total / (1024 * 1024):.1f}MB "
            f"supera la soglia di {max_uncompressed_bytes // (1024 * 1024)}MB."
        )


from custodia_cli.connectors.parsers.docx import parse_docx  # noqa: E402
from custodia_cli.connectors.parsers.magic import (  # noqa: E402
    detect_mime_by_magic,
    mime_matches_extension,
)
from custodia_cli.connectors.parsers.pdf import parse_pdf  # noqa: E402
from custodia_cli.connectors.parsers.pool import ParserPool  # noqa: E402
from custodia_cli.connectors.parsers.xlsx import parse_xlsx  # noqa: E402

__all__ = [
    "MAX_UNCOMPRESSED_BYTES",
    "ParserPool",
    "check_zip_uncompressed_size",
    "detect_mime_by_magic",
    "mime_matches_extension",
    "parse_docx",
    "parse_pdf",
    "parse_xlsx",
]
