"""Test unit per `StateStore`."""

from __future__ import annotations

import sqlite3
from typing import Iterator

import pytest

from custodia_cli.state import SCHEMA_VERSION, StateStore
from custodia_cli.state.store import StateStoreCorruptionError


@pytest.fixture()
def store(tmp_path) -> Iterator[StateStore]:
    db = tmp_path / "state.db"
    with StateStore(db) as s:
        yield s


def test_schema_applied(store: StateStore) -> None:
    assert store.schema_version == SCHEMA_VERSION

    tables = {
        row[0]
        for row in store._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    assert {"runs", "documents", "entities", "review_decisions"}.issubset(tables)

    # La colonna v2 deve esistere su `review_decisions`.
    cols = {
        row[1]
        for row in store._conn.execute(
            "PRAGMA table_info(review_decisions)"
        ).fetchall()
    }
    assert "previous_frontmatter_json" in cols


def test_add_and_list_documents(store: StateStore) -> None:
    doc_id = store.add_document(
        source_id="drive::abc123",
        source_path="/finto/fattura.pdf",
        mime_type="application/pdf",
        text="Fattura 1/2026 — Acme srl",
        metadata={"size_bytes": 1234},
    )
    assert doc_id >= 1

    docs = store.list_documents()
    assert len(docs) == 1
    assert docs[0]["source_id"] == "drive::abc123"
    assert docs[0]["metadata"] == {"size_bytes": 1234}
    assert docs[0]["status"] == "pending"

    # filtro per status / mime
    assert store.list_documents(status="pending") == docs
    assert store.list_documents(status="done") == []
    assert store.list_documents(mime_type="application/pdf") == docs
    assert store.list_documents(mime_type="text/plain") == []


def test_add_document_duplicate_source_id_raises(store: StateStore) -> None:
    store.add_document(
        source_id="dup",
        source_path="/x",
        mime_type="text/plain",
        text="",
    )
    with pytest.raises(sqlite3.IntegrityError):
        store.add_document(
            source_id="dup",
            source_path="/y",
            mime_type="text/plain",
            text="",
        )


def test_upsert_entity_insert_then_update(store: StateStore) -> None:
    pk1 = store.upsert_entity(
        entity_type="cliente",
        entity_id="acme-srl",
        frontmatter={"nome": "Acme srl", "settore": "manifatturiero"},
        body_md="# Acme srl\n",
        source_doc_ids=[1, 2],
        confidence=0.82,
    )
    assert pk1 >= 1

    pk2 = store.upsert_entity(
        entity_type="cliente",
        entity_id="acme-srl",
        frontmatter={"nome": "Acme Srl", "settore": "metalmeccanica"},
        body_md="# Acme Srl\n",
        source_doc_ids=[1, 2, 3],
        confidence=0.91,
    )
    assert pk2 == pk1, "upsert deve mantenere la stessa primary key"

    pending = store.list_pending_entities()
    assert len(pending) == 1
    assert pending[0]["frontmatter"]["settore"] == "metalmeccanica"
    assert pending[0]["source_doc_ids"] == [1, 2, 3]
    assert pending[0]["confidence"] == pytest.approx(0.91)


def test_list_pending_entities_filter_by_type(store: StateStore) -> None:
    store.upsert_entity(
        entity_type="cliente",
        entity_id="a",
        frontmatter={},
        body_md="",
        source_doc_ids=[],
        confidence=0.5,
    )
    store.upsert_entity(
        entity_type="fornitore",
        entity_id="b",
        frontmatter={},
        body_md="",
        source_doc_ids=[],
        confidence=0.5,
    )
    clienti = store.list_pending_entities(entity_type="cliente")
    fornitori = store.list_pending_entities(entity_type="fornitore")
    assert len(clienti) == 1 and clienti[0]["entity_id"] == "a"
    assert len(fornitori) == 1 and fornitori[0]["entity_id"] == "b"


def test_record_review_decision_approved(store: StateStore) -> None:
    pk = store.upsert_entity(
        entity_type="cliente",
        entity_id="x",
        frontmatter={"nome": "X"},
        body_md="",
        source_doc_ids=[],
        confidence=0.6,
    )
    store.record_review_decision(entity_pk=pk, decision="approved")

    writes = store.list_pending_writes()
    assert len(writes) == 1
    assert writes[0]["id"] == pk
    assert writes[0]["status"] == "approved"
    assert store.list_pending_entities() == []  # non più pending


def test_record_review_decision_rejected(store: StateStore) -> None:
    pk = store.upsert_entity(
        entity_type="cliente",
        entity_id="x",
        frontmatter={},
        body_md="",
        source_doc_ids=[],
        confidence=0.6,
    )
    store.record_review_decision(entity_pk=pk, decision="rejected")
    assert store.list_pending_writes() == []
    assert store.list_pending_entities() == []


def test_record_review_decision_edited_overwrites_frontmatter(store: StateStore) -> None:
    pk = store.upsert_entity(
        entity_type="cliente",
        entity_id="x",
        frontmatter={"nome": "Vecchio"},
        body_md="",
        source_doc_ids=[],
        confidence=0.6,
    )
    store.record_review_decision(
        entity_pk=pk,
        decision="edited",
        edited_frontmatter={"nome": "Nuovo", "settore": "tech"},
    )
    writes = store.list_pending_writes()
    assert len(writes) == 1
    assert writes[0]["frontmatter"] == {"nome": "Nuovo", "settore": "tech"}


def test_record_review_decision_edited_preserves_previous_frontmatter(
    store: StateStore,
) -> None:
    """FIX B: la review history per 'edited' deve conservare il frontmatter
    pre-edit accanto a quello edited."""
    pk = store.upsert_entity(
        entity_type="cliente",
        entity_id="x",
        frontmatter={"nome": "Vecchio", "settore": "antico"},
        body_md="",
        source_doc_ids=[],
        confidence=0.6,
    )
    store.record_review_decision(
        entity_pk=pk,
        decision="edited",
        edited_frontmatter={"nome": "Nuovo"},
    )
    row = store._conn.execute(
        "SELECT previous_frontmatter_json, edited_frontmatter_json "
        "FROM review_decisions WHERE entity_pk = ?",
        (pk,),
    ).fetchone()
    import json

    assert row["previous_frontmatter_json"] is not None
    assert json.loads(row["previous_frontmatter_json"]) == {
        "nome": "Vecchio",
        "settore": "antico",
    }
    assert json.loads(row["edited_frontmatter_json"]) == {"nome": "Nuovo"}


def test_record_review_decision_approved_has_no_previous_frontmatter(
    store: StateStore,
) -> None:
    pk = store.upsert_entity(
        entity_type="cliente",
        entity_id="x",
        frontmatter={"nome": "X"},
        body_md="",
        source_doc_ids=[],
        confidence=0.6,
    )
    store.record_review_decision(entity_pk=pk, decision="approved")
    row = store._conn.execute(
        "SELECT previous_frontmatter_json FROM review_decisions WHERE entity_pk = ?",
        (pk,),
    ).fetchone()
    assert row["previous_frontmatter_json"] is None


def test_record_review_decision_invalid(store: StateStore) -> None:
    pk = store.upsert_entity(
        entity_type="cliente",
        entity_id="x",
        frontmatter={},
        body_md="",
        source_doc_ids=[],
        confidence=0.5,
    )
    with pytest.raises(ValueError):
        store.record_review_decision(entity_pk=pk, decision="maybe")
    with pytest.raises(ValueError):
        store.record_review_decision(entity_pk=99999, decision="approved")
    with pytest.raises(ValueError):
        store.record_review_decision(entity_pk=pk, decision="edited")  # no fm


def test_register_and_complete_run(store: StateStore) -> None:
    run_id = store.register_run(command="scan drive", args={"root_folder_id": "abc"})
    assert run_id >= 1

    row = store._conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
    assert row["status"] == "running"
    assert row["completed_at"] is None

    store.complete_run(run_id, status="success", summary="3 documenti")

    row = store._conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
    assert row["status"] == "success"
    assert row["completed_at"] is not None
    assert row["summary"] == "3 documenti"


def test_complete_run_invalid_status(store: StateStore) -> None:
    run_id = store.register_run(command="test", args={})
    with pytest.raises(ValueError):
        store.complete_run(run_id, status="boh")
    with pytest.raises(ValueError):
        store.complete_run(99999, status="success")


def test_reopen_persisted_db(tmp_path) -> None:
    db = tmp_path / "state.db"
    with StateStore(db) as s1:
        s1.add_document(
            source_id="s1", source_path="/x", mime_type="text/plain", text="hello"
        )

    with StateStore(db) as s2:
        docs = s2.list_documents()
        assert len(docs) == 1
        assert docs[0]["source_id"] == "s1"
        assert s2.schema_version == SCHEMA_VERSION


def test_schema_version_property(store: StateStore) -> None:
    """FIX D: la versione schema è esposta come property pubblica."""
    assert store.schema_version == SCHEMA_VERSION


def test_context_manager_closes_connection(tmp_path) -> None:
    """FIX E: lo store usato come context manager chiude la connessione all'uscita."""
    db = tmp_path / "state.db"
    with StateStore(db) as s:
        s.add_document(source_id="ctx", source_path="/x", mime_type="t", text="")
    # Dopo l'uscita la connessione è chiusa: ogni execute solleva.
    with pytest.raises(sqlite3.ProgrammingError):
        s._conn.execute("SELECT 1")


def test_open_with_unknown_future_schema_version_raises(tmp_path) -> None:
    """FIX H: se il DB è stato scritto da una versione futura, rifiutare l'open."""
    db = tmp_path / "state.db"
    with StateStore(db) as s:
        assert s.schema_version == SCHEMA_VERSION
    # Manipola user_version a un valore > SCHEMA_VERSION.
    conn = sqlite3.connect(str(db))
    conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION + 100}")
    conn.commit()
    conn.close()

    with pytest.raises(RuntimeError, match="incompatibile"):
        StateStore(db)


def test_corrupted_json_in_documents_raises(tmp_path) -> None:
    """FIX C/I: JSON malformato nelle colonne *_json -> StateStoreCorruptionError."""
    db = tmp_path / "state.db"
    with StateStore(db) as s:
        s.add_document(
            source_id="c",
            source_path="/x",
            mime_type="text/plain",
            text="hello",
            metadata={"ok": True},
        )

    # Corruzione manuale del JSON.
    conn = sqlite3.connect(str(db))
    conn.execute("UPDATE documents SET metadata_json = '{invalid' WHERE id = 1")
    conn.commit()
    conn.close()

    with StateStore(db) as s2:
        with pytest.raises(StateStoreCorruptionError, match="metadata_json"):
            s2.list_documents()


def test_corrupted_json_in_entities_raises(tmp_path) -> None:
    db = tmp_path / "state.db"
    with StateStore(db) as s:
        s.upsert_entity(
            entity_type="cliente",
            entity_id="x",
            frontmatter={"nome": "Acme"},
            body_md="",
            source_doc_ids=[1, 2],
            confidence=0.7,
        )

    conn = sqlite3.connect(str(db))
    conn.execute(
        "UPDATE entities SET source_doc_ids_json = 'not-json-at-all' WHERE id = 1"
    )
    conn.commit()
    conn.close()

    with StateStore(db) as s2:
        with pytest.raises(StateStoreCorruptionError, match="source_doc_ids_json"):
            s2.list_pending_entities()


def test_migration_v1_to_v2_preserves_data(tmp_path) -> None:
    """Apertura di un DB v1 esistente: la migrazione aggiunge la colonna
    nuova senza perdere i dati pre-esistenti."""
    db = tmp_path / "state.db"

    # Costruzione manuale di un DB v1 (solo schema base, user_version = 1).
    schema_path = (
        __import__("custodia_cli.state.store", fromlist=["_SCHEMA_PATH"])._SCHEMA_PATH
    )
    sql = schema_path.read_text(encoding="utf-8")
    conn = sqlite3.connect(str(db))
    conn.executescript(sql)
    conn.execute("PRAGMA user_version = 1")
    conn.execute(
        "INSERT INTO entities ("
        "entity_type, entity_id, frontmatter_json, body_md, "
        "source_doc_ids_json, confidence, status, created_at) "
        "VALUES ('cliente','legacy','{}','','[]',0.5,'pending','2026-01-01T00:00:00+00:00')"
    )
    conn.commit()
    conn.close()

    # Apertura via StateStore: deve migrare a v2 senza errori.
    with StateStore(db) as s:
        assert s.schema_version == SCHEMA_VERSION
        pending = s.list_pending_entities()
        assert len(pending) == 1 and pending[0]["entity_id"] == "legacy"
        cols = {
            row[1]
            for row in s._conn.execute(
                "PRAGMA table_info(review_decisions)"
            ).fetchall()
        }
        assert "previous_frontmatter_json" in cols
