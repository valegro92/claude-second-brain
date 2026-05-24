"""
Extractor: orchestrator della pipeline di estrazione entità da documenti.

Flusso end-to-end:
1. Carica i documenti `pending` dallo StateStore (input).
2. Per ogni documento, esegue lo stadio CATEGORIZE (tier FAST) per identificare
   quali entità del tipo richiesto compaiono.
3. Aggrega per `entity_id` (slug derivato dal nome): documenti che parlano
   della stessa entità vengono raggruppati.
4. Per ogni gruppo, esegue lo stadio EXTRACT (tier SMART) con tool-use forzato
   contro lo schema canonical.
5. Se l'entità ha più chunk/documenti, il merger aggrega in un singolo
   EntityCandidate.
6. Il validator verifica conformità allo schema. Se invalido, il candidato è
   comunque ritornato con confidence ridotta e flag `validation_errors` nel
   metadata frontmatter (per review in U6).

L'extractor NON scrive su StateStore: chi orchestra (commands/build.py) decide
la policy di persistenza.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any

from custodia_cli.extractor.chunking import chunk_document
from custodia_cli.extractor.merger import merge_entity_candidates
from custodia_cli.extractor.prompts import (
    CATEGORIZE_OUTPUT_SCHEMA,
    categorize_system_prompt,
    categorize_user_prompt,
    extract_system_prompt,
    extract_user_prompt,
)
from custodia_cli.extractor.schema import load_canonical_schema
from custodia_cli.extractor.validator import validate_entity
from custodia_cli.llm.base import LLMProvider, Message, ModelTier
from custodia_cli.llm.exceptions import LLMError, LLMValidationError
from custodia_cli.state import StateStore

logger = logging.getLogger(__name__)


# Entity types supportati in v0.1.
SUPPORTED_ENTITY_TYPES: tuple[str, ...] = (
    "cliente",
    "fornitore",
    "commessa",
    "comunicazione",
)


@dataclass
class EntityCandidate:
    """Candidato di scheda entità prodotto dall'extractor, in attesa di review.

    Attributes:
        entity_type: tipo canonico (cliente|fornitore|commessa|comunicazione).
        entity_id: slug stabile (es. "rossetto-laminazioni").
        frontmatter: dict YAML frontmatter conforme allo schema canonical.
        body_md: corpo markdown della scheda (può essere vuoto per v0.1).
        source_doc_ids: PK dei `documents` nello StateStore da cui deriva.
        confidence: 0.0–1.0; 1.0 = tutti i campi obbligatori popolati e valido.
    """

    entity_type: str
    entity_id: str
    frontmatter: dict[str, Any]
    body_md: str = ""
    source_doc_ids: list[int] = field(default_factory=list)
    confidence: float = 1.0


# ---------------------------------------------------------------------------
# Utility: slugify e normalizzazione nomi
# ---------------------------------------------------------------------------

_SLUG_RE = re.compile(r"[^a-z0-9]+")
_LEGAL_FORM_SUFFIXES = (
    " srl",
    " s.r.l.",
    " spa",
    " s.p.a.",
    " sas",
    " s.a.s.",
    " snc",
    " s.n.c.",
    " sa",
    " srls",
)


def _normalize_name(name: str) -> str:
    """Normalizza un nome aziendale per il grouping.

    Lower, rimuove suffissi legali (SRL/SPA/...), strip spazi multipli.
    Permette di considerare "Rossetto Laminazioni SRL" == "Rossetto Laminazioni".
    """
    s = name.strip().lower()
    for suffix in _LEGAL_FORM_SUFFIXES:
        if s.endswith(suffix):
            s = s[: -len(suffix)]
            break
    return " ".join(s.split())


def _slugify(name: str) -> str:
    """Slug minuscolo, ascii-only, separato da `-`. Stabile per entity_id."""
    normalized = unicodedata.normalize("NFKD", name)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    slug = _SLUG_RE.sub("-", ascii_only.lower()).strip("-")
    return slug or "entita-senza-nome"


# ---------------------------------------------------------------------------
# Confidence heuristic
# ---------------------------------------------------------------------------


def _compute_confidence(frontmatter: dict[str, Any], schema: dict[str, Any]) -> float:
    """Confidence in [0.0, 1.0] basata sulla percentuale di campi popolati.

    Heuristic semplice ma utile per il triage in review (U6): le entità con
    confidence < 0.5 sono evidenziate per attenzione.
    """
    properties = schema.get("properties", {})
    if not properties:
        return 1.0
    populated = 0
    total = 0
    for key in properties:
        total += 1
        value = frontmatter.get(key)
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        if isinstance(value, (list, dict)) and len(value) == 0:
            continue
        populated += 1
    if total == 0:
        return 1.0
    return populated / total


# ---------------------------------------------------------------------------
# Extractor
# ---------------------------------------------------------------------------


class Extractor:
    """Orchestratore della pipeline di estrazione (U5).

    Args:
        llm: provider LLM (Anthropic o Fake) per categorize ed extract.
        store: StateStore aperto per leggere documenti pending.
    """

    def __init__(self, llm: LLMProvider, store: StateStore) -> None:
        self.llm = llm
        self.store = store

    # -- stadio 1: categorize -----------------------------------------------

    def _categorize_document(
        self,
        *,
        document: dict[str, Any],
        entity_type: str,
    ) -> list[dict[str, str]]:
        """Per un singolo documento, identifica le entità del tipo richiesto.

        Ritorna lista di `{"name": str, "hint": str}`. Lista vuota se nessuna.
        Eventuali errori LLM vengono loggati e producono lista vuota (skip safe).
        """
        text = document.get("text") or ""
        if not text.strip():
            return []
        # Solo l'inizio del testo per categorize (FAST, basso costo).
        snippet = text[:8000]
        system = categorize_system_prompt(entity_type)
        user = categorize_user_prompt(
            document_text=snippet,
            source_path=document.get("source_path", ""),
        )
        try:
            result = self.llm.extract_structured(
                [Message(role="user", content=user)],
                schema=CATEGORIZE_OUTPUT_SCHEMA,
                system=system,
                tier=ModelTier.FAST,
            )
        except LLMError as exc:
            logger.warning(
                "categorize fallita per doc id=%s (%s): %s",
                document.get("id"),
                document.get("source_path"),
                exc,
            )
            return []

        raw_entities = result.get("entities", [])
        out: list[dict[str, str]] = []
        for e in raw_entities:
            name = str(e.get("name", "")).strip()
            if not name:
                continue
            out.append({"name": name, "hint": str(e.get("hint", ""))})
        return out

    # -- stadio 2: extract --------------------------------------------------

    def _extract_entity(
        self,
        *,
        entity_type: str,
        entity_name: str,
        documents: list[dict[str, Any]],
        schema: dict[str, Any],
    ) -> EntityCandidate | None:
        """Per una tupla (entity_name, documents) produce un EntityCandidate.

        Gestisce chunking interno: se i documenti combinati superano il budget,
        invia un chunk alla volta e fa merge dei risultati parziali.
        """
        # Prepara la lista combinata di chunk: ogni chunk porta con sé
        # il source_doc_id originale.
        all_chunks: list[tuple[int, str, str]] = []  # (doc_id, source_path, text)
        for d in documents:
            doc_id = int(d["id"])
            chunks = chunk_document(
                source_doc_id=doc_id,
                text=d.get("text") or "",
                mime_type=d.get("mime_type", ""),
                token_counter=self.llm,
            )
            for ch in chunks:
                all_chunks.append((doc_id, d.get("source_path", ""), ch.text))

        if not all_chunks:
            return None

        partials: list[EntityCandidate] = []
        for doc_id, source_path, text in all_chunks:
            user = extract_user_prompt(
                entity_name=entity_name,
                documents=[{"source_path": source_path, "text": text}],
            )
            try:
                result = self.llm.extract_structured(
                    [Message(role="user", content=user)],
                    schema=schema,
                    system=extract_system_prompt(entity_type),
                    tier=ModelTier.SMART,
                )
            except LLMValidationError as exc:
                # Output non conforme: skippa questo chunk ma loggadiagnostica.
                logger.warning(
                    "extract: output non conforme per %r (doc_id=%s): %s",
                    entity_name,
                    doc_id,
                    exc,
                )
                continue
            except LLMError as exc:
                logger.warning(
                    "extract: LLMError per %r (doc_id=%s): %s",
                    entity_name,
                    doc_id,
                    exc,
                )
                continue

            # Forza `tipo` corretto (l'LLM può sbagliare).
            result.setdefault("tipo", entity_type)
            # `nome`: forza fallback al hint se mancante.
            if not result.get("nome"):
                result["nome"] = entity_name

            confidence = _compute_confidence(result, schema)
            partials.append(
                EntityCandidate(
                    entity_type=entity_type,
                    entity_id=_slugify(
                        _normalize_name(result.get("nome") or entity_name)
                    ),
                    frontmatter=result,
                    body_md="",
                    source_doc_ids=[doc_id],
                    confidence=confidence,
                )
            )

        if not partials:
            return None

        # Re-aggrega: tutti i partial dovrebbero avere stesso entity_id
        # (perché derivano dallo stesso entity_name normalizzato). Se uno
        # diverge per noise dell'LLM, lo forziamo allo slug del primo.
        primary_id = partials[0].entity_id
        for p in partials[1:]:
            if p.entity_id != primary_id:
                logger.debug(
                    "extract: slug divergente fra chunk (%s vs %s) — uniformo a %s",
                    p.entity_id,
                    primary_id,
                    primary_id,
                )
                p.entity_id = primary_id

        merged = merge_entity_candidates(partials)

        # Validazione finale: se invalido, marca con confidence ridotta e
        # annota errori nei `validation_errors` del frontmatter (visibili in review).
        valid, errors = validate_entity(merged.frontmatter, entity_type)
        if not valid:
            logger.warning(
                "validate: candidato %r/%s non conforme: %s",
                entity_type,
                merged.entity_id,
                errors,
            )
            merged.frontmatter["validation_errors"] = errors
            # Penalizza la confidence: max 0.5 quando schema fail.
            merged.confidence = min(merged.confidence, 0.5)

        return merged

    # -- pubblica ------------------------------------------------------------

    def extract(
        self,
        entity_type: str,
        *,
        run_id: int | None = None,
    ) -> list[EntityCandidate]:
        """Esegue la pipeline completa per un entity_type.

        Args:
            entity_type: uno fra `cliente|fornitore|commessa|comunicazione`.
            run_id: id del run CLI (opzionale, per logging futuro).

        Returns:
            Lista di EntityCandidate (può essere vuota se i documenti non
            menzionano entità del tipo richiesto).

        Raises:
            ValueError: entity_type non supportato.
        """
        if entity_type not in SUPPORTED_ENTITY_TYPES:
            raise ValueError(
                f"entity_type {entity_type!r} non supportato. "
                f"Supportati: {SUPPORTED_ENTITY_TYPES}."
            )
        del run_id  # placeholder, non usato in v0.1

        documents = self.store.list_documents(status="pending")
        if not documents:
            logger.info("extract %r: nessun documento pending", entity_type)
            return []

        schema = load_canonical_schema(entity_type)

        # Stage 1: categorize tutti i documenti, raggruppa per entity_name normalizzato.
        groups: dict[str, dict[str, Any]] = {}
        # struttura: normalized_name -> {"display_name": str, "documents": [doc, ...]}
        for doc in documents:
            entities = self._categorize_document(
                document=doc, entity_type=entity_type
            )
            for ent in entities:
                key = _normalize_name(ent["name"])
                if not key:
                    continue
                bucket = groups.setdefault(
                    key, {"display_name": ent["name"], "documents": []}
                )
                bucket["documents"].append(doc)

        if not groups:
            logger.info(
                "extract %r: categorize non ha trovato entità in %d documenti",
                entity_type,
                len(documents),
            )
            return []

        # Stage 2: extract per ogni gruppo.
        candidates: list[EntityCandidate] = []
        for key, bucket in groups.items():
            candidate = self._extract_entity(
                entity_type=entity_type,
                entity_name=bucket["display_name"],
                documents=bucket["documents"],
                schema=schema,
            )
            if candidate is not None:
                candidates.append(candidate)

        return candidates


__all__ = [
    "EntityCandidate",
    "Extractor",
    "SUPPORTED_ENTITY_TYPES",
]
