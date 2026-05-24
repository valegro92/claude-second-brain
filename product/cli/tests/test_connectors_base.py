"""Test contratti base dei connettori (SourceDocument, Connector Protocol)."""

from __future__ import annotations

from typing import Iterator

import pytest

from custodia_cli.connectors import Connector, ParserError, SourceDocument


def test_source_document_is_frozen() -> None:
    """SourceDocument è un frozen dataclass: assegnazione attributi vietata."""
    doc = SourceDocument(
        source_id="gdrive:abc",
        source_path="/foo/bar.pdf",
        mime_type="application/pdf",
        text="hello",
    )
    with pytest.raises((AttributeError, TypeError)):
        doc.text = "tampered"  # type: ignore[misc]


def test_source_document_default_metadata_is_empty_dict() -> None:
    doc = SourceDocument(
        source_id="x",
        source_path="/x",
        mime_type="text/plain",
        text="",
    )
    assert doc.metadata == {}


def test_source_document_metadata_independent_between_instances() -> None:
    """Due istanze costruite senza metadata NON condividono la stessa dict (factory)."""
    d1 = SourceDocument(source_id="a", source_path="/a", mime_type="text/plain", text="")
    d2 = SourceDocument(source_id="b", source_path="/b", mime_type="text/plain", text="")
    assert d1.metadata is not d2.metadata


def test_connector_protocol_has_iter_documents() -> None:
    """Il Protocol Connector espone almeno ``iter_documents``."""
    assert hasattr(Connector, "iter_documents")


def test_connector_protocol_runtime_check() -> None:
    """Una subclass conforme deve passare isinstance(..., Connector)."""

    class DummyConnector:
        name = "dummy"

        def iter_documents(self) -> Iterator[SourceDocument]:
            yield SourceDocument(
                source_id="dummy:1",
                source_path="/dummy",
                mime_type="text/plain",
                text="ciao",
            )

    instance = DummyConnector()
    assert isinstance(instance, Connector)
    docs = list(instance.iter_documents())
    assert len(docs) == 1
    assert docs[0].source_id == "dummy:1"


def test_parser_error_is_exception() -> None:
    """ParserError deve ereditare da Exception per propagazione standard."""
    assert issubclass(ParserError, Exception)
