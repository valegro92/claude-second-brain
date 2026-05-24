"""Post-step di consolidamento: costruisce l'indice ``_by_hash.json``.

Legge tutti i file ``_status/inventory/*.jsonl`` (esclusi cursor) e produce
``_status/inventory/_by_hash.json`` con la mappa::

    {
      "<sha256>": [<record_dict>, <record_dict>, ...],
      ...
    }

Usato dal cantiere RECONCILER per il dedup hash-based. I record senza
``sha256`` (es. file Drive non ancora scaricati) vengono raccolti in una
chiave speciale ``"__missing__"`` per facilitare il follow-up.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from pathlib import Path
from typing import Any

from scanners._base import FileRecord

logger = logging.getLogger(__name__)

INDEX_FILENAME = "_by_hash.json"


def build_hash_index(state_dir: Path) -> dict[str, list[dict[str, Any]]]:
    """Costruisce e scrive l'indice. Ritorna la mappa per uso programmatico."""
    inventory_dir = state_dir / "inventory"
    if not inventory_dir.exists():
        logger.warning("Inventory dir non esiste: %s", inventory_dir)
        return {}

    by_hash: dict[str, list[dict[str, Any]]] = defaultdict(list)
    files_processed = 0
    records_processed = 0
    for jsonl_path in sorted(inventory_dir.glob("*.jsonl")):
        # Skip files che potrebbero non essere inventari (difensivo)
        if jsonl_path.name.startswith("_"):
            continue
        files_processed += 1
        with jsonl_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = FileRecord.from_jsonl(line)
                except (json.JSONDecodeError, TypeError, KeyError) as exc:
                    logger.warning("Riga malformata in %s: %s", jsonl_path, exc)
                    continue
                records_processed += 1
                key = record.sha256 or "__missing__"
                d = json.loads(line)  # serializzazione coerente con jsonl
                by_hash[key].append(d)

    index_path = inventory_dir / INDEX_FILENAME
    index_path.write_text(
        json.dumps(by_hash, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info(
        "Hash index scritto in %s — %d hash unici da %d record (%d file inventory)",
        index_path,
        len(by_hash),
        records_processed,
        files_processed,
    )
    return dict(by_hash)


if __name__ == "__main__":  # pragma: no cover - entry point manuale
    import argparse

    parser = argparse.ArgumentParser(description="Costruisce _by_hash.json")
    parser.add_argument("--state-dir", type=Path, default=Path("_status"))
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    build_hash_index(args.state_dir)
