-- Custodia state store schema v1 (baseline).
-- Le migrazioni incrementali successive (v1 -> v2 -> ...) sono applicate da
-- StateStore._apply_schema in Python: vedi SCHEMA_VERSION in store.py.
-- Tutte le timestamp sono ISO 8601 UTC stringhe.
-- I campi *_json sono testo serializzato (json.dumps, ensure_ascii=False).

CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    command TEXT NOT NULL,
    args_json TEXT NOT NULL DEFAULT '{}',
    started_at TEXT NOT NULL,
    completed_at TEXT,
    status TEXT NOT NULL DEFAULT 'running',
    summary TEXT NOT NULL DEFAULT ''
);
-- Le colonne progress_json e heartbeat_at sono aggiunte dalla migrazione v3→v4.

CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER,
    source_id TEXT NOT NULL UNIQUE,
    source_path TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    text TEXT NOT NULL DEFAULT '',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES runs(id)
);

CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
CREATE INDEX IF NOT EXISTS idx_documents_mime ON documents(mime_type);

CREATE TABLE IF NOT EXISTS entities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    frontmatter_json TEXT NOT NULL DEFAULT '{}',
    body_md TEXT NOT NULL DEFAULT '',
    source_doc_ids_json TEXT NOT NULL DEFAULT '[]',
    confidence REAL NOT NULL DEFAULT 0.0,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL,
    UNIQUE(entity_type, entity_id)
);

CREATE INDEX IF NOT EXISTS idx_entities_type_status ON entities(entity_type, status);

CREATE TABLE IF NOT EXISTS review_decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_pk INTEGER NOT NULL,
    decision TEXT NOT NULL,
    edited_frontmatter_json TEXT,
    decided_at TEXT NOT NULL,
    FOREIGN KEY (entity_pk) REFERENCES entities(id)
);

CREATE INDEX IF NOT EXISTS idx_review_decisions_entity ON review_decisions(entity_pk);

-- scan_manifest: tracking incrementale (Sprint 2a, U2).
-- La definizione baseline è qui per documentazione; il fresh-install applica
-- comunque ``schema.sql`` (v1) e poi salta a SCHEMA_VERSION corrente via
-- migrazioni Python (vedi StateStore._apply_schema). La migrazione v4→v5
-- crea questa tabella in modo identico.
-- CREATE TABLE IF NOT EXISTS scan_manifest (
--     connector_name TEXT NOT NULL,
--     source_id TEXT NOT NULL,
--     content_hash_sha1_16 BLOB NOT NULL,
--     mtime_iso TEXT NOT NULL,
--     file_size INTEGER NOT NULL,
--     last_seen_run_id INTEGER,
--     first_seen_at TEXT NOT NULL,
--     last_seen_at TEXT NOT NULL,
--     PRIMARY KEY (connector_name, source_id),
--     FOREIGN KEY (last_seen_run_id) REFERENCES runs(id)
-- );
