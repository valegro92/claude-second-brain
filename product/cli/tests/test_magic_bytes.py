"""
Test del modulo ``connectors.parsers.magic`` — detection MIME via primi 16
bytes e validazione coerenza con estensione.
"""

from __future__ import annotations

from pathlib import Path

from custodia_cli.connectors.parsers.magic import (
    detect_mime_by_magic,
    mime_matches_extension,
)


# ----------------------------------------------------------------------
# detect_mime_by_magic — signature reali
# ----------------------------------------------------------------------


def test_detect_pdf_real_header(tmp_path: Path) -> None:
    f = tmp_path / "foo.pdf"
    f.write_bytes(b"%PDF-1.5\n%\xe2\xe3\xcf\xd3\n... rest of pdf ...")
    assert detect_mime_by_magic(f) == "application/pdf"


def test_detect_zip_header_used_for_docx_xlsx(tmp_path: Path) -> None:
    """DOCX/XLSX/PPTX sono ZIP container: la magic-detection ritorna zip."""
    f = tmp_path / "doc.docx"
    f.write_bytes(b"PK\x03\x04\x14\x00\x00\x00... rest of zip ...")
    assert detect_mime_by_magic(f) == "application/zip"


def test_detect_png_header(tmp_path: Path) -> None:
    f = tmp_path / "img.png"
    f.write_bytes(b"\x89PNG\r\n\x1a\n... rest ...")
    assert detect_mime_by_magic(f) == "image/png"


def test_detect_jpeg_header(tmp_path: Path) -> None:
    f = tmp_path / "img.jpg"
    f.write_bytes(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00")
    assert detect_mime_by_magic(f) == "image/jpeg"


def test_detect_ole_storage_old_doc(tmp_path: Path) -> None:
    """Vecchi Office 97-2003 .doc/.xls usano CFB/OLE2."""
    f = tmp_path / "old.doc"
    f.write_bytes(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1\x00\x00")
    assert detect_mime_by_magic(f) == "application/x-ole-storage"


def test_detect_returns_none_on_unknown_binary(tmp_path: Path) -> None:
    """Bytes random non riconosciuti → None (non solleva)."""
    f = tmp_path / "weird.bin"
    f.write_bytes(b"\x12\x34\x56\x78\x9a\xbc\xde\xf0 garbage")
    assert detect_mime_by_magic(f) is None


def test_detect_pdf_signature_must_be_at_start(tmp_path: Path) -> None:
    """``%PDF-`` non all'inizio → None (no false positive)."""
    f = tmp_path / "fake.pdf"
    f.write_bytes(b"hello world this contains %PDF- somewhere in the middle")
    assert detect_mime_by_magic(f) is None


def test_detect_on_nonexistent_path_returns_none(tmp_path: Path) -> None:
    """File inesistente → None, niente eccezioni."""
    f = tmp_path / "does-not-exist.pdf"
    assert detect_mime_by_magic(f) is None


def test_detect_accepts_bytes_directly() -> None:
    """API supporta sia Path che bytes diretti."""
    assert detect_mime_by_magic(b"%PDF-1.7") == "application/pdf"
    assert detect_mime_by_magic(b"PK\x03\x04rest") == "application/zip"
    assert detect_mime_by_magic(b"") is None


def test_detect_short_file_no_crash(tmp_path: Path) -> None:
    """File < 16 bytes non deve crashare."""
    f = tmp_path / "tiny.txt"
    f.write_bytes(b"ab")
    assert detect_mime_by_magic(f) is None


# ----------------------------------------------------------------------
# mime_matches_extension — validazione coerenza
# ----------------------------------------------------------------------


def test_mime_matches_real_pdf(tmp_path: Path) -> None:
    f = tmp_path / "real.pdf"
    f.write_bytes(b"%PDF-1.4 contents")
    assert mime_matches_extension(f) is True


def test_mime_mismatch_pdf_extension_but_text_content(tmp_path: Path) -> None:
    """File .pdf con contenuto plain text → False (estensione ingannevole)."""
    f = tmp_path / "fake.pdf"
    f.write_bytes(b"Lorem ipsum dolor sit amet plain text\n")
    assert mime_matches_extension(f) is False


def test_mime_matches_docx_with_zip_content(tmp_path: Path) -> None:
    f = tmp_path / "doc.docx"
    f.write_bytes(b"PK\x03\x04" + b"\x00" * 12)
    assert mime_matches_extension(f) is True


def test_mime_mismatch_docx_with_text_content(tmp_path: Path) -> None:
    """.docx ma content text → False."""
    f = tmp_path / "fake.docx"
    f.write_bytes(b"this is just plain text, not a zip")
    assert mime_matches_extension(f) is False


def test_unknown_extension_passes_through(tmp_path: Path) -> None:
    """Estensione non tracciata → True (no veto)."""
    f = tmp_path / "data.unknown"
    f.write_bytes(b"anything goes here")
    assert mime_matches_extension(f) is True


def test_no_extension_passes_through(tmp_path: Path) -> None:
    """File senza estensione → True (passa, non possiamo invalidare)."""
    f = tmp_path / "Makefile"
    f.write_bytes(b"all:\n\techo hi\n")
    assert mime_matches_extension(f) is True


def test_undetectable_content_on_tracked_extension_vetos(tmp_path: Path) -> None:
    """Estensione tracciata (.pdf/.docx/...) ma magic-detection ritorna None
    → False: il file non è credibile come PDF/DOCX/..., evitiamo di lanciare
    il parser pesante."""
    f = tmp_path / "weird.pdf"
    # Bytes random, nessuna signature riconosciuta.
    f.write_bytes(b"\x01\x02\x03\x04\x05" + b"x" * 32)
    assert mime_matches_extension(f) is False


def test_undetectable_content_on_unknown_extension_passes(tmp_path: Path) -> None:
    """Estensione NON tracciata + magic detection None → True (no veto)."""
    f = tmp_path / "data.unknown"
    f.write_bytes(b"\x01\x02\x03 anything")
    assert mime_matches_extension(f) is True
