"""
`custodia write --vault PATH` — materializza nel vault le entity approved.

Scrive un file `.md` per ogni entity con ``status='approved'`` e
``written_at IS NULL``. Idempotente: una seconda esecuzione non riscrive nulla
salvo che siano state aggiunte nuove decisioni. Esistente con contenuto
diverso ⇒ backup in `<vault>/.custodia-backups/` prima della sovrascrittura.
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from custodia_cli.commands.init import state_db_path_for_vault
from custodia_cli.review import write_entities
from custodia_cli.state import StateStore

console = Console()


def write_command(
    vault: Path = typer.Option(
        ...,
        "--vault",
        help="Path al vault Obsidian del cliente.",
    ),
    no_backup: bool = typer.Option(
        False,
        "--no-backup",
        help="Disabilita il backup dei file esistenti prima di sovrascrivere.",
    ),
) -> None:
    """Scrive nel vault le entity approved come file `.md` Obsidian."""
    db_path = state_db_path_for_vault(vault)
    if not db_path.exists():
        console.print(
            f"[red]✗[/red] State store non trovato in {db_path}. "
            "Esegui prima `custodia init`."
        )
        raise typer.Exit(code=1)

    vault_resolved = vault.expanduser().resolve()

    try:
        with StateStore(db_path) as store:
            pending = store.list_pending_writes()
            if not pending:
                console.print(
                    "[dim]Nessuna entity da scrivere "
                    "(0 approved + non-written).[/dim]"
                )
                raise typer.Exit(code=0)

            result = write_entities(
                pending, vault_resolved, backup=not no_backup
            )
            # Marca come written solo quelle senza errori.
            error_ids = {eid for eid, _ in result.errors}
            for ent in pending:
                if str(ent["entity_id"]) in error_ids:
                    continue
                store.mark_entity_written(ent["id"])
    except typer.Exit:
        raise
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]✗[/red] Write fallita: {exc}")
        raise typer.Exit(code=1) from exc

    console.print(
        f"[green]✓[/green] {len(result.written)} file scritti · "
        f"[dim]{len(result.skipped)} saltati (no change)[/dim] · "
        f"[yellow]{len(result.backups)} backup[/yellow]"
        + (
            f" · [red]{len(result.errors)} errori[/red]"
            if result.errors
            else ""
        )
    )
    for path in result.written:
        console.print(f"  [green]+[/green] {path}")
    for path in result.backups:
        console.print(f"  [yellow]↦[/yellow] backup {path}")
    for eid, msg in result.errors:
        console.print(f"  [red]✗[/red] {eid}: {msg}")


__all__ = ["write_command"]
