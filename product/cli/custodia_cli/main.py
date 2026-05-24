"""
Entry point del CLI Custodia.

Espone i sub-comandi:
- init       (funzionale, U1)
- scan       (stub, U3/U4)
- build      (stub, U5)
- review     (stub, U6)
- write      (stub, U6)
"""

from __future__ import annotations

import typer

from custodia_cli.commands.build import build_app
from custodia_cli.commands.init import init_command
from custodia_cli.commands.review import review_command
from custodia_cli.commands.scan import scan_app
from custodia_cli.commands.write import write_command

app = typer.Typer(
    name="custodia",
    help="Custodia CLI — ingestion e build vault Obsidian per consulenti.",
    no_args_is_help=True,
    add_completion=False,
)

# Comandi singoli
app.command("init", help="Inizializza lo state store per un vault.")(init_command)
app.command("review", help="REPL human-in-the-loop sui candidati pending.")(review_command)
app.command("write", help="Scrive le entity approvate come .md nel vault.")(write_command)

# Sub-app multi-comando
app.add_typer(scan_app, name="scan")
app.add_typer(build_app, name="build")


def main() -> None:
    """Entry point pubblico (usato anche dallo script `custodia`)."""
    app()


if __name__ == "__main__":
    main()
