"""
Pagina Dashboard: home del progetto attivo.

Mostra:
- Banner "Next step" che dice esplicitamente cosa fare adesso.
- Metriche aggregate.
- Lista recenti run, quick actions.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import streamlit as st

from custodia_web.components.pipeline_header import render_pipeline_header
from custodia_web.services import projects as projects_svc
from custodia_web.services import vault as vault_svc


def _open_in_finder(path: Path) -> None:
    """Apre la cartella nel file explorer del sistema (macOS / Linux / Windows)."""
    try:
        if sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=False)
        elif sys.platform == "win32":
            subprocess.run(["explorer", str(path)], check=False)
        else:
            subprocess.run(["xdg-open", str(path)], check=False)
    except (OSError, subprocess.SubprocessError) as exc:
        st.error(f"Impossibile aprire {path}: {exc}")


def _next_step_banner(stats: vault_svc.VaultStats) -> None:
    """Mostra un banner che dice esplicitamente il prossimo passo.

    L'inferenza è basata sullo stato attuale del vault (docs, entità, .md).
    Include un bottone diretto alla pagina suggerita.
    """
    total_ent = sum(stats.entities_by_status.values())
    pending = stats.entities_by_status.get("pending", 0)
    approved = stats.entities_by_status.get("approved", 0)
    total_md = sum(stats.md_by_subdir.values())

    if stats.docs_total == 0:
        msg = (
            "**Inizia indicando dove pescare i documenti.** Apri **Raccolta** "
            "e scegli la fonte: cartella locale, Drive, Outlook o Fatture in Cloud."
        )
        target = "Scan"
        kind = "info"
    elif total_ent == 0:
        msg = (
            f"Hai **{stats.docs_total} documenti** raccolti. "
            "Adesso vai in **Estrazione**: l'AI li legge e propone le schede "
            "di clienti, fornitori e commesse."
        )
        target = "Build"
        kind = "info"
    elif pending > 0:
        msg = (
            f"Ci sono **{pending} schede da controllare** prima di consegnarle "
            "al vault. Per ognuna decidi: la tengo, la correggo, la scarto, "
            "o la unisco a una già esistente."
        )
        target = "Review"
        kind = "warning"
    elif approved > 0 and total_md == 0:
        msg = (
            f"**{approved} schede approvate**, ma il vault è ancora vuoto. "
            "Apri **Consegna** e clicca *Scrivi nel vault* per portarle "
            "nella cartella finale del cliente."
        )
        target = "Vault"
        kind = "info"
    elif approved > 0 and total_md > 0:
        msg = (
            f"✓ Vault pronto: **{total_md} schede** consegnabili. "
            "Vai in **Settings** per il collegamento all'agente AI "
            "e mostralo al cliente nell'Atto 3."
        )
        target = "Settings"
        kind = "success"
    else:
        msg = (
            "Stato neutro: continua con il prossimo passo del flusso qui sotto."
        )
        target = "Scan"
        kind = "info"

    {"info": st.info, "warning": st.warning, "success": st.success}[kind](
        f"👉 {msg}"
    )
    cols = st.columns([1, 4])
    with cols[0]:
        if st.button(f"→ Apri {target}", key=f"next_step_btn_{target}", type="primary"):
            st.session_state["current_page"] = target
            st.rerun()


def render(active: projects_svc.Project) -> None:
    """Renderizza la dashboard del progetto attivo."""
    render_pipeline_header(active, "Dashboard")
    st.divider()

    st.title(f"Dashboard — {active.name}")
    st.caption(f"Cartella di lavoro: `{active.vault_path}` · ID `{active.id}`")

    stats = vault_svc.vault_stats(Path(active.vault_path))

    if not stats.state_db_exists:
        st.warning(
            "Questo cliente è ancora vuoto. Vai in **Raccolta** e lancia la "
            "prima scansione: la memoria del progetto si crea da sola."
        )

    # Banner "next step" subito visibile, prima delle metriche.
    _next_step_banner(stats)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            "Documenti raccolti",
            stats.docs_total,
            delta=f"{stats.docs_pending} da elaborare" if stats.docs_pending else None,
        )
    with col2:
        approved = stats.entities_by_status.get("approved", 0)
        pending = stats.entities_by_status.get("pending", 0)
        st.metric("Schede approvate", approved,
                  delta=f"{pending} da rivedere" if pending else None)
    with col3:
        total_md = sum(stats.md_by_subdir.values())
        st.metric("Schede nel vault", total_md)
    with col4:
        last = stats.last_run
        if last:
            label = f"{last['command']}"
            st.metric("Ultima operazione", label, delta=last["status"])
        else:
            st.metric("Ultima operazione", "—")

    st.divider()

    colA, colB = st.columns(2)
    with colA:
        st.subheader("Schede per tipo")
        if stats.entities_by_type:
            for et, n in sorted(stats.entities_by_type.items()):
                st.markdown(f"- **{et}**: {n}")
        else:
            st.caption("Nessuna scheda ancora estratta.")

        st.subheader("Schede nel vault per cartella")
        cols = st.columns(len(stats.md_by_subdir))
        for col, (sub, n) in zip(cols, sorted(stats.md_by_subdir.items())):
            col.metric(sub, n)

    with colB:
        st.subheader("Operazioni recenti")
        runs = vault_svc.list_recent_runs(Path(active.vault_path), limit=10)
        if not runs:
            st.caption("Nessuna operazione registrata.")
        else:
            for r in runs:
                badge_color = {
                    "success": "#22c55e",
                    "error": "#ef4444",
                    "running": "#f59e0b",
                }.get(r.get("status") or "", "#94a3b8")
                st.markdown(
                    f"<div style='padding:6px 8px;margin-bottom:4px;"
                    f"border-left:3px solid {badge_color};background:#f8fafc;border-radius:4px;'>"
                    f"<strong>{r['command']}</strong> · "
                    f"<span style='color:{badge_color};'>{r.get('status', '?')}</span><br/>"
                    f"<span style='font-size:0.75rem;color:#475569;'>"
                    f"{r['started_at']} · {r.get('summary') or ''}</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

    st.divider()

    st.subheader("Scorciatoie")
    qcol1, qcol2, qcol3 = st.columns(3)
    vault_path = Path(active.vault_path).expanduser()
    with qcol1:
        if st.button("📂 Apri cartella vault"):
            _open_in_finder(vault_path)
    with qcol2:
        if st.button("⚙️ Collegamento all'agente AI"):
            st.session_state["current_page"] = "Settings"
            st.rerun()
    with qcol3:
        if st.button("🔍 Vai a Revisione"):
            st.session_state["current_page"] = "Review"
            st.rerun()


__all__ = ["render"]
