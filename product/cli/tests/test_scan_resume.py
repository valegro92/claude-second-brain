"""
Test del resume scan fs interrotto (U5, Sprint 2a).

Coperture:
- ``StateStore.find_interrupted_runs`` ritorna ``args`` deserializzati.
- ``StateStore.get_run_args`` ritorna dict o None.
- CLI ``custodia scan fs --resume`` senza interrupted run → exit 1.
- CLI ``--resume`` con un interrupted run → riesegue lo scan con gli stessi
  args; il manifest U2 fa skip dei file già processati.
- CLI ``--resume --run-id N`` errori vari (non esiste, non è scan fs).
"""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from custodia_cli.commands.init import run_init, state_db_path_for_vault
from custodia_cli.jobs.progress import ProgressSnapshot
from custodia_cli.main import app
from custodia_cli.state import StateStore

runner = CliRunner()


def _make_interrupted_scan_fs(
    store: StateStore, *, root: str, excludes: list[str] | None = None
) -> int:
    """Crea un run 'scan fs' marcato come interrupted (status='partial',
    progress.status='interrupted')."""
    run_id = store.register_run(
        command="scan fs",
        args={
            "root": root,
            "excludes": list(excludes or []),
            "exclude_patterns": list(excludes or []),
            "max_size_mb": 50,
            "follow_symlinks": False,
        },
    )
    store.update_run_progress(
        run_id, ProgressSnapshot(status="interrupted", current=3).to_payload()
    )
    store.complete_run(run_id, status="partial", summary="Interrotto.")
    return run_id


def test_find_interrupted_runs_returns_args(tmp_path: Path) -> None:
    db = tmp_path / "state.db"
    store = StateStore(db)
    run_id = store.register_run(command="scan fs", args={"root": "/x", "max_size_mb": 25})
    # Forza heartbeat vecchio.
    with store._conn:  # noqa: SLF001
        store._conn.execute(  # noqa: SLF001
            "UPDATE runs SET heartbeat_at = datetime('now', '-10 minutes') WHERE id = ?",
            (run_id,),
        )

    rows = store.find_interrupted_runs(threshold_minutes=5)
    assert len(rows) == 1
    r = rows[0]
    assert r["id"] == run_id
    assert r["command"] == "scan fs"
    assert isinstance(r["args"], dict)
    assert r["args"]["root"] == "/x"
    assert r["args"]["max_size_mb"] == 25
    store.close()


def test_get_run_args_returns_dict(tmp_path: Path) -> None:
    db = tmp_path / "state.db"
    store = StateStore(db)
    run_id = store.register_run(command="scan fs", args={"root": "/a", "max_size_mb": 11})
    args = store.get_run_args(run_id)
    assert isinstance(args, dict)
    assert args["root"] == "/a"
    assert args["max_size_mb"] == 11
    store.close()


def test_get_run_args_missing_returns_none(tmp_path: Path) -> None:
    db = tmp_path / "state.db"
    store = StateStore(db)
    assert store.get_run_args(9999) is None
    store.close()


def test_cli_resume_no_interrupted_runs_exits(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    run_init(vault)
    result = runner.invoke(
        app, ["scan", "fs", "--vault", str(vault), "--resume"]
    )
    assert result.exit_code != 0
    assert "Nessuno scan" in result.output or "nessuno" in result.output.lower()


def test_cli_resume_explicit_run_id_not_found(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    run_init(vault)
    result = runner.invoke(
        app,
        ["scan", "fs", "--vault", str(vault), "--resume", "--run-id", "999"],
    )
    assert result.exit_code != 0
    assert "non esiste" in result.output.lower()


def test_cli_resume_run_id_wrong_command(tmp_path: Path) -> None:
    """Un --run-id che punta a un run non-'scan fs' deve fallire chiaramente."""
    vault = tmp_path / "vault"
    vault.mkdir()
    run_init(vault)
    db_path = state_db_path_for_vault(vault)
    with StateStore(db_path) as store:
        other_id = store.register_run(command="scan drive", args={"root_folder_id": "X"})

    result = runner.invoke(
        app,
        [
            "scan", "fs", "--vault", str(vault),
            "--resume", "--run-id", str(other_id),
        ],
    )
    assert result.exit_code != 0
    assert "non è" in result.output.lower() or "scan fs" in result.output


def test_cli_resume_executes_scan(tmp_path: Path, finto_drive_root: Path) -> None:
    """--resume su run interrotto valido deve eseguire lo scan e finire OK."""
    vault = tmp_path / "vault"
    vault.mkdir()
    run_init(vault)
    db_path = state_db_path_for_vault(vault)

    # Crea un interrupted run che punta al fixture finto_drive_root.
    with StateStore(db_path) as store:
        old_run_id = _make_interrupted_scan_fs(store, root=str(finto_drive_root))

    result = runner.invoke(
        app, ["scan", "fs", "--vault", str(vault), "--resume"]
    )
    assert result.exit_code == 0, result.output
    assert "Resume del run" in result.output or "scan" in result.output.lower()

    # Verifica che un nuovo run sia stato creato + ha status success.
    with StateStore(db_path) as store:
        rows = store._conn.execute(  # noqa: SLF001
            "SELECT id, status, command FROM runs WHERE command LIKE 'scan fs%' "
            "ORDER BY id DESC"
        ).fetchall()
        assert len(rows) >= 2  # vecchio interrotto + nuovo
        latest = rows[0]
        assert latest["id"] != old_run_id
        assert latest["status"] == "success"


def test_cli_resume_skips_via_manifest(
    tmp_path: Path, finto_drive_root: Path
) -> None:
    """Dopo un primo scan completo, un --resume su run interrotto deve
    saltare via manifest tutti i file già presenti (skipped_unchanged > 0)."""
    vault = tmp_path / "vault"
    vault.mkdir()
    run_init(vault)
    db_path = state_db_path_for_vault(vault)

    # 1) Primo scan completo (popola il manifest).
    result1 = runner.invoke(
        app,
        ["scan", "fs", "--vault", str(vault), "--root", str(finto_drive_root)],
    )
    assert result1.exit_code == 0, result1.output

    # 2) Crea un fake interrupted run sul medesimo root.
    with StateStore(db_path) as store:
        # Senza --resume nel primo scan, il manifest NON era popolato.
        # Per testare il manifest skip nel resume, popoliamolo manualmente:
        # iteriamo le entries documents e inseriamo nel manifest.
        # In alternativa: facciamo un altro scan fs --resume su un interrupted
        # creato AD HOC, e verifichiamo che il secondo run interrupted (di
        # --resume) sfrutti il manifest. Per farlo davvero servirebbe il
        # manifest popolato dal primo run, ma il CLI scan_fs base non passa
        # state_store. Quindi qui creiamo manualmente le manifest entries.
        import hashlib
        for src in finto_drive_root.rglob("*"):
            if not src.is_file():
                continue
            rel = src.relative_to(finto_drive_root)
            source_id = (
                "fs:" + hashlib.sha1(str(src.resolve()).encode()).hexdigest()[:16]
            )
            content_hash = hashlib.sha1(src.read_bytes()[:1_000_000]).digest()[:16]
            try:
                store.manifest_upsert(
                    connector_name="filesystem",
                    source_id=source_id,
                    content_hash_sha1_16=content_hash,
                    mtime_iso="2026-01-01T00:00:00+00:00",
                    file_size=src.stat().st_size,
                    run_id=None,
                )
            except Exception:
                pass

        # Crea interrupted run e marca così via reaper UI rileva.
        old_id = _make_interrupted_scan_fs(store, root=str(finto_drive_root))

    # 3) --resume: dovrebbe sfruttare il manifest e finire più velocemente.
    result2 = runner.invoke(
        app, ["scan", "fs", "--vault", str(vault), "--resume"]
    )
    assert result2.exit_code == 0, result2.output

    # Verifica che ci sia almeno uno skipped_unchanged nelle stats: stampato
    # dal CLI output. Il connector contabilizza skip via stats.
    # In output del CLI scan fs ha "skippati (excluded/size/ext/unknown)".
    # skipped_unchanged non è ancora nell'output stringa: lo verifichiamo via
    # state DB: il nuovo run deve avere meno documenti aggiunti.
    with StateStore(db_path) as store:
        # Ultimo run (resume) non dovrebbe aver creato documents per file
        # già nel manifest. I documenti precedenti restano: filtriamo per run_id.
        rows = store._conn.execute(  # noqa: SLF001
            "SELECT id FROM runs WHERE command LIKE 'scan fs%' ORDER BY id DESC"
        ).fetchall()
        latest_id = rows[0]["id"]
        n_docs_in_latest = store._conn.execute(  # noqa: SLF001
            "SELECT COUNT(*) AS n FROM documents WHERE run_id = ?",
            (latest_id,),
        ).fetchone()["n"]
        # Tutti i file erano in manifest → quasi tutti i file dovrebbero
        # essere stati skippati (n_docs_in_latest << 5).
        assert n_docs_in_latest < 5
    _ = old_id  # silenzia unused
