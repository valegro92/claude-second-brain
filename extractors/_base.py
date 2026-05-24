"""Base class e schema per gli extractor. Interfaccia stabile."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ExtractionResult:
    """Output uniforme di un extractor."""

    markdown: str  # contenuto principale come markdown
    metadata: dict[str, Any] = field(default_factory=dict)  # extracted-specific
    warnings: list[str] = field(default_factory=list)
    quality: float = 1.0  # 0.0-1.0 self-assessment


class Extractor(ABC):
    """Base per un extractor.

    Convenzioni:
      - input: path al file locale (lo scanner si occupa del download per le sorgenti cloud)
      - output: ExtractionResult salvato su `_status/extracted/<sha12>/main.md` + meta.json + _warnings.log
    """

    name: str  # override: "pdf", "docx", "xlsx", "eml", "plain", "pdf_ocr"
    mimes: list[str] = []  # mime types gestiti, override nelle sottoclassi
    extensions: list[str] = []  # estensioni gestite (con il punto: ".pdf")

    @abstractmethod
    def extract(self, file_path: Path) -> ExtractionResult:
        raise NotImplementedError

    @classmethod
    def write_extraction(
        cls, result: ExtractionResult, state_dir: Path, sha256: str, source_record: dict[str, Any]
    ) -> Path:
        """Salva l'estrazione in `_status/extracted/<sha12>/`. Ritorna la cartella creata."""
        sha12 = sha256[:12]
        out_dir = state_dir / "extracted" / sha12
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "main.md").write_text(result.markdown, encoding="utf-8")
        (out_dir / "meta.json").write_text(
            json.dumps(
                {"metadata": result.metadata, "quality": result.quality},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        (out_dir / "source.json").write_text(
            json.dumps(source_record, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
        )
        if result.warnings:
            (out_dir / "_warnings.log").write_text("\n".join(result.warnings), encoding="utf-8")
        return out_dir
