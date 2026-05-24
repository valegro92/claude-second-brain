"""
Background worker per Build (estrazione entità LLM).

Wrapper attorno a ``custodia_web.services.extract`` che lancia ``build_all`` /
``build_entity_type`` in un thread separato e pubblica progress live nel
``StateStore`` per il polling Streamlit.

Limitazione attuale: l'Extractor non espone progress per-documento (lavora
internamente su batch di categorize+extract). Il progress che pubblichiamo è
quindi a granularità "entity_type": per ``all`` (4 tipi) abbiamo 4 step,
ognuno dei quali pubblica current/total = i/4 + il numero di candidati
emessi finora. Per ``entity_type`` singolo, abbiamo 2 fasi (categorize +
extract): pubblichiamo running con counter ``current_item`` = "Estraggo
clienti…". Granularità più fine sarà parte di U5/U6 (richiede modifiche
all'Extractor stesso).

Cancel: l'Extractor è una chiamata sincrona "bloccante" (categorize + extract
internamente fanno chiamate LLM in serie). Il cancel viene controllato FRA
un entity_type e l'altro (per ``build_all``), oppure non viene controllato
affatto per single-type build. Conseguenza pratica: cancellare un build
singolo richiede di aspettare che il provider LLM ritorni dalla chiamata
corrente — accettabile dato che le chiamate Anthropic durano ~5-30s tipici.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from custodia_cli.jobs import (
    CancelledError,
    CancelToken,
    ProgressReporter,
    ProgressSnapshot,
)
from custodia_cli.state import StateStore
from custodia_cli.commands.init import state_db_path_for_vault

from custodia_web.services.extract import (
    BuildResult,
    ENTITY_TYPES,
    _build_provider,
)

logger = logging.getLogger(__name__)


@dataclass
class BuildJobResult:
    """Risultato finale di un job build, possibilmente multi-entity."""

    results: list[BuildResult] = field(default_factory=list)
    error: str | None = None

    @property
    def total_saved(self) -> int:
        return sum(r.saved for r in self.results)


def _entity_type_label(entity_type: str) -> str:
    return {
        "cliente": "clienti",
        "fornitore": "fornitori",
        "commessa": "commesse",
        "comunicazione": "comunicazioni",
    }.get(entity_type, entity_type)


def build_with_progress(
    *,
    vault: Path,
    entity_type: str,
    llm_provider: str,
    fixture_path: Path | None,
    cancel: CancelToken,
    run_id_callback: Callable[[int], None] | None = None,
) -> BuildJobResult:
    """Esegue build per uno o tutti gli entity_type pubblicando progress live.

    Se ``entity_type == "all"`` itera su :data:`ENTITY_TYPES` controllando il
    cancel fra un tipo e l'altro. Apre il proprio :class:`StateStore` nel
    thread chiamante (= worker).
    """
    db_path = state_db_path_for_vault(Path(vault).expanduser().resolve())
    if not db_path.exists():
        return BuildJobResult(
            error=f"State DB non trovato: {db_path}. Lancia prima uno scan."
        )

    try:
        provider = _build_provider(llm_provider, fixture_path)
    except ValueError as exc:
        return BuildJobResult(error=str(exc))

    targets: list[str] = (
        list(ENTITY_TYPES) if entity_type == "all" else [entity_type]
    )
    total_steps = len(targets)

    job_result = BuildJobResult()

    with StateStore(db_path) as store:
        run_id = store.register_run(
            command=f"build {entity_type}",
            args={
                "entity_type": entity_type,
                "llm_provider": llm_provider,
                "fixture": str(fixture_path) if fixture_path else None,
            },
        )
        if run_id_callback is not None:
            try:
                run_id_callback(run_id)
            except Exception:  # noqa: BLE001
                logger.exception("run_id_callback ha fallito")

        reporter = ProgressReporter(store, run_id, min_interval_ms=200)
        reporter.flush()
        reporter.update(ProgressSnapshot(
            status="running",
            current=0,
            total=total_steps,
            current_item="Inizio estrazione…",
        ))

        start_time = time.monotonic()
        total_saved = 0

        # Import locale per evitare costo a module-load
        from custodia_cli.extractor import Extractor

        try:
            for idx, et in enumerate(targets):
                cancel.raise_if_cancelled()

                label = _entity_type_label(et)
                reporter.flush()
                reporter.update(ProgressSnapshot(
                    status="running",
                    current=idx,
                    total=total_steps,
                    current_item=f"Estraggo {label}…",
                    throughput_per_sec=(idx / max(time.monotonic() - start_time, 0.001)),
                    extra={"phase": "extracting", "entity_type": et},
                ))

                result = BuildResult(entity_type=et)
                try:
                    extractor = Extractor(llm=provider, store=store)
                    candidates = extractor.extract(et, run_id=run_id)
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
                    result.usage_log = list(getattr(provider, "usage_log", []) or [])
                except CancelledError:
                    raise
                except Exception as exc:  # noqa: BLE001
                    result.error = str(exc)
                    logger.exception("build %s fallita", et)

                job_result.results.append(result)
                total_saved += result.saved

                # Update post-step
                reporter.update(ProgressSnapshot(
                    status="running",
                    current=idx + 1,
                    total=total_steps,
                    current_item=f"✓ {label}: {result.saved} candidati",
                    throughput_per_sec=((idx + 1) / max(time.monotonic() - start_time, 0.001)),
                    extra={"phase": "done_step", "entity_type": et, "saved": total_saved},
                ))

            # Snapshot finale OK
            elapsed = time.monotonic() - start_time
            reporter.flush()
            reporter.update(ProgressSnapshot(
                status="success",
                current=total_steps,
                total=total_steps,
                current_item=f"Completato — {total_saved} candidati",
                throughput_per_sec=(total_steps / max(elapsed, 0.001)),
                extra={"total_saved": total_saved, "run_id": run_id},
            ))
            store.complete_run(
                run_id,
                status="success",
                summary=f"{total_saved} candidati estratti in {elapsed:.1f}s",
            )
            return job_result

        except CancelledError:
            elapsed = time.monotonic() - start_time
            reporter.flush()
            reporter.update(ProgressSnapshot(
                status="cancelled",
                current=len(job_result.results),
                total=total_steps,
                current_item="Annullato dall'utente",
                extra={"total_saved": total_saved, "run_id": run_id},
            ))
            store.complete_run(
                run_id,
                status="partial",
                summary=(
                    f"Annullato dopo {len(job_result.results)}/{total_steps} "
                    f"entity_type · {total_saved} candidati salvati"
                ),
            )
            return job_result

        except Exception as exc:  # noqa: BLE001
            reporter.flush()
            reporter.update(ProgressSnapshot(
                status="error",
                current=len(job_result.results),
                total=total_steps,
                current_item=f"Errore: {exc}",
                errors=1,
                extra={"run_id": run_id},
            ))
            store.complete_run(run_id, status="error", summary=str(exc))
            job_result.error = str(exc)
            return job_result


def launch_build_thread(
    *,
    vault: Path,
    entity_type: str,
    llm_provider: str,
    fixture_path: Path | None,
    cancel: CancelToken,
    on_result: Callable[[BuildJobResult], None] | None = None,
) -> tuple[threading.Thread, dict[str, Any]]:
    """Lancia ``build_with_progress`` in un thread daemon.

    Stesso pattern di :func:`launch_scan_filesystem_thread`: ritorna
    ``(thread, ctx)`` dove ``ctx["run_id"]`` viene popolato appena
    disponibile, ``ctx["result"]`` alla fine.
    """
    ctx: dict[str, Any] = {"run_id": None, "result": None}

    def _set_run_id(rid: int) -> None:
        ctx["run_id"] = rid

    def _target() -> None:
        try:
            result = build_with_progress(
                vault=vault,
                entity_type=entity_type,
                llm_provider=llm_provider,
                fixture_path=fixture_path,
                cancel=cancel,
                run_id_callback=_set_run_id,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("build_with_progress: errore non gestito")
            result = BuildJobResult(error=str(exc))
        ctx["result"] = result
        if on_result is not None:
            try:
                on_result(result)
            except Exception:  # noqa: BLE001
                logger.exception("on_result callback ha fallito")

    thread = threading.Thread(
        target=_target, name=f"custodia-build-{entity_type}", daemon=True
    )
    thread.start()
    return thread, ctx


__all__ = [
    "BuildJobResult",
    "build_with_progress",
    "launch_build_thread",
]
