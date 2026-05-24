"""
StateStore: wrapper SQLite per lo stato persistente del CLI Custodia.

Lo stato vive in `<vault_parent>/.custodia-state/state.db`. Contiene:
- runs: audit trail invocazioni CLI
- documents: SourceDocument prodotti dai connettori (U3/U4)
- entities: EntityCandidate prodotti dall'extractor (U5)
- review_decisions: scelte human-in-the-loop (U6)
"""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 5

_SCHEMA_PATH = Path(__file__).parent / "schema.sql"


class StateStoreCorruptionError(RuntimeError):
    """Sollevata quando una colonna `_json` contiene JSON malformato/illeggibile.

    Indica corruzione fisica del DB o manomissione esterna: il chiamante deve
    decidere se interrompere il run o ripristinare il backup.
    """


def _now_iso() -> str:
    """Timestamp ISO 8601 UTC."""
    return datetime.now(timezone.utc).isoformat()


def _dump_json(value: Any) -> str:
    """Serializza in JSON conservando caratteri unicode."""
    return json.dumps(value, ensure_ascii=False)


def _load_json(
    text: str | None,
    *,
    field: str,
    row_id: int | None = None,
) -> Any:
    """Deserializza JSON da SQLite. Ritorna ``None`` se text è ``None``/vuoto.

    In caso di JSON malformato solleva :class:`StateStoreCorruptionError`
    citando il campo, il row id e i primi 80 caratteri del valore offending.
    """
    if text is None or text == "":
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        snippet = text[:80].replace("\n", "\\n")
        raise StateStoreCorruptionError(
            "JSON malformato in colonna "
            f"{field!r} (row_id={row_id}): {exc.msg} — valore: {snippet!r}"
        ) from exc


class StateStore:
    """Wrapper sincrono attorno a una connessione SQLite per lo stato CLI."""

    def __init__(self, db_path: str | Path) -> None:
        """
        Apre (o crea) il database all'`db_path` indicato.

        Args:
            db_path: path al file SQLite, oppure ":memory:" per database in-memory.
        """
        self.db_path: str | Path = db_path
        if isinstance(db_path, Path):
            db_path.parent.mkdir(parents=True, exist_ok=True)
            connection_target = str(db_path)
        else:
            connection_target = db_path

        # check_same_thread=False permette l'uso della stessa connessione da
        # worker thread del JobRunner. La serializzazione delle transazioni è
        # garantita da SQLite (BEGIN IMMEDIATE) + dal pattern ``with self._conn``
        # usato in tutti i metodi di scrittura.
        self._conn = sqlite3.connect(connection_target, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        # RLock serializza l'accesso alla connessione fra worker thread del
        # JobRunner. Reentrant per permettere a un metodo che già detiene il
        # lock di chiamarne un altro internamente.
        self._lock = threading.RLock()
        self._apply_schema()

    @property
    def schema_version(self) -> int:
        """Versione corrente dello schema applicato sul DB aperto."""
        cur = self._conn.execute("PRAGMA user_version")
        return int(cur.fetchone()[0])

    def _apply_schema(self) -> None:
        """Applica `schema.sql` e le migrazioni incrementali fino a SCHEMA_VERSION.

        Idempotente: rilegge ``user_version`` ad ogni open e applica solo le
        migrazioni mancanti. Solleva ``RuntimeError`` se trova una versione
        sconosciuta (>SCHEMA_VERSION).
        """
        current_version = int(
            self._conn.execute("PRAGMA user_version").fetchone()[0]
        )
        if current_version == SCHEMA_VERSION:
            return
        if current_version > SCHEMA_VERSION:
            raise RuntimeError(
                "Schema state store incompatibile: "
                f"user_version={current_version}, atteso {SCHEMA_VERSION}. "
                "DB scritto da una versione più recente di Custodia."
            )

        # Da 0 → applica lo schema base (v1).
        if current_version == 0:
            sql_text = _SCHEMA_PATH.read_text(encoding="utf-8")
            with self._conn:
                self._conn.executescript(sql_text)
                self._conn.execute("PRAGMA user_version = 1")
            current_version = 1

        # 1 → 2: aggiunge previous_frontmatter_json a review_decisions.
        if current_version == 1 and SCHEMA_VERSION >= 2:
            with self._conn:
                self._conn.execute(
                    "ALTER TABLE review_decisions "
                    "ADD COLUMN previous_frontmatter_json TEXT"
                )
                self._conn.execute("PRAGMA user_version = 2")
            current_version = 2

        # 2 → 3: aggiunge written_at a entities per tracciare write idempotente.
        if current_version == 2 and SCHEMA_VERSION >= 3:
            with self._conn:
                self._conn.execute(
                    "ALTER TABLE entities ADD COLUMN written_at TEXT"
                )
                self._conn.execute("PRAGMA user_version = 3")
            current_version = 3

        # 3 → 4: aggiunge progress_json e heartbeat_at a runs per supportare
        # JobRunner / ProgressReporter (Sprint 2a, U1).
        if current_version == 3 and SCHEMA_VERSION >= 4:
            with self._conn:
                self._conn.execute(
                    "ALTER TABLE runs ADD COLUMN progress_json TEXT DEFAULT NULL"
                )
                self._conn.execute(
                    "ALTER TABLE runs ADD COLUMN heartbeat_at TEXT DEFAULT NULL"
                )
                self._conn.execute("PRAGMA user_version = 4")
            current_version = 4

        # 4 → 5: aggiunge tabella scan_manifest per incremental scan
        # (Sprint 2a, U2). PK composta (connector_name, source_id) scoped per
        # connettore così filesystem/google_drive/outlook restano isolati.
        # ``content_hash_sha1_16`` è SHA1 troncato a 16 byte (128 bit) sui primi
        # 1MB del file: sufficiente per change-detection senza esplodere lo
        # storage. ``last_seen_run_id`` permette audit (quale run ha visto X).
        if current_version == 4 and SCHEMA_VERSION >= 5:
            with self._conn:
                self._conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS scan_manifest (
                        connector_name TEXT NOT NULL,
                        source_id TEXT NOT NULL,
                        content_hash_sha1_16 BLOB NOT NULL,
                        mtime_iso TEXT NOT NULL,
                        file_size INTEGER NOT NULL,
                        last_seen_run_id INTEGER,
                        first_seen_at TEXT NOT NULL,
                        last_seen_at TEXT NOT NULL,
                        PRIMARY KEY (connector_name, source_id),
                        FOREIGN KEY (last_seen_run_id) REFERENCES runs(id)
                    )
                    """
                )
                self._conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_scan_manifest_hash
                    ON scan_manifest(connector_name, content_hash_sha1_16)
                    """
                )
                self._conn.execute("PRAGMA user_version = 5")
            current_version = 5

        if current_version != SCHEMA_VERSION:
            raise RuntimeError(
                "Schema state store incompatibile: nessuna migrazione "
                f"disponibile da v{current_version} a v{SCHEMA_VERSION}."
            )

    def close(self) -> None:
        """Chiude la connessione SQLite."""
        self._conn.close()

    def __enter__(self) -> StateStore:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    # ------------------------------------------------------------------
    # documents
    # ------------------------------------------------------------------

    def add_document(
        self,
        *,
        source_id: str,
        source_path: str,
        mime_type: str,
        text: str,
        metadata: dict[str, Any] | None = None,
        run_id: int | None = None,
        status: str = "pending",
    ) -> int:
        """
        Inserisce un documento. `source_id` è univoco: re-inserire lo stesso
        source_id solleva `sqlite3.IntegrityError`.

        Returns:
            la primary key del documento appena inserito.
        """
        with self._conn:
            cur = self._conn.execute(
                """
                INSERT INTO documents (
                    run_id, source_id, source_path, mime_type, text,
                    metadata_json, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    source_id,
                    source_path,
                    mime_type,
                    text,
                    _dump_json(metadata or {}),
                    status,
                    _now_iso(),
                ),
            )
        return int(cur.lastrowid)

    def list_documents(
        self,
        *,
        status: str | None = None,
        mime_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Lista documenti filtrati per status e/o mime_type."""
        clauses: list[str] = []
        params: list[Any] = []
        if status is not None:
            clauses.append("status = ?")
            params.append(status)
        if mime_type is not None:
            clauses.append("mime_type = ?")
            params.append(mime_type)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self._conn.execute(
            f"SELECT * FROM documents {where} ORDER BY id ASC",
            params,
        ).fetchall()
        return [self._document_row_to_dict(r) for r in rows]

    @staticmethod
    def _document_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
        metadata = _load_json(
            row["metadata_json"], field="metadata_json", row_id=row["id"]
        )
        return {
            "id": row["id"],
            "run_id": row["run_id"],
            "source_id": row["source_id"],
            "source_path": row["source_path"],
            "mime_type": row["mime_type"],
            "text": row["text"],
            "metadata": metadata if metadata is not None else {},
            "status": row["status"],
            "created_at": row["created_at"],
        }

    # ------------------------------------------------------------------
    # entities
    # ------------------------------------------------------------------

    def upsert_entity(
        self,
        *,
        entity_type: str,
        entity_id: str,
        frontmatter: dict[str, Any],
        body_md: str,
        source_doc_ids: list[int],
        confidence: float,
        status: str = "pending",
    ) -> int:
        """
        Inserisce o aggiorna una entity (`UNIQUE(entity_type, entity_id)`).

        Implementato come singolo ``INSERT ... ON CONFLICT DO UPDATE`` atomico:
        elimina la race condition fra SELECT iniziale e UPDATE/INSERT. In caso
        di update mantiene la primary key esistente, ``created_at`` e
        ``entity_type/entity_id`` originali; sovrascrive tutti gli altri campi.

        Returns:
            la primary key della entity (consistente fra insert e update grazie
            a ``RETURNING id``).
        """
        now = _now_iso()
        with self._conn:
            cur = self._conn.execute(
                """
                INSERT INTO entities (
                    entity_type, entity_id, frontmatter_json, body_md,
                    source_doc_ids_json, confidence, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(entity_type, entity_id) DO UPDATE SET
                    frontmatter_json = excluded.frontmatter_json,
                    body_md = excluded.body_md,
                    source_doc_ids_json = excluded.source_doc_ids_json,
                    confidence = excluded.confidence,
                    status = excluded.status
                RETURNING id
                """,
                (
                    entity_type,
                    entity_id,
                    _dump_json(frontmatter),
                    body_md,
                    _dump_json(source_doc_ids),
                    float(confidence),
                    status,
                    now,
                ),
            )
            row = cur.fetchone()
            return int(row["id"])

    def list_pending_entities(
        self,
        entity_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Lista entity con `status='pending'`, eventualmente filtrate per tipo."""
        clauses = ["status = 'pending'"]
        params: list[Any] = []
        if entity_type is not None:
            clauses.append("entity_type = ?")
            params.append(entity_type)
        where = f"WHERE {' AND '.join(clauses)}"
        rows = self._conn.execute(
            f"SELECT * FROM entities {where} ORDER BY id ASC",
            params,
        ).fetchall()
        return [self._entity_row_to_dict(r) for r in rows]

    @staticmethod
    def _entity_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
        frontmatter = _load_json(
            row["frontmatter_json"], field="frontmatter_json", row_id=row["id"]
        )
        source_doc_ids = _load_json(
            row["source_doc_ids_json"],
            field="source_doc_ids_json",
            row_id=row["id"],
        )
        # ``written_at`` esiste solo da schema v3+; usiamo .keys() per evitare
        # KeyError se un test apre un row in contesti pre-migrazione.
        keys = row.keys() if hasattr(row, "keys") else []
        written_at = row["written_at"] if "written_at" in keys else None
        return {
            "id": row["id"],
            "entity_type": row["entity_type"],
            "entity_id": row["entity_id"],
            "frontmatter": frontmatter if frontmatter is not None else {},
            "body_md": row["body_md"],
            "source_doc_ids": source_doc_ids if source_doc_ids is not None else [],
            "confidence": row["confidence"],
            "status": row["status"],
            "created_at": row["created_at"],
            "written_at": written_at,
        }

    # ------------------------------------------------------------------
    # review decisions
    # ------------------------------------------------------------------

    def record_review_decision(
        self,
        *,
        entity_pk: int,
        decision: str,
        edited_frontmatter: dict[str, Any] | None = None,
    ) -> None:
        """
        Registra una decisione di review e aggiorna lo `status` della entity.

        Decisioni attese: ``"approved"``, ``"rejected"``, ``"edited"``. Per
        ``"edited"`` sovrascrive anche il frontmatter dell'entity con
        ``edited_frontmatter`` e preserva il frontmatter pre-edit nella
        colonna ``review_decisions.previous_frontmatter_json``, garantendo
        history completa per audit/rollback.
        """
        if decision not in {"approved", "rejected", "edited"}:
            raise ValueError(
                f"decision deve essere 'approved'|'rejected'|'edited', ricevuto {decision!r}"
            )
        with self._conn:
            entity_row = self._conn.execute(
                "SELECT id, frontmatter_json FROM entities WHERE id = ?",
                (entity_pk,),
            ).fetchone()
            if entity_row is None:
                raise ValueError(f"entity_pk {entity_pk} non esiste")

            previous_frontmatter_text: str | None = None
            if decision == "edited":
                # Snapshot del frontmatter prima dell'edit, conservato così com'è
                # (testo grezzo) per fedeltà massima.
                previous_frontmatter_text = entity_row["frontmatter_json"]

            self._conn.execute(
                """
                INSERT INTO review_decisions (
                    entity_pk, decision, edited_frontmatter_json,
                    previous_frontmatter_json, decided_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    entity_pk,
                    decision,
                    _dump_json(edited_frontmatter) if edited_frontmatter is not None else None,
                    previous_frontmatter_text,
                    _now_iso(),
                ),
            )

            if decision == "approved":
                self._conn.execute(
                    "UPDATE entities SET status = 'approved' WHERE id = ?",
                    (entity_pk,),
                )
            elif decision == "rejected":
                self._conn.execute(
                    "UPDATE entities SET status = 'rejected' WHERE id = ?",
                    (entity_pk,),
                )
            elif decision == "edited":
                if edited_frontmatter is None:
                    raise ValueError("decision='edited' richiede edited_frontmatter")
                self._conn.execute(
                    """
                    UPDATE entities SET
                        frontmatter_json = ?,
                        status = 'approved'
                    WHERE id = ?
                    """,
                    (_dump_json(edited_frontmatter), entity_pk),
                )

    def list_pending_writes(self) -> list[dict[str, Any]]:
        """Entity approvate ma non ancora scritte nel vault.

        Filtra ``status='approved' AND written_at IS NULL``: una entity scritta
        viene marcata via :meth:`mark_entity_written` e non riappare nella lista
        ai successivi `custodia write`, rendendo l'operazione idempotente.
        """
        rows = self._conn.execute(
            "SELECT * FROM entities "
            "WHERE status = 'approved' AND written_at IS NULL "
            "ORDER BY id ASC"
        ).fetchall()
        return [self._entity_row_to_dict(r) for r in rows]

    def mark_entity_written(self, entity_pk: int) -> None:
        """Marca un'entity come scritta al vault (set ``written_at``).

        Idempotente: una seconda chiamata aggiorna il timestamp ma non rompe
        nulla. Solleva ``ValueError`` se ``entity_pk`` non esiste.
        """
        with self._conn:
            result = self._conn.execute(
                "UPDATE entities SET written_at = ? WHERE id = ?",
                (_now_iso(), entity_pk),
            )
            if result.rowcount == 0:
                raise ValueError(f"entity_pk {entity_pk} non esiste")

    # ------------------------------------------------------------------
    # runs
    # ------------------------------------------------------------------

    def register_run(self, *, command: str, args: dict[str, Any]) -> int:
        """Registra l'inizio di un run e ritorna il `run_id`."""
        with self._lock, self._conn:
            cur = self._conn.execute(
                """
                INSERT INTO runs (command, args_json, started_at, status)
                VALUES (?, ?, ?, 'running')
                """,
                (command, _dump_json(args), _now_iso()),
            )
        return int(cur.lastrowid)

    def complete_run(
        self,
        run_id: int,
        *,
        status: str,
        summary: str = "",
    ) -> None:
        """Marca un run come completato con `status` finale e summary opzionale."""
        if status not in {"success", "error", "partial"}:
            raise ValueError(
                f"status deve essere 'success'|'error'|'partial', ricevuto {status!r}"
            )
        with self._lock, self._conn:
            result = self._conn.execute(
                """
                UPDATE runs SET
                    completed_at = ?,
                    status = ?,
                    summary = ?
                WHERE id = ?
                """,
                (_now_iso(), status, summary, run_id),
            )
            if result.rowcount == 0:
                raise ValueError(f"run_id {run_id} non esiste")

    # ------------------------------------------------------------------
    # progress / heartbeat (Sprint 2a, U1)
    # ------------------------------------------------------------------

    def update_run_progress(self, run_id: int, payload: dict[str, Any]) -> None:
        """Aggiorna ``progress_json`` e ``heartbeat_at`` di un run.

        Non valida lo schema del payload: è responsabilità del chiamante
        (tipicamente :class:`ProgressReporter`) costruire un dict serializzabile.
        Idempotente: scrivere più volte sovrascrive senza errori.

        Solleva ``ValueError`` se ``run_id`` non esiste.
        """
        with self._lock, self._conn:
            result = self._conn.execute(
                """
                UPDATE runs SET
                    progress_json = ?,
                    heartbeat_at = ?
                WHERE id = ?
                """,
                (_dump_json(payload), _now_iso(), run_id),
            )
            if result.rowcount == 0:
                raise ValueError(f"run_id {run_id} non esiste")

    def get_run_progress(self, run_id: int) -> dict[str, Any] | None:
        """Ritorna lo snapshot di progresso di un run.

        Forma del dict ritornato::

            {
                "status": "running" | "success" | ...,   # da runs.status
                "progress": {...payload...} | None,       # da progress_json
                "heartbeat_at": "ISO-8601" | None,
                "started_at": "ISO-8601",
                "completed_at": "ISO-8601" | None,
            }

        Ritorna ``None`` se ``run_id`` non esiste.
        """
        with self._lock:
            row = self._conn.execute(
                "SELECT id, status, progress_json, heartbeat_at, started_at, "
                "completed_at FROM runs WHERE id = ?",
                (run_id,),
            ).fetchone()
        if row is None:
            return None
        progress = _load_json(
            row["progress_json"], field="progress_json", row_id=row["id"]
        )
        return {
            "status": row["status"],
            "progress": progress,
            "heartbeat_at": row["heartbeat_at"],
            "started_at": row["started_at"],
            "completed_at": row["completed_at"],
        }

    def mark_run_heartbeat(self, run_id: int) -> None:
        """Aggiorna solo ``heartbeat_at`` di un run, senza toccare progress.

        Pensato per i casi in cui il job sta facendo I/O lento e non ha
        cambiamenti di stato da pubblicare, ma deve segnalare "sono vivo".
        Solleva ``ValueError`` se ``run_id`` non esiste.
        """
        with self._lock, self._conn:
            result = self._conn.execute(
                "UPDATE runs SET heartbeat_at = ? WHERE id = ?",
                (_now_iso(), run_id),
            )
            if result.rowcount == 0:
                raise ValueError(f"run_id {run_id} non esiste")

    # ------------------------------------------------------------------
    # scan manifest (Sprint 2a, U2)
    # ------------------------------------------------------------------

    def manifest_lookup_by_source(
        self,
        connector_name: str,
        source_id: str,
    ) -> dict[str, Any] | None:
        """Lookup manifest entry per (connector_name, source_id).

        Ritorna ``None`` se non esiste, altrimenti dict con:
        ``{content_hash, mtime_iso, file_size, last_seen_run_id,
        first_seen_at, last_seen_at}``.
        """
        with self._lock:
            row = self._conn.execute(
                """
                SELECT connector_name, source_id, content_hash_sha1_16,
                       mtime_iso, file_size, last_seen_run_id,
                       first_seen_at, last_seen_at
                FROM scan_manifest
                WHERE connector_name = ? AND source_id = ?
                """,
                (connector_name, source_id),
            ).fetchone()
        if row is None:
            return None
        return {
            "connector_name": row["connector_name"],
            "source_id": row["source_id"],
            "content_hash": bytes(row["content_hash_sha1_16"]),
            "mtime_iso": row["mtime_iso"],
            "file_size": int(row["file_size"]),
            "last_seen_run_id": row["last_seen_run_id"],
            "first_seen_at": row["first_seen_at"],
            "last_seen_at": row["last_seen_at"],
        }

    def manifest_lookup_by_hash(
        self,
        connector_name: str,
        content_hash_sha1_16: bytes,
    ) -> dict[str, Any] | None:
        """Lookup manifest entry per (connector_name, content_hash).

        Utile per detection di file rinominati/spostati: stesso hash, source_id
        diverso. Ritorna il PRIMO match (in caso di collisioni, comunque
        astronomicamente improbabili con 128 bit).
        """
        if not isinstance(content_hash_sha1_16, (bytes, bytearray)):
            raise TypeError("content_hash_sha1_16 deve essere bytes")
        if len(content_hash_sha1_16) != 16:
            raise ValueError(
                f"content_hash_sha1_16 deve essere 16 byte, "
                f"ricevuto {len(content_hash_sha1_16)}"
            )
        with self._lock:
            row = self._conn.execute(
                """
                SELECT connector_name, source_id, content_hash_sha1_16,
                       mtime_iso, file_size, last_seen_run_id,
                       first_seen_at, last_seen_at
                FROM scan_manifest
                WHERE connector_name = ? AND content_hash_sha1_16 = ?
                LIMIT 1
                """,
                (connector_name, bytes(content_hash_sha1_16)),
            ).fetchone()
        if row is None:
            return None
        return {
            "connector_name": row["connector_name"],
            "source_id": row["source_id"],
            "content_hash": bytes(row["content_hash_sha1_16"]),
            "mtime_iso": row["mtime_iso"],
            "file_size": int(row["file_size"]),
            "last_seen_run_id": row["last_seen_run_id"],
            "first_seen_at": row["first_seen_at"],
            "last_seen_at": row["last_seen_at"],
        }

    def manifest_upsert(
        self,
        *,
        connector_name: str,
        source_id: str,
        content_hash_sha1_16: bytes,
        mtime_iso: str,
        file_size: int,
        run_id: int | None,
    ) -> None:
        """Inserisce o aggiorna una entry manifest.

        Su update preserva ``first_seen_at`` (timestamp del primo scan che ha
        visto il file) e aggiorna ``last_seen_at`` + ``last_seen_run_id`` +
        eventuali metadata (hash, mtime, size). Sempre atomic via
        ``INSERT ... ON CONFLICT DO UPDATE``.
        """
        if not isinstance(content_hash_sha1_16, (bytes, bytearray)):
            raise TypeError("content_hash_sha1_16 deve essere bytes")
        if len(content_hash_sha1_16) != 16:
            raise ValueError(
                f"content_hash_sha1_16 deve essere 16 byte, "
                f"ricevuto {len(content_hash_sha1_16)}"
            )
        now = _now_iso()
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO scan_manifest (
                    connector_name, source_id, content_hash_sha1_16,
                    mtime_iso, file_size, last_seen_run_id,
                    first_seen_at, last_seen_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(connector_name, source_id) DO UPDATE SET
                    content_hash_sha1_16 = excluded.content_hash_sha1_16,
                    mtime_iso = excluded.mtime_iso,
                    file_size = excluded.file_size,
                    last_seen_run_id = excluded.last_seen_run_id,
                    last_seen_at = excluded.last_seen_at
                """,
                (
                    connector_name,
                    source_id,
                    bytes(content_hash_sha1_16),
                    mtime_iso,
                    int(file_size),
                    run_id,
                    now,
                    now,
                ),
            )

    def manifest_count(self, connector_name: str | None = None) -> int:
        """Conta entry nel manifest, opzionalmente filtrate per connector."""
        with self._lock:
            if connector_name is None:
                row = self._conn.execute(
                    "SELECT COUNT(*) AS n FROM scan_manifest"
                ).fetchone()
            else:
                row = self._conn.execute(
                    "SELECT COUNT(*) AS n FROM scan_manifest "
                    "WHERE connector_name = ?",
                    (connector_name,),
                ).fetchone()
        return int(row["n"])

    def manifest_clear(self, connector_name: str | None = None) -> int:
        """Cancella entry manifest. Ritorna n. righe cancellate.

        Utile per ``--force-rescan`` o per pulizia post-rename connector.
        """
        with self._lock, self._conn:
            if connector_name is None:
                result = self._conn.execute("DELETE FROM scan_manifest")
            else:
                result = self._conn.execute(
                    "DELETE FROM scan_manifest WHERE connector_name = ?",
                    (connector_name,),
                )
        return int(result.rowcount)

    def find_interrupted_runs(
        self, threshold_minutes: int = 5
    ) -> list[dict[str, Any]]:
        """Trova run con ``status='running'`` e heartbeat scaduto.

        Usa SQLite ``datetime()`` per il confronto temporale: ``heartbeat_at``
        è memorizzato come ISO 8601 e accetta il formato direttamente.
        Include anche run con ``heartbeat_at IS NULL`` solo se ``started_at``
        è più vecchio della soglia (run iniziato e mai più aggiornato).

        Include ``args`` (dict deserializzato da ``args_json``) e
        ``progress`` (deserializzato da ``progress_json``, può essere None)
        per permettere al chiamante di mostrare un banner "Riprendi" con
        contesto e di rilanciare lo scan con gli stessi parametri.
        """
        cutoff_expr = f"datetime('now', '-{int(threshold_minutes)} minutes')"
        with self._lock:
            rows = self._conn.execute(
                f"""
                SELECT id, command, args_json, progress_json,
                       started_at, heartbeat_at
                FROM runs
                WHERE status = 'running' AND (
                    (heartbeat_at IS NOT NULL AND datetime(heartbeat_at) < {cutoff_expr})
                    OR (heartbeat_at IS NULL AND datetime(started_at) < {cutoff_expr})
                )
                ORDER BY id ASC
                """
            ).fetchall()
        result: list[dict[str, Any]] = []
        for r in rows:
            args = _load_json(r["args_json"], field="args_json", row_id=r["id"])
            progress = _load_json(
                r["progress_json"], field="progress_json", row_id=r["id"]
            )
            result.append(
                {
                    "id": r["id"],
                    "command": r["command"],
                    "args": args if args is not None else {},
                    "progress": progress,
                    "started_at": r["started_at"],
                    "heartbeat_at": r["heartbeat_at"],
                }
            )
        return result

    def get_run_args(self, run_id: int) -> dict[str, Any] | None:
        """Ritorna gli argomenti registrati per un run (``args_json``).

        Ritorna ``None`` se il ``run_id`` non esiste. Solleva
        :class:`StateStoreCorruptionError` se ``args_json`` è malformato.
        """
        with self._lock:
            row = self._conn.execute(
                "SELECT id, args_json FROM runs WHERE id = ?",
                (run_id,),
            ).fetchone()
        if row is None:
            return None
        args = _load_json(row["args_json"], field="args_json", row_id=row["id"])
        return args if args is not None else {}
