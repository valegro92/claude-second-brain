"""
`custodia scan {drive,fs}` — ingestion sorgenti.

- ``scan drive`` (U3): connettore Google Drive read-only, OAuth desktop flow.
- ``scan fs`` (U4): stub, implementato in unit successiva.

Entrambi persistono i ``SourceDocument`` prodotti in StateStore via
``add_document``, dopo aver registrato un run nella tabella ``runs`` per
tracciabilità.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import typer

_UNIQUE_SOURCE_ID_MARKERS = (
    "documents.source_id",
    "UNIQUE constraint failed: documents.source_id",
    "source_id",
)


def _is_duplicate_source_id_error(exc: sqlite3.IntegrityError) -> bool:
    """True solo se l'IntegrityError corrisponde al duplicato di ``source_id``.

    Discrimina dal generico IntegrityError per evitare di mascherare bug reali
    (NOT NULL, FOREIGN KEY, CHECK).
    """
    msg = str(exc).lower()
    return any(marker.lower() in msg for marker in _UNIQUE_SOURCE_ID_MARKERS)
from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)

from custodia_cli.commands.init import state_db_path_for_vault, state_dir_for_vault
from custodia_cli.state import StateStore

console = Console()

scan_app = typer.Typer(
    name="scan",
    help="Scansiona sorgenti (Drive, filesystem) per produrre SourceDocument.",
    no_args_is_help=True,
)


def _ensure_state_db(vault: Path) -> Path:
    """Verifica che lo state DB esista; altrimenti errore chiaro."""
    db_path = state_db_path_for_vault(vault)
    if not db_path.exists():
        raise typer.BadParameter(
            f"State store non trovato in {db_path}. "
            f"Esegui prima: custodia init --vault {vault}"
        )
    return db_path


def _resolve_resume_args(
    db_path: Path,
    *,
    run_id: int | None,
    fallback_max_size_mb: int,
) -> tuple[Path, list[str], int, bool, bool]:
    """Estrae gli args di uno scan fs interrotto per il --resume.

    Logica:
    - Se ``run_id`` è fornito: cerca esattamente quel run; se non esiste o
      non è uno ``scan fs`` esce con typer.Exit(1).
    - Altrimenti: prende il più recente run interrotto con command ``scan fs``.
      Se non ce ne sono, esce con typer.Exit(1) e messaggio chiaro.

    Ritorna ``(root, exclude_list, max_size_mb, follow_symlinks,
    allow_dangerous_root)`` come tupla pronta per essere usata dal comando.
    """
    with StateStore(db_path) as store:
        if run_id is not None:
            args = store.get_run_args(int(run_id))
            row = store._conn.execute(
                "SELECT id, command FROM runs WHERE id = ?", (int(run_id),)
            ).fetchone()
            if row is None:
                console.print(f"[red]✗[/red] Run #{run_id} non esiste.")
                raise typer.Exit(code=1)
            if not str(row["command"]).startswith("scan fs"):
                console.print(
                    f"[red]✗[/red] Run #{run_id} non è uno 'scan fs' "
                    f"({row['command']!r})."
                )
                raise typer.Exit(code=1)
        else:
            # Cerca il più recente 'scan fs' con progress.status='interrupted'
            # OPPURE con status='running' (potrebbe non essere stato ancora
            # reaped: lo trattiamo come interrupted di fatto se l'utente
            # invoca --resume — è la sua scelta esplicita).
            row = store._conn.execute(
                """
                SELECT id, command, args_json, progress_json
                FROM runs
                WHERE command LIKE 'scan fs%'
                  AND (
                    status = 'running'
                    OR (status = 'partial' AND progress_json LIKE '%interrupted%')
                  )
                ORDER BY id DESC
                LIMIT 1
                """
            ).fetchone()
            if row is None:
                console.print(
                    "[yellow]⚠[/yellow]  Nessuno scan interrotto da riprendere "
                    "per questo vault."
                )
                raise typer.Exit(code=1)
            args = store.get_run_args(int(row["id"]))
            console.print(
                f"[cyan]→[/cyan] Resume del run #{row['id']} "
                f"({row['command']})."
            )

    if not isinstance(args, dict) or not args.get("root"):
        console.print(
            "[red]✗[/red] Args non recuperabili per il run da riprendere."
        )
        raise typer.Exit(code=1)

    root = Path(str(args["root"]))
    excludes = list(args.get("exclude_patterns") or args.get("excludes") or [])
    max_size_mb = int(args.get("max_size_mb") or fallback_max_size_mb)
    follow_symlinks = bool(args.get("follow_symlinks") or False)
    allow_dangerous_root = bool(args.get("allow_dangerous_root") or False)
    return root, excludes, max_size_mb, follow_symlinks, allow_dangerous_root


@scan_app.command("drive")
def scan_drive_command(
    vault: Path = typer.Option(
        ...,
        "--vault",
        help="Path al vault Obsidian del cliente (deve esistere `custodia init`).",
    ),
    root_folder_id: str = typer.Option(
        ...,
        "--root-folder-id",
        help="ID della folder root Google Drive da scansionare ricorsivamente.",
    ),
    credentials: Path | None = typer.Option(
        None,
        "--credentials",
        help=(
            "Path al credentials.json OAuth desktop (in alternativa: env "
            "CUSTODIA_GOOGLE_CREDENTIALS_JSON)."
        ),
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Traversa la folder ma non scarica/parsa nulla; produce solo metadata.",
    ),
) -> None:
    """Scansiona una folder root Google Drive e persiste i SourceDocument."""
    # Import locale: evita di caricare googleapiclient quando si usa solo `scan fs`.
    from custodia_cli.connectors.google_drive import GoogleDriveConnector

    db_path = _ensure_state_db(vault)
    state_dir = state_dir_for_vault(vault)
    token_cache = state_dir / "google_token.json"
    cache_dir = state_dir / "cache"

    connector = GoogleDriveConnector(
        root_folder_id=root_folder_id,
        credentials_path=credentials,
        token_cache_path=token_cache,
        dry_run=dry_run,
        cache_dir=None if dry_run else cache_dir,
    )

    with StateStore(db_path) as store:
        run_id = store.register_run(
            command="scan drive",
            args={
                "root_folder_id": root_folder_id,
                "dry_run": dry_run,
                "credentials": str(credentials) if credentials else None,
            },
        )

        n_docs = 0
        n_dup = 0
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.completed]{task.completed} doc"),
                TimeElapsedColumn(),
                console=console,
                transient=False,
            ) as progress:
                task = progress.add_task("Scansione Google Drive", total=None)
                for doc in connector.iter_documents():
                    try:
                        store.add_document(
                            run_id=run_id,
                            source_id=doc.source_id,
                            source_path=doc.source_path,
                            mime_type=doc.mime_type,
                            text=doc.text,
                            metadata=dict(doc.metadata),
                        )
                        n_docs += 1
                    except sqlite3.IntegrityError as exc:
                        if _is_duplicate_source_id_error(exc):
                            # source_id già presente: incremental scan, skip.
                            n_dup += 1
                        else:
                            # NOT NULL / FK / CHECK: bug reale, propaga.
                            raise
                    progress.update(task, advance=1)
        except (KeyboardInterrupt, SystemExit) as exc:
            store.complete_run(
                run_id,
                status="error",
                summary="Interrotto dall'utente (KeyboardInterrupt)",
            )
            console.print("[yellow]⚠[/yellow]  Scan interrotto dall'utente.")
            raise
        except Exception as exc:  # noqa: BLE001 — vogliamo logging utente e re-raise
            store.complete_run(run_id, status="error", summary=str(exc))
            console.print(f"[red]✗[/red] Scan fallito: {exc}")
            raise typer.Exit(code=1) from exc

        summary = (
            f"{n_docs} doc nuovi, {n_dup} già presenti, "
            f"stats={connector.stats}"
        )
        store.complete_run(run_id, status="success", summary=summary)

    console.print(
        f"[green]✓[/green] Scan completato — [bold]{n_docs}[/bold] doc nuovi, "
        f"[dim]{n_dup} già presenti[/dim]."
    )
    stats = connector.stats
    console.print(
        f"  · processati: {stats['processed']} · "
        f"skippati (size): {stats['skipped_size']} · "
        f"skippati (mime): {stats['skipped_mime']} · "
        f"trashed: {stats['skipped_trashed']} · "
        f"errori: {stats['errors']}"
    )


@scan_app.command("fs")
def scan_fs_command(
    vault: Path = typer.Option(
        ...,
        "--vault",
        help="Path al vault Obsidian del cliente (deve esistere `custodia init`).",
    ),
    root: Path | None = typer.Option(
        None,
        "--root",
        help=(
            "Path radice locale da scansionare ricorsivamente. "
            "Obbligatorio salvo --resume."
        ),
    ),
    exclude: list[str] = typer.Option(  # noqa: B008
        None,
        "--exclude",
        help="Pattern glob da escludere (ripetibile, oltre ai default).",
    ),
    max_size_mb: int = typer.Option(
        50,
        "--max-size-mb",
        help="Skip silente di file più grandi di questa soglia (default 50MB).",
    ),
    follow_symlinks: bool = typer.Option(
        False,
        "--follow-symlinks",
        help=(
            "Segui i symlink durante il traversal. OFF di default per "
            "prevenire loop e symlink-escape. Attiva solo se sai cosa fai."
        ),
    ),
    allow_dangerous_root: bool = typer.Option(
        False,
        "--i-know-what-im-doing",
        help=(
            "Bypassa il guardrail sui root troppo permissivi (/, $HOME, /etc…). "
            "Default OFF: protegge da scansioni accidentali del filesystem."
        ),
    ),
    resume: bool = typer.Option(
        False,
        "--resume",
        help=(
            "Riprendi lo scan filesystem più recente interrotto per questo "
            "vault. Riutilizza gli args originali (--root, --exclude, "
            "--max-size-mb, ...). Il manifest U2 fa skip dei file già visti."
        ),
    ),
    resume_run_id: int | None = typer.Option(
        None,
        "--run-id",
        help=(
            "Con --resume: id esplicito del run da riprendere. Senza, prende "
            "il più recente interrotto per questo vault."
        ),
    ),
) -> None:
    """Scansiona una cartella locale o mount NAS e persiste i SourceDocument."""
    # Import locale: tiene gli import del comando 'scan' coerenti con 'drive'.
    from custodia_cli.connectors.filesystem import FilesystemConnector

    db_path = _ensure_state_db(vault)

    # --resume path: estrae args dal run interrotto e li sostituisce ai
    # parametri CLI. Funziona prima di qualunque check su `root`.
    if resume:
        root, exclude, max_size_mb, follow_symlinks, allow_dangerous_root = (
            _resolve_resume_args(
                db_path,
                run_id=resume_run_id,
                fallback_max_size_mb=max_size_mb,
            )
        )

    if root is None:
        console.print(
            "[red]✗[/red] --root è obbligatorio (salvo --resume)."
        )
        raise typer.Exit(code=1)

    root = root.expanduser().resolve()
    if not root.exists():
        console.print(f"[red]✗[/red] Root inesistente: {root}")
        raise typer.Exit(code=1)
    if not root.is_dir():
        console.print(f"[red]✗[/red] Root non è una directory: {root}")
        raise typer.Exit(code=1)

    user_excludes = list(exclude) if exclude else []

    with StateStore(db_path) as store:
        run_id = store.register_run(
            command="scan fs",
            args={
                "root": str(root),
                "excludes": user_excludes,
                "exclude_patterns": user_excludes,
                "max_size_mb": max_size_mb,
                "follow_symlinks": follow_symlinks,
                "allow_dangerous_root": allow_dangerous_root,
                "resume": resume,
            },
        )

        # In --resume passiamo state_store al connector così il manifest
        # U2 fa lo skip dei file già visti nei run precedenti.
        connector_kwargs: dict = dict(
            root_path=root,
            exclude_patterns=user_excludes,
            max_file_size_mb=max_size_mb,
            follow_symlinks=follow_symlinks,
            allow_dangerous_root=allow_dangerous_root,
        )
        if resume:
            connector_kwargs["state_store"] = store
            connector_kwargs["manifest_run_id"] = run_id
            connector_kwargs["force_rescan"] = False

        try:
            connector = FilesystemConnector(**connector_kwargs)
        except ValueError as exc:
            store.complete_run(run_id, status="error", summary=str(exc))
            console.print(f"[red]✗[/red] {exc}")
            raise typer.Exit(code=1) from exc
        except (FileNotFoundError, NotADirectoryError) as exc:
            store.complete_run(run_id, status="error", summary=str(exc))
            console.print(f"[red]✗[/red] {exc}")
            raise typer.Exit(code=1) from exc

        n_docs = 0
        n_dup = 0
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.completed]{task.completed} doc"),
                TimeElapsedColumn(),
                console=console,
                transient=False,
            ) as progress:
                task = progress.add_task("Scansione filesystem", total=None)
                for doc in connector.iter_documents():
                    try:
                        store.add_document(
                            run_id=run_id,
                            source_id=doc.source_id,
                            source_path=doc.source_path,
                            mime_type=doc.mime_type,
                            text=doc.text,
                            metadata=dict(doc.metadata),
                        )
                        n_docs += 1
                    except sqlite3.IntegrityError as exc:
                        if _is_duplicate_source_id_error(exc):
                            # source_id già presente: incremental rescan.
                            n_dup += 1
                        else:
                            raise
                    progress.update(task, advance=1)
        except (KeyboardInterrupt, SystemExit):
            store.complete_run(
                run_id,
                status="error",
                summary="Interrotto dall'utente (KeyboardInterrupt)",
            )
            console.print("[yellow]⚠[/yellow]  Scan interrotto dall'utente.")
            raise
        except Exception as exc:  # noqa: BLE001 — vogliamo logging utente e re-raise
            store.complete_run(run_id, status="error", summary=str(exc))
            console.print(f"[red]✗[/red] Scan fallito: {exc}")
            raise typer.Exit(code=1) from exc

        summary = (
            f"{n_docs} doc nuovi, {n_dup} già presenti, "
            f"stats={connector.stats}"
        )
        store.complete_run(run_id, status="success", summary=summary)

    console.print(
        f"[green]✓[/green] Scan completato — [bold]{n_docs}[/bold] doc nuovi, "
        f"[dim]{n_dup} già presenti[/dim]."
    )
    stats = connector.stats
    console.print(
        f"  · processati: {stats['processed']} · "
        f"skippati (excluded): {stats['skipped_excluded']} · "
        f"skippati (size): {stats['skipped_size']} · "
        f"skippati (ext): {stats['skipped_ext']} · "
        f"skippati (unknown): {stats['skipped_unknown']} · "
        f"errori: {stats['errors']}"
    )


@scan_app.command("outlook")
def scan_outlook_command(
    vault: Path = typer.Option(
        ...,
        "--vault",
        help="Path al vault Obsidian del cliente (deve esistere `custodia init`).",
    ),
    folder: str | None = typer.Option(
        None,
        "--folder",
        help=(
            "Folder Outlook da scansionare (nome well-known come 'inbox', "
            "'sentitems', 'archive' o folder ID). Default: 'inbox'."
        ),
    ),
    credentials: Path | None = typer.Option(
        None,
        "--credentials",
        help=(
            "Path al credentials.json Microsoft (in alternativa: env "
            "CUSTODIA_MICROSOFT_CREDENTIALS_JSON)."
        ),
    ),
    since: str | None = typer.Option(
        None,
        "--since",
        help="Filtra messaggi >= questa data (formato YYYY-MM-DD).",
    ),
    max_messages: int | None = typer.Option(
        None,
        "--max",
        help="Limite hard al numero di messaggi (utile per smoke test).",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Scarica solo headers + bodyPreview, no body completo.",
    ),
) -> None:
    """Scansiona una folder Outlook 365 e persiste i SourceDocument."""
    # Import locale: evita di caricare msal/requests se si usa solo 'scan fs'.
    from datetime import datetime, timezone as _tz

    from custodia_cli.connectors.outlook import OutlookConnector

    db_path = _ensure_state_db(vault)
    state_dir = state_dir_for_vault(vault)
    token_cache = state_dir / "microsoft_token.json"
    cache_dir = state_dir / "cache" / "outlook"

    since_dt: "datetime | None" = None
    if since:
        try:
            since_dt = datetime.strptime(since, "%Y-%m-%d").replace(tzinfo=_tz.utc)
        except ValueError as exc:
            console.print(
                f"[red]✗[/red] --since deve essere YYYY-MM-DD ({exc})"
            )
            raise typer.Exit(code=1) from exc

    connector = OutlookConnector(
        folder_id=folder,
        credentials_path=credentials,
        token_cache_path=token_cache,
        cache_dir=None if dry_run else cache_dir,
        dry_run=dry_run,
        max_messages=max_messages,
        since=since_dt,
    )

    with StateStore(db_path) as store:
        run_id = store.register_run(
            command="scan outlook",
            args={
                "folder": folder or "inbox",
                "since": since,
                "max_messages": max_messages,
                "dry_run": dry_run,
                # FIX SEC-5/OA-6: NON persistere il path raw del credentials JSON
                # in runs.args_json (potrebbe leakare path con info clienti).
                # Registriamo solo un flag booleano.
                "credentials_provided": credentials is not None,
            },
        )

        n_docs = 0
        n_dup = 0
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.completed]{task.completed} email"),
                TimeElapsedColumn(),
                console=console,
                transient=False,
            ) as progress:
                task = progress.add_task("Scansione Outlook 365", total=None)
                for doc in connector.iter_documents():
                    try:
                        store.add_document(
                            run_id=run_id,
                            source_id=doc.source_id,
                            source_path=doc.source_path,
                            mime_type=doc.mime_type,
                            text=doc.text,
                            metadata=dict(doc.metadata),
                        )
                        n_docs += 1
                    except sqlite3.IntegrityError as exc:
                        if _is_duplicate_source_id_error(exc):
                            n_dup += 1
                        else:
                            raise
                    progress.update(task, advance=1)
        except (KeyboardInterrupt, SystemExit):
            store.complete_run(
                run_id,
                status="error",
                summary="Interrotto dall'utente (KeyboardInterrupt)",
            )
            console.print("[yellow]⚠[/yellow]  Scan interrotto dall'utente.")
            raise
        except Exception as exc:  # noqa: BLE001
            store.complete_run(run_id, status="error", summary=str(exc))
            console.print(f"[red]✗[/red] Scan fallito: {exc}")
            raise typer.Exit(code=1) from exc

        summary = (
            f"{n_docs} email nuove, {n_dup} già presenti, "
            f"stats={connector.stats}"
        )
        store.complete_run(run_id, status="success", summary=summary)

    console.print(
        f"[green]✓[/green] Scan completato — [bold]{n_docs}[/bold] email nuove, "
        f"[dim]{n_dup} già presenti[/dim]."
    )
    stats = connector.stats
    console.print(
        f"  · processati: {stats['processed']} · "
        f"skippati (since): {stats['skipped_since']} · "
        f"skippati (max): {stats['skipped_max']} · "
        f"errori: {stats['errors']}"
    )


@scan_app.command("fic")
def scan_fic_command(
    vault: Path = typer.Option(
        ...,
        "--vault",
        help="Path al vault Obsidian del cliente (deve esistere `custodia init`).",
    ),
    company_id: int = typer.Option(
        ...,
        "--company-id",
        help="ID company Fatture in Cloud (numerico).",
    ),
    credentials: Path | None = typer.Option(
        None,
        "--credentials",
        help=(
            "Path al credentials.json FIC (in alternativa: env "
            "CUSTODIA_FIC_CREDENTIALS_JSON)."
        ),
    ),
    since: str | None = typer.Option(
        None,
        "--since",
        help=(
            "Filtra fatture con date >= questa data (formato YYYY-MM-DD). "
            "Default: 24 mesi indietro."
        ),
    ),
    resources: str | None = typer.Option(
        None,
        "--resources",
        help=(
            "Risorse da scaricare, comma-separated. "
            "Default: clients,suppliers,invoices."
        ),
    ),
    max_per_resource: int | None = typer.Option(
        None,
        "--max",
        help="Limite hard al numero di item per risorsa (utile per smoke test).",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Produce SourceDocument con text vuoto (solo metadata).",
    ),
) -> None:
    """Scansiona clienti/fornitori/fatture FIC e persiste i SourceDocument."""
    # Import locale: tiene la CLI snappy per chi usa solo `scan fs`.
    from datetime import datetime, timedelta, timezone as _tz

    from custodia_cli.connectors.fatture_in_cloud import FattureInCloudConnector

    db_path = _ensure_state_db(vault)
    state_dir = state_dir_for_vault(vault)
    token_cache = state_dir / "fic_token.json"
    cache_dir = state_dir / "cache" / "fic"

    # since: default 24 mesi indietro se non fornito.
    if since:
        try:
            since_dt: "datetime | None" = datetime.strptime(
                since, "%Y-%m-%d"
            ).replace(tzinfo=_tz.utc)
        except ValueError as exc:
            console.print(
                f"[red]✗[/red] --since deve essere YYYY-MM-DD ({exc})"
            )
            raise typer.Exit(code=1) from exc
    else:
        since_dt = datetime.now(tz=_tz.utc) - timedelta(days=24 * 30)

    # Parsing risorse.
    resources_list: list[str] | None = None
    if resources:
        resources_list = [r.strip() for r in resources.split(",") if r.strip()]

    try:
        connector = FattureInCloudConnector(
            company_id=company_id,
            credentials_path=credentials,
            token_cache_path=token_cache,
            cache_dir=None if dry_run else cache_dir,
            dry_run=dry_run,
            max_per_resource=max_per_resource,
            since=since_dt,
            resources=resources_list,
        )
    except ValueError as exc:
        console.print(f"[red]✗[/red] {exc}")
        raise typer.Exit(code=1) from exc

    with StateStore(db_path) as store:
        run_id = store.register_run(
            command="scan fic",
            args={
                "company_id": company_id,
                "since": since_dt.strftime("%Y-%m-%d"),
                "resources": resources_list or "default",
                "max_per_resource": max_per_resource,
                "dry_run": dry_run,
                # FIX SEC-5/OA-6: NON persistere il path raw del credentials JSON
                # in runs.args_json (potrebbe leakare path con info clienti).
                "credentials_provided": credentials is not None,
            },
        )

        n_docs = 0
        n_dup = 0
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.completed]{task.completed} item"),
                TimeElapsedColumn(),
                console=console,
                transient=False,
            ) as progress:
                task = progress.add_task("Scansione Fatture in Cloud", total=None)
                for doc in connector.iter_documents():
                    try:
                        store.add_document(
                            run_id=run_id,
                            source_id=doc.source_id,
                            source_path=doc.source_path,
                            mime_type=doc.mime_type,
                            text=doc.text,
                            metadata=dict(doc.metadata),
                        )
                        n_docs += 1
                    except sqlite3.IntegrityError as exc:
                        if _is_duplicate_source_id_error(exc):
                            n_dup += 1
                        else:
                            raise
                    progress.update(task, advance=1)
        except (KeyboardInterrupt, SystemExit):
            store.complete_run(
                run_id,
                status="error",
                summary="Interrotto dall'utente (KeyboardInterrupt)",
            )
            console.print("[yellow]⚠[/yellow]  Scan interrotto dall'utente.")
            raise
        except Exception as exc:  # noqa: BLE001
            store.complete_run(run_id, status="error", summary=str(exc))
            console.print(f"[red]✗[/red] Scan fallito: {exc}")
            raise typer.Exit(code=1) from exc

        summary = (
            f"{n_docs} item nuovi, {n_dup} già presenti, "
            f"stats={connector.stats}"
        )
        store.complete_run(run_id, status="success", summary=summary)

    console.print(
        f"[green]✓[/green] Scan completato — [bold]{n_docs}[/bold] item nuovi, "
        f"[dim]{n_dup} già presenti[/dim]."
    )
    stats = connector.stats
    console.print(
        f"  · clienti: {stats['processed_clients']} · "
        f"fornitori: {stats['processed_suppliers']} · "
        f"fatture: {stats['processed_invoices']} · "
        f"skippati (max): {stats['skipped_max']} · "
        f"errori: {stats['errors']}"
    )


__all__ = ["scan_app"]
