"""
Pagina Scan: 4 sorgenti come card visive (no più tab nascoste).

L'utente vede subito che le sorgenti supportate sono 4 — non solo "filesystem".
Selezionando una card si apre il form di configurazione di quel connettore
sotto le card stesse.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

import streamlit as st

from custodia_cli.jobs import CancelToken
from custodia_cli.commands.init import state_db_path_for_vault
from custodia_cli.state import StateStore
from custodia_web.components.interrupted_banner import render_interrupted_banner
from custodia_web.components.find_data_help import (
    render_fic_company_help,
    render_fic_credentials_help,
    render_filesystem_help,
    render_google_drive_credentials_help,
    render_google_drive_folder_help,
    render_outlook_credentials_help,
    render_outlook_folder_help,
)
from custodia_web.components.live_progress import (
    render_final_summary,
    render_live_progress,
)
from custodia_web.components.pipeline_header import render_pipeline_header
from custodia_web.components.progress import live_progress, make_doc_counter_cb
from custodia_web.services import job_state
from custodia_web.services import projects as projects_svc
from custodia_web.services import scan as scan_svc
from custodia_web.services import vault as vault_svc


# Definizione delle 4 sorgenti supportate. command_prefix = quello che lo
# scan_service registra nella tabella runs (es "scan fs").
_SOURCES: list[dict[str, Any]] = [
    {
        "key": "fs",
        "icon": "📁",
        "label": "Filesystem",
        "blurb": "Cartella locale o mount NAS / Drive sync.",
        "env_var": None,
        "command_prefix": "scan fs",
    },
    {
        "key": "drive",
        "icon": "🔷",
        "label": "Google Drive",
        "blurb": "Cartella Drive condivisa, via OAuth.",
        "env_var": "CUSTODIA_GOOGLE_CREDENTIALS_JSON",
        "command_prefix": "scan drive",
    },
    {
        "key": "outlook",
        "icon": "✉️",
        "label": "Outlook 365",
        "blurb": "Inbox / cartelle del cliente, via Microsoft Graph.",
        "env_var": "CUSTODIA_MICROSOFT_CREDENTIALS_JSON",
        "command_prefix": "scan outlook",
    },
    {
        "key": "fic",
        "icon": "📊",
        "label": "Fatture in Cloud",
        "blurb": "Clienti, fornitori, fatture API-side.",
        "env_var": "CUSTODIA_FIC_CREDENTIALS_JSON",
        "command_prefix": "scan fic",
    },
]


def _runs_by_source(vault: Path) -> dict[str, int]:
    """Conta i run di scan completati per ciascuna sorgente.

    Approssimazione: prendiamo gli ultimi 50 run dal DB e contiamo per
    ``command`` prefix. Buono per il counter "X scan eseguiti".
    """
    counts = {s["key"]: 0 for s in _SOURCES}
    runs = vault_svc.list_recent_runs(vault, limit=50)
    for r in runs:
        cmd = (r.get("command") or "").lower()
        for s in _SOURCES:
            if cmd.startswith(s["command_prefix"]):
                counts[s["key"]] += 1
                break
    return counts


def _render_result(result: scan_svc.ScanResult) -> None:
    if result.error:
        st.error(f"Errore: {result.error}")
        return
    st.success(
        f"✓ Scan completato — **{result.new_docs}** doc nuovi · "
        f"{result.duplicates} duplicati"
    )
    st.info(
        "👉 Prossimo passo: vai in **Build** per estrarre clienti, fornitori e "
        "commesse dai documenti appena indicizzati."
    )
    bcol1, bcol2 = st.columns([1, 4])
    with bcol1:
        if st.button("→ Vai a Build", key="goto_build_post_scan", type="primary"):
            st.session_state["current_page"] = "Build"
            st.rerun()
    if result.stats:
        with st.expander("Stats connettore", expanded=False):
            st.json(result.stats)


# ---------------------------------------------------------------------------
# Form per ciascuna sorgente
# ---------------------------------------------------------------------------


def _form_filesystem(vault: Path, project_id: str) -> None:
    st.markdown("##### Configura sorgente · Filesystem")
    st.caption("Indica la cartella radice da scansionare.")
    render_filesystem_help()
    prefilled = st.session_state.get("fs_form_prefill_root", "")
    with st.form("fs_form"):
        root = st.text_input("Root path", value=prefilled, placeholder="/Users/me/Drive/cliente")
        exclude_raw = st.text_input(
            "Exclude patterns (separati da virgola)",
            value="*.bak, __pycache__",
            help="Pattern glob aggiuntivi rispetto ai default.",
        )
        max_size = st.number_input("Max file size (MB)", min_value=1, max_value=500, value=50)
        follow = st.checkbox("Segui symlink", value=False)
        dangerous = st.checkbox(
            "Bypass guardrail root pericolose (/, $HOME, /etc)",
            value=False,
            help="Lascia OFF di default.",
        )
        force_rescan = st.checkbox(
            "Force re-scan (ignora manifest incrementale)",
            value=False,
            help=(
                "Default OFF: i file invariati vengono skippati grazie al "
                "manifest (Sprint 2a U2). Attiva solo se hai dubbi sulla "
                "consistenza del manifest."
            ),
        )
        submitted = st.form_submit_button("🔍 Scan filesystem", type="primary")
    if submitted:
        if not root.strip():
            st.warning("Indica una root path.")
            return
        excludes = [p.strip() for p in exclude_raw.split(",") if p.strip()]
        # Consuma il prefill dopo il submit così non lo riproponiamo.
        st.session_state.pop("fs_form_prefill_root", None)

        # Lancia in background e registra il job in session_state.
        token = CancelToken()
        thread, ctx = scan_svc.launch_scan_filesystem_thread(
            vault=vault,
            root=Path(root),
            exclude_patterns=excludes,
            max_size_mb=int(max_size),
            follow_symlinks=follow,
            allow_dangerous_root=dangerous,
            force_rescan=force_rescan,
            cancel=token,
        )
        # Aspetta brevemente che il worker registri il run_id (max 2s).
        # Senza questo, il primo polling non saprebbe quale run leggere.
        deadline = time.monotonic() + 2.0
        while ctx.get("run_id") is None and time.monotonic() < deadline:
            time.sleep(0.05)
        run_id = ctx.get("run_id")
        if run_id is None:
            st.error("Worker scan non ha registrato un run entro 2s; riprova.")
            return

        active = job_state.ActiveJob(
            run_id=int(run_id),
            token=token,
            kind="scan",
            thread=thread,
            label=f"Scan filesystem · {Path(root).name}",
        )
        # Memorizza anche il ctx del worker così possiamo recuperare il
        # ScanResult finale a polling concluso.
        st.session_state[f"job_ctx_{project_id}"] = ctx
        job_state.set_active_job(project_id, active)
        st.rerun()


def _form_drive(vault: Path) -> None:
    st.markdown("##### Configura sorgente · Google Drive")
    has_env = bool(os.environ.get("CUSTODIA_GOOGLE_CREDENTIALS_JSON"))
    if not has_env:
        st.info(
            "Imposta `CUSTODIA_GOOGLE_CREDENTIALS_JSON` (oppure indica il "
            "credentials.json qui sotto) per usare il connector Drive."
        )
    render_google_drive_folder_help()
    render_google_drive_credentials_help()
    with st.form("drive_form"):
        folder = st.text_input("Root folder ID", placeholder="0AbCdEfGhIj...")
        creds = st.text_input(
            "credentials.json (path, opzionale)",
            value="",
            help="Lascia vuoto se hai già settato la env var.",
        )
        dry_run = st.checkbox("Dry run (no download)", value=False)
        submitted = st.form_submit_button("🔍 Scan Drive", type="primary")
    if submitted:
        if not folder.strip():
            st.warning("Indica il root folder ID.")
            return
        creds_path = Path(creds) if creds.strip() else None
        with live_progress("Scansione Google Drive") as report:
            cb = make_doc_counter_cb(report, prefix="doc")
            result = scan_svc.scan_drive(
                vault=vault,
                root_folder_id=folder.strip(),
                credentials_path=creds_path,
                dry_run=dry_run,
                progress_cb=cb,
            )
        _render_result(result)


def _form_outlook(vault: Path) -> None:
    st.markdown("##### Configura sorgente · Outlook 365")
    has_env = bool(os.environ.get("CUSTODIA_MICROSOFT_CREDENTIALS_JSON"))
    if not has_env:
        st.info(
            "Imposta `CUSTODIA_MICROSOFT_CREDENTIALS_JSON` (oppure indica il "
            "credentials.json qui sotto) per usare Outlook 365."
        )
    render_outlook_folder_help()
    render_outlook_credentials_help()
    with st.form("outlook_form"):
        folder = st.text_input("Folder", value="inbox", help="`inbox`, `sentitems`, `archive` o folder ID")
        creds = st.text_input("credentials.json (path, opzionale)", value="")
        since = st.text_input("Since (YYYY-MM-DD)", value="")
        max_msg = st.number_input("Max messaggi (0 = unlimited)", min_value=0, value=0)
        dry_run = st.checkbox("Dry run (no body completo)", value=False)
        submitted = st.form_submit_button("🔍 Scan Outlook", type="primary")
    if submitted:
        creds_path = Path(creds) if creds.strip() else None
        with live_progress("Scansione Outlook 365") as report:
            cb = make_doc_counter_cb(report, prefix="email")
            result = scan_svc.scan_outlook(
                vault=vault,
                folder=folder.strip() or None,
                credentials_path=creds_path,
                since=since.strip() or None,
                max_messages=int(max_msg) if max_msg else None,
                dry_run=dry_run,
                progress_cb=cb,
            )
        _render_result(result)


def _form_fic(vault: Path) -> None:
    st.markdown("##### Configura sorgente · Fatture in Cloud")
    has_env = bool(os.environ.get("CUSTODIA_FIC_CREDENTIALS_JSON"))
    if not has_env:
        st.info(
            "Imposta `CUSTODIA_FIC_CREDENTIALS_JSON` (oppure indica il "
            "credentials.json qui sotto) per usare Fatture in Cloud."
        )
    render_fic_company_help()
    render_fic_credentials_help()
    with st.form("fic_form"):
        company_id = st.number_input("Company ID", min_value=1, value=1)
        creds = st.text_input("credentials.json (path, opzionale)", value="")
        since = st.text_input("Since (YYYY-MM-DD, default -24 mesi)", value="")
        resources = st.text_input(
            "Resources (csv)", value="clients,suppliers,invoices",
        )
        max_per = st.number_input("Max per risorsa (0 = unlimited)", min_value=0, value=0)
        dry_run = st.checkbox("Dry run (solo metadata)", value=False)
        submitted = st.form_submit_button("🔍 Scan FIC", type="primary")
    if submitted:
        creds_path = Path(creds) if creds.strip() else None
        resources_list = [r.strip() for r in resources.split(",") if r.strip()]
        with live_progress("Scansione Fatture in Cloud") as report:
            cb = make_doc_counter_cb(report, prefix="item")
            result = scan_svc.scan_fic(
                vault=vault,
                company_id=int(company_id),
                credentials_path=creds_path,
                since=since.strip() or None,
                resources=resources_list,
                max_per_resource=int(max_per) if max_per else None,
                dry_run=dry_run,
                progress_cb=cb,
            )
        _render_result(result)


# I form non-filesystem usano ancora il pattern sincrono ``live_progress``:
# il loro tempo di esecuzione è dominato da chiamate API esterne e non hanno
# il problema scalabilità del filesystem. Il refactor in background è
# scoped a Filesystem (U4 Sprint 2a). Saranno migrati in 2b.

def _form_filesystem_dispatch(vault: Path, project_id: str) -> None:
    return _form_filesystem(vault, project_id)


def _form_drive_dispatch(vault: Path, project_id: str) -> None:
    return _form_drive(vault)


def _form_outlook_dispatch(vault: Path, project_id: str) -> None:
    return _form_outlook(vault)


def _form_fic_dispatch(vault: Path, project_id: str) -> None:
    return _form_fic(vault)


_FORMS = {
    "fs": _form_filesystem_dispatch,
    "drive": _form_drive_dispatch,
    "outlook": _form_outlook_dispatch,
    "fic": _form_fic_dispatch,
}


# ---------------------------------------------------------------------------
# Polling view: layout dedicato quando c'è uno scan attivo
# ---------------------------------------------------------------------------


def _render_scan_progress_view(
    active: projects_svc.Project, job: job_state.ActiveJob
) -> None:
    """Polling view per scan in background.

    Pattern: read snapshot -> render -> if running: sleep + rerun -> else:
    final summary + bottone "Chiudi". Streamlit gestisce nativamente il loop
    via ``st.rerun()`` quindi non c'è ``while True``, e altre pagine restano
    navigabili (basta cliccare nel menu).
    """
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

    # Se il worker thread è già morto ma il DB dice ancora "running", forziamo
    # un poll extra: lo stato è quasi sempre stato scritto un attimo prima
    # del shutdown del thread.
    if not job.thread.is_alive() and inner_status == "running":
        # Diamo un'ultima chance al worker di flushare lo snapshot finale.
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
            if st.button("✕ Annulla", type="secondary", key=f"cancel_{job.run_id}"):
                job.token.set_cancelled()
                st.toast("Annullamento in corso…", icon="⏸")
        with col2:
            st.caption(
                "Lo scan continua in background. Puoi navigare le altre "
                "pagine — il progress riprende qui."
            )

        # Auto-refresh ogni 500ms.
        time.sleep(0.5)
        st.rerun()
        return

    # Stato terminale: mostra summary + bottone "Chiudi".
    render_final_summary(snapshot, title=job.label)

    # Se il ctx del worker ha un ScanResult, mostra anche dettagli.
    ctx = st.session_state.get(f"job_ctx_{active.id}")
    if ctx and ctx.get("result") is not None:
        result: scan_svc.ScanResult = ctx["result"]
        if result.error:
            st.error(f"Errore: {result.error}")
        else:
            st.info(
                f"**{result.new_docs}** doc nuovi · {result.duplicates} duplicati"
            )
            st.info(
                "👉 Prossimo passo: vai in **Build** per estrarre clienti, "
                "fornitori e commesse."
            )

    bcol1, bcol2 = st.columns([1, 1])
    with bcol1:
        if st.button("Chiudi", key=f"close_{job.run_id}", type="primary"):
            job_state.clear_active_job(active.id)
            st.session_state.pop(f"job_ctx_{active.id}", None)
            st.rerun()
    with bcol2:
        if inner_status == "success" and st.button(
            "→ Vai a Build", key=f"goto_build_{job.run_id}"
        ):
            job_state.clear_active_job(active.id)
            st.session_state.pop(f"job_ctx_{active.id}", None)
            st.session_state["current_page"] = "Build"
            st.rerun()


# ---------------------------------------------------------------------------
# Card grid + render
# ---------------------------------------------------------------------------


def _render_source_card(
    col, source: dict[str, Any], scan_count: int, selected_key: str
) -> None:
    """Renderizza una card sorgente. Bottone seleziona l'apertura del form."""
    is_active = selected_key == source["key"]
    has_env = bool(os.environ.get(source["env_var"])) if source["env_var"] else True

    if scan_count > 0:
        status_line = f"✓ {scan_count} scan eseguiti"
        status_color = "#10b981"
    elif not has_env and source["env_var"]:
        status_line = "Credenziali da configurare"
        status_color = "#f59e0b"
    else:
        status_line = "Mai usato"
        status_color = "#94a3b8"

    border = "#0F766E" if is_active else "#e2e8f0"
    bg = "#f0fdfa" if is_active else "#ffffff"

    col.markdown(
        f"<div style='padding:14px;border-radius:10px;background:{bg};"
        f"border:2px solid {border};min-height:130px;margin-bottom:6px;'>"
        f"<div style='font-size:1.4rem;'>{source['icon']}</div>"
        f"<div style='font-weight:700;font-size:1.0rem;color:#0F766E;"
        f"margin-top:2px;'>{source['label']}</div>"
        f"<div style='font-size:0.78rem;color:#475569;margin-top:4px;"
        f"min-height:34px;'>{source['blurb']}</div>"
        f"<div style='font-size:0.72rem;color:{status_color};margin-top:6px;"
        f"font-weight:600;'>{status_line}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )
    label = "✓ Selezionata" if is_active else "Configura / Scan"
    if col.button(label, key=f"sel_source_{source['key']}", use_container_width=True):
        st.session_state["scan_selected_source"] = source["key"]
        st.rerun()


def render(active: projects_svc.Project) -> None:
    """Renderizza la pagina Scan."""
    render_pipeline_header(active, "Scan")
    st.divider()

    # Polling view: se c'è uno scan attivo per questo progetto, rendiamo il
    # layout dedicato (progress + cancel) invece del form di configurazione.
    active_job = job_state.get_active_job(active.id)
    if active_job is not None and active_job.kind == "scan":
        st.title(f"Scan — {active.name}")
        _render_scan_progress_view(active, active_job)
        return

    st.title(f"Scan — {active.name}")
    st.caption(
        "Acquisisci documenti da sorgenti diverse nello state store del progetto. "
        "Puoi usare più sorgenti per lo stesso vault."
    )

    # Demo banner: se l'utente è appena arrivato da "Prova con demo".
    if st.session_state.pop("demo_just_created", False):
        st.success(
            "🎬 Esempio pre-caricato. La form Filesystem qui sotto è già "
            "popolata con la cartella finto-drive del repo. Clicca 🔍 Scan "
            "filesystem per partire — tutto offline."
        )

    vault = Path(active.vault_path)

    # U5: banner per scan interrotti — disegnato prima delle card così
    # l'utente vede subito "c'è uno scan da riprendere" senza dover scorrere.
    render_interrupted_banner(vault, active.id)

    runs_count = _runs_by_source(vault)

    selected_key = st.session_state.get("scan_selected_source", "fs")

    # Default smart: se l'utente arriva dal demo, vogliamo Filesystem.
    if "fs_form_prefill_root" in st.session_state:
        selected_key = "fs"

    st.markdown("##### Sorgenti disponibili")
    st.caption(
        "Clicca una sorgente per aprire la sua form di configurazione qui sotto."
    )
    row1 = st.columns(2)
    row2 = st.columns(2)
    _render_source_card(row1[0], _SOURCES[0], runs_count["fs"], selected_key)
    _render_source_card(row1[1], _SOURCES[1], runs_count["drive"], selected_key)
    _render_source_card(row2[0], _SOURCES[2], runs_count["outlook"], selected_key)
    _render_source_card(row2[1], _SOURCES[3], runs_count["fic"], selected_key)

    st.divider()
    _FORMS[selected_key](vault, active.id)


__all__ = ["render"]
