"""
Wrapper della webapp attorno ai connettori del CLI Custodia.

Espone funzioni sync-friendly che ritornano un risultato strutturato (no
``typer.Exit``) e tengono lo StateStore aperto solo per la durata del run.

Le funzioni accettano un ``progress_cb`` opzionale (chiamato dopo ogni doc
indicizzato con il count corrente) — utile per progress bar Streamlit.
"""

from __future__ import annotations

import logging
import os
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from custodia_cli.commands.init import (
    run_init as _run_init,
    state_db_path_for_vault,
    state_dir_for_vault,
)
from custodia_cli.jobs import (
    CancelledError,
    CancelToken,
    ProgressReporter,
    ProgressSnapshot,
)
from custodia_cli.state import StateStore

logger = logging.getLogger(__name__)


ProgressCb = Callable[[int, int], None]  # (processed, duplicates)


@dataclass
class ScanResult:
    """Riepilogo di una scansione."""

    new_docs: int = 0
    duplicates: int = 0
    stats: dict[str, int] = field(default_factory=dict)
    error: str | None = None


_UNIQUE_MARKERS = ("documents.source_id", "UNIQUE constraint failed", "source_id")


def _is_dup(exc: sqlite3.IntegrityError) -> bool:
    msg = str(exc).lower()
    return any(m.lower() in msg for m in _UNIQUE_MARKERS)


def ensure_state_initialized(vault: Path) -> Path:
    """Esegue `custodia init` idempotente. Ritorna il path del state.db."""
    vault = Path(vault).expanduser().resolve()
    _run_init(vault)
    return state_db_path_for_vault(vault)


def _persist_docs(
    iter_docs,
    *,
    store: StateStore,
    run_id: int,
    progress_cb: ProgressCb | None,
) -> tuple[int, int]:
    """Persiste i SourceDocument prodotti da un iteratore.

    Conta nuovi vs duplicati. Errori di sqlite non-dup → propaga.
    """
    n_new = 0
    n_dup = 0
    for doc in iter_docs:
        try:
            store.add_document(
                run_id=run_id,
                source_id=doc.source_id,
                source_path=doc.source_path,
                mime_type=doc.mime_type,
                text=doc.text,
                metadata=dict(doc.metadata),
            )
            n_new += 1
        except sqlite3.IntegrityError as exc:
            if _is_dup(exc):
                n_dup += 1
            else:
                raise
        if progress_cb is not None:
            progress_cb(n_new, n_dup)
    return n_new, n_dup


def scan_filesystem(
    *,
    vault: Path,
    root: Path,
    exclude_patterns: list[str] | None = None,
    max_size_mb: int = 50,
    follow_symlinks: bool = False,
    allow_dangerous_root: bool = False,
    progress_cb: ProgressCb | None = None,
) -> ScanResult:
    """Scansiona una cartella locale. Equivalente di `custodia scan fs`."""
    from custodia_cli.connectors.filesystem import FilesystemConnector

    db_path = ensure_state_initialized(vault)
    root = Path(root).expanduser().resolve()
    if not root.is_dir():
        return ScanResult(error=f"Root inesistente o non directory: {root}")

    try:
        connector = FilesystemConnector(
            root_path=root,
            exclude_patterns=list(exclude_patterns or []),
            max_file_size_mb=max_size_mb,
            follow_symlinks=follow_symlinks,
            allow_dangerous_root=allow_dangerous_root,
        )
    except (ValueError, FileNotFoundError, NotADirectoryError) as exc:
        return ScanResult(error=str(exc))

    with StateStore(db_path) as store:
        run_id = store.register_run(
            command="scan fs",
            args={"root": str(root), "max_size_mb": max_size_mb},
        )
        try:
            n_new, n_dup = _persist_docs(
                connector.iter_documents(),
                store=store,
                run_id=run_id,
                progress_cb=progress_cb,
            )
        except Exception as exc:  # noqa: BLE001 — vogliamo riportare l'errore in UI
            store.complete_run(run_id, status="error", summary=str(exc))
            return ScanResult(error=str(exc), stats=dict(connector.stats))

        stats = dict(connector.stats)
        summary = f"{n_new} doc nuovi, {n_dup} duplicati, stats={stats}"
        store.complete_run(run_id, status="success", summary=summary)

    return ScanResult(new_docs=n_new, duplicates=n_dup, stats=stats)


def scan_drive(
    *,
    vault: Path,
    root_folder_id: str,
    credentials_path: Path | None = None,
    dry_run: bool = False,
    progress_cb: ProgressCb | None = None,
) -> ScanResult:
    """Scansiona Google Drive. Riusa token cache in `<state_dir>/google_token.json`."""
    from custodia_cli.connectors.google_drive import GoogleDriveConnector

    db_path = ensure_state_initialized(vault)
    state_dir = state_dir_for_vault(Path(vault).expanduser().resolve())
    token_cache = state_dir / "google_token.json"
    cache_dir = state_dir / "cache"

    try:
        connector = GoogleDriveConnector(
            root_folder_id=root_folder_id,
            credentials_path=credentials_path,
            token_cache_path=token_cache,
            dry_run=dry_run,
            cache_dir=None if dry_run else cache_dir,
        )
    except Exception as exc:  # noqa: BLE001 — auth/config error
        return ScanResult(error=str(exc))

    with StateStore(db_path) as store:
        run_id = store.register_run(
            command="scan drive",
            args={"root_folder_id": root_folder_id, "dry_run": dry_run},
        )
        try:
            n_new, n_dup = _persist_docs(
                connector.iter_documents(),
                store=store,
                run_id=run_id,
                progress_cb=progress_cb,
            )
        except Exception as exc:  # noqa: BLE001
            store.complete_run(run_id, status="error", summary=str(exc))
            return ScanResult(error=str(exc), stats=dict(connector.stats))

        stats = dict(connector.stats)
        store.complete_run(
            run_id,
            status="success",
            summary=f"{n_new} doc nuovi, {n_dup} duplicati",
        )

    return ScanResult(new_docs=n_new, duplicates=n_dup, stats=stats)


def scan_outlook(
    *,
    vault: Path,
    folder: str | None = None,
    credentials_path: Path | None = None,
    since: str | None = None,
    max_messages: int | None = None,
    dry_run: bool = False,
    progress_cb: ProgressCb | None = None,
) -> ScanResult:
    """Scansiona una folder Outlook 365. `since` formato 'YYYY-MM-DD'."""
    from datetime import datetime, timezone as _tz

    from custodia_cli.connectors.outlook import OutlookConnector

    db_path = ensure_state_initialized(vault)
    state_dir = state_dir_for_vault(Path(vault).expanduser().resolve())
    token_cache = state_dir / "microsoft_token.json"
    cache_dir = state_dir / "cache" / "outlook"

    since_dt = None
    if since:
        try:
            since_dt = datetime.strptime(since, "%Y-%m-%d").replace(tzinfo=_tz.utc)
        except ValueError as exc:
            return ScanResult(error=f"--since deve essere YYYY-MM-DD ({exc})")

    try:
        connector = OutlookConnector(
            folder_id=folder,
            credentials_path=credentials_path,
            token_cache_path=token_cache,
            cache_dir=None if dry_run else cache_dir,
            dry_run=dry_run,
            max_messages=max_messages,
            since=since_dt,
        )
    except Exception as exc:  # noqa: BLE001
        return ScanResult(error=str(exc))

    with StateStore(db_path) as store:
        run_id = store.register_run(
            command="scan outlook",
            args={"folder": folder or "inbox", "since": since, "dry_run": dry_run},
        )
        try:
            n_new, n_dup = _persist_docs(
                connector.iter_documents(),
                store=store,
                run_id=run_id,
                progress_cb=progress_cb,
            )
        except Exception as exc:  # noqa: BLE001
            store.complete_run(run_id, status="error", summary=str(exc))
            return ScanResult(error=str(exc), stats=dict(connector.stats))

        stats = dict(connector.stats)
        store.complete_run(
            run_id, status="success",
            summary=f"{n_new} email nuove, {n_dup} duplicati",
        )

    return ScanResult(new_docs=n_new, duplicates=n_dup, stats=stats)


def scan_fic(
    *,
    vault: Path,
    company_id: int,
    credentials_path: Path | None = None,
    since: str | None = None,
    resources: list[str] | None = None,
    max_per_resource: int | None = None,
    dry_run: bool = False,
    progress_cb: ProgressCb | None = None,
) -> ScanResult:
    """Scansiona Fatture in Cloud (clienti/fornitori/fatture)."""
    from datetime import datetime, timedelta, timezone as _tz

    from custodia_cli.connectors.fatture_in_cloud import FattureInCloudConnector

    db_path = ensure_state_initialized(vault)
    state_dir = state_dir_for_vault(Path(vault).expanduser().resolve())
    token_cache = state_dir / "fic_token.json"
    cache_dir = state_dir / "cache" / "fic"

    if since:
        try:
            since_dt = datetime.strptime(since, "%Y-%m-%d").replace(tzinfo=_tz.utc)
        except ValueError as exc:
            return ScanResult(error=f"--since deve essere YYYY-MM-DD ({exc})")
    else:
        since_dt = datetime.now(tz=_tz.utc) - timedelta(days=24 * 30)

    try:
        connector = FattureInCloudConnector(
            company_id=company_id,
            credentials_path=credentials_path,
            token_cache_path=token_cache,
            cache_dir=None if dry_run else cache_dir,
            dry_run=dry_run,
            max_per_resource=max_per_resource,
            since=since_dt,
            resources=resources,
        )
    except Exception as exc:  # noqa: BLE001
        return ScanResult(error=str(exc))

    with StateStore(db_path) as store:
        run_id = store.register_run(
            command="scan fic",
            args={
                "company_id": company_id,
                "since": since_dt.strftime("%Y-%m-%d"),
                "resources": resources or "default",
                "dry_run": dry_run,
            },
        )
        try:
            n_new, n_dup = _persist_docs(
                connector.iter_documents(),
                store=store,
                run_id=run_id,
                progress_cb=progress_cb,
            )
        except Exception as exc:  # noqa: BLE001
            store.complete_run(run_id, status="error", summary=str(exc))
            return ScanResult(error=str(exc), stats=dict(connector.stats))

        stats = dict(connector.stats)
        store.complete_run(
            run_id, status="success",
            summary=f"{n_new} item nuovi, {n_dup} duplicati",
        )

    return ScanResult(new_docs=n_new, duplicates=n_dup, stats=stats)


# ---------------------------------------------------------------------------
# Background worker filesystem (U4, Sprint 2a)
# ---------------------------------------------------------------------------
#
# Differenze rispetto a ``scan_filesystem``:
# - Esegue dentro un thread worker dedicato (lanciato dal chiamante).
# - Pubblica progress su ``StateStore.update_run_progress`` via
#   :class:`ProgressReporter`, così la pagina Streamlit può fare polling con
#   ``store.get_run_progress(run_id)``.
# - Supporta cancel via :class:`CancelToken`: l'utente preme il bottone
#   "Annulla" e il worker termina pulitamente al prossimo file (≤ ~500ms tipici).
# - Apre lo ``StateStore`` dentro il thread (sqlite3 ha
#   ``check_same_thread=False`` ma è comunque più pulito non condividere
#   l'istanza fra main thread Streamlit e worker).
# - Stima ``total`` con un walk veloce iniziale: O(N) sul filesystem,
#   typically pochi secondi anche per 50K file.


def _estimate_file_count(
    root: Path,
    excludes: list[str] | None,
    cancel: CancelToken,
    *,
    cap_seconds: float = 5.0,
    cap_files: int = 100_000,
) -> int | None:
    """Conta velocemente i candidati file sotto ``root``.

    Best-effort: usa ``os.walk`` con i pattern di esclusione del Filesystem
    Connector (default + smart excludes) per essere coerente con ciò che lo
    scan vero processerà davvero. Esce dopo ``cap_seconds`` secondi o
    ``cap_files`` file per non bloccare la UI su NAS lenti.

    Ritorna ``None`` se il walk non è completato (utente avrà una progress
    bar indeterminata).
    """
    # Importazione locale per evitare cost al module-load.
    from custodia_cli.connectors.filesystem import (
        _DEFAULT_EXCLUDES,
        _SMART_EXCLUDES_EXTENDED,
    )
    import fnmatch

    all_patterns: list[str] = list(_DEFAULT_EXCLUDES) + list(_SMART_EXCLUDES_EXTENDED)
    if excludes:
        all_patterns.extend(excludes)

    def is_excluded(name: str) -> bool:
        for pat in all_patterns:
            if fnmatch.fnmatch(name, pat):
                return True
        return False

    deadline = time.monotonic() + cap_seconds
    count = 0
    try:
        for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
            # Cancel responsivo anche durante la stima.
            if cancel.is_cancelled:
                return None
            # Prune dei sottodir esclusi (in-place per os.walk).
            dirnames[:] = [d for d in dirnames if not is_excluded(d)]
            for fname in filenames:
                if is_excluded(fname):
                    continue
                count += 1
                if count >= cap_files:
                    return None
            if time.monotonic() > deadline:
                return None
    except OSError as exc:
        logger.warning("estimate_file_count: errore walk su %s: %s", root, exc)
        return None
    return count


def scan_filesystem_with_progress(
    *,
    vault: Path,
    root: Path,
    exclude_patterns: list[str] | None = None,
    max_size_mb: int = 50,
    follow_symlinks: bool = False,
    allow_dangerous_root: bool = False,
    force_rescan: bool = False,
    cancel: CancelToken,
    run_id_callback: Callable[[int], None] | None = None,
) -> ScanResult:
    """Worker function per scan filesystem in background.

    Pensato per essere lanciato in un :class:`threading.Thread` dal chiamante
    Streamlit. Apre il suo :class:`StateStore`, registra un run, pubblica
    progress via :class:`ProgressReporter`. Ritorna :class:`ScanResult`.

    Su :class:`CancelledError` finalizza il run come ``partial`` con summary
    "Annullato dall'utente" e ritorna :class:`ScanResult` parziale (non
    rilancia).

    Args:
        run_id_callback: se fornito, viene chiamato con il ``run_id`` appena
            registrato — utile per il main thread che vuole pollare il
            progress su quel run_id senza aspettare la fine del worker.
    """
    from custodia_cli.connectors.filesystem import FilesystemConnector

    db_path = ensure_state_initialized(vault)
    root = Path(root).expanduser().resolve()
    if not root.is_dir():
        return ScanResult(error=f"Root inesistente o non directory: {root}")

    with StateStore(db_path) as store:
        run_id = store.register_run(
            command="scan fs",
            args={
                "root": str(root),
                "exclude_patterns": list(exclude_patterns or []),
                "max_size_mb": max_size_mb,
                "follow_symlinks": follow_symlinks,
                "force_rescan": force_rescan,
            },
        )
        if run_id_callback is not None:
            try:
                run_id_callback(run_id)
            except Exception:  # noqa: BLE001 - non bloccare il worker
                logger.exception("run_id_callback ha fallito")

        reporter = ProgressReporter(store, run_id, min_interval_ms=200)
        # Snapshot iniziale: "running" senza counter — la UI non lascia mai
        # vuoto il polling.
        reporter.flush()
        reporter.update(ProgressSnapshot(status="running"))

        # Stima totale (best effort).
        estimated_total = _estimate_file_count(root, exclude_patterns, cancel)

        try:
            connector = FilesystemConnector(
                root_path=root,
                exclude_patterns=list(exclude_patterns or []),
                max_file_size_mb=max_size_mb,
                follow_symlinks=follow_symlinks,
                allow_dangerous_root=allow_dangerous_root,
                state_store=store,
                manifest_run_id=run_id,
                force_rescan=force_rescan,
            )
        except (ValueError, FileNotFoundError, NotADirectoryError) as exc:
            store.complete_run(run_id, status="error", summary=str(exc))
            return ScanResult(error=str(exc))

        n_new = 0
        n_dup = 0
        start_time = time.monotonic()

        try:
            for doc in connector.iter_documents():
                # Cancel check: il punto di sicurezza è qui, fra un file e
                # l'altro. iter_documents non interromperà il batch parser
                # in-flight ma alla yield successiva si esce.
                cancel.raise_if_cancelled()

                try:
                    store.add_document(
                        run_id=run_id,
                        source_id=doc.source_id,
                        source_path=doc.source_path,
                        mime_type=doc.mime_type,
                        text=doc.text,
                        metadata=dict(doc.metadata),
                    )
                    n_new += 1
                except sqlite3.IntegrityError as exc:
                    if _is_dup(exc):
                        n_dup += 1
                    else:
                        raise

                # Calcola throughput e ETA solo dopo qualche file per non
                # fluttuare nei primi 100ms.
                elapsed = time.monotonic() - start_time
                processed = n_new + n_dup
                throughput = processed / elapsed if elapsed > 0.1 else 0.0
                eta: float | None = None
                if estimated_total and throughput > 0 and processed < estimated_total:
                    eta = max(0.0, (estimated_total - processed) / throughput)

                reporter.update(ProgressSnapshot(
                    status="running",
                    current=processed,
                    total=estimated_total,
                    current_item=str(doc.source_path),
                    throughput_per_sec=throughput,
                    eta_seconds=eta,
                    skipped=dict(connector.stats),
                    errors=int(connector.stats.get("errors", 0)),
                    extra={"run_id": run_id, "n_new": n_new, "n_dup": n_dup},
                ))

            # Snapshot finale di successo (forza il write).
            stats = dict(connector.stats)
            reporter.flush()
            reporter.update(ProgressSnapshot(
                status="success",
                current=n_new + n_dup,
                total=estimated_total or (n_new + n_dup),
                throughput_per_sec=(n_new + n_dup) / max(time.monotonic() - start_time, 0.001),
                skipped=stats,
                errors=int(stats.get("errors", 0)),
                extra={"n_new": n_new, "n_dup": n_dup, "run_id": run_id},
            ))
            summary = f"{n_new} doc nuovi, {n_dup} duplicati, stats={stats}"
            store.complete_run(run_id, status="success", summary=summary)
            return ScanResult(new_docs=n_new, duplicates=n_dup, stats=stats)

        except CancelledError:
            stats = dict(connector.stats)
            reporter.flush()
            reporter.update(ProgressSnapshot(
                status="cancelled",
                current=n_new + n_dup,
                total=estimated_total,
                skipped=stats,
                errors=int(stats.get("errors", 0)),
                extra={"n_new": n_new, "n_dup": n_dup, "run_id": run_id},
            ))
            store.complete_run(
                run_id,
                status="partial",
                summary=f"Annullato dopo {n_new} doc nuovi, {n_dup} duplicati.",
            )
            return ScanResult(
                new_docs=n_new,
                duplicates=n_dup,
                stats=stats,
                error=None,  # cancel non è un errore, è una scelta dell'utente
            )

        except Exception as exc:  # noqa: BLE001
            stats = dict(connector.stats)
            reporter.flush()
            reporter.update(ProgressSnapshot(
                status="error",
                current=n_new + n_dup,
                total=estimated_total,
                skipped=stats,
                errors=int(stats.get("errors", 0)) + 1,
                extra={"error": str(exc), "run_id": run_id},
            ))
            store.complete_run(run_id, status="error", summary=str(exc))
            return ScanResult(
                new_docs=n_new,
                duplicates=n_dup,
                stats=stats,
                error=str(exc),
            )


def launch_scan_filesystem_thread(
    *,
    vault: Path,
    root: Path,
    exclude_patterns: list[str] | None,
    max_size_mb: int,
    follow_symlinks: bool,
    allow_dangerous_root: bool,
    force_rescan: bool,
    cancel: CancelToken,
    on_result: Callable[[ScanResult], None] | None = None,
) -> tuple[threading.Thread, dict[str, Any]]:
    """Lancia ``scan_filesystem_with_progress`` in un thread daemon.

    Ritorna ``(thread, ctx)`` dove ``ctx`` è un dict popolato in-place dal
    worker con:

    - ``run_id``: appena disponibile (subito dopo register_run).
    - ``result``: alla fine del job (ScanResult).

    Il chiamante può polling-are ``ctx["run_id"]`` per sapere quando partire
    col polling del progress, e ``ctx["result"]`` per sapere se il job è
    terminato. Il thread è daemon=True così non blocca lo shutdown del
    processo Streamlit.
    """
    ctx: dict[str, Any] = {"run_id": None, "result": None}

    def _set_run_id(rid: int) -> None:
        ctx["run_id"] = rid

    def _target() -> None:
        try:
            result = scan_filesystem_with_progress(
                vault=vault,
                root=root,
                exclude_patterns=exclude_patterns,
                max_size_mb=max_size_mb,
                follow_symlinks=follow_symlinks,
                allow_dangerous_root=allow_dangerous_root,
                force_rescan=force_rescan,
                cancel=cancel,
                run_id_callback=_set_run_id,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("scan_filesystem_with_progress: errore non gestito")
            result = ScanResult(error=str(exc))
        ctx["result"] = result
        if on_result is not None:
            try:
                on_result(result)
            except Exception:  # noqa: BLE001
                logger.exception("on_result callback ha fallito")

    thread = threading.Thread(
        target=_target, name=f"custodia-scan-{root.name}", daemon=True
    )
    thread.start()
    return thread, ctx


# ---------------------------------------------------------------------------
# Resume / reap interrupted runs (U5, Sprint 2a)
# ---------------------------------------------------------------------------


@dataclass
class InterruptedRun:
    """Dato strutturato di un run interrotto, pronto per la UI."""

    run_id: int
    command: str
    args: dict[str, Any]
    started_at: str
    heartbeat_at: str | None
    progress: dict[str, Any] | None

    @property
    def is_filesystem(self) -> bool:
        return self.command.startswith("scan fs")

    @property
    def root(self) -> str | None:
        return self.args.get("root") if isinstance(self.args, dict) else None

    @property
    def processed(self) -> int:
        """Numero di item processati prima dell'interruzione."""
        if not self.progress:
            return 0
        cur = self.progress.get("current")
        if isinstance(cur, (int, float)):
            return int(cur)
        return 0


def reap_interrupted_runs_for_vault(
    vault: Path, threshold_minutes: int = 5
) -> int:
    """Marca come ``partial`` (interrupted) i run con heartbeat scaduto.

    Apre lo state DB del vault, identifica i run con ``status='running'`` la
    cui ``heartbeat_at`` è più vecchia di ``threshold_minutes``, e li marca
    come interrotti. Ritorna il numero di run reaped.

    Idempotente. No-op se lo state DB non esiste (progetto mai inizializzato).
    """
    from custodia_cli.jobs.progress import ProgressSnapshot

    vault = Path(vault).expanduser().resolve()
    db_path = state_db_path_for_vault(vault)
    if not db_path.exists():
        return 0
    count = 0
    try:
        with StateStore(db_path) as store:
            rows = store.find_interrupted_runs(threshold_minutes=threshold_minutes)
            for row in rows:
                rid = int(row["id"])
                try:
                    store.update_run_progress(
                        rid,
                        ProgressSnapshot(status="interrupted").to_payload(),
                    )
                    store.complete_run(
                        rid,
                        status="partial",
                        summary="Interrotto: heartbeat scaduto.",
                    )
                    count += 1
                except Exception:  # noqa: BLE001
                    logger.exception("reap fallita per run_id=%s", rid)
    except Exception:  # noqa: BLE001
        logger.exception("reap_interrupted_runs_for_vault fallita per %s", vault)
    return count


def list_interrupted_scan_runs(
    vault: Path, *, command_prefix: str = "scan fs"
) -> list[InterruptedRun]:
    """Lista i run interrotti per un vault, filtrati per prefisso ``command``.

    Pre-condizione tipica: ``reap_interrupted_runs_for_vault`` è stato già
    chiamato e ha marcato i run come ``partial`` con ``status='interrupted'``
    nel ``progress_json``. Qui leggiamo dalla tabella ``runs`` per status
    ``partial`` e progress ``status='interrupted'``, oppure run ``running``
    con heartbeat scaduto (defensive: in caso il reap non sia stato chiamato).

    Per semplicità delle UI, ritorna SOLO scan fs interrotti (per ora il
    background worker è solo filesystem; le altre sorgenti girano sync).
    Ordinati per ``started_at`` DESCENDING: il più recente è il primo.
    """
    vault = Path(vault).expanduser().resolve()
    db_path = state_db_path_for_vault(vault)
    if not db_path.exists():
        return []
    out: list[InterruptedRun] = []
    try:
        with StateStore(db_path) as store:
            # 1) Run già marcati 'partial' con progress.status='interrupted'.
            rows = store._conn.execute(
                """
                SELECT id, command, args_json, progress_json,
                       started_at, heartbeat_at, summary
                FROM runs
                WHERE status = 'partial' AND command LIKE ?
                ORDER BY id DESC
                """,
                (f"{command_prefix}%",),
            ).fetchall()
            for r in rows:
                import json as _json
                try:
                    progress = (
                        _json.loads(r["progress_json"])
                        if r["progress_json"] else None
                    )
                except Exception:  # noqa: BLE001
                    progress = None
                # Filtra: solo se progress.status == "interrupted".
                if not progress or progress.get("status") != "interrupted":
                    continue
                try:
                    args = _json.loads(r["args_json"]) if r["args_json"] else {}
                except Exception:  # noqa: BLE001
                    args = {}
                out.append(
                    InterruptedRun(
                        run_id=int(r["id"]),
                        command=r["command"],
                        args=args if isinstance(args, dict) else {},
                        started_at=r["started_at"],
                        heartbeat_at=r["heartbeat_at"],
                        progress=progress,
                    )
                )
    except Exception:  # noqa: BLE001
        logger.exception("list_interrupted_scan_runs fallita per %s", vault)
    return out


def resume_scan_filesystem(
    *,
    vault: Path,
    run_id: int,
    cancel: CancelToken,
) -> tuple[threading.Thread, dict[str, Any]] | None:
    """Ri-lancia uno scan filesystem usando gli args del run interrotto.

    Estrae ``args_json`` del run con ID ``run_id`` (deve essere un ``scan fs``)
    e chiama :func:`launch_scan_filesystem_thread` con gli stessi parametri.
    Il manifest U2 fa lo skip automatico dei file già processati.

    Ritorna ``(thread, ctx)`` come :func:`launch_scan_filesystem_thread`,
    oppure ``None`` se il run non esiste o non è un ``scan fs``.

    Nota: ``force_rescan`` è sempre ``False`` nel resume — vogliamo
    esplicitamente sfruttare il manifest per il fast-skip.
    """
    vault = Path(vault).expanduser().resolve()
    db_path = state_db_path_for_vault(vault)
    if not db_path.exists():
        return None
    with StateStore(db_path) as store:
        # Verifica esistenza + recupera command + args.
        row = store._conn.execute(
            "SELECT id, command, args_json FROM runs WHERE id = ?",
            (int(run_id),),
        ).fetchone()
        if row is None:
            return None
        if not str(row["command"]).startswith("scan fs"):
            return None
        args = store.get_run_args(int(run_id)) or {}

    root_raw = args.get("root")
    if not root_raw:
        return None
    root = Path(root_raw)
    exclude_patterns = list(args.get("exclude_patterns") or args.get("excludes") or [])
    max_size_mb = int(args.get("max_size_mb") or 50)
    follow_symlinks = bool(args.get("follow_symlinks") or False)
    # In resume non bypassiamo il guardrail dangerous-root: se l'utente l'aveva
    # bypassato la prima volta, lo accetta anche nel resume.
    allow_dangerous_root = bool(args.get("allow_dangerous_root") or False)

    return launch_scan_filesystem_thread(
        vault=vault,
        root=root,
        exclude_patterns=exclude_patterns,
        max_size_mb=max_size_mb,
        follow_symlinks=follow_symlinks,
        allow_dangerous_root=allow_dangerous_root,
        force_rescan=False,
        cancel=cancel,
    )


def dismiss_interrupted_run(vault: Path, run_id: int) -> bool:
    """Cancella dal log un run interrotto.

    Lo rimuove dalla tabella ``runs`` (e tutti i suoi documenti via FK?).
    In realtà i documents hanno solo ``run_id`` come riferimento metadati, non
    una FK strict, quindi possiamo cancellare il run senza rotture: i documenti
    già persistiti restano nel manifest/state.

    Ritorna ``True`` se cancellato, ``False`` se non trovato.
    """
    vault = Path(vault).expanduser().resolve()
    db_path = state_db_path_for_vault(vault)
    if not db_path.exists():
        return False
    with StateStore(db_path) as store:
        result = store._conn.execute(
            "DELETE FROM runs WHERE id = ?", (int(run_id),)
        )
        store._conn.commit()
        return int(result.rowcount) > 0


__all__ = [
    "ScanResult",
    "InterruptedRun",
    "ensure_state_initialized",
    "scan_filesystem",
    "scan_filesystem_with_progress",
    "launch_scan_filesystem_thread",
    "scan_drive",
    "scan_outlook",
    "scan_fic",
    "reap_interrupted_runs_for_vault",
    "list_interrupted_scan_runs",
    "resume_scan_filesystem",
    "dismiss_interrupted_run",
]
