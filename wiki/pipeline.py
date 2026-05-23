"""Pipeline single-file: orchestratore di scanner → extractor → categorizer → reconciler → draft.

Usato sia dal CLI batch (`wiki extract` / `wiki categorize`) sia dal watcher
(che chiama una sola funzione per ogni file droppato nella `_inbox/`).

Tutte le funzioni qui sono **idempotenti**: se il file (per sha256) è già stato
processato, vengono saltate con un log. Lo stato di "già visto" è derivato dalla
presenza di:

  - record nel JSONL della sorgente (per scanner)
  - directory `_status/extracted/<sha12>/` (per extractor)

Niente db: tutto su filesystem, in modo che il watcher possa girare senza setup.
"""
from __future__ import annotations

import hashlib
import json
import logging
import mimetypes
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from extractors._base import ExtractionResult, Extractor
from extractors.pdf import PdfExtractor
from extractors.plain import PlainExtractor
from scanners._base import FileRecord

from categorizers._enums import Categoria

logger = logging.getLogger(__name__)


# ----- registry minimale (mime/ext → extractor) --------------------------
# Tenuto qui invece di `extractors/_registry.py` per non toccare il package
# extractors (vincolo di perimetro). Quando il registry vero sarà disponibile,
# basta importarlo e cancellare questo blocco.

_EXTRACTORS: list[Extractor] = [PdfExtractor(), PlainExtractor()]

# Caricamento opzionale di docx (l'import in alto romperebbe se l'extractor
# avesse dipendenze non installate; qui lo facciamo soft).
try:  # pragma: no cover - dipendenze opzionali
    from extractors.docx import DocxExtractor  # type: ignore

    _EXTRACTORS.append(DocxExtractor())
except Exception as _exc:  # pragma: no cover
    logger.debug("DocxExtractor non disponibile: %s", _exc)


def _pick_extractor(file_path: Path) -> Extractor | None:
    """Sceglie l'extractor per estensione, poi per mime, fallback a plain."""
    ext = file_path.suffix.lower()
    for extr in _EXTRACTORS:
        if ext in extr.extensions:
            return extr
    mime, _ = mimetypes.guess_type(str(file_path))
    if mime:
        for extr in _EXTRACTORS:
            if mime in extr.mimes:
                return extr
    # Fallback: plain prova a decodificare il file come testo
    try:
        file_path.read_text(encoding="utf-8")
        return PlainExtractor()
    except (UnicodeDecodeError, OSError):
        return None


# ----- helper SHA256 + record da path locale ------------------------------

_HASH_CHUNK = 1024 * 1024


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(_HASH_CHUNK)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _build_record_from_inbox(file_path: Path) -> FileRecord:
    """Costruisce un :class:`FileRecord` per un file droppato in `_inbox/`.

    La sorgente è ``inbox``: il watcher non passa per uno scanner formale,
    ma il record è normalizzato per il resto della pipeline.
    """
    st = file_path.stat()
    mime, _ = mimetypes.guess_type(str(file_path))
    return FileRecord(
        source="inbox",
        source_id=str(file_path),
        path=file_path.name,
        name=file_path.name,
        size=st.st_size,
        mtime=datetime.fromtimestamp(st.st_mtime, tz=timezone.utc),
        mime=mime,
        author=None,
        last_modified_by=None,
        permissions=None,
        sha256=_sha256_file(file_path),
        extras={"abs_path": str(file_path)},
    )


# ----- idempotenza: stato globale derivato dal disco ---------------------


def _already_extracted(state_dir: Path, sha256: str) -> bool:
    return (state_dir / "extracted" / sha256[:12]).exists()


def _all_known_shas(state_dir: Path) -> set[str]:
    """Legge tutti i jsonl di inventory e ritorna l'insieme degli sha256 visti."""
    inv_dir = state_dir / "inventory"
    if not inv_dir.exists():
        return set()
    out: set[str] = set()
    for jsonl in inv_dir.glob("*.jsonl"):
        try:
            for line in jsonl.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                sha = rec.get("sha256")
                if sha:
                    out.add(sha)
        except OSError:  # pragma: no cover - difensivo
            continue
    return out


# ----- output: bozza minima nel batch corrente ---------------------------


def _current_batch_id(state_dir: Path) -> str:
    """Calcola l'ID del batch corrente: directory mtime più recente o nuovo."""
    drafts_dir = state_dir / "drafts"
    drafts_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    return today  # un batch al giorno è sufficiente per Step 2 watcher


def _write_draft(
    state_dir: Path,
    record: FileRecord,
    extraction: ExtractionResult,
    categoria: Categoria,
    confidence: float,
    reason: str,
) -> Path:
    """Scrive una bozza markdown nel batch corrente."""
    batch_id = _current_batch_id(state_dir)
    batch_dir = state_dir / "drafts" / batch_id
    batch_dir.mkdir(parents=True, exist_ok=True)
    sha12 = (record.sha256 or "unknown")[:12]
    draft_path = batch_dir / f"draft-{sha12}-{record.name}.md"
    front_matter = (
        f"---\n"
        f"sha256: {record.sha256}\n"
        f"source: {record.source}\n"
        f"path: {record.path}\n"
        f"categoria: {categoria.value}\n"
        f"confidence: {confidence:.2f}\n"
        f"reason: {reason}\n"
        f"quality: {extraction.quality:.2f}\n"
        f"---\n\n"
    )
    body = extraction.markdown[:4000]  # bozza, non documento intero
    draft_path.write_text(front_matter + body, encoding="utf-8")
    return draft_path


# ----- API pubblica -------------------------------------------------------


@dataclass
class PipelineResult:
    """Risultato dell'esecuzione del pipeline su un singolo file."""

    record: FileRecord
    categoria: Categoria | None
    confidence: float
    reason: str
    extraction_dir: Path | None
    draft_path: Path | None
    skipped: bool
    skip_reason: str | None


def run_pipeline_for_file(
    file_path: Path,
    config: dict[str, Any],
    state_dir: Path,
) -> PipelineResult:
    """Esegue il pipeline completo su un file.

    Stadi:
      1. Costruzione record (scanner-like) + sha256
      2. Estrazione → `_status/extracted/<sha12>/`
      3. Categorizzazione (regole; passata Claude rimandata al sprint dedicato)
      4. Reconciler check (dedup per sha contro inventory)
      5. Bozza in `_status/drafts/<batch_id>/`

    Idempotenza: se lo sha è già presente in inventory o se la cartella di
    estrazione esiste, esce subito con ``skipped=True``.
    """
    file_path = Path(file_path).resolve()
    if not file_path.exists() or not file_path.is_file():
        return PipelineResult(
            record=FileRecord(
                source="inbox",
                source_id=str(file_path),
                path=str(file_path),
                name=file_path.name,
                size=0,
                mtime=datetime.now(timezone.utc),
            ),
            categoria=None,
            confidence=0.0,
            reason="file inesistente",
            extraction_dir=None,
            draft_path=None,
            skipped=True,
            skip_reason="not-a-file",
        )

    # 1) Record + dedup hash globale
    try:
        record = _build_record_from_inbox(file_path)
    except OSError as exc:
        logger.warning("Impossibile costruire record per %s: %s", file_path, exc)
        return PipelineResult(
            record=FileRecord(
                source="inbox", source_id=str(file_path), path=str(file_path),
                name=file_path.name, size=0, mtime=datetime.now(timezone.utc),
            ),
            categoria=None,
            confidence=0.0,
            reason=str(exc),
            extraction_dir=None,
            draft_path=None,
            skipped=True,
            skip_reason="oserror",
        )

    sha = record.sha256 or ""
    known = _all_known_shas(state_dir)
    if sha and sha in known:
        logger.info("Skip %s: sha già in inventory", file_path.name)
        return PipelineResult(
            record=record, categoria=None, confidence=0.0,
            reason="dedup-hash", extraction_dir=None, draft_path=None,
            skipped=True, skip_reason="already-in-inventory",
        )
    if sha and _already_extracted(state_dir, sha):
        logger.info("Skip %s: cartella estrazione già esistente", file_path.name)
        return PipelineResult(
            record=record, categoria=None, confidence=0.0,
            reason="already-extracted", extraction_dir=state_dir / "extracted" / sha[:12],
            draft_path=None, skipped=True, skip_reason="already-extracted",
        )

    # Scrive il record nell'inventory "inbox.jsonl" (append-only)
    inv_dir = state_dir / "inventory"
    inv_dir.mkdir(parents=True, exist_ok=True)
    inbox_jsonl = inv_dir / "inbox.jsonl"
    with inbox_jsonl.open("a", encoding="utf-8") as f:
        f.write(record.to_jsonl() + "\n")

    # 2) Extractor
    extractor = _pick_extractor(file_path)
    if extractor is None:
        logger.info("Skip %s: nessun extractor disponibile", file_path.name)
        return PipelineResult(
            record=record, categoria=None, confidence=0.0,
            reason="no-extractor", extraction_dir=None, draft_path=None,
            skipped=True, skip_reason="no-extractor",
        )
    try:
        extraction = extractor.extract(file_path)
    except Exception as exc:  # pragma: no cover - difensivo
        logger.exception("Estrazione fallita su %s: %s", file_path, exc)
        return PipelineResult(
            record=record, categoria=None, confidence=0.0,
            reason=f"extractor-error: {exc}", extraction_dir=None, draft_path=None,
            skipped=True, skip_reason="extractor-error",
        )

    extraction_dir = Extractor.write_extraction(
        extraction, state_dir, sha, source_record=json.loads(record.to_jsonl()),
    )

    # 3) Categorizzazione (passata 1: regole)
    try:
        from categorizers.rules import classify

        categoria, confidence, reason = classify(record)
    except Exception as exc:  # pragma: no cover - difensivo
        logger.warning("Categorizer non disponibile (%s), uso DA_CHIARIRE", exc)
        categoria, confidence, reason = Categoria.DA_CHIARIRE, 0.0, "no-rules"

    record.categoria = categoria.value
    record.confidence = confidence
    record.reason = reason

    # 4) Reconciler check: dedup hash con il resto dell'inventory
    if sha in known:
        record.dedup = {"role": "duplicate-of", "canonical": None}

    # 5) Bozza nel batch corrente
    draft_path = _write_draft(state_dir, record, extraction, categoria, confidence, reason)

    # 6) Step 3: rigenerazione automatica dashboard se attiva nel config
    # (silenziosa, log info). Eseguita dopo ogni file droppato in `_inbox/` o
    # processato batch in modo che il Custode abbia sempre lo snapshot fresco.
    maybe_regenerate_dashboard(config, state_dir)

    return PipelineResult(
        record=record,
        categoria=categoria,
        confidence=confidence,
        reason=reason,
        extraction_dir=extraction_dir,
        draft_path=draft_path,
        skipped=False,
        skip_reason=None,
    )


def maybe_regenerate_dashboard(config: dict[str, Any], state_dir: Path) -> None:
    """Rigenera la dashboard del cliente se ``config.dashboard.auto`` è ``True``.

    Hook silenzioso (log info / warning), pensato per essere chiamato al
    termine degli stage che modificano lo ``_status/`` (extract, categorize,
    reconcile, watcher). Errori non propagati: la dashboard è ausiliaria,
    una sua failure non deve interrompere la pipeline.
    """
    if not (config.get("dashboard") or {}).get("auto"):
        return
    try:
        from wiki.dashboard import generate_dashboard

        # Vault root: derivato risalendo da state_dir (`_status/<slug>/` →
        # `<repo>/vault/`). Se non trovato, lascia ``None`` (la dashboard
        # calcolerà salute vault vuota).
        repo_root = state_dir.resolve().parent.parent
        vault_dir = repo_root / "vault"
        generate_dashboard(
            state_dir=state_dir,
            vault_dir=vault_dir if vault_dir.exists() else None,
            output_path=state_dir / "dashboard.html",
            cliente=state_dir.name or "ignoto",
        )
        logger.info("Dashboard auto-rigenerata in %s/dashboard.html", state_dir)
    except Exception as exc:  # pragma: no cover - fail-soft
        logger.warning("Rigenerazione dashboard fallita: %s", exc)
