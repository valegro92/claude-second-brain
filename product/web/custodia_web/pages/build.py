"""
Pagina Build: estrazione entità via Extractor LLM.

Permette di scegliere entity_type e provider LLM (anthropic | fake) e mostra
i candidati prodotti in tabella con confidence e usage.

A partire da Sprint 2a (U4), il build gira in un thread background con
progress live + bottone Annulla, così la UI non blocca durante chiamate
LLM lunghe.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

import streamlit as st

from custodia_cli.commands.init import state_db_path_for_vault
from custodia_cli.jobs import CancelToken
from custodia_cli.state import StateStore
from custodia_web.components.find_data_help import render_llm_provider_help
from custodia_web.components.live_progress import (
    render_final_summary,
    render_live_progress,
)
from custodia_web.components.pipeline_header import render_pipeline_header
from custodia_web.services import build as build_svc
from custodia_web.services import extract as extract_svc
from custodia_web.services import job_state
from custodia_web.services import projects as projects_svc


def _render_build_result(result: extract_svc.BuildResult) -> None:
    if result.error:
        st.error(f"Errore in `{result.entity_type}`: {result.error}")
        return
    st.success(
        f"✓ `{result.entity_type}` — **{result.saved}** candidati salvati · "
        f"€{result.total_cost_eur:.4f} · "
        f"{result.total_input_tokens} tok in / {result.total_output_tokens} tok out"
    )
    if result.candidates:
        st.dataframe(result.candidates, use_container_width=True, hide_index=True)


def _render_build_progress_view(
    active: projects_svc.Project, job: job_state.ActiveJob
) -> None:
    """Polling view per build in background. Pattern identico a scan."""
    db_path = state_db_path_for_vault(Path(active.vault_path).expanduser().resolve())
    snapshot: dict[str, Any] | None = None
    try:
        with StateStore(db_path) as store:
            snapshot = store.get_run_progress(job.run_id)
    except Exception as exc:  # noqa: BLE001
        st.error(f"Errore lettura progress: {exc}")

    inner_status = "running"
    if snapshot:
        prog = snapshot.get("progress") or {}
        inner_status = prog.get("status") or snapshot.get("status") or "running"

    if not job.thread.is_alive() and inner_status == "running":
        time.sleep(0.1)
        try:
            with StateStore(db_path) as store:
                snapshot = store.get_run_progress(job.run_id)
            if snapshot:
                prog = snapshot.get("progress") or {}
                inner_status = prog.get("status") or snapshot.get("status") or "running"
        except Exception:  # noqa: BLE001
            pass

    if inner_status == "running":
        render_live_progress(snapshot, title=job.label)
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("✕ Annulla", type="secondary", key=f"cancel_build_{job.run_id}"):
                job.token.set_cancelled()
                st.toast(
                    "Annullamento in corso… (può richiedere ~30s se "
                    "Anthropic sta ancora rispondendo)",
                    icon="⏸",
                )
        with col2:
            st.caption(
                "L'estrazione continua in background. Le chiamate LLM in "
                "corso devono completare prima del cancel effettivo."
            )
        time.sleep(0.5)
        st.rerun()
        return

    # Stato terminale
    render_final_summary(snapshot, title=job.label)

    ctx = st.session_state.get(f"job_ctx_{active.id}")
    result: build_svc.BuildJobResult | None = None
    if ctx:
        result = ctx.get("result")
    if result:
        if result.error:
            st.error(f"Errore: {result.error}")
        elif result.total_saved > 0:
            st.info(f"👉 Prossimo passo: revisiona i candidati in **Review**.")
        for r in result.results:
            st.subheader(f"`{r.entity_type}`")
            _render_build_result(r)

    bcol1, bcol2 = st.columns([1, 1])
    with bcol1:
        if st.button("Chiudi", key=f"close_build_{job.run_id}", type="primary"):
            job_state.clear_active_job(active.id)
            st.session_state.pop(f"job_ctx_{active.id}", None)
            st.rerun()
    with bcol2:
        if (
            result
            and result.total_saved > 0
            and st.button("→ Vai a Review", key=f"goto_review_{job.run_id}")
        ):
            job_state.clear_active_job(active.id)
            st.session_state.pop(f"job_ctx_{active.id}", None)
            st.session_state["current_page"] = "Review"
            st.rerun()


def render(active: projects_svc.Project) -> None:
    """Renderizza la pagina Build."""
    render_pipeline_header(active, "Build")
    st.divider()

    # Polling view se c'è un build attivo.
    active_job = job_state.get_active_job(active.id)
    if active_job is not None and active_job.kind == "build":
        st.title(f"Build — {active.name}")
        _render_build_progress_view(active, active_job)
        return

    st.title(f"Build — {active.name}")
    st.caption(
        "Estrae candidati `cliente`/`fornitore`/`commessa`/`comunicazione` "
        "dai documenti accumulati nello state store. Dopo il build, i candidati "
        "diventano `pending` e li revisioni in **Review**."
    )

    vault = Path(active.vault_path)

    col1, col2 = st.columns(2)
    with col1:
        entity_type = st.selectbox(
            "Entity type",
            options=("cliente", "fornitore", "commessa", "comunicazione", "all"),
            index=0,
        )
    with col2:
        has_anthropic = bool(os.environ.get("CUSTODIA_ANTHROPIC_API_KEY"))
        default = 0 if has_anthropic else 1
        llm_provider = st.radio(
            "Provider LLM",
            options=("anthropic", "fake"),
            index=default,
            horizontal=True,
            help=(
                "Anthropic richiede `CUSTODIA_ANTHROPIC_API_KEY`. "
                "Fake usa risposte canned (offline)."
            ),
        )
        render_llm_provider_help()

    fixture_path: Path | None = None
    if llm_provider == "fake":
        fixture_default = ""
        cli_root_guess = (
            Path(__file__).resolve().parents[3]
            / "cli"
            / "tests"
            / "fixtures"
            / "llm"
            / "extractor_responses.yaml"
        )
        if cli_root_guess.exists():
            fixture_default = str(cli_root_guess)
        fixture_str = st.text_input(
            "Fixture YAML (canned responses)",
            value=fixture_default,
            help="Obbligatorio quando provider = fake.",
        )
        if fixture_str.strip():
            fixture_path = Path(fixture_str.strip())

    if not has_anthropic and llm_provider == "anthropic":
        st.warning(
            "`CUSTODIA_ANTHROPIC_API_KEY` non risulta settata. "
            "Imposta la env var oppure usa il provider `fake` con una fixture."
        )

    if st.button("🚀 Estrai", type="primary"):
        token = CancelToken()
        thread, ctx = build_svc.launch_build_thread(
            vault=vault,
            entity_type=entity_type,
            llm_provider=llm_provider,
            fixture_path=fixture_path,
            cancel=token,
        )
        deadline = time.monotonic() + 2.0
        while ctx.get("run_id") is None and time.monotonic() < deadline:
            time.sleep(0.05)
        run_id = ctx.get("run_id")
        if run_id is None:
            st.error("Worker build non ha registrato un run entro 2s; riprova.")
            return

        label = (
            f"Build {entity_type}"
            if entity_type != "all"
            else "Build (tutti gli entity_type)"
        )
        active_job = job_state.ActiveJob(
            run_id=int(run_id),
            token=token,
            kind="build",
            thread=thread,
            label=label,
        )
        st.session_state[f"job_ctx_{active.id}"] = ctx
        job_state.set_active_job(active.id, active_job)
        st.rerun()


__all__ = ["render"]
