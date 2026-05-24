"""Configurazione pytest condivisa.

Definisce i marker `requires_pandoc`, `requires_tesseract`, `requires_reportlab`
che permettono di skippare test dipendenti da tool/lib opzionali quando
l'ambiente di CI non li ha disponibili.

Uso nei test::

    @pytest.mark.requires_pandoc
    def test_che_richiede_pandoc(...): ...

    @pytest.mark.requires_tesseract
    def test_che_richiede_ocr(...): ...

    @pytest.mark.requires_reportlab
    def test_che_genera_pdf_reali(...): ...

I marker sono auto-skipped da una hook ``pytest_collection_modifyitems``
quando il binario/modulo non è disponibile, in modo che la CI minimal
(senza pandoc/tesseract installati) non rompa.
"""

from __future__ import annotations

import importlib.util
import shutil

import pytest

# --- registrazione marker --------------------------------------------------


def pytest_configure(config: pytest.Config) -> None:
    """Registra i marker custom così pytest non emette warning su 'unknown mark'."""
    config.addinivalue_line(
        "markers",
        "requires_pandoc: skippa il test se il binario `pandoc` non è in PATH",
    )
    config.addinivalue_line(
        "markers",
        "requires_tesseract: skippa il test se il binario `tesseract` non è in PATH",
    )
    config.addinivalue_line(
        "markers",
        "requires_reportlab: skippa il test se la libreria `reportlab` non è installata",
    )


# --- detection helpers -----------------------------------------------------


def _has_binary(name: str) -> bool:
    return shutil.which(name) is not None


def _has_module(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


# --- skip automatico per marker mancanti ----------------------------------


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Applica skip ai test marcati con `requires_*` se la dipendenza manca."""
    skip_pandoc = pytest.mark.skip(reason="binario 'pandoc' non disponibile nell'ambiente")
    skip_tesseract = pytest.mark.skip(reason="binario 'tesseract' non disponibile nell'ambiente")
    skip_reportlab = pytest.mark.skip(reason="libreria 'reportlab' non installata")

    has_pandoc = _has_binary("pandoc")
    has_tesseract = _has_binary("tesseract")
    has_reportlab = _has_module("reportlab")

    for item in items:
        if "requires_pandoc" in item.keywords and not has_pandoc:
            item.add_marker(skip_pandoc)
        if "requires_tesseract" in item.keywords and not has_tesseract:
            item.add_marker(skip_tesseract)
        if "requires_reportlab" in item.keywords and not has_reportlab:
            item.add_marker(skip_reportlab)
