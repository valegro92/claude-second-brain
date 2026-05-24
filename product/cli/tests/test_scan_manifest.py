"""
Test del manifest di scansione incrementale (Sprint 2a, U2).

Copre:
- API ``StateStore.manifest_*`` (upsert, lookup_by_source, lookup_by_hash,
  count, clear).
- Migrazione schema v4 → v5: applica su DB pre-esistente, idempotente.
- Vincoli sull'hash a 16 byte (validazione input).
- Foreign key su ``last_seen_run_id``.
- Concorrenza: thread paralleli condividono lo stesso StateStore via RLock.
"""

from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path

import pytest

from custodia_cli.state.store import SCHEMA_VERSION, StateStore


# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------


@pytest.fixture
def store(tmp_path: Path) -> StateStore:
    """StateStore freschissimo su file (no in-memory: vogliamo testare il
    file-based path identico a produzione)."""
    db_path = tmp_path / "state.db"
    return StateStore(db_path)


def _make_hash(seed: int) -> bytes:
    """Helper: 16 byte deterministici da un seed int."""
    return bytes([(seed + i) % 256 for i in range(16)])


# ----------------------------------------------------------------------
# manifest_upsert + manifest_lookup_by_source
# ----------------------------------------------------------------------


def test_manifest_upsert_and_lookup_roundtrip(store: StateStore) -> None:
    """Inserisce una entry e la rileggi by source_id."""
    h = _make_hash(1)
    store.manifest_upsert(
        connector_name="filesystem",
        source_id="fs:abc123",
        content_hash_sha1_16=h,
        mtime_iso="2025-01-01T12:00:00+00:00",
        file_size=4096,
        run_id=None,
    )
    entry = store.manifest_lookup_by_source("filesystem", "fs:abc123")
    assert entry is not None
    assert entry["source_id"] == "fs:abc123"
    assert entry["content_hash"] == h
    assert entry["mtime_iso"] == "2025-01-01T12:00:00+00:00"
    assert entry["file_size"] == 4096
    assert entry["last_seen_run_id"] is None
    assert entry["first_seen_at"] is not None
    assert entry["last_seen_at"] is not None


def test_manifest_lookup_by_source_missing(store: StateStore) -> None:
    """Lookup su (connector, source) inesistente ritorna None."""
    assert store.manifest_lookup_by_source("filesystem", "fs:nope") is None


def test_manifest_lookup_by_source_scoped_by_connector(
    store: StateStore,
) -> None:
    """Entry con stesso source_id ma connector diverso non interferiscono."""
    store.manifest_upsert(
        connector_name="filesystem",
        source_id="x",
        content_hash_sha1_16=_make_hash(1),
        mtime_iso="2025-01-01T00:00:00+00:00",
        file_size=10,
        run_id=None,
    )
    store.manifest_upsert(
        connector_name="google_drive",
        source_id="x",
        content_hash_sha1_16=_make_hash(2),
        mtime_iso="2025-01-02T00:00:00+00:00",
        file_size=20,
        run_id=None,
    )
    fs_entry = store.manifest_lookup_by_source("filesystem", "x")
    gd_entry = store.manifest_lookup_by_source("google_drive", "x")
    assert fs_entry is not None and gd_entry is not None
    assert fs_entry["content_hash"] != gd_entry["content_hash"]
    assert fs_entry["file_size"] == 10
    assert gd_entry["file_size"] == 20


def test_manifest_upsert_updates_existing(store: StateStore) -> None:
    """Il secondo upsert sovrascrive hash/mtime/size ma preserva first_seen_at."""
    h1 = _make_hash(1)
    h2 = _make_hash(2)
    store.manifest_upsert(
        connector_name="filesystem",
        source_id="fs:foo",
        content_hash_sha1_16=h1,
        mtime_iso="2025-01-01T00:00:00+00:00",
        file_size=100,
        run_id=None,
    )
    first = store.manifest_lookup_by_source("filesystem", "fs:foo")
    assert first is not None
    first_seen_initial = first["first_seen_at"]

    # piccola pausa per garantire timestamp diversi
    time.sleep(0.01)

    store.manifest_upsert(
        connector_name="filesystem",
        source_id="fs:foo",
        content_hash_sha1_16=h2,
        mtime_iso="2025-02-01T00:00:00+00:00",
        file_size=200,
        run_id=None,
    )
    second = store.manifest_lookup_by_source("filesystem", "fs:foo")
    assert second is not None
    assert second["content_hash"] == h2
    assert second["mtime_iso"] == "2025-02-01T00:00:00+00:00"
    assert second["file_size"] == 200
    # first_seen_at è preservato
    assert second["first_seen_at"] == first_seen_initial
    # last_seen_at è aggiornato
    assert second["last_seen_at"] >= first["last_seen_at"]


# ----------------------------------------------------------------------
# manifest_lookup_by_hash
# ----------------------------------------------------------------------


def test_manifest_lookup_by_hash_finds_renamed_file(store: StateStore) -> None:
    """Stesso content_hash, source_id diverso → ritorna l'entry originale.

    Use case: file rinominato/spostato fra due scan.
    """
    h = _make_hash(42)
    store.manifest_upsert(
        connector_name="filesystem",
        source_id="fs:original_path_id",
        content_hash_sha1_16=h,
        mtime_iso="2025-01-01T00:00:00+00:00",
        file_size=1024,
        run_id=None,
    )
    hit = store.manifest_lookup_by_hash("filesystem", h)
    assert hit is not None
    assert hit["source_id"] == "fs:original_path_id"


def test_manifest_lookup_by_hash_validates_length(store: StateStore) -> None:
    """Hash non-16-byte solleva ValueError."""
    with pytest.raises(ValueError, match="16 byte"):
        store.manifest_lookup_by_hash("filesystem", b"too_short")
    with pytest.raises(ValueError, match="16 byte"):
        store.manifest_lookup_by_hash("filesystem", b"x" * 32)


def test_manifest_upsert_validates_hash_length(store: StateStore) -> None:
    """Upsert con hash di lunghezza errata solleva ValueError."""
    with pytest.raises(ValueError, match="16 byte"):
        store.manifest_upsert(
            connector_name="filesystem",
            source_id="x",
            content_hash_sha1_16=b"too_short",
            mtime_iso="2025-01-01T00:00:00+00:00",
            file_size=100,
            run_id=None,
        )


def test_manifest_upsert_validates_hash_type(store: StateStore) -> None:
    """Upsert con hash non-bytes (str) solleva TypeError."""
    with pytest.raises(TypeError, match="bytes"):
        store.manifest_upsert(
            connector_name="filesystem",
            source_id="x",
            content_hash_sha1_16="not_bytes",  # type: ignore[arg-type]
            mtime_iso="2025-01-01T00:00:00+00:00",
            file_size=100,
            run_id=None,
        )


# ----------------------------------------------------------------------
# manifest_count + manifest_clear
# ----------------------------------------------------------------------


def test_manifest_count_with_and_without_filter(store: StateStore) -> None:
    """count totale vs count filtrato per connector."""
    for i in range(3):
        store.manifest_upsert(
            connector_name="filesystem",
            source_id=f"fs:{i}",
            content_hash_sha1_16=_make_hash(i),
            mtime_iso="2025-01-01T00:00:00+00:00",
            file_size=10,
            run_id=None,
        )
    for i in range(2):
        store.manifest_upsert(
            connector_name="google_drive",
            source_id=f"gd:{i}",
            content_hash_sha1_16=_make_hash(i + 100),
            mtime_iso="2025-01-01T00:00:00+00:00",
            file_size=10,
            run_id=None,
        )
    assert store.manifest_count() == 5
    assert store.manifest_count("filesystem") == 3
    assert store.manifest_count("google_drive") == 2
    assert store.manifest_count("outlook") == 0


def test_manifest_clear_by_connector(store: StateStore) -> None:
    """clear con filter rimuove solo le entry di quel connector."""
    store.manifest_upsert(
        connector_name="filesystem",
        source_id="a",
        content_hash_sha1_16=_make_hash(1),
        mtime_iso="2025-01-01T00:00:00+00:00",
        file_size=10,
        run_id=None,
    )
    store.manifest_upsert(
        connector_name="google_drive",
        source_id="b",
        content_hash_sha1_16=_make_hash(2),
        mtime_iso="2025-01-01T00:00:00+00:00",
        file_size=10,
        run_id=None,
    )
    n = store.manifest_clear("filesystem")
    assert n == 1
    assert store.manifest_count() == 1
    assert store.manifest_count("filesystem") == 0
    assert store.manifest_count("google_drive") == 1


def test_manifest_clear_all(store: StateStore) -> None:
    """clear senza filter rimuove tutto."""
    for i in range(5):
        store.manifest_upsert(
            connector_name="filesystem",
            source_id=f"x{i}",
            content_hash_sha1_16=_make_hash(i),
            mtime_iso="2025-01-01T00:00:00+00:00",
            file_size=10,
            run_id=None,
        )
    n = store.manifest_clear()
    assert n == 5
    assert store.manifest_count() == 0


# ----------------------------------------------------------------------
# Foreign key su run_id
# ----------------------------------------------------------------------


def test_manifest_run_id_foreign_key(store: StateStore) -> None:
    """Upsert con run_id che esiste OK; con run_id orfano solleva IntegrityError."""
    run_id = store.register_run(command="test", args={})
    # Valid run_id: OK
    store.manifest_upsert(
        connector_name="filesystem",
        source_id="x",
        content_hash_sha1_16=_make_hash(1),
        mtime_iso="2025-01-01T00:00:00+00:00",
        file_size=10,
        run_id=run_id,
    )
    entry = store.manifest_lookup_by_source("filesystem", "x")
    assert entry is not None
    assert entry["last_seen_run_id"] == run_id

    # run_id inesistente: SQLite con foreign_keys=ON solleva IntegrityError
    with pytest.raises(sqlite3.IntegrityError):
        store.manifest_upsert(
            connector_name="filesystem",
            source_id="y",
            content_hash_sha1_16=_make_hash(2),
            mtime_iso="2025-01-01T00:00:00+00:00",
            file_size=10,
            run_id=99999,
        )


def test_manifest_run_id_none_is_accepted(store: StateStore) -> None:
    """run_id=None è esplicitamente permesso (backfill manuale, debug)."""
    store.manifest_upsert(
        connector_name="filesystem",
        source_id="x",
        content_hash_sha1_16=_make_hash(1),
        mtime_iso="2025-01-01T00:00:00+00:00",
        file_size=10,
        run_id=None,
    )  # no exception


# ----------------------------------------------------------------------
# Migrazione v4 → v5
# ----------------------------------------------------------------------


def test_migration_creates_table_and_index(tmp_path: Path) -> None:
    """Aprire un DB nuovo applica tutte le migrazioni fino a v5.

    Verifica che la tabella scan_manifest e l'indice esistano.
    """
    db_path = tmp_path / "fresh.db"
    store = StateStore(db_path)
    assert store.schema_version == SCHEMA_VERSION
    assert SCHEMA_VERSION >= 5

    tables = {
        r["name"]
        for r in store._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    assert "scan_manifest" in tables

    indexes = {
        r["name"]
        for r in store._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index'"
        ).fetchall()
    }
    assert "idx_scan_manifest_hash" in indexes


def test_migration_idempotent(tmp_path: Path) -> None:
    """Riaprire un DB v5 esistente non rompe nulla."""
    db_path = tmp_path / "double.db"
    store1 = StateStore(db_path)
    store1.manifest_upsert(
        connector_name="filesystem",
        source_id="x",
        content_hash_sha1_16=_make_hash(1),
        mtime_iso="2025-01-01T00:00:00+00:00",
        file_size=10,
        run_id=None,
    )
    store1.close()

    store2 = StateStore(db_path)
    assert store2.schema_version == SCHEMA_VERSION
    entry = store2.manifest_lookup_by_source("filesystem", "x")
    assert entry is not None
    store2.close()


def test_migration_from_v4(tmp_path: Path) -> None:
    """DB con user_version=4 manualmente: apertura applica solo la migrazione
    v4→v5, NON ri-esegue le precedenti."""
    db_path = tmp_path / "from_v4.db"
    # Boot via StateStore (porta a v5), poi facciamo finta di essere a v4.
    store = StateStore(db_path)
    # Cancella la tabella e abbassa user_version a 4.
    store._conn.execute("DROP TABLE IF EXISTS scan_manifest")
    store._conn.execute("DROP INDEX IF EXISTS idx_scan_manifest_hash")
    store._conn.execute("PRAGMA user_version = 4")
    store._conn.commit()
    store.close()

    # Riapri: migration v4→v5 deve ricreare la tabella.
    store2 = StateStore(db_path)
    assert store2.schema_version == 5
    # La tabella è di nuovo lì.
    store2.manifest_upsert(
        connector_name="filesystem",
        source_id="x",
        content_hash_sha1_16=_make_hash(1),
        mtime_iso="2025-01-01T00:00:00+00:00",
        file_size=10,
        run_id=None,
    )
    assert store2.manifest_count() == 1
    store2.close()


# ----------------------------------------------------------------------
# Concorrenza (RLock)
# ----------------------------------------------------------------------


def test_concurrent_upsert_no_race(store: StateStore) -> None:
    """10 thread inseriscono entry distinte in parallelo: nessuna race."""
    errors: list[BaseException] = []

    def worker(i: int) -> None:
        try:
            store.manifest_upsert(
                connector_name="filesystem",
                source_id=f"fs:thread_{i}",
                content_hash_sha1_16=_make_hash(i),
                mtime_iso="2025-01-01T00:00:00+00:00",
                file_size=i * 100,
                run_id=None,
            )
            entry = store.manifest_lookup_by_source(
                "filesystem", f"fs:thread_{i}"
            )
            assert entry is not None
            assert entry["file_size"] == i * 100
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"Race condition: {errors}"
    assert store.manifest_count("filesystem") == 10
