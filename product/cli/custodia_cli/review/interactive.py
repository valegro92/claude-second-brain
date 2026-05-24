"""
REPL Rich-based per il review human-in-the-loop dei candidati.

Ciclo:
1. Carica i candidati ``pending`` dallo StateStore (filtrabili per tipo).
2. Per ognuno renderizza pannello sinistro (YAML candidato) e destro (diff vs
   vault esistente o "[Nuova entità]").
3. Legge una scelta ``a/e/s/m/q``.
4. Persiste la decisione via ``store.record_review_decision``.

Modalità ``--yes``: auto-accept di tutti i candidati, zero prompt — usata da
test E2E e da CI.

Modalità ``--resume``: ripristina lo stato dell'ultima sessione. In pratica i
candidati già decisi non sono più ``pending``, quindi un re-run riprende
naturalmente dal punto in cui si era interrotti.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text

from custodia_cli.review.diff import existing_vault_path, render_diff
from custodia_cli.review.editor import EditorError, open_in_editor
from custodia_cli.review.merger import merge_body, merge_dicts
from custodia_cli.review.yaml_io import dump_frontmatter, ordered_keys_for_type
from custodia_cli.state.store import StateStore

# Tipo callback per leggere una scelta dell'utente. Riceve un prompt e ritorna
# una stringa (es. "a", "e", "s", "m", "q"). Test possono iniettare un mock.
ChoicePrompt = Callable[[str], str]


def _default_choice_prompt(message: str) -> str:
    """Legge una riga da stdin (sincrono, blocking)."""
    try:
        return input(message).strip().lower()
    except EOFError:
        return "q"


def _render_candidate_panel(entity: dict[str, Any]) -> Panel:
    """Pannello sinistro: YAML del candidato con syntax highlighting."""
    fm_text = dump_frontmatter(
        entity.get("frontmatter") or {},
        ordered_keys_for_type(entity["entity_type"]),
    )
    title = f"candidato: {entity['entity_type']}/{entity['entity_id']}"
    return Panel(
        Syntax(fm_text or "(vuoto)", "yaml", theme="ansi_dark"),
        title=title,
        border_style="cyan",
    )


def _render_layout(
    entity: dict[str, Any],
    vault_root: Path,
) -> Layout:
    """Layout split-pane: candidato | diff vault."""
    layout = Layout()
    layout.split_row(
        Layout(name="left", ratio=1),
        Layout(name="right", ratio=1),
    )
    layout["left"].update(_render_candidate_panel(entity))
    layout["right"].update(
        render_diff(
            entity.get("frontmatter") or {},
            existing_vault_path(
                vault_root, entity["entity_type"], entity["entity_id"]
            ),
        )
    )
    return layout


def _print_footer(console: Console) -> None:
    """Hint comandi sotto al layout."""
    footer = Text.assemble(
        ("[a]", "bold green"),
        "ccept  ",
        ("[e]", "bold yellow"),
        "dit  ",
        ("[s]", "bold red"),
        "kip  ",
        ("[m]", "bold magenta"),
        "erge  ",
        ("[q]", "bold blue"),
        "uit",
    )
    console.print(footer)


def _handle_edit(
    store: StateStore,
    entity: dict[str, Any],
    state_dir: Path,
    console: Console,
) -> bool:
    """Loop di edit: ri-prompt finché l'utente produce YAML valido o annulla.

    Returns:
        True se la decisione è stata registrata, False se l'utente ha annullato.
    """
    current = entity.get("frontmatter") or {}
    while True:
        try:
            edited = open_in_editor(
                current,
                entity_type=entity["entity_type"],
                state_dir=state_dir,
                entity_pk=entity["id"],
            )
        except EditorError as exc:
            console.print(f"[red]✗[/red] {exc}")
            choice = input("Riprovare? [r]i-edita / [s]kip: ").strip().lower()
            if choice.startswith("r"):
                continue
            return False
        store.record_review_decision(
            entity_pk=entity["id"],
            decision="edited",
            edited_frontmatter=edited,
        )
        return True


def _handle_merge(
    store: StateStore,
    entity: dict[str, Any],
    vault_root: Path,
    console: Console,
    *,
    interactive: bool,
) -> bool:
    """Merge candidato + vault esistente; registra come 'edited'."""
    from custodia_cli.review.diff import _parse_existing_vault_file

    target = existing_vault_path(
        vault_root, entity["entity_type"], entity["entity_id"]
    )
    if not target.exists():
        console.print(
            "[yellow]·[/yellow] Nessun file nel vault, "
            "nulla da mergiare. Tratto come 'accept'."
        )
        store.record_review_decision(
            entity_pk=entity["id"], decision="approved"
        )
        return True
    vault_fm, vault_body = _parse_existing_vault_file(target)

    def _prompt(key: str, vault_value: Any, cand_value: Any) -> Any:
        if not interactive:
            return cand_value
        console.print(
            f"\nConflitto su [bold]{key}[/bold]:\n"
            f"  vault    : {vault_value!r}\n"
            f"  candidato: {cand_value!r}"
        )
        choice = input("Quale tieni? [v]ault / [c]andidato: ").strip().lower()
        return vault_value if choice.startswith("v") else cand_value

    merged_fm = merge_dicts(
        vault_fm, entity.get("frontmatter") or {}, prompt=_prompt
    )
    merged_body = merge_body(vault_body, entity.get("body_md") or "")
    store.record_review_decision(
        entity_pk=entity["id"],
        decision="edited",
        edited_frontmatter=merged_fm,
    )
    # Aggiorna anche il body (record_review_decision non lo tocca).
    store._conn.execute(  # type: ignore[attr-defined]
        "UPDATE entities SET body_md = ? WHERE id = ?",
        (merged_body, entity["id"]),
    )
    store._conn.commit()  # type: ignore[attr-defined]
    return True


def run_review_repl(
    store: StateStore,
    vault_root: Path,
    state_dir: Path,
    *,
    entity_type: str | None = None,
    auto_accept: bool = False,
    choice_prompt: ChoicePrompt | None = None,
    console: Console | None = None,
) -> dict[str, int]:
    """Esegue il REPL review fino a chiusura o esaurimento candidati.

    Args:
        store: StateStore aperto sul DB del vault.
        vault_root: directory radice del vault (per il diff).
        state_dir: directory `.custodia-state/` (per file temp di edit).
        entity_type: filtra per tipo (es. ``'cliente'``); None = tutti.
        auto_accept: se True, accetta tutti senza prompt.
        choice_prompt: callback per leggere la scelta dell'utente (default:
            ``input()``). Iniettabile dai test.
        console: Rich Console iniettabile (utile per cattura output nei test).

    Returns:
        Dict riepilogo: chiavi ``accepted, edited, rejected, merged, quit``.
    """
    console = console or Console()
    choice_prompt = choice_prompt or _default_choice_prompt

    pending = store.list_pending_entities(entity_type=entity_type)
    summary = {
        "accepted": 0,
        "edited": 0,
        "rejected": 0,
        "merged": 0,
        "quit": 0,
        "total": len(pending),
    }

    if not pending:
        console.print("[dim]Nessun candidato pending da rivedere.[/dim]")
        return summary

    for idx, entity in enumerate(pending, start=1):
        console.rule(
            f"[{idx}/{len(pending)}] "
            f"{entity['entity_type']} / {entity['entity_id']}"
        )
        console.print(_render_layout(entity, vault_root))
        _print_footer(console)

        if auto_accept:
            store.record_review_decision(
                entity_pk=entity["id"], decision="approved"
            )
            summary["accepted"] += 1
            continue

        decision_made = False
        while not decision_made:
            choice = choice_prompt("Scelta [a/e/s/m/q]: ")
            if choice == "a":
                store.record_review_decision(
                    entity_pk=entity["id"], decision="approved"
                )
                summary["accepted"] += 1
                decision_made = True
            elif choice == "e":
                if _handle_edit(store, entity, state_dir, console):
                    summary["edited"] += 1
                decision_made = True
            elif choice == "s":
                store.record_review_decision(
                    entity_pk=entity["id"], decision="rejected"
                )
                summary["rejected"] += 1
                decision_made = True
            elif choice == "m":
                _handle_merge(
                    store, entity, vault_root, console, interactive=True
                )
                summary["merged"] += 1
                decision_made = True
            elif choice == "q":
                summary["quit"] = 1
                console.print("[dim]Sessione interrotta. Stato salvato.[/dim]")
                return summary
            else:
                console.print(
                    "[red]·[/red] Scelta non valida. Usa a/e/s/m/q."
                )

    return summary


__all__ = ["run_review_repl", "ChoicePrompt"]
