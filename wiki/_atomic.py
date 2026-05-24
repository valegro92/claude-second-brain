"""Helper per scrittura atomica di file.

Pattern: scrivi su ``<path>.tmp``, fsync, poi ``os.replace`` a ``<path>``.
Se il processo viene ucciso a metà, il file originale resta intatto.

Usato per scritture su:
  - ``_status/audit/decisions.jsonl`` (append-only, ma il rotate uses atomic)
  - ``_status/cost.jsonl``
  - ``_status/inventory/<source>.cursor``
  - bozze in ``_status/drafts/``
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


def atomic_write_text(path: Path, content: str, encoding: str = "utf-8") -> None:
    """Scrive ``content`` in ``path`` atomicamente via tmp+rename.

    Garantisce che ``path`` o contiene il vecchio contenuto, o il nuovo.
    Mai uno stato intermedio.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Scrivi in tmp nella stessa directory (per garantire rename atomico)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding=encoding,
        dir=str(path.parent),
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as tmp:
        tmp.write(content)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_path = Path(tmp.name)
    # Rename atomico sostituisce path
    os.replace(tmp_path, path)


def atomic_write_bytes(path: Path, content: bytes) -> None:
    """Versione binary di ``atomic_write_text``."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="wb",
        dir=str(path.parent),
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as tmp:
        tmp.write(content)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_path = Path(tmp.name)
    os.replace(tmp_path, path)


def atomic_write_json(path: Path, data: Any, indent: int = 2) -> None:
    """Serializza ``data`` come JSON e scrive atomicamente."""
    atomic_write_text(path, json.dumps(data, ensure_ascii=False, indent=indent))


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    """Append di una riga JSON al file. Best-effort atomico (un singolo write).

    Per JSONL append-only il rischio di corruzione parziale è molto basso
    (write di una linea singola con \\n è quasi sempre atomico sui filesystem
    moderni per <4KB). Per garanzia totale, l'alternativa è acquisire un lock
    o usare un sink separato — qui accettiamo il trade-off.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, ensure_ascii=False, default=str) + "\n"
    with path.open("a", encoding="utf-8") as f:
        f.write(line)
        f.flush()
