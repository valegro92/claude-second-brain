"""Gestione persistente dello stato delle bozze in un batch.

Stato di ogni bozza in `_status/drafts/<batch_id>/_state.json`:
mappa draft_name -> {"stato": <StatoBozza>, "edits": <str|None>, "ts": <iso>, "note": <str|None>}.

Il file e' scritto in modo atomico (write -> rename) per evitare corruzione su crash.
"""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from categorizers._enums import StatoBozza

_STATE_FILENAME = "_state.json"

# Lock per accesso concorrente (Flask dev server e' single-thread ma i test
# possono usare il client in parallelo). Una sola istanza per processo basta.
_lock = threading.Lock()


def _state_path(batch_dir: Path) -> Path:
    """Path al file di stato del batch."""
    return batch_dir / _STATE_FILENAME


def load_state(batch_dir: Path) -> dict[str, dict[str, Any]]:
    """Carica lo stato delle bozze dal disco. Ritorna mappa vuota se non esiste."""
    path = _state_path(batch_dir)
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {}
        return data
    except (json.JSONDecodeError, OSError):
        # Stato corrotto: fallback a vuoto, sara' rigenerato al prossimo save.
        return {}


def save_state(batch_dir: Path, state: dict[str, dict[str, Any]]) -> None:
    """Salva lo stato in modo atomico (write su tmp + rename)."""
    path = _state_path(batch_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def get_draft_state(batch_dir: Path, draft_name: str) -> dict[str, Any]:
    """Ritorna lo stato di una singola bozza (default PENDING se non registrato)."""
    state = load_state(batch_dir)
    return state.get(draft_name, {"stato": StatoBozza.PENDING.value, "edits": None, "ts": None, "note": None})


def set_draft_state(
    batch_dir: Path,
    draft_name: str,
    stato: StatoBozza,
    *,
    edits: str | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    """Aggiorna lo stato di una bozza in modo thread-safe e ritorna l'entry aggiornata."""
    with _lock:
        state = load_state(batch_dir)
        entry = state.get(draft_name, {})
        entry["stato"] = stato.value
        entry["ts"] = datetime.now(timezone.utc).isoformat()
        if edits is not None:
            entry["edits"] = edits
        if note is not None:
            entry["note"] = note
        # Mantieni le chiavi minime sempre presenti
        entry.setdefault("edits", None)
        entry.setdefault("note", None)
        state[draft_name] = entry
        save_state(batch_dir, state)
        return entry


def count_by_stato(batch_dir: Path, draft_names: list[str]) -> dict[str, int]:
    """Conta le bozze per stato sull'elenco fornito. Stati assenti = PENDING."""
    state = load_state(batch_dir)
    counts = {s.value: 0 for s in StatoBozza}
    for name in draft_names:
        stato = state.get(name, {}).get("stato", StatoBozza.PENDING.value)
        counts[stato] = counts.get(stato, 0) + 1
    return counts
