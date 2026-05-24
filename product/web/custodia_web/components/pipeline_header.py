"""
Pipeline header persistente: barra visiva con i 4 step
Raccolta → Estrazione → Revisione → Consegna.

Mostrata in cima a ogni pagina (tranne Settings) per rendere autoevidente il
modello mentale del prodotto e a che punto è il progetto.

Le chiavi interne (scan/build/review/write) restano invariate per compatibilità
con il routing; cambiano solo le label visibili all'utente.

Design: card con border-left colorato per stato (done/active/todo), counter in
chip pill, numero step in cerchio piccolo a sinistra. Look "premium SaaS".
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from custodia_web.services import projects as projects_svc
from custodia_web.services import vault as vault_svc


# Mapping pagina-corrente → step pipeline. Dashboard non è uno step ma una home.
_PAGE_TO_STEP = {
    "Scan": "scan",
    "Build": "build",
    "Review": "review",
    "Vault": "write",
}

_STEPS = (
    ("scan", "1", "Raccolta", "Cosa pescare e da dove"),
    ("build", "2", "Estrazione", "L'AI legge e crea le schede"),
    ("review", "3", "Revisione", "Controlli e correggi"),
    ("write", "4", "Consegna", "Vault pronto per il cliente"),
)


def _step_state(
    key: str, stats: vault_svc.VaultStats, current: str | None
) -> tuple[str, str]:
    """Ritorna (status, counter) per uno step.

    status ∈ {"done", "active", "todo"}. counter è una stringa breve da mostrare.
    """
    if key == "scan":
        if stats.docs_total > 0:
            status = "active" if current == "scan" else "done"
        else:
            status = "active" if current == "scan" else "todo"
        counter = f"{stats.docs_total} documenti" if stats.docs_total else "—"

    elif key == "build":
        total_ent = sum(stats.entities_by_status.values())
        if total_ent > 0:
            status = "active" if current == "build" else "done"
        else:
            status = "active" if current == "build" else "todo"
        counter = f"{total_ent} schede pronte" if total_ent else "—"

    elif key == "review":
        pending = stats.entities_by_status.get("pending", 0)
        approved = stats.entities_by_status.get("approved", 0)
        if pending == 0 and approved > 0:
            status = "active" if current == "review" else "done"
        elif pending > 0:
            status = "active" if current == "review" else "todo"
        else:
            status = "active" if current == "review" else "todo"
        counter = (
            f"{pending} da rivedere"
            if pending
            else (f"{approved} ok" if approved else "—")
        )

    else:  # write
        total_md = sum(stats.md_by_subdir.values())
        if total_md > 0:
            status = "active" if current == "write" else "done"
        else:
            status = "active" if current == "write" else "todo"
        counter = f"{total_md} nel vault" if total_md else "—"

    return status, counter


# Palette per i 3 stati: (bg, border, fg_title, fg_counter, num_bg, num_fg)
_STATE_STYLE = {
    "done": {
        "bg": "#ECFDF5",
        "border_full": "#A7F3D0",
        "border_accent": "#059669",
        "fg_title": "#065F46",
        "fg_counter": "#047857",
        "num_bg": "#059669",
        "num_fg": "#FFFFFF",
        "shadow": "none",
    },
    "active": {
        "bg": "#FFFFFF",
        "border_full": "#0F766E",
        "border_accent": "#0F766E",
        "fg_title": "#0F766E",
        "fg_counter": "#0F766E",
        "num_bg": "#0F766E",
        "num_fg": "#FFFFFF",
        "shadow": "0 0 0 4px rgba(15,118,110,.08), 0 4px 6px rgba(15,118,110,.08)",
    },
    "todo": {
        "bg": "#F8FAFC",
        "border_full": "#E2E8F0",
        "border_accent": "#CBD5E1",
        "fg_title": "#64748B",
        "fg_counter": "#94A3B8",
        "num_bg": "#E2E8F0",
        "num_fg": "#64748B",
        "shadow": "none",
    },
}


def render_pipeline_header(active: projects_svc.Project, current_page: str) -> None:
    """Renderizza la barra pipeline in cima alla pagina.

    Args:
        active: progetto attivo (richiesto: serve a leggere lo stato del vault).
        current_page: nome della pagina corrente (Dashboard, Scan, Build, …).
    """
    current = _PAGE_TO_STEP.get(current_page)
    stats = vault_svc.vault_stats(Path(active.vault_path))

    cols = st.columns(4, gap="small")
    for col, (key, num, label, tag) in zip(cols, _STEPS):
        status, counter = _step_state(key, stats, current)
        s = _STATE_STYLE[status]
        border_width = "2px" if status == "active" else "1px"
        weight = "700" if status == "active" else "600"

        col.markdown(
            f"""
            <div style="
                background: {s['bg']};
                border: {border_width} solid {s['border_full']};
                border-left: 4px solid {s['border_accent']};
                border-radius: 10px;
                padding: 0.85rem 1rem;
                box-shadow: {s['shadow']};
                height: 100%;
                transition: all 0.15s ease;
            ">
                <div style="display: flex; align-items: center;
                            gap: 0.6rem; margin-bottom: 0.35rem;">
                    <span style="
                        display: inline-flex;
                        align-items: center;
                        justify-content: center;
                        width: 22px;
                        height: 22px;
                        background: {s['num_bg']};
                        color: {s['num_fg']};
                        border-radius: 9999px;
                        font-size: 11px;
                        font-weight: 700;
                        flex-shrink: 0;
                    ">{num}</span>
                    <span style="font-size: 14px; font-weight: {weight};
                                 color: {s['fg_title']};
                                 letter-spacing: -0.005em;">{label}</span>
                </div>
                <div style="font-size: 11px; color: #94A3B8;
                            margin-bottom: 0.25rem; line-height: 1.3;">
                    {tag}
                </div>
                <div style="display: inline-block;
                            background: rgba(255,255,255,0.6);
                            border: 1px solid {s['border_full']};
                            color: {s['fg_counter']};
                            font-size: 11px;
                            font-weight: 600;
                            padding: 0.15rem 0.55rem;
                            border-radius: 9999px;">
                    {counter}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


__all__ = ["render_pipeline_header"]
