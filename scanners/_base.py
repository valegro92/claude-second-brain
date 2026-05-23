"""Base class e schema per gli scanner. Interfaccia stabile, non modificare senza aggiornare tutti gli scanner concreti."""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator


@dataclass
class FileRecord:
    """Rappresentazione uniforme di un file scoperto da uno scanner, indipendente dalla sorgente."""

    source: str  # "nas", "gdrive", "m365", "email", "server"
    source_id: str  # id univoco nella sorgente (path locale, file id Google, message-id email, ecc.)
    path: str  # path leggibile (ricostruito dalla cartella di origine)
    name: str
    size: int
    mtime: datetime
    mime: str | None = None
    author: str | None = None
    last_modified_by: str | None = None
    permissions: dict[str, Any] | None = None
    sha256: str | None = None
    extras: dict[str, Any] = field(default_factory=dict)
    # campi popolati da fasi successive
    categoria: str | None = None  # vivo | da-consultare | archivio | cestino | da-chiarire
    confidence: float | None = None
    reason: str | None = None
    dedup: dict[str, Any] | None = None  # {"role": "canonical"|"duplicate-of", "canonical": id}

    def to_jsonl(self) -> str:
        """Serializza il record come singola riga JSON (per file JSONL append-only)."""
        d = asdict(self)
        d["mtime"] = self.mtime.isoformat()
        return json.dumps(d, ensure_ascii=False)

    @classmethod
    def from_jsonl(cls, line: str) -> FileRecord:
        d = json.loads(line)
        d["mtime"] = datetime.fromisoformat(d["mtime"])
        return cls(**d)


class Scanner(ABC):
    """Base per uno scanner. Idempotente e resumable.

    Convenzioni:
      - output: ogni record yieldato viene anche appeso a `_status/inventory/<source>.jsonl`
      - resume: lo scanner salva un cursor in `_status/inventory/<source>.cursor` per ripartire
      - perimetro: i filtri include/exclude + size + extension sono applicati internamente
    """

    source_name: str  # override nelle sottoclassi: "nas", "gdrive", ecc.

    def __init__(self, config: dict[str, Any], state_dir: Path) -> None:
        self.config = config
        self.state_dir = state_dir
        self.inventory_dir = state_dir / "inventory"
        self.inventory_dir.mkdir(parents=True, exist_ok=True)
        self.jsonl_path = self.inventory_dir / f"{self.source_name}.jsonl"
        self.cursor_path = self.inventory_dir / f"{self.source_name}.cursor"

    @abstractmethod
    def scan(self) -> Iterator[FileRecord]:
        """Yields FileRecord. Implementazione idempotente e resumable."""
        raise NotImplementedError

    def write_record(self, record: FileRecord) -> None:
        """Appende un record al JSONL della sorgente."""
        with self.jsonl_path.open("a", encoding="utf-8") as f:
            f.write(record.to_jsonl() + "\n")

    def read_cursor(self) -> str | None:
        """Legge il cursor di resume, None se prima esecuzione."""
        if not self.cursor_path.exists():
            return None
        return self.cursor_path.read_text(encoding="utf-8").strip() or None

    def write_cursor(self, cursor: str) -> None:
        self.cursor_path.write_text(cursor, encoding="utf-8")

    def apply_filters(self, record: FileRecord) -> bool:
        """True se il record passa i filtri perimetro globali e specifici."""
        filtri = self.config.get("filtri_globali", {})
        max_mb = filtri.get("max_file_mb", 100)
        if record.size > max_mb * 1024 * 1024:
            return False
        exclude_ext = filtri.get("exclude_extensions", [])
        name_lower = record.name.lower()
        if any(name_lower.endswith(ext.lower()) for ext in exclude_ext):
            return False
        # Filtri perimetro specifici della sorgente (include/exclude paths)
        perimetro = self.config.get("sorgenti", {}).get(self.source_name, {}).get("perimetro", {})
        excludes = perimetro.get("exclude", [])
        if any(ex in record.path for ex in excludes):
            return False
        includes = perimetro.get("include", [])
        if includes and not any(inc in record.path for inc in includes):
            return False
        return True
