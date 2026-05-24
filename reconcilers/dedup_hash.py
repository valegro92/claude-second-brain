"""Dedup per hash binario.

Vedi brief sezione 5.1.

Legge ``_status/inventory/_by_hash.json`` prodotto da
``scanners/dedup_index.py`` e per ogni gruppo con > 1 record sceglie un
"canonical" e marca gli altri come duplicati. Aggiorna i JSONL di
inventario in-place inserendo il campo ``dedup``.

Priorità di sorgente per scegliere il canonical (più alto vince):
``gdrive > m365 > nas > email-attachment > server > email``. A parità
di sorgente vince ``mtime`` più recente.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from scanners._base import FileRecord

logger = logging.getLogger(__name__)


# Più alto = preferito come canonical.
SOURCE_PRIORITY: dict[str, int] = {
    "gdrive": 50,
    "m365": 40,
    "nas": 30,
    "email-attachment": 20,
    "server": 15,
    "email": 10,
}


def _priority(source: str) -> int:
    return SOURCE_PRIORITY.get(source, 0)


def _record_id(r: FileRecord) -> str:
    """ID stabile di un record (combinazione source + source_id)."""
    return f"{r.source}:{r.source_id}"


def _load_by_hash(state_dir: Path) -> dict[str, list[dict[str, Any]]]:
    path = state_dir / "inventory" / "_by_hash.json"
    if not path.exists():
        logger.warning("_by_hash.json mancante in %s", path)
        return {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _load_jsonl(jsonl: Path) -> list[FileRecord]:
    records: list[FileRecord] = []
    with jsonl.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            records.append(FileRecord.from_jsonl(line))
    return records


def _write_jsonl(jsonl: Path, records: Iterable[FileRecord]) -> None:
    tmp = jsonl.with_suffix(jsonl.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(r.to_jsonl() + "\n")
    tmp.replace(jsonl)


def _choose_canonical(refs: list[dict[str, Any]]) -> dict[str, Any]:
    """Sceglie il canonical da una lista di reference (dict da _by_hash.json).

    Ogni reference deve avere almeno ``source``, ``source_id``, ``mtime``.
    """

    def key(ref: dict[str, Any]) -> tuple[int, str]:
        return (_priority(ref.get("source", "")), str(ref.get("mtime", "")))

    return max(refs, key=key)


def _index_records_by_id(jsonl_files: list[Path]) -> dict[str, tuple[Path, FileRecord]]:
    """Mappa record_id → (jsonl_di_origine, FileRecord)."""
    index: dict[str, tuple[Path, FileRecord]] = {}
    for jsonl in jsonl_files:
        for r in _load_jsonl(jsonl):
            index[_record_id(r)] = (jsonl, r)
    return index


def apply_dedup_groups(
    by_hash: dict[str, list[dict[str, Any]]],
    state_dir: Path,
) -> dict[str, Any]:
    """Applica le decisioni di dedup ai JSONL di inventario.

    Pure function di alto livello: utile da chiamare in test passando un
    ``by_hash`` sintetico.
    """
    inv = state_dir / "inventory"
    jsonl_files = sorted(p for p in inv.glob("*.jsonl") if not p.name.startswith("_"))
    if not jsonl_files:
        logger.warning("Nessun JSONL inventario in %s", inv)
        return {"n_groups": 0, "n_duplicates": 0, "n_canonical": 0}

    index = _index_records_by_id(jsonl_files)
    n_groups = 0
    n_duplicates = 0
    n_canonical = 0

    for sha, refs in by_hash.items():
        if not isinstance(refs, list) or len(refs) <= 1:
            continue
        n_groups += 1
        canonical_ref = _choose_canonical(refs)
        canonical_id = f"{canonical_ref.get('source')}:{canonical_ref.get('source_id')}"
        sibling_ids = [
            f"{r.get('source')}:{r.get('source_id')}"
            for r in refs
            if f"{r.get('source')}:{r.get('source_id')}" != canonical_id
        ]
        for ref in refs:
            rid = f"{ref.get('source')}:{ref.get('source_id')}"
            target = index.get(rid)
            if target is None:
                logger.debug("Record %s in _by_hash ma non in inventory", rid)
                continue
            _, record = target
            if rid == canonical_id:
                record.dedup = {
                    "role": "canonical",
                    "canonical": None,
                    "siblings": sibling_ids,
                    "sha256": sha,
                }
                n_canonical += 1
            else:
                record.dedup = {
                    "role": "duplicate-of",
                    "canonical": canonical_id,
                    "siblings": [],
                    "sha256": sha,
                }
                n_duplicates += 1

    # Raggruppa i record per jsonl di origine e riscrivi.
    by_file: dict[Path, list[FileRecord]] = {}
    for jsonl, record in index.values():
        by_file.setdefault(jsonl, []).append(record)
    for jsonl, records in by_file.items():
        _write_jsonl(jsonl, records)

    stats = {
        "n_groups": n_groups,
        "n_duplicates": n_duplicates,
        "n_canonical": n_canonical,
    }
    logger.info("dedup_hash done: %s", stats)
    return stats


def run_dedup_hash(state_dir: Path) -> dict[str, Any]:
    """Entry point: carica ``_by_hash.json`` e applica le decisioni."""
    by_hash = _load_by_hash(state_dir)
    return apply_dedup_groups(by_hash, state_dir)


__all__ = [
    "SOURCE_PRIORITY",
    "apply_dedup_groups",
    "run_dedup_hash",
]
