"""Passata 2 del categorizer: chiamata Claude Haiku sui residui DA_CHIARIRE.

Vedi `_brief/04-step-2-tech-plan.md` sezione 4.2 e 7.3 per pricing.

Convenzioni:
* Batch da 20 record per chiamata (riduce overhead di prompt).
* Due modalità:
    - ``safe``: solo metadati (nome, path, size, mtime, mime).
    - ``full``: aggiunge i primi 500 caratteri di ``extracted/<sha>/main.md``
      se esistono.
* Ogni chiamata viene loggata in ``_status/cost.jsonl`` con token + costo
  stimato in EUR (cambio fisso 1 USD = 0.92 EUR, riassestabile centralmente).
* Modello default: ``claude-haiku-4-5``.

I costi sono approssimazioni — il driver economico vero è il tempo di
Valentino, non la spesa Claude (vedi brief 7.4).
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from scanners._base import FileRecord

from categorizers._enums import Categoria

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------- costanti
DEFAULT_MODEL: str = "claude-haiku-4-5"
DEFAULT_BATCH_SIZE: int = 20
SNIPPET_CHARS: int = 500
# Tasso di cambio statico (rivedere periodicamente). Riferimento brief 7.3.
USD_TO_EUR: float = 0.92
# Pricing per 1M token, come da brief 7.3.
PRICING_USD_PER_MTOK: dict[str, dict[str, float]] = {
    "claude-haiku-4-5": {"in": 1.0, "out": 5.0},
    "claude-sonnet-4-5": {"in": 3.0, "out": 15.0},
    # Alias di sicurezza per varianti di naming.
    "claude-haiku-4.5": {"in": 1.0, "out": 5.0},
    "claude-sonnet-4.5": {"in": 3.0, "out": 15.0},
}


_PROMPT_SYSTEM = (
    "Sei un consulente che categorizza file aziendali di una PMI italiana. "
    "Categorie ammesse: VIVO, DA-CONSULTARE, ARCHIVIO, CESTINO, DA-CHIARIRE. "
    "Rispondi SOLO con un array JSON, una entry per file. Schema entry: "
    '{"sha": "<sha o source_id>", "cat": "<categoria>", "conf": 0.0-1.0, "why": "<breve motivo>"}. '
    "Nessun testo fuori dall'array."
)


def _estimate_cost_eur(model: str, tokens_in: int, tokens_out: int) -> float:
    """Stima costo in EUR di una chiamata, default tariffa Haiku se sconosciuto."""
    pricing = PRICING_USD_PER_MTOK.get(model, PRICING_USD_PER_MTOK[DEFAULT_MODEL])
    usd = (tokens_in / 1_000_000) * pricing["in"] + (tokens_out / 1_000_000) * pricing["out"]
    return round(usd * USD_TO_EUR, 6)


def _read_snippet(state_dir: Path, sha256: str | None) -> str | None:
    """Legge i primi ``SNIPPET_CHARS`` caratteri di ``extracted/<sha12>/main.md``."""
    if not sha256:
        return None
    sha12 = sha256[:12]
    main_md = state_dir / "extracted" / sha12 / "main.md"
    if not main_md.exists():
        return None
    try:
        with main_md.open("r", encoding="utf-8") as f:
            return f.read(SNIPPET_CHARS)
    except OSError as exc:
        logger.warning("Impossibile leggere snippet %s: %s", main_md, exc)
        return None


def _record_to_payload(record: FileRecord, mode: str, state_dir: Path | None) -> dict[str, Any]:
    """Riduce un FileRecord a dict da inviare al modello, secondo modalità."""
    payload: dict[str, Any] = {
        "sha": record.sha256 or record.source_id,
        "name": record.name,
        "path": record.path,
        "size": record.size,
        "mtime": record.mtime.isoformat() if isinstance(record.mtime, datetime) else str(record.mtime),
        "mime": record.mime,
    }
    if mode == "full" and state_dir is not None:
        snippet = _read_snippet(state_dir, record.sha256)
        if snippet:
            payload["snippet"] = snippet
    return payload


def _build_prompt(records: list[FileRecord], mode: str, state_dir: Path | None) -> str:
    """Costruisce il blocco utente del prompt (system è fisso)."""
    payloads = [_record_to_payload(r, mode, state_dir) for r in records]
    lines = [
        "Per ogni file qui sotto, decidi la categoria.",
        "Files:",
        json.dumps(payloads, ensure_ascii=False),
    ]
    return "\n".join(lines)


def _log_cost(state_dir: Path, entry: dict[str, Any]) -> None:
    """Append a ``_status/cost.jsonl``."""
    cost_path = state_dir / "cost.jsonl"
    cost_path.parent.mkdir(parents=True, exist_ok=True)
    with cost_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _parse_categoria(raw: str) -> Categoria:
    """Tollera varianti di naming nella risposta del modello."""
    if not raw:
        return Categoria.DA_CHIARIRE
    norm = raw.strip().lower().replace("_", "-")
    mapping = {
        "vivo": Categoria.VIVO,
        "da-consultare": Categoria.DA_CONSULTARE,
        "da consultare": Categoria.DA_CONSULTARE,
        "archivio": Categoria.ARCHIVIO,
        "cestino": Categoria.CESTINO,
        "da-chiarire": Categoria.DA_CHIARIRE,
        "da chiarire": Categoria.DA_CHIARIRE,
    }
    return mapping.get(norm, Categoria.DA_CHIARIRE)


def _parse_response(text: str, records: list[FileRecord]) -> list[dict[str, Any]]:
    """Estrae la lista JSON dalla risposta del modello, robusto a wrapping testuale."""
    text = text.strip()
    # Tenta direttamente il parse.
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Fallback: ritaglia tra prima ``[`` e ultima ``]``.
        start = text.find("[")
        end = text.rfind("]")
        if start == -1 or end == -1 or end < start:
            logger.warning("Risposta non parsabile come JSON, fallback DA_CHIARIRE")
            return [
                {
                    "sha": r.sha256 or r.source_id,
                    "cat": Categoria.DA_CHIARIRE.value,
                    "conf": 0.0,
                    "why": "risposta-LLM-non-parsata",
                }
                for r in records
            ]
        try:
            data = json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return [
                {
                    "sha": r.sha256 or r.source_id,
                    "cat": Categoria.DA_CHIARIRE.value,
                    "conf": 0.0,
                    "why": "risposta-LLM-non-parsata",
                }
                for r in records
            ]
    if not isinstance(data, list):
        return []
    # Normalizza ogni entry.
    out: list[dict[str, Any]] = []
    for entry in data:
        if not isinstance(entry, dict):
            continue
        cat = _parse_categoria(str(entry.get("cat", "")))
        try:
            conf = float(entry.get("conf", 0.0))
        except (TypeError, ValueError):
            conf = 0.0
        out.append(
            {
                "sha": str(entry.get("sha", "")),
                "cat": cat.value,
                "conf": max(0.0, min(1.0, conf)),
                "why": str(entry.get("why", "")),
            }
        )
    return out


def _chunked(seq: list[FileRecord], n: int) -> Iterable[list[FileRecord]]:
    for i in range(0, len(seq), n):
        yield seq[i : i + n]


def _get_anthropic_client():  # pragma: no cover - tested via mock
    """Costruisce un client Anthropic on-demand (import lazy)."""
    try:
        import anthropic  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "Il pacchetto `anthropic` non è installato. Aggiungilo via uv."
        ) from exc
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY non impostata nell'ambiente.")
    return anthropic.Anthropic(api_key=api_key)


def categorize_batch(
    records: list[FileRecord],
    mode: str = "safe",
    *,
    model: str = DEFAULT_MODEL,
    batch_size: int = DEFAULT_BATCH_SIZE,
    state_dir: Path | None = None,
    client: Any | None = None,
) -> list[dict[str, Any]]:
    """Categorizza una lista di record via Claude, in batch.

    Args:
        records: lista di FileRecord da categorizzare (tipicamente i ``DA_CHIARIRE``).
        mode: ``safe`` (solo metadati) o ``full`` (aggiunge snippet).
        model: id modello Anthropic. Default Haiku 4.5.
        batch_size: quanti record per chiamata. Default 20.
        state_dir: cartella `_status/`. Necessaria per leggere snippet e
            scrivere ``cost.jsonl``. Se ``None`` la funzione funziona ma
            senza logging dei costi (utile in test).
        client: client Anthropic già istanziato (utile per mock nei test).

    Returns:
        Lista di dict ``{sha, cat, conf, why}``, una entry per record.
    """
    if not records:
        return []
    if mode not in {"safe", "full"}:
        raise ValueError(f"Modalità sconosciuta: {mode}")

    if client is None:
        client = _get_anthropic_client()

    results: list[dict[str, Any]] = []
    for chunk in _chunked(records, batch_size):
        user_prompt = _build_prompt(chunk, mode, state_dir)
        response = client.messages.create(
            model=model,
            max_tokens=1024,
            system=_PROMPT_SYSTEM,
            messages=[{"role": "user", "content": user_prompt}],
        )
        # Estrae testo + usage in modo robusto (SDK reale e mock).
        text = _extract_text(response)
        tokens_in, tokens_out = _extract_usage(response)
        results.extend(_parse_response(text, chunk))

        if state_dir is not None:
            cost = _estimate_cost_eur(model, tokens_in, tokens_out)
            _log_cost(
                state_dir,
                {
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "stage": "categorize",
                    "model": model,
                    "tokens_in": tokens_in,
                    "tokens_out": tokens_out,
                    "cost_eur": cost,
                    "batch_size": len(chunk),
                    "mode": mode,
                },
            )
            logger.info(
                "categorize batch n=%d tokens=%d/%d cost=%.4f EUR",
                len(chunk),
                tokens_in,
                tokens_out,
                cost,
            )
    return results


def _extract_text(response: Any) -> str:
    """Estrae il testo dalla response del SDK Anthropic (o da un mock)."""
    # SDK reale: response.content è una lista di blocchi con .text
    content = getattr(response, "content", None)
    if content is None and isinstance(response, dict):
        content = response.get("content")
    if isinstance(content, list) and content:
        block = content[0]
        text = getattr(block, "text", None)
        if text is None and isinstance(block, dict):
            text = block.get("text")
        if text is not None:
            return str(text)
    if isinstance(content, str):
        return content
    return ""


def _extract_usage(response: Any) -> tuple[int, int]:
    """Estrae (input_tokens, output_tokens) tollerando vari shape."""
    usage = getattr(response, "usage", None)
    if usage is None and isinstance(response, dict):
        usage = response.get("usage")
    if usage is None:
        return (0, 0)
    in_tok = getattr(usage, "input_tokens", None)
    out_tok = getattr(usage, "output_tokens", None)
    if in_tok is None and isinstance(usage, dict):
        in_tok = usage.get("input_tokens", 0)
        out_tok = usage.get("output_tokens", 0)
    try:
        return int(in_tok or 0), int(out_tok or 0)
    except (TypeError, ValueError):
        return (0, 0)


__all__ = [
    "DEFAULT_MODEL",
    "DEFAULT_BATCH_SIZE",
    "PRICING_USD_PER_MTOK",
    "categorize_batch",
]
