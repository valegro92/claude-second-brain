"""
`custodia build {clients,fornitori,commesse,communications}` — U5.

Per ogni entity_type, esegue la pipeline LLM-driven (Extractor) sui documenti
pending nello StateStore e persiste i candidati come `entities` con
`status="pending"`. U6 li sottoporrà a review.

Provider LLM selezionabile via `--llm-provider {anthropic|fake}`. Per `fake`
è obbligatorio anche `--fixture` con il path al file YAML di canned responses.
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from custodia_cli.commands.init import state_db_path_for_vault
from custodia_cli.extractor import Extractor
from custodia_cli.llm.registry import get_provider
from custodia_cli.state import StateStore

console = Console()

build_app = typer.Typer(
    name="build",
    help="Estrae candidati di entity dai documenti accumulati nello state store.",
    no_args_is_help=True,
)


# Mappa nome comando → entity_type interno.
_COMMAND_TO_ENTITY_TYPE: dict[str, str] = {
    "clients": "cliente",
    "fornitori": "fornitore",
    "commesse": "commessa",
    "communications": "comunicazione",
}


def _ensure_state_db(vault: Path) -> Path:
    """Verifica che lo state DB esista; altrimenti errore chiaro."""
    db_path = state_db_path_for_vault(vault)
    if not db_path.exists():
        raise typer.BadParameter(
            f"State store non trovato in {db_path}. "
            f"Esegui prima: custodia init --vault {vault}"
        )
    return db_path


def _usage_summary(usage_log: list) -> str:
    """Sintetizza un usage_log LLM in stringa per CLI."""
    if not usage_log:
        return "nessuna chiamata LLM registrata"
    total_in = sum(u.input_tokens for u in usage_log)
    total_out = sum(u.output_tokens for u in usage_log)
    total_cost = sum(u.cost_eur_estimate for u in usage_log)
    return (
        f"{len(usage_log)} chiamate LLM · "
        f"{total_in} token in · {total_out} token out · "
        f"costo stimato €{total_cost:.4f}"
    )


def _run_build(
    *,
    vault: Path,
    entity_type: str,
    llm_provider: str,
    fixture: Path | None,
) -> None:
    """Logica condivisa per tutti i sub-comandi build."""
    db_path = _ensure_state_db(vault)

    provider_kwargs: dict = {}
    if llm_provider == "fake":
        if fixture is None:
            raise typer.BadParameter(
                "Per --llm-provider=fake è obbligatorio passare --fixture <path>."
            )
        provider_kwargs["fixture_path"] = fixture

    try:
        provider = get_provider(llm_provider, **provider_kwargs)
    except ValueError as exc:
        console.print(f"[red]✗[/red] {exc}")
        raise typer.Exit(code=1) from exc

    with StateStore(db_path) as store:
        run_id = store.register_run(
            command=f"build {entity_type}",
            args={
                "vault": str(vault),
                "entity_type": entity_type,
                "llm_provider": llm_provider,
                "fixture": str(fixture) if fixture else None,
            },
        )
        try:
            extractor = Extractor(llm=provider, store=store)
            candidates = extractor.extract(entity_type, run_id=run_id)
            n_saved = 0
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
                n_saved += 1
        except (KeyboardInterrupt, SystemExit):
            store.complete_run(
                run_id,
                status="error",
                summary="Interrotto dall'utente (KeyboardInterrupt)",
            )
            console.print("[yellow]⚠[/yellow]  Build interrotto dall'utente.")
            raise
        except Exception as exc:  # noqa: BLE001 — vogliamo logging + exit 1
            store.complete_run(run_id, status="error", summary=str(exc))
            console.print(f"[red]✗[/red] Build fallito: {exc}")
            raise typer.Exit(code=1) from exc

        usage_summary = _usage_summary(getattr(provider, "usage_log", []))
        summary = f"{n_saved} candidati salvati · {usage_summary}"
        store.complete_run(run_id, status="success", summary=summary)

    # Riepilogo Rich.
    table = Table(title=f"Custodia build {entity_type}")
    table.add_column("entity_id", style="bold")
    table.add_column("confidence", justify="right")
    table.add_column("fonti", justify="right")
    for cand in candidates:
        table.add_row(
            cand.entity_id,
            f"{cand.confidence:.2f}",
            str(len(cand.source_doc_ids)),
        )
    console.print(table)
    console.print(
        f"[green]✓[/green] [bold]{n_saved}[/bold] candidati salvati · {usage_summary}"
    )


# -- Opzioni condivise tramite factory di Typer ----------------------------


def _vault_option() -> Path:
    return typer.Option(
        ...,
        "--vault",
        help="Path al vault Obsidian del cliente (deve esistere `custodia init`).",
    )


def _llm_provider_option() -> str:
    return typer.Option(
        "anthropic",
        "--llm-provider",
        help="Provider LLM da usare: anthropic | fake (richiede --fixture).",
    )


def _fixture_option() -> Path | None:
    return typer.Option(
        None,
        "--fixture",
        help="Path al file YAML di canned responses (solo per --llm-provider=fake).",
    )


@build_app.command("clients")
def build_clients(
    vault: Path = _vault_option(),
    llm_provider: str = _llm_provider_option(),
    fixture: Path | None = _fixture_option(),
) -> None:
    """Estrae candidati `cliente` dai documenti pending."""
    _run_build(
        vault=vault,
        entity_type="cliente",
        llm_provider=llm_provider,
        fixture=fixture,
    )


@build_app.command("fornitori")
def build_fornitori(
    vault: Path = _vault_option(),
    llm_provider: str = _llm_provider_option(),
    fixture: Path | None = _fixture_option(),
) -> None:
    """Estrae candidati `fornitore` dai documenti pending."""
    _run_build(
        vault=vault,
        entity_type="fornitore",
        llm_provider=llm_provider,
        fixture=fixture,
    )


@build_app.command("commesse")
def build_commesse(
    vault: Path = _vault_option(),
    llm_provider: str = _llm_provider_option(),
    fixture: Path | None = _fixture_option(),
) -> None:
    """Estrae candidati `commessa` dai documenti pending."""
    _run_build(
        vault=vault,
        entity_type="commessa",
        llm_provider=llm_provider,
        fixture=fixture,
    )


@build_app.command("communications")
def build_communications(
    vault: Path = _vault_option(),
    llm_provider: str = _llm_provider_option(),
    fixture: Path | None = _fixture_option(),
) -> None:
    """Estrae comunicazioni inbox dai documenti pending."""
    _run_build(
        vault=vault,
        entity_type="comunicazione",
        llm_provider=llm_provider,
        fixture=fixture,
    )


@build_app.command("all")
def build_all(
    vault: Path = _vault_option(),
    llm_provider: str = _llm_provider_option(),
    fixture: Path | None = _fixture_option(),
) -> None:
    """Esegue in sequenza build per cliente, fornitore, commessa, comunicazione."""
    for entity_type in ("cliente", "fornitore", "commessa", "comunicazione"):
        console.rule(f"[bold]build {entity_type}[/bold]")
        _run_build(
            vault=vault,
            entity_type=entity_type,
            llm_provider=llm_provider,
            fixture=fixture,
        )


__all__ = ["build_app"]
