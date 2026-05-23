"""Orchestratore del categorizer.

Legge tutti gli ``_status/inventory/<source>.jsonl``, applica
:func:`categorizers.rules.classify` a ogni record, raggruppa i
``DA_CHIARIRE`` e li passa a :func:`categorizers.claude.categorize_batch`.
Aggiorna in-place i JSONL inserendo ``categoria``, ``confidence`` e
``reason``. Logga ogni decisione in ``_status/audit/categorize.jsonl``.

Idempotente: re-eseguito non duplica decisioni (riscrive i JSONL,
l'audit log è append-only ma è un log, non uno stato).
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from scanners._base import FileRecord

from categorizers import claude as claude_mod
from categorizers import rules
from categorizers._enums import Categoria

logger = logging.getLogger(__name__)


def _iter_jsonl_files(state_dir: Path) -> list[Path]:
    inv = state_dir / "inventory"
    if not inv.exists():
        return []
    # Ordina per stabilità del log (gdrive, m365, nas...).
    return sorted(p for p in inv.glob("*.jsonl") if not p.name.startswith("_"))


def _load_records(jsonl: Path) -> list[FileRecord]:
    records: list[FileRecord] = []
    with jsonl.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            records.append(FileRecord.from_jsonl(line))
    return records


def _write_records(jsonl: Path, records: Iterable[FileRecord]) -> None:
    """Riscrive il JSONL atomicamente (tmp + rename)."""
    tmp = jsonl.with_suffix(jsonl.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(r.to_jsonl() + "\n")
    tmp.replace(jsonl)


def _append_audit(audit_path: Path, entry: dict[str, Any]) -> None:
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    with audit_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _record_key(r: FileRecord) -> str:
    """Chiave stabile per cross-reference tra batch LLM e record."""
    return r.sha256 or r.source_id


def run_categorization(
    state_dir: Path,
    config: dict[str, Any],
    *,
    client: Any | None = None,
) -> dict[str, Any]:
    """Esegue le due passate del categorizer su tutti i JSONL inventario.

    Args:
        state_dir: cartella ``_status/`` del cliente corrente.
        config: dict caricato da ``bootstrap/clients/<slug>/config.yml``.
            Chiavi rilevanti: ``privacy.modalita`` (``safe``|``full``),
            ``categorizer.model``, ``categorizer.batch_size``.
        client: client Anthropic preconfezionato (utile per i test).

    Returns:
        Dict con statistiche di run (n_total, n_rules, n_llm, per_categoria).
    """
    audit_path = state_dir / "audit" / "categorize.jsonl"
    mode = config.get("privacy", {}).get("modalita", "safe")
    cat_cfg = config.get("categorizer", {})
    model = cat_cfg.get("model", claude_mod.DEFAULT_MODEL)
    batch_size = int(cat_cfg.get("batch_size", claude_mod.DEFAULT_BATCH_SIZE))

    stats: dict[str, Any] = {
        "n_total": 0,
        "n_rules": 0,
        "n_llm": 0,
        "per_categoria": {c.value: 0 for c in Categoria},
        "sources": [],
    }

    jsonl_files = _iter_jsonl_files(state_dir)
    if not jsonl_files:
        logger.warning("Nessun JSONL trovato in %s/inventory", state_dir)
        return stats

    for jsonl in jsonl_files:
        records = _load_records(jsonl)
        stats["n_total"] += len(records)
        stats["sources"].append({"source": jsonl.stem, "n": len(records)})
        # Passata 1: regole su tutto.
        to_llm: list[FileRecord] = []
        for r in records:
            cat, conf, why = rules.classify(r)
            if cat == Categoria.DA_CHIARIRE or conf < rules.LOW_CONFIDENCE_THRESHOLD:
                # Segno intanto come DA_CHIARIRE, poi sovrascrivo se l'LLM decide.
                r.categoria = Categoria.DA_CHIARIRE.value
                r.confidence = conf
                r.reason = "rules: " + why
                to_llm.append(r)
            else:
                r.categoria = cat.value
                r.confidence = conf
                r.reason = "rules: " + why
                stats["n_rules"] += 1
                _append_audit(
                    audit_path,
                    {
                        "ts": datetime.now(timezone.utc).isoformat(),
                        "source": jsonl.stem,
                        "key": _record_key(r),
                        "stage": "rules",
                        "chosen": r.categoria,
                        "conf": r.confidence,
                        "reason": r.reason,
                    },
                )

        # Passata 2: Claude sui DA_CHIARIRE.
        if to_llm:
            logger.info(
                "categorize source=%s: %d → rules / %d → LLM (mode=%s)",
                jsonl.stem,
                stats["n_rules"],
                len(to_llm),
                mode,
            )
            try:
                llm_results = claude_mod.categorize_batch(
                    to_llm,
                    mode=mode,
                    model=model,
                    batch_size=batch_size,
                    state_dir=state_dir,
                    client=client,
                    config=config,
                )
            except Exception as exc:  # pragma: no cover - fail-soft
                logger.exception("Fallita chiamata Claude per %s: %s", jsonl.stem, exc)
                llm_results = []
            # Index per chiave per cross-reference.
            by_key = {entry["sha"]: entry for entry in llm_results}
            for r in to_llm:
                entry = by_key.get(_record_key(r))
                if entry is None:
                    # Modello non ha risposto su questo record: resta DA_CHIARIRE.
                    continue
                r.categoria = entry["cat"]
                r.confidence = float(entry["conf"])
                r.reason = "claude: " + str(entry.get("why", ""))
                stats["n_llm"] += 1
                _append_audit(
                    audit_path,
                    {
                        "ts": datetime.now(timezone.utc).isoformat(),
                        "source": jsonl.stem,
                        "key": _record_key(r),
                        "stage": "claude",
                        "model": model,
                        "chosen": r.categoria,
                        "conf": r.confidence,
                        "reason": r.reason,
                    },
                )

        # Conteggio finale per categoria.
        for r in records:
            cat_val = r.categoria or Categoria.DA_CHIARIRE.value
            stats["per_categoria"][cat_val] = stats["per_categoria"].get(cat_val, 0) + 1
        # Riscrivi il JSONL aggiornato.
        _write_records(jsonl, records)

    logger.info("categorize done: %s", stats)
    return stats


__all__ = ["run_categorization"]
