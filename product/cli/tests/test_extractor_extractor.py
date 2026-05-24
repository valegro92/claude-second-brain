"""Test E2E dell'Extractor con FakeLLMProvider."""

from __future__ import annotations

from pathlib import Path

import pytest

from custodia_cli.extractor import Extractor
from custodia_cli.extractor.extractor import _normalize_name, _slugify
from custodia_cli.llm.fakes import FakeLLMProvider
from custodia_cli.state import StateStore


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "llm" / "extractor_responses.yaml"


@pytest.fixture
def store_with_rossetto_docs() -> StateStore:
    """StateStore in-memory con 2 documenti che parlano di Rossetto."""
    store = StateStore(":memory:")
    store.add_document(
        source_id="t:1",
        source_path="/finto/fattura-rossetto-001.pdf",
        mime_type="application/pdf",
        text=(
            "FATTURA n. 001/2024\n"
            "Cliente: Rossetto Laminazioni SRL\n"
            "P.IVA: 03421560289\n"
        ),
    )
    store.add_document(
        source_id="t:2",
        source_path="/finto/contratto-rossetto-2024.pdf",
        mime_type="application/pdf",
        text=(
            "CONTRATTO QUADRO 2024\n"
            "Cliente: Rossetto Laminazioni SRL\n"
            "Sede: Vicenza\n"
        ),
    )
    return store


@pytest.fixture
def store_with_generic_doc() -> StateStore:
    """StateStore con un documento che NON parla di clienti."""
    store = StateStore(":memory:")
    store.add_document(
        source_id="t:9",
        source_path="/finto/manuale-tecnico.pdf",
        mime_type="application/pdf",
        text="Manuale tecnico generico, nessun riferimento a clienti specifici.",
    )
    return store


def test_extract_unknown_entity_type_raises(store_with_rossetto_docs: StateStore) -> None:
    """entity_type non supportato → ValueError."""
    provider = FakeLLMProvider(fixture_path=FIXTURE_PATH)
    extractor = Extractor(llm=provider, store=store_with_rossetto_docs)
    with pytest.raises(ValueError, match="non supportato"):
        extractor.extract("alieno")


def test_extract_no_documents_returns_empty() -> None:
    """Nessun documento pending → lista vuota."""
    store = StateStore(":memory:")
    provider = FakeLLMProvider(fixture_path=FIXTURE_PATH)
    extractor = Extractor(llm=provider, store=store)
    assert extractor.extract("cliente") == []


def test_extract_clients_happy_path(
    store_with_rossetto_docs: StateStore,
) -> None:
    """2 documenti che parlano di Rossetto → 1 candidato cliente aggregato."""
    provider = FakeLLMProvider(fixture_path=FIXTURE_PATH)
    extractor = Extractor(llm=provider, store=store_with_rossetto_docs)
    candidates = extractor.extract("cliente")

    assert len(candidates) == 1
    cand = candidates[0]
    assert cand.entity_type == "cliente"
    assert cand.entity_id == "rossetto-laminazioni"
    assert cand.frontmatter["nome"] == "Rossetto Laminazioni SRL"
    assert cand.frontmatter["piva"] == "03421560289"
    assert cand.frontmatter["tipo"] == "cliente"
    # Le source_doc_ids puntano ai 2 documenti aggregati.
    assert sorted(cand.source_doc_ids) == [1, 2]
    # Confidence > 0 (campi popolati).
    assert cand.confidence > 0.0


def test_extract_persists_via_upsert(store_with_rossetto_docs: StateStore) -> None:
    """Dopo extract, upsert_entity → list_pending_entities ritorna i candidati."""
    provider = FakeLLMProvider(fixture_path=FIXTURE_PATH)
    extractor = Extractor(llm=provider, store=store_with_rossetto_docs)
    candidates = extractor.extract("cliente")
    for cand in candidates:
        store_with_rossetto_docs.upsert_entity(
            entity_type=cand.entity_type,
            entity_id=cand.entity_id,
            frontmatter=cand.frontmatter,
            body_md=cand.body_md,
            source_doc_ids=cand.source_doc_ids,
            confidence=cand.confidence,
            status="pending",
        )
    pending = store_with_rossetto_docs.list_pending_entities("cliente")
    assert len(pending) == 1
    assert pending[0]["entity_id"] == "rossetto-laminazioni"


def test_extract_generic_doc_yields_no_candidates(
    store_with_generic_doc: StateStore,
) -> None:
    """Doc che non parla di clienti → categorize ritorna lista vuota → 0 candidati."""
    provider = FakeLLMProvider(fixture_path=FIXTURE_PATH)
    extractor = Extractor(llm=provider, store=store_with_generic_doc)
    candidates = extractor.extract("cliente")
    assert candidates == []


def test_slugify_basic() -> None:
    """slugify normalizza case, spazi e caratteri non-ASCII."""
    assert _slugify("Rossetto Laminazioni SRL") == "rossetto-laminazioni-srl"
    assert _slugify("Caffè è bello!") == "caffe-e-bello"
    assert _slugify("   ") == "entita-senza-nome"


def test_normalize_name_strips_legal_form() -> None:
    """Suffissi legali rimossi nella normalizzazione."""
    assert _normalize_name("Rossetto Laminazioni SRL") == "rossetto laminazioni"
    assert _normalize_name("Bianchi Impianti SpA") == "bianchi impianti"
    assert _normalize_name("X SAS") == "x"
    # Doppio spazio collassato.
    assert _normalize_name("  Acme   Corp  ") == "acme corp"
