"""
Wrapper della webapp attorno all'Extractor LLM (`custodia build`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from custodia_cli.commands.init import state_db_path_for_vault
from custodia_cli.extractor import Extractor
from custodia_cli.llm.registry import get_provider
from custodia_cli.state import StateStore


ENTITY_TYPES = ("cliente", "fornitore", "commessa", "comunicazione")


@dataclass
class BuildResult:
    """Riepilogo di un singolo build per un entity_type."""

    entity_type: str
    saved: int = 0
    candidates: list[dict[str, Any]] = field(default_factory=list)
    usage_log: list[Any] = field(default_factory=list)
    error: str | None = None

    @property
    def total_cost_eur(self) -> float:
        return float(sum(getattr(u, "cost_eur_estimate", 0.0) for u in self.usage_log))

    @property
    def total_input_tokens(self) -> int:
        return int(sum(getattr(u, "input_tokens", 0) for u in self.usage_log))

    @property
    def total_output_tokens(self) -> int:
        return int(sum(getattr(u, "output_tokens", 0) for u in self.usage_log))


def _build_provider(llm_provider: str, fixture_path: Path | None):
    """Costruisce il provider LLM. Solleva ValueError con messaggio leggibile."""
    kwargs: dict[str, Any] = {}
    if llm_provider == "fake":
        if fixture_path is None:
            raise ValueError(
                "Provider 'fake' richiede un fixture YAML. "
                "Imposta il path della fixture canned responses."
            )
        kwargs["fixture_path"] = Path(fixture_path)
    return get_provider(llm_provider, **kwargs)


def build_entity_type(
    *,
    vault: Path,
    entity_type: str,
    llm_provider: str = "anthropic",
    fixture_path: Path | None = None,
) -> BuildResult:
    """Esegue l'extractor per un singolo `entity_type`.

    Equivalente a `custodia build {clients|fornitori|commesse|communications}`.
    """
    if entity_type not in ENTITY_TYPES:
        raise ValueError(f"entity_type sconosciuto: {entity_type!r}. Validi: {ENTITY_TYPES}")

    db_path = state_db_path_for_vault(Path(vault).expanduser().resolve())
    if not db_path.exists():
        return BuildResult(entity_type=entity_type, error=f"State DB non trovato: {db_path}. Lancia prima uno scan.")

    try:
        provider = _build_provider(llm_provider, fixture_path)
    except ValueError as exc:
        return BuildResult(entity_type=entity_type, error=str(exc))

    result = BuildResult(entity_type=entity_type)

    with StateStore(db_path) as store:
        run_id = store.register_run(
            command=f"build {entity_type}",
            args={
                "entity_type": entity_type,
                "llm_provider": llm_provider,
                "fixture": str(fixture_path) if fixture_path else None,
            },
        )
        try:
            extractor = Extractor(llm=provider, store=store)
            candidates = extractor.extract(entity_type, run_id=run_id)
            for cand in candidates:
                store.upsert_entity(
                    entity_type=cand.entity_type,
                    entity_id=cand.entity_id,
                    frontmatter=cand.frontmatter,
                    body_md=cand.body_md,
                    source_doc_ids=cand.source_doc_ids,
                    confidence=cand.confidence,
                    status="pending",
                )
                result.saved += 1
                result.candidates.append({
                    "entity_id": cand.entity_id,
                    "confidence": cand.confidence,
                    "source_docs": len(cand.source_doc_ids),
                })
        except Exception as exc:  # noqa: BLE001
            store.complete_run(run_id, status="error", summary=str(exc))
            result.error = str(exc)
            return result

        result.usage_log = list(getattr(provider, "usage_log", []) or [])
        summary = (
            f"{result.saved} candidati · "
            f"{result.total_input_tokens} tok in · "
            f"{result.total_output_tokens} tok out · "
            f"€{result.total_cost_eur:.4f}"
        )
        store.complete_run(run_id, status="success", summary=summary)

    return result


def build_all(
    *,
    vault: Path,
    llm_provider: str = "anthropic",
    fixture_path: Path | None = None,
) -> list[BuildResult]:
    """Esegue build in sequenza per tutti i tipi. Continua anche se uno fallisce."""
    results = []
    for et in ENTITY_TYPES:
        results.append(
            build_entity_type(
                vault=vault,
                entity_type=et,
                llm_provider=llm_provider,
                fixture_path=fixture_path,
            )
        )
    return results


__all__ = ["BuildResult", "ENTITY_TYPES", "build_entity_type", "build_all"]
