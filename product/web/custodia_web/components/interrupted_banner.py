"""
Banner UI per scan interrotti (U5, Sprint 2a).

Disegna un banner sopra il form di scan quando il vault del progetto attivo
contiene run di scan filesystem terminati come ``interrupted`` (heartbeat
scaduto). L'utente può:

- Cliccare "Riprendi scan": ri-lancia lo scan con gli stessi args; il
  manifest U2 fa lo skip dei file già processati.
- Cliccare "Ignora": nasconde il banner per questa sessione (no DB write).
- Espandere "Vedi N-1 run più vecchi" per scan interrotti precedenti dello
  stesso progetto, con possibilità di eliminarli dal log uno per uno.

Il banner mostra solo il run più recente in primo piano; gli altri vivono
nell'expander per non rumoreggiare la UI.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import streamlit as st

from custodia_cli.jobs import CancelToken
from custodia_web.services import job_state
from custodia_web.services import scan as scan_svc


_DISMISSED_KEY = "interrupted_dismissed"


def _get_dismissed() -> set[int]:
    """Set dei run_id dismissati nella sessione corrente."""
    if _DISMISSED_KEY not in st.session_state:
        st.session_state[_DISMISSED_KEY] = set()
    return st.session_state[_DISMISSED_KEY]


def _dismiss(run_id: int) -> None:
    _get_dismissed().add(int(run_id))


def _format_elapsed(iso_ts: str | None) -> str:
    """Trasforma un timestamp ISO in elapsed friendly: '2 ore fa'."""
    if not iso_ts:
        return "tempo sconosciuto"
    try:
        ts = datetime.fromisoformat(iso_ts)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
    except ValueError:
        return iso_ts
    now = datetime.now(timezone.utc)
    delta = (now - ts).total_seconds()
    if delta < 60:
        return "pochi secondi fa"
    if delta < 3600:
        return f"{int(delta // 60)} minuti fa"
    if delta < 86400:
        return f"{int(delta // 3600)} ore fa"
    return f"{int(delta // 86400)} giorni fa"


def render_interrupted_banner(
    vault: Path,
    project_id: str,
    *,
    on_resume: Callable[[scan_svc.InterruptedRun], None] | None = None,
) -> bool:
    """Renderizza il banner se ci sono scan filesystem interrotti.

    Ritorna ``True`` se almeno un banner è stato disegnato (utile per il
    caller che vuole eventualmente saltare il render del form sotto). Filtra
    fuori i run dismessi nella session corrente.

    ``on_resume`` opzionale: viene chiamato DOPO aver lanciato il thread di
    resume, prima del ``st.rerun()``. Default: integra il default (registra
    ActiveJob in session_state).
    """
    runs = scan_svc.list_interrupted_scan_runs(vault, command_prefix="scan fs")
    dismissed = _get_dismissed()
    runs = [r for r in runs if r.run_id not in dismissed]
    if not runs:
        return False

    latest = runs[0]
    older = runs[1:]

    root_display = latest.root or "(cartella sconosciuta)"
    started_str = _format_elapsed(latest.started_at)
    processed = latest.processed

    # Banner principale.
    with st.container():
        st.warning(
            f"⚠ **Scan interrotto rilevato** — Run #{latest.run_id} · "
            f"`{root_display}`\n\n"
            f"Iniziato {started_str} · {processed:,} file processati.  \n"
            "Il processo è stato chiuso prima del completamento. "
            "Riprendendo, salterò i file già visti e processerò solo i rimanenti."
        )
        col1, col2, col3 = st.columns([1.2, 1, 4])
        with col1:
            if st.button(
                "▶ Riprendi scan",
                key=f"resume_{latest.run_id}",
                type="primary",
            ):
                _resume_run(vault, project_id, latest, on_resume=on_resume)
        with col2:
            if st.button("Ignora", key=f"dismiss_{latest.run_id}"):
                _dismiss(latest.run_id)
                st.rerun()

    if older:
        with st.expander(
            f"Vedi {len(older)} scan interrotti più vecchi", expanded=False
        ):
            for r in older:
                cols = st.columns([4, 1, 1])
                cols[0].caption(
                    f"Run #{r.run_id} · `{r.root or '?'}` · "
                    f"{_format_elapsed(r.started_at)} · {r.processed:,} file"
                )
                if cols[1].button(
                    "Riprendi", key=f"resume_old_{r.run_id}"
                ):
                    _resume_run(vault, project_id, r, on_resume=on_resume)
                if cols[2].button(
                    "Elimina", key=f"del_old_{r.run_id}"
                ):
                    if scan_svc.dismiss_interrupted_run(vault, r.run_id):
                        st.toast(f"Run #{r.run_id} eliminato dal log", icon="🗑")
                    st.rerun()
    return True


def _resume_run(
    vault: Path,
    project_id: str,
    interrupted: scan_svc.InterruptedRun,
    *,
    on_resume: Callable[[scan_svc.InterruptedRun], None] | None,
) -> None:
    """Helper interno: lancia il resume e registra ActiveJob."""
    token = CancelToken()
    result = scan_svc.resume_scan_filesystem(
        vault=vault, run_id=interrupted.run_id, cancel=token
    )
    if result is None:
        st.error(
            f"Impossibile riprendere run #{interrupted.run_id}: "
            "args non recuperabili o run non trovato."
        )
        return
    thread, ctx = result

    # Attesa breve per ottenere il run_id del nuovo thread.
    deadline = time.monotonic() + 2.0
    while ctx.get("run_id") is None and time.monotonic() < deadline:
        time.sleep(0.05)
    new_run_id = ctx.get("run_id")
    if new_run_id is None:
        st.error("Worker resume non ha registrato un run entro 2s; riprova.")
        return

    label_root = interrupted.root or "?"
    active = job_state.ActiveJob(
        run_id=int(new_run_id),
        token=token,
        kind="scan",
        thread=thread,
        label=f"Scan filesystem (resume) · {Path(label_root).name}",
    )
    st.session_state[f"job_ctx_{project_id}"] = ctx
    job_state.set_active_job(project_id, active)
    # Marca il banner come gestito per non riapparire dopo il rerun.
    _dismiss(interrupted.run_id)
    if on_resume is not None:
        try:
            on_resume(interrupted)
        except Exception:  # noqa: BLE001
            pass
    st.rerun()


__all__ = ["render_interrupted_banner"]
