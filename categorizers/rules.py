"""Passata 1 del categorizer: regole euristiche deterministiche.

Idea (vedi `_brief/04-step-2-tech-plan.md`, sezione 4.1): score per ognuna
delle 5 categorie a partire da segnali leggibili (età, naming, path,
dimensione). Se il punteggio della categoria vincente è >= 0.7 il file viene
considerato "regola-deciso" e non passa al modello LLM. Se < 0.5 finisce
fra i ``DA_CHIARIRE`` da passare a Claude.

Le soglie restano costanti modulo e sono importate dal pipeline.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime

from categorizers._enums import Categoria
from scanners._base import FileRecord

# ----------------------------------------------------------------- soglie
# Cutoff confidence per dire "regola sicura, niente Claude".
HIGH_CONFIDENCE_THRESHOLD: float = 0.7
# Sotto questa soglia il record entra nella coda LLM.
LOW_CONFIDENCE_THRESHOLD: float = 0.5

# ------------------------------------------------------------ segnali base
# Naming che tipicamente indica scarto o ridondanza.
_RED_FLAG_NAMING: tuple[str, ...] = (
    "copia di",
    "copia di copia",
    "copy of",
    "untitled",
    "senza titolo",
    "nuovo documento",
    "_old",
    ".bak",
    ".tmp",
    "~$",  # lock file Office
)

# Token di path che gridano "archivio storico".
_ARCHIVE_PATH_TOKENS: tuple[str, ...] = (
    "_archivio",
    "/archivio",
    "vecchio",
    "vecchi",
    "old/",
    "_old",
    "_old_",
    "/backup",
    "_backup",
    "backup_2",  # Backup_2022/, Backup_2021/
    "storico",
    "obsoleto",
    "non_usare",
    "non usare",
    "_da_eliminare",
)

# Token di path che gridano "roba viva, operativa".
_LIVE_PATH_TOKENS: tuple[str, ...] = (
    "/attivi",
    "/aperti",
    "/in-corso",
    "/in_corso",
    "/wip",
    "/vivi",
    "/commerciale",
    # Pattern italiani PMI: cartelle operative ricorrenti
    "/clienti/",
    "/fornitori/",
    "/offerte/",
    "/ordini/",
    "/fatture/",
    "/ddt/",
    "/comunicazioni/",
    "/preventivi/",
    "/commesse/",
    "/progetti/",
)

# Token di path che indicano riferimenti permanenti (DA_CONSULTARE).
_CONSULT_PATH_TOKENS: tuple[str, ...] = (
    "/contratti/",
    "/listini/",
    "/manuali/",
    "/modelli/",
    "/templates/",
    "/documenti/",
    "/normativa/",
    "/normative/",
    "/policies/",
    "/policy/",
    "/procedure/",
    "/riferimenti/",
    "/references/",
    "/anagrafica/",
    "/anagrafiche/",
)

# Pattern naming italiano "documento di business" (forte segnale che NON e' rumore).
# Combinato con eta' recente -> VIVO, eta' vecchia -> ARCHIVIO.
_BUSINESS_NAME_TOKENS: tuple[str, ...] = (
    "fattura",
    "fatture",
    "fattura_",
    "ddt",
    "ddt_",
    "offerta",
    "offerta_",
    "preventivo",
    "preventivo_",
    "conferma_ordine",
    "conferma-ordine",
    "ordine_",
    "contratto",
    "contratto_",
    "listino",
    "listino_",
    "manuale",
    "manuale_",
    "anagrafica",
    "anagrafica_",
    "contatti",
    "scheda_cliente",
    "scheda_fornitore",
    "riepilogo",
    "report",
    "relazione",
    "comunicazione",
    "perizia",
    "verbale",
)


def _now() -> datetime:
    """Wrappa ``datetime.now`` per essere mockabile nei test."""
    return datetime.now(UTC)


def _age_days(mtime: datetime) -> int:
    """Età del file in giorni, robusta a mtime naive/aware."""
    now = _now()
    if mtime.tzinfo is None:
        mtime = mtime.replace(tzinfo=UTC)
    delta = now - mtime
    return max(delta.days, 0)


def _bump(scores: dict[Categoria, float], cat: Categoria, delta: float) -> None:
    """Incrementa con clamp a [0, 1]."""
    scores[cat] = min(1.0, max(0.0, scores[cat] + delta))


def score(record: FileRecord) -> dict[Categoria, float]:
    """Calcola gli score per ognuna delle 5 categorie su un singolo record.

    Restituisce un dict con un valore in [0, 1] per ogni :class:`Categoria`.
    Tutti i segnali sono additivi e poi clampati, in modo che l'aggiunta di
    una nuova regola non possa "esplodere" oltre 1.
    """
    scores: dict[Categoria, float] = dict.fromkeys(Categoria, 0.0)

    # --- segnale 1: età ---------------------------------------------------
    age = _age_days(record.mtime)
    if age < 90:
        _bump(scores, Categoria.VIVO, 0.6)
    elif age < 365:
        _bump(scores, Categoria.VIVO, 0.3)
        _bump(scores, Categoria.DA_CONSULTARE, 0.3)
    elif age < 1095:  # ~3 anni
        _bump(scores, Categoria.DA_CONSULTARE, 0.4)
        _bump(scores, Categoria.ARCHIVIO, 0.3)
    else:
        _bump(scores, Categoria.ARCHIVIO, 0.6)

    # --- segnale 2: naming red-flag --------------------------------------
    name_lower = (record.name or "").lower()
    if any(pat in name_lower for pat in _RED_FLAG_NAMING):
        _bump(scores, Categoria.CESTINO, 0.5)
    # Lock file di Office non sono mai contenuto utile.
    if name_lower.startswith("~$"):
        _bump(scores, Categoria.CESTINO, 0.5)

    # --- segnale 3: path keyword -----------------------------------------
    path_lower = (record.path or "").lower()
    if any(tok in path_lower for tok in _ARCHIVE_PATH_TOKENS):
        _bump(scores, Categoria.ARCHIVIO, 0.7)
    if any(tok in path_lower for tok in _LIVE_PATH_TOKENS):
        _bump(scores, Categoria.VIVO, 0.4)
    if any(tok in path_lower for tok in _CONSULT_PATH_TOKENS):
        _bump(scores, Categoria.DA_CONSULTARE, 0.5)
    # Cestino vero e proprio: segnale fortissimo.
    if "/cestino" in path_lower or path_lower.startswith("cestino/") or "/trash" in path_lower:
        _bump(scores, Categoria.CESTINO, 0.9)

    # --- segnale 5: naming business italiano + eta' ----------------------
    # Documenti di business con nome riconoscibile rinforzano la categoria
    # gia' suggerita dall'eta' (no override, solo bump per uscire dal DA_CHIARIRE).
    if any(tok in name_lower for tok in _BUSINESS_NAME_TOKENS):
        if age < 365:
            _bump(scores, Categoria.VIVO, 0.3)
        elif age < 1095:
            _bump(scores, Categoria.DA_CONSULTARE, 0.3)
        else:
            _bump(scores, Categoria.ARCHIVIO, 0.3)

    # --- segnale 4: dimensione anomala -----------------------------------
    # File zero-byte: quasi sempre placeholder o residui.
    if record.size == 0:
        _bump(scores, Categoria.CESTINO, 0.4)
    # File giganteschi (>200MB) in PMI: di solito export una tantum o video.
    if record.size > 200 * 1024 * 1024:
        _bump(scores, Categoria.DA_CHIARIRE, 0.3)

    return scores


def classify(record: FileRecord) -> tuple[Categoria, float, str]:
    """Restituisce ``(categoria_vincente, confidence, reason)``.

    La logica di routing è:
      * confidence >= ``HIGH_CONFIDENCE_THRESHOLD`` → categoria scelta
        direttamente, niente LLM.
      * confidence < ``LOW_CONFIDENCE_THRESHOLD`` → categoria forzata a
        ``DA_CHIARIRE``: deciderà il modello in passata 2.
      * in mezzo → ritorniamo la vincente ma il chiamante può decidere
        se inviarla comunque al modello.
    """
    scores = score(record)
    winner, conf = max(scores.items(), key=lambda kv: kv[1])
    reasons: list[str] = []
    age = _age_days(record.mtime)
    reasons.append(f"age={age}d")
    name_lower = (record.name or "").lower()
    if any(pat in name_lower for pat in _RED_FLAG_NAMING):
        reasons.append("naming-red-flag")
    path_lower = (record.path or "").lower()
    if any(tok in path_lower for tok in _ARCHIVE_PATH_TOKENS):
        reasons.append("path=archivio")
    if any(tok in path_lower for tok in _LIVE_PATH_TOKENS):
        reasons.append("path=vivo")
    if record.size == 0:
        reasons.append("size=0")

    if conf < LOW_CONFIDENCE_THRESHOLD:
        return Categoria.DA_CHIARIRE, conf, "no-rule-decisive: " + ",".join(reasons)
    return winner, conf, ",".join(reasons)


def needs_llm(record: FileRecord) -> bool:
    """True se il record va passato alla passata 2 (Claude).

    Comodità: la pipeline può chiamare ``classify`` ma poi capita di voler
    sapere a colpo d'occhio "questo l'hai mandato a Claude o no?".
    """
    cat, conf, _ = classify(record)
    return cat == Categoria.DA_CHIARIRE or conf < LOW_CONFIDENCE_THRESHOLD


def classify_many(records: Iterable[FileRecord]) -> list[tuple[FileRecord, Categoria, float, str]]:
    """Helper batch: applica :func:`classify` su un iterabile."""
    out: list[tuple[FileRecord, Categoria, float, str]] = []
    for r in records:
        cat, conf, why = classify(r)
        out.append((r, cat, conf, why))
    return out
