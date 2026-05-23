"""Dedup "soft" basato su naming pattern (vedi brief 5.2).

Riconosce pattern come ``_v1``, ``_FINAL``, ``copia di``, ``(2)`` e raggruppa
i file che condividono lo stesso ``parent_path`` e la stessa "base
normalizzata". Non auto-applica: produce una bozza di decisione in
``_status/drafts/<batch-id>/dedup-soft-<n>.md`` che Valentino approva via UI.

Algoritmo:
  1. Per ogni record calcola ``(parent_path, base_normalizzata, ext)``
  2. Cluster: stesso parent + stessa base + stessa ext.
  3. Cluster con > 1 record producono una bozza con tabella ``CANONICAL``
     candidato (mtime più recente vince) + lista candidati da scartare.
"""
from __future__ import annotations

import logging
import re
from collections import defaultdict
from pathlib import Path
from typing import Iterable

from scanners._base import FileRecord

logger = logging.getLogger(__name__)


# Pattern di soft-dup, applicati alla parte di nome senza estensione.
# `re.IGNORECASE` ovunque.
SOFT_DUP_PATTERNS: list[re.Pattern[str]] = [
    # "nome copia", "nome copia (2)", "nome copy of", "Copia di nome"
    re.compile(r"^(?P<base>.+?)[\s_-]*(?:copia(?:\s+di)?|copy(?:\s+of)?)(?:[\s_-]*\(?(?P<n>\d+)\)?)?$", re.I),
    re.compile(r"^copia\s+di\s+(?P<base>.+)$", re.I),
    # "nome v1", "nome_v12", "nome-V003"
    re.compile(r"^(?P<base>.+?)[\s_-]*v(?P<n>\d+)$", re.I),
    # "nome FINAL", "nome_definitivo", "nome-def"
    re.compile(r"^(?P<base>.+?)[\s_-]+(?:final|finale|definitivo|def)$", re.I),
    # "nome (2)", "nome (12)"
    re.compile(r"^(?P<base>.+?)[\s_-]*\((?P<n>\d+)\)$", re.I),
]


def _split_ext(name: str) -> tuple[str, str]:
    """Restituisce (stem, ext_con_punto). Niente ext → ext stringa vuota."""
    if "." not in name:
        return name, ""
    dot = name.rfind(".")
    return name[:dot], name[dot:].lower()


def normalize_base(name: str) -> tuple[str, bool]:
    """Restituisce ``(base_canonica, era_soft_dup)``.

    Riconosce i pattern :data:`SOFT_DUP_PATTERNS` e ritorna la base "pulita".
    Se nessun pattern matcha, ritorna ``(stem, False)``.
    """
    stem, _ext = _split_ext(name)
    candidate = stem.strip()
    matched = False
    # Applica pattern in loop finché qualcuno matcha (es. "nome_v2_FINAL").
    for _ in range(5):
        for pattern in SOFT_DUP_PATTERNS:
            m = pattern.match(candidate)
            if m:
                base = m.group("base").strip(" _-")
                if base and base != candidate:
                    candidate = base
                    matched = True
                    break
        else:
            break
    # Normalizza spazi e case per matching.
    return candidate.lower().strip(" _-"), matched


def _parent_path(path: str) -> str:
    """Estrae la cartella padre da un path POSIX-like."""
    p = path.replace("\\", "/")
    if "/" not in p:
        return ""
    return p.rsplit("/", 1)[0]


def cluster_soft_dups(records: Iterable[FileRecord]) -> list[list[FileRecord]]:
    """Raggruppa i record per (parent_path, base_normalizzata, ext).

    Ritorna solo i cluster con > 1 record.
    """
    buckets: dict[tuple[str, str, str], list[FileRecord]] = defaultdict(list)
    for r in records:
        base, matched = normalize_base(r.name)
        _stem, ext = _split_ext(r.name)
        parent = _parent_path(r.path)
        if not matched:
            # Anche senza pattern, può esserci un cluster (3 file con stesso nome
            # in cartelle diverse non ci interessa; stesso nome stessa cartella
            # è impossibile su filesystem ma succede cross-source).
            base = base or _stem.lower()
        buckets[(parent, base, ext)].append(r)
    return [grp for grp in buckets.values() if len(grp) > 1]


def _pick_canonical(group: list[FileRecord]) -> FileRecord:
    """Mtime più recente vince. Tiebreak: nome più corto."""
    return max(group, key=lambda r: (r.mtime, -len(r.name)))


def _render_decision(batch_id: str, idx: int, group: list[FileRecord]) -> str:
    """Genera il markdown della bozza-decisione per un cluster."""
    canonical = _pick_canonical(group)
    lines = [
        "---",
        "tipo: decisione-dedup-soft",
        f"batch: {batch_id}",
        f"index: {idx:03d}",
        "stato: bozza-generata-da-scandagliamento",
        f"n-candidati: {len(group)}",
        "---",
        "",
        f"# Dedup soft #{idx:03d} — {len(group)} file simili",
        "",
        "## Cluster",
        "",
        f"- Cartella: `{_parent_path(canonical.path) or '/'}`",
        f"- Base normalizzata: `{normalize_base(canonical.name)[0]}`",
        "",
        "## Proposta",
        "",
        f"Canonical: `{canonical.name}` (mtime {canonical.mtime.isoformat()},"
        f" source `{canonical.source}`)",
        "",
        "| Ruolo | Nome | Source | Mtime | Size |",
        "|---|---|---|---|---|",
    ]
    for r in sorted(group, key=lambda x: x.name):
        role = "CANONICAL" if r is canonical else "candidato-archivio"
        lines.append(
            f"| {role} | `{r.name}` | {r.source} | {r.mtime.isoformat()} | {r.size} |"
        )
    lines.extend(
        [
            "",
            "## Decisione richiesta",
            "",
            "- [ ] **approva**: mantieni canonical, sposta gli altri in `_archivio/`",
            "- [ ] **rifiuta**: sono tutti file distinti, nessun dedup",
            "- [ ] **modifica**: scegli un altro canonical e specifica sotto",
            "",
            "## Note",
            "",
            "TODO Valentino: rivedere prima di flush.",
        ]
    )
    return "\n".join(lines) + "\n"


def run_dedup_soft(state_dir: Path, batch_id: str) -> dict[str, int]:
    """Esegue il dedup soft su tutti i JSONL inventario.

    Produce una bozza per cluster in
    ``_status/drafts/<batch_id>/dedup-soft-<n>.md``.

    Returns:
        Statistiche: ``{n_clusters, n_files}``.
    """
    inv = state_dir / "inventory"
    if not inv.exists():
        logger.warning("Nessun inventory in %s", inv)
        return {"n_clusters": 0, "n_files": 0}

    all_records: list[FileRecord] = []
    for jsonl in inv.glob("*.jsonl"):
        if jsonl.name.startswith("_"):
            continue
        with jsonl.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                all_records.append(FileRecord.from_jsonl(line))

    clusters = cluster_soft_dups(all_records)
    drafts_dir = state_dir / "drafts" / batch_id
    drafts_dir.mkdir(parents=True, exist_ok=True)
    for idx, group in enumerate(clusters, start=1):
        path = drafts_dir / f"dedup-soft-{idx:03d}.md"
        path.write_text(_render_decision(batch_id, idx, group), encoding="utf-8")

    stats = {"n_clusters": len(clusters), "n_files": sum(len(g) for g in clusters)}
    logger.info("dedup_soft done: %s drafts in %s", stats, drafts_dir)
    return stats


__all__ = [
    "SOFT_DUP_PATTERNS",
    "normalize_base",
    "cluster_soft_dups",
    "run_dedup_soft",
]
