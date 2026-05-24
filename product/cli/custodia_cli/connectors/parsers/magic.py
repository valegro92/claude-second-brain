"""
Detection rapida del MIME effettivo di un file leggendo i primi 16 bytes.

Utile come prefilter prima di lanciare il parser per due motivi:

1. Skip rapido di file con estensione "ingannevole" (es. ``.pdf`` che è
   in realtà testo plain): evita di buttarli al parser pesante.
2. Validate che il parser giusto verrà invocato.

Restituisce il MIME canonical o ``None`` se non riconosciuto. Nessuna
dipendenza esterna (no python-magic / libmagic): usiamo i magic bytes
"hard-coded" dei formati che ci interessano.
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Mapping signature (bytes prefix) → MIME canonical.
#
# L'ordine NON conta perché i prefissi sono mutuamente esclusivi per i
# formati che ci interessano (PDF/PNG/JPEG/ZIP/OLE2).
_MAGIC_SIGNATURES: dict[bytes, str] = {
    # PDF — "%PDF-" come ASCII.
    b"%PDF-": "application/pdf",
    # ZIP — base per i formati OOXML (DOCX/XLSX/PPTX) che sono zip-based.
    b"PK\x03\x04": "application/zip",
    b"PK\x05\x06": "application/zip",  # empty archive
    b"PK\x07\x08": "application/zip",  # spanned archive
    # Old Office (CFB / OLE2): .doc, .xls, .ppt 97-2003.
    b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1": "application/x-ole-storage",
    # JPEG: due varianti (JFIF + Exif e raw SOI).
    b"\xff\xd8\xff": "image/jpeg",
    # PNG: 8-byte header.
    b"\x89PNG\r\n\x1a\n": "image/png",
}


def detect_mime_by_magic(
    path: Path | bytes, max_bytes: int = 16
) -> str | None:
    """Legge i primi ``max_bytes`` di un file e ritorna il MIME riconosciuto
    o ``None``.

    Args:
        path: ``Path`` (legge dal disco) oppure ``bytes`` diretti.
        max_bytes: numero massimo di bytes da leggere come header. Default 16.

    Returns:
        Stringa MIME canonical (es. ``"application/pdf"``) oppure ``None``
        se nessuna signature match o se la lettura fallisce.

    Note:
        Errori di IO (``OSError``, ``PermissionError``) sono catturati e
        ritornano ``None``: il caller decide cosa fare. Non solleviamo
        per non costringere chi prefiltri a try/except ovunque.
    """
    if isinstance(path, Path):
        try:
            with open(path, "rb") as fh:
                head = fh.read(max_bytes)
        except OSError as exc:
            logger.debug("magic: lettura fallita su %s: %s", path, exc)
            return None
    else:
        head = path[:max_bytes]

    for signature, mime in _MAGIC_SIGNATURES.items():
        if head.startswith(signature):
            return mime

    return None


# Mapping estensione → set di MIME accettabili dai magic bytes.
#
# DOCX/XLSX/PPTX sono ZIP, quindi i magic bytes detectano ``application/zip``.
# Non possiamo distinguere fra di loro senza aprire il container: ci basta
# sapere che è un ZIP per non passarlo al parser come PDF.
_EXPECTED_MIME_BY_EXTENSION: dict[str, tuple[str, ...]] = {
    ".pdf": ("application/pdf",),
    ".docx": ("application/zip",),
    ".xlsx": ("application/zip",),
    ".pptx": ("application/zip",),
    ".doc": ("application/x-ole-storage",),
    ".xls": ("application/x-ole-storage",),
    ".ppt": ("application/x-ole-storage",),
    ".jpg": ("image/jpeg",),
    ".jpeg": ("image/jpeg",),
    ".png": ("image/png",),
}


def mime_matches_extension(path: Path) -> bool:
    """Verifica se il MIME detected dai magic bytes corrisponde all'estensione.

    Logica:
    - Estensione NON tracciata → ``True`` (no veto, non sappiamo).
    - Estensione tracciata E magic-detection ritorna ``None`` o un MIME
      diverso da quanto atteso → ``False`` (file sospetto).
    - Estensione tracciata E detection corrisponde → ``True``.

    Args:
        path: file su disco da controllare.

    Returns:
        ``True`` se il file è "credibile" rispetto all'estensione;
        ``False`` se l'estensione promette un formato binario noto
        (PDF/DOCX/...) ma i magic bytes dicono altrimenti.

    Esempi:
        - ``foo.pdf`` con header ``%PDF-`` → True.
        - ``foo.pdf`` con header ``Lorem ipsum`` (text) → False.
        - ``foo.docx`` con header ZIP (``PK\\x03\\x04``) → True.
        - ``foo.docx`` con header text plain → False.
        - ``foo.unknown`` con header text plain → True (no expected, no veto).

    Note:
        Per file molto piccoli o vuoti che dovrebbero essere binari ma non
        hanno header (es. PDF da 0 byte) il risultato è ``False``: questo
        è il comportamento desiderato perché un PDF realmente vuoto non
        può essere parsato comunque.
    """
    ext = path.suffix.lower()
    expected = _EXPECTED_MIME_BY_EXTENSION.get(ext)
    if not expected:
        # Estensione non tracciata: non possiamo invalidare.
        return True

    detected = detect_mime_by_magic(path)
    if detected is None:
        # Estensione promette un formato binario noto ma i magic bytes
        # non corrispondono a NESSUNA delle signature note → veto.
        return False

    return detected in expected


__all__ = [
    "detect_mime_by_magic",
    "mime_matches_extension",
]
