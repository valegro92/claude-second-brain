"""Test del modulo chunking per i SourceDocument lunghi."""

from __future__ import annotations

from custodia_cli.extractor.chunking import (
    DEFAULT_MAX_TOKENS,
    Chunk,
    chunk_document,
)


def test_short_document_returns_single_chunk() -> None:
    """Documento sotto soglia → 1 chunk con strategy='single'."""
    text = "Breve documento di test. Una sola riga."
    chunks = chunk_document(source_doc_id=42, text=text)
    assert len(chunks) == 1
    assert chunks[0].text == text
    assert chunks[0].source_doc_id == 42
    assert chunks[0].chunk_index == 0
    assert chunks[0].metadata["strategy"] == "single"


def test_empty_document_returns_no_chunks() -> None:
    """Testo vuoto o solo whitespace → lista vuota."""
    assert chunk_document(source_doc_id=1, text="") == []
    assert chunk_document(source_doc_id=1, text="   \n\n  ") == []


def test_long_document_splits_on_page_markers() -> None:
    """Marker `--- Pagina N ---` produce split per pagine."""
    big_chunk = "x" * 250_000  # ~62.5k token stima
    text = (
        "Header generale.\n\n"
        "--- Pagina 1 ---\n"
        + big_chunk
        + "\n\n--- Pagina 2 ---\n"
        + big_chunk
        + "\n\n--- Pagina 3 ---\n"
        + "Pagina finale corta."
    )
    chunks = chunk_document(source_doc_id=7, text=text, max_tokens=50_000)
    assert len(chunks) >= 2
    for c in chunks:
        assert c.metadata["strategy"] == "pages"
        assert c.source_doc_id == 7


def test_long_document_splits_on_paragraphs_when_no_markers() -> None:
    """Doc lungo senza marker → split per paragrafi."""
    paragraphs = ["Paragrafo " + str(i) + " " + ("x" * 5000) for i in range(80)]
    text = "\n\n".join(paragraphs)
    chunks = chunk_document(source_doc_id=3, text=text, max_tokens=20_000)
    assert len(chunks) >= 2
    for c in chunks:
        assert c.metadata["strategy"] == "paragraphs"


def test_sheet_marker_splits_xlsx_style() -> None:
    """Marker `## Sheet: <nome>` produce split per sheet."""
    big = "y" * 250_000
    text = (
        "Workbook intro.\n\n"
        "## Sheet: Listino\n"
        + big
        + "\n\n## Sheet: Clienti\n"
        + big
    )
    chunks = chunk_document(source_doc_id=11, text=text, max_tokens=50_000)
    assert len(chunks) >= 1
    assert all(c.metadata["strategy"] == "sheets" for c in chunks)


def test_chunks_have_incremental_index() -> None:
    """chunk_index parte da 0 e cresce."""
    paragraphs = ["Para " + ("x" * 4000) for _ in range(40)]
    text = "\n\n".join(paragraphs)
    chunks = chunk_document(source_doc_id=99, text=text, max_tokens=10_000)
    assert len(chunks) >= 2
    indices = [c.chunk_index for c in chunks]
    assert indices == list(range(len(chunks)))


def test_chunk_uses_provider_token_counter() -> None:
    """Se viene passato un token_counter custom, lo usa."""

    class FakeCounter:
        def __init__(self) -> None:
            self.calls = 0

        def count_tokens(self, text: str) -> int:
            self.calls += 1
            return 100  # sotto soglia sempre

    counter = FakeCounter()
    chunks = chunk_document(
        source_doc_id=1,
        text="x" * 500_000,
        token_counter=counter,
    )
    # 100 token < default 50k → un solo chunk.
    assert len(chunks) == 1
    assert counter.calls >= 1


def test_default_max_tokens_constant() -> None:
    """Documenta che il default è 50k come da piano (D5)."""
    assert DEFAULT_MAX_TOKENS == 50_000


def test_chunk_is_frozen_dataclass() -> None:
    """Chunk è immutabile (frozen=True)."""
    ch = Chunk(text="a", source_doc_id=1, chunk_index=0)
    import dataclasses

    with __import__("pytest").raises(dataclasses.FrozenInstanceError):
        ch.text = "b"  # type: ignore[misc]
