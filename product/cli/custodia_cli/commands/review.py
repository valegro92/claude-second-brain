"""
`custodia review --vault PATH` — REPL human-in-the-loop sui candidati pending.

Carica i candidati ``pending`` dallo StateStore e lancia il REPL Rich-based
che permette accept/edit/skip/merge/quit per ognuno. Le decisioni vengono
persistite immediatamente: una sessione interrotta può essere ripresa con
``--resume`` (no-op funzionale: i candidati già decisi non sono più pending).
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from custodia_cli.commands.init import (
    state_db_path_for_vault,
    state_dir_for_vault,
)
from custodia_cli.review import run_review_repl
from custodia_cli.state import StateStore

console = Console()


_VALID_ENTITY_TYPES = {"cliente", "fornitore", "commessa", "comunicazione", "all"}


def review_command(
    vault: Path = typer.Option(
        ...,
        "--vault",
        help="Path al vault Obsidian del cliente.",
    ),
    entity_type: str = typer.Option(
        "all",
        "--entity-type",
        help="Filtra per tipo: cliente|fornitore|commessa|comunicazione|all.",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        help="Auto-accept tutti i candidati (no prompt). Usato in CI e test.",
    ),
    resume: bool = typer.Option(
        False,
        "--resume",
        help="Riprende una sessione precedente. Funzionalmente equivalente "
        "ad un nuovo run: i candidati già decisi non sono più pending.",
    ),
) -> None:
    """REPL human-in-the-loop sui candidati pending dello StateStore."""
    db_path = state_db_path_for_vault(vault)
    if not db_path.exists():
        console.print(
            f"[red]✗[/red] State store non trovato in {db_path}. "
            "Esegui prima `custodia init`."
        )
        raise typer.Exit(code=1)

    if entity_type not in _VALID_ENTITY_TYPES:
        console.print(
            f"[red]✗[/red] entity-type sconosciuto: {entity_type!r}. "
            f"Valori validi: {sorted(_VALID_ENTITY_TYPES)}"
        )
        raise typer.Exit(code=1)

    type_filter = None if entity_type == "all" else entity_type
    state_dir = state_dir_for_vault(vault)
    vault_resolved = vault.expanduser().resolve()

    try:
        with StateStore(db_path) as store:
            summary = run_review_repl(
                store,
                vault_resolved,
                state_dir,
                entity_type=type_filter,
                auto_accept=yes,
                console=console,
            )
    except Exception as exc:  # noqa: BLE001 — errore utente leggibile
        console.print(f"[red]✗[/red] Review fallita: {exc}")
        raise typer.Exit(code=1) from exc

    console.print(
        f"\n[bold]Riepilogo review[/bold]: "
        f"[green]{summary['accepted']} accept[/green] · "
        f"[yellow]{summary['edited']} edit[/yellow] · "
        f"[red]{summary['rejected']} skip[/red] · "
        f"[magenta]{summary['merged']} merge[/magenta] "
        f"su {summary['total']} candidati"
    )


__all__ = ["review_command"]
