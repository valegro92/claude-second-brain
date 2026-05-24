"""
FakeLLMProvider: provider deterministico per test offline.

Legge un file YAML di canned responses. Ad ogni chiamata cerca il primo prefix
che matcha la concatenazione di system + last_message.content e ritorna la
response associata. Solleva KeyError diagnostico se nessun prefix matcha.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from custodia_cli.llm.base import LLMUsage, Message, ModelTier, now_iso


class FakeLLMProvider:
    """
    Provider fake che legge response pre-registrate da un file YAML.

    Schema YAML atteso:
        responses:
          - match_prefix: "stringa da matchare come prefix"
            operation: complete | extract_structured
            response: "stringa" oppure {dict}
            tokens_in: 100
            tokens_out: 50

    Comportamento:
    - Concatena `system + "\\n" + messages[-1].content` per matchare i prefix.
    - Ritorna il primo match in ordine di file.
    - Logga sempre in usage_log.
    - Solleva KeyError diagnostico se nessun prefix matcha (utile per test).
    """

    name: str = "fake"

    def __init__(self, fixture_path: str | Path) -> None:
        """Carica il file YAML di fixture. Solleva FileNotFoundError se non esiste."""
        path = Path(fixture_path)
        if not path.is_file():
            raise FileNotFoundError(f"Fixture YAML non trovata: {path}")
        with path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        self._responses: list[dict[str, Any]] = list(data.get("responses", []))
        self.usage_log: list[LLMUsage] = []
        self._fixture_path: Path = path

    def _build_match_key(self, system: str, messages: list[Message]) -> str:
        """Concatena system e ultimo content per cercare match_prefix."""
        last_content = messages[-1].content if messages else ""
        if system:
            return f"{system}\n{last_content}"
        return last_content

    def _find(self, key: str, operation: str) -> dict[str, Any]:
        """Cerca la prima response con match_prefix prefisso di key e operation coerente."""
        for entry in self._responses:
            prefix = entry.get("match_prefix", "")
            op = entry.get("operation", "complete")
            if op != operation:
                continue
            if key.startswith(prefix):
                return entry
        available = [
            entry.get("match_prefix", "")[:50]
            for entry in self._responses
            if entry.get("operation", "complete") == operation
        ]
        raise KeyError(
            f"FakeLLMProvider: nessuna response per operation={operation!r} "
            f"con prefix matching su key={key[:120]!r} (fixture={self._fixture_path}). "
            f"Prefix disponibili per questa operation: {available}"
        )

    def _log(self, entry: dict[str, Any], operation: str, model: str = "fake-model") -> None:
        """Appende un record LLMUsage prendendo tokens dalla fixture (default 0)."""
        self.usage_log.append(
            LLMUsage(
                provider=self.name,
                model=model,
                input_tokens=int(entry.get("tokens_in", 0)),
                output_tokens=int(entry.get("tokens_out", 0)),
                cost_eur_estimate=0.0,
                operation=operation,
                timestamp=now_iso(),
            )
        )

    def complete(
        self,
        messages: list[Message],
        *,
        system: str = "",
        tier: ModelTier = ModelTier.SMART,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> str:
        """Ritorna la response stringa dal primo match. KeyError se nessun match."""
        if not messages:
            raise ValueError("FakeLLMProvider.complete: messages non puo' essere vuoto.")
        key = self._build_match_key(system, messages)
        entry = self._find(key, operation="complete")
        self._log(entry, operation="complete")
        response = entry.get("response", "")
        if not isinstance(response, str):
            raise TypeError(
                f"FakeLLMProvider.complete: response deve essere str, ricevuto {type(response).__name__}"
            )
        return response

    def extract_structured(
        self,
        messages: list[Message],
        *,
        schema: dict,
        system: str = "",
        tier: ModelTier = ModelTier.SMART,
    ) -> dict:
        """Ritorna la response dict dal primo match. KeyError se nessun match."""
        if not messages:
            raise ValueError(
                "FakeLLMProvider.extract_structured: messages non puo' essere vuoto."
            )
        key = self._build_match_key(system, messages)
        entry = self._find(key, operation="extract_structured")
        self._log(entry, operation="extract_structured")
        response = entry.get("response", {})
        if not isinstance(response, dict):
            raise TypeError(
                f"FakeLLMProvider.extract_structured: response deve essere dict, "
                f"ricevuto {type(response).__name__}"
            )
        return response

    def count_tokens(self, text: str) -> int:
        """Stima costante via len//4. Non logga per evitare rumore nei test."""
        return max(1, len(text) // 4)
