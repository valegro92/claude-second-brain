"""
Chunking dei SourceDocument lunghi per restare sotto il context limit LLM.

Strategia conservativa (D5 del piano Sprint 1):
- Documento sotto soglia → 1 chunk unico.
- Documento sopra soglia → split per marker noti dei parser custodia:
    * "--- Pagina N ---" (PDF, da `parsers/pdf.py`)
    * "## Sheet: <nome>" (XLSX, da `parsers/xlsx.py`)
    * "## Header:" (XLSX header sezione)
- Fallback: split per paragrafi (linea vuota).

Stima token: usa `provider.count_tokens` se disponibile, altrimenti `len//4`.
Meglio chunk leggermente sotto soglia che chunk al limite (D5 motiva conservativo).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Protocol


class _TokenCounter(Protocol):
    """Subset minimale del Protocol LLMProvider utile al chunker."""

    def count_tokens(self, text: str) -> int: ...


@dataclass(frozen=True)
class Chunk:
    """Pezzo di documento pronto per essere inviato all'LLM.

    Attributes:
        text: testo del chunk.
        source_doc_id: PK del documento sorgente nello StateStore.
        chunk_index: indice 0-based del chunk dentro il documento.
        metadata: campi extra (page_range, sheet_name, ...) per debug.
    """

    text: str
    source_doc_id: int
    chunk_index: int
    metadata: dict[str, Any] = field(default_factory=dict)


# Marker noti prodotti dai parser di Custodia.
_PAGE_MARKER_RE = re.compile(r"\n\n--- Pagina \d+ ---\n", re.MULTILINE)
_SHEET_MARKER_RE = re.compile(r"\n\n## Sheet:.*?\n", re.MULTILINE)
_HEADER_MARKER_RE = re.compile(r"\n\n## Header:.*?\n", re.MULTILINE)

# Limite teorico di sicurezza per chunk. 50k token ≈ 200k char con tokenizer
# Anthropic, lasciando ~150k token di headroom dentro context window 200k.
DEFAULT_MAX_TOKENS: int = 50_000


def _estimate_tokens(text: str, counter: _TokenCounter | None) -> int:
    """Conta token via provider, fallback `len(text) // 4`."""
    if counter is not None:
        try:
            return counter.count_tokens(text)
        except Exception:  # noqa: BLE001 — fallback sempre disponibile
            pass
    return max(1, len(text) // 4)


def _split_by_marker(text: str, regex: re.Pattern[str]) -> list[str]:
    """Split mantenendo il marker associato al pezzo che SEGUE.

    Esempio: "intro\\n\\n--- Pagina 1 ---\\nA\\n\\n--- Pagina 2 ---\\nB"
    →  ["intro", "--- Pagina 1 ---\\nA", "--- Pagina 2 ---\\nB"]
    """
    matches = list(regex.finditer(text))
    if not matches:
        return [text]
    parts: list[str] = []
    # Pre-marker (se presente).
    first = matches[0]
    pre = text[: first.start()].strip()
    if pre:
        parts.append(pre)
    # Per ogni marker: dal contenuto del marker fino al prossimo (escluso).
    for i, m in enumerate(matches):
        start = m.start() + 2  # salta i due \n iniziali del marker
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        chunk = text[start:end].strip()
        if chunk:
            parts.append(chunk)
    return parts


def _split_by_paragraphs(text: str, max_chars: int) -> list[str]:
    """Split a paragrafi (linea vuota) accumulando fino a max_chars per blob."""
    paragraphs = re.split(r"\n\s*\n", text)
    blobs: list[str] = []
    buf: list[str] = []
    buf_size = 0
    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
        if buf_size + len(p) > max_chars and buf:
            blobs.append("\n\n".join(buf))
            buf = [p]
            buf_size = len(p)
        else:
            buf.append(p)
            buf_size += len(p) + 2
    if buf:
        blobs.append("\n\n".join(buf))
    return blobs


def chunk_document(
    *,
    source_doc_id: int,
    text: str,
    mime_type: str = "",
    max_tokens: int = DEFAULT_MAX_TOKENS,
    token_counter: _TokenCounter | None = None,
) -> list[Chunk]:
    """Spezza un documento in chunk sotto soglia.

    Args:
        source_doc_id: PK del documento nello StateStore (per linkare la fonte).
        text: testo grezzo del documento.
        mime_type: hint MIME (informativo per metadata, non altera la logica).
        max_tokens: budget token per chunk.
        token_counter: oggetto con `count_tokens(str) -> int` per stima precisa.

    Returns:
        Lista di Chunk con indice incrementale a partire da 0. Lista vuota se
        il testo è interamente whitespace.
    """
    if not text or not text.strip():
        return []

    total = _estimate_tokens(text, token_counter)
    if total <= max_tokens:
        return [
            Chunk(
                text=text,
                source_doc_id=source_doc_id,
                chunk_index=0,
                metadata={"strategy": "single", "tokens_estimate": total},
            )
        ]

    # Stima conservativa: max_tokens → ~ max_tokens * 4 char.
    max_chars = max_tokens * 4

    # Prova in cascata: pagine → sheet → header → paragrafi.
    page_parts = _split_by_marker(text, _PAGE_MARKER_RE)
    if len(page_parts) > 1:
        return _group_under_budget(
            parts=page_parts,
            source_doc_id=source_doc_id,
            max_chars=max_chars,
            strategy="pages",
        )

    sheet_parts = _split_by_marker(text, _SHEET_MARKER_RE)
    if len(sheet_parts) > 1:
        return _group_under_budget(
            parts=sheet_parts,
            source_doc_id=source_doc_id,
            max_chars=max_chars,
            strategy="sheets",
        )

    header_parts = _split_by_marker(text, _HEADER_MARKER_RE)
    if len(header_parts) > 1:
        return _group_under_budget(
            parts=header_parts,
            source_doc_id=source_doc_id,
            max_chars=max_chars,
            strategy="headers",
        )

    para_blobs = _split_by_paragraphs(text, max_chars)
    chunks: list[Chunk] = []
    for i, blob in enumerate(para_blobs):
        chunks.append(
            Chunk(
                text=blob,
                source_doc_id=source_doc_id,
                chunk_index=i,
                metadata={"strategy": "paragraphs"},
            )
        )
    return chunks


def _group_under_budget(
    *,
    parts: list[str],
    source_doc_id: int,
    max_chars: int,
    strategy: str,
) -> list[Chunk]:
    """Accorpa parti consecutive in chunk sotto max_chars; preserva ordine."""
    chunks: list[Chunk] = []
    buf: list[str] = []
    buf_size = 0
    chunk_index = 0
    parts_in_buf: list[int] = []
    for i, p in enumerate(parts):
        if buf_size + len(p) > max_chars and buf:
            chunks.append(
                Chunk(
                    text="\n\n".join(buf),
                    source_doc_id=source_doc_id,
                    chunk_index=chunk_index,
                    metadata={"strategy": strategy, "parts": list(parts_in_buf)},
                )
            )
            chunk_index += 1
            buf = [p]
            buf_size = len(p)
            parts_in_buf = [i]
        else:
            buf.append(p)
            buf_size += len(p) + 2
            parts_in_buf.append(i)
    if buf:
        chunks.append(
            Chunk(
                text="\n\n".join(buf),
                source_doc_id=source_doc_id,
                chunk_index=chunk_index,
                metadata={"strategy": strategy, "parts": list(parts_in_buf)},
            )
        )
    return chunks


__all__ = ["Chunk", "chunk_document", "DEFAULT_MAX_TOKENS"]
