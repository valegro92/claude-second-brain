"""
`custodia init --vault PATH`

Crea lo state store SQLite in `<vault_parent>/.custodia-state/state.db`.
Idempotente: se il DB esiste già, controlla che lo schema sia compatibile e
stampa un messaggio di no-op.
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from custodia_cli.state import SCHEMA_VERSION, StateStore

console = Console()


def state_dir_for_vault(vault: Path) -> Path:
    """
    Ritorna il path della directory `.custodia-state/` per il vault dato.

    Convention: lo stato vive *fuori* dal vault, accanto ad esso. Se il vault
    è `/clienti/acme/vault`, lo stato finisce in `/clienti/acme/.custodia-state/`.
    """
    vault = vault.expanduser().resolve()
    return vault.parent / ".custodia-state"


def state_db_path_for_vault(vault: Path) -> Path:
    """Path completo a `state.db` per il vault dato."""
    return state_dir_for_vault(vault) / "state.db"


def run_init(vault: Path) -> None:
    """Logica reale, separata dal Typer callback per test diretti."""
    state_dir = state_dir_for_vault(vault)
    db_path = state_dir / "state.db"

    already_existed = db_path.exists()
    state_dir.mkdir(parents=True, exist_ok=True)

    with StateStore(db_path) as store:
        # Il costruttore applica lo schema. Una verifica esplicita non è
        # necessaria ma utile per log: leggiamo la user_version.
        version = store.schema_version

    if already_existed:
        console.print(
            f"[yellow]·[/yellow] State store già presente in [bold]{db_path}[/bold] "
            f"(schema v{version}). Nessuna modifica."
        )
    else:
        console.print(
            f"[green]✓[/green] State store inizializzato in [bold]{db_path}[/bold] "
            f"(schema v{version})."
        )


def init_command(
    vault: Path = typer.Option(
        ...,
        "--vault",
        help="Path al vault Obsidian del cliente (la directory radice, es. /clienti/acme/vault).",
    ),
) -> None:
    """Inizializza lo state store SQLite per un vault Custodia."""
    try:
        run_init(vault)
    except Exception as exc:  # noqa: BLE001 — vogliamo un errore utente leggibile
        console.print(f"[red]✗[/red] Inizializzazione fallita: {exc}")
        raise typer.Exit(code=1) from exc


__all__ = ["init_command", "run_init", "state_db_path_for_vault", "state_dir_for_vault"]
