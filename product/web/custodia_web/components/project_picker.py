"""
Project picker in sidebar: selectbox dei progetti + form per crearne uno nuovo.

Effetti collaterali: aggiorna `set_active_project` quando l'utente cambia
selezione e forza `st.rerun()` per refreshare le pagine.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from custodia_web.services import projects as projects_svc


def render_sidebar() -> projects_svc.Project | None:
    """Renderizza il picker in sidebar e ritorna il progetto attivo."""
    st.sidebar.markdown(
        "<div style='font-size:1.4rem;font-weight:700;color:#0F766E;'>Custodia</div>"
        "<div style='font-size:0.85rem;color:#475569;margin-bottom:0.2rem;'>"
        "console consulente"
        "</div>"
        "<div style='font-size:0.78rem;color:#64748b;line-height:1.35;"
        "margin-bottom:0.6rem;'>"
        "Trasforma i documenti del cliente in un archivio che l'AI sa leggere."
        "</div>",
        unsafe_allow_html=True,
    )

    items = projects_svc.list_projects()
    active = projects_svc.get_active_project()

    if items:
        labels = [f"{p.name}" for p in items]
        ids = [p.id for p in items]
        default_idx = ids.index(active.id) if active and active.id in ids else 0
        chosen_label = st.sidebar.selectbox(
            "Cliente attivo",
            labels,
            index=default_idx,
            key="project_picker_select",
        )
        chosen_id = ids[labels.index(chosen_label)]
        if active is None or chosen_id != active.id:
            projects_svc.set_active_project(chosen_id)
            st.rerun()
        active = projects_svc.get_active_project()
    else:
        st.sidebar.info("Nessun cliente ancora. Creane uno qui sotto.")

    # Auto-expand della form se l'utente ha cliccato "Crea progetto vuoto"
    # dall'empty state principale.
    _force_open = st.session_state.pop("open_new_project_form", False)
    with st.sidebar.expander("➕ Nuovo cliente", expanded=_force_open or not items):
        with st.form("new_project_form", clear_on_submit=True):
            name = st.text_input("Nome cliente", placeholder="Rossetto Laminazioni SRL")
            vault_path = st.text_input(
                "Cartella di lavoro",
                placeholder="/Users/me/Vault/rossetto",
                help="Dove salvare le schede del cliente. Se la cartella non esiste, viene creata.",
            )
            color = st.color_picker("Colore", value="#0F766E")
            submitted = st.form_submit_button("Crea")
            if submitted:
                if not name.strip() or not vault_path.strip():
                    st.warning("Nome e cartella sono obbligatori.")
                else:
                    try:
                        Path(vault_path).expanduser().mkdir(parents=True, exist_ok=True)
                        proj = projects_svc.create_project(name, vault_path, color=color)
                        st.success(f"Cliente creato: {proj.id}")
                        st.rerun()
                    except (OSError, ValueError) as exc:
                        st.error(f"Errore: {exc}")

    if active is not None:
        st.sidebar.markdown(
            f"<div style='margin-top:0.8rem;padding:0.4rem 0.6rem;"
            f"background:{active.color}22;border-left:3px solid {active.color};"
            f"border-radius:4px;font-size:0.8rem;'>"
            f"<strong>{active.name}</strong><br/>"
            f"<code style='font-size:0.7rem;color:#475569;'>{active.vault_path}</code>"
            f"</div>",
            unsafe_allow_html=True,
        )
        with st.sidebar.expander("Gestione cliente"):
            if st.button("🗑 Rimuovi dalla lista", key="delete_project_btn",
                         help="Toglie il cliente dalla console. I file sul disco restano dove sono."):
                projects_svc.delete_project(active.id)
                st.rerun()

    with st.sidebar.expander("❓ Come funziona"):
        st.markdown(
            "Custodia trasforma documenti aziendali del tuo cliente "
            "(mail, contratti, fatture, listini) in un archivio strutturato "
            "che un assistente AI può consultare.\n\n"
            "**Il tuo lavoro:**\n"
            "1. Indichi a Custodia **dove pescare** (Drive, NAS, Outlook, "
            "Fatture in Cloud)\n"
            "2. L'AI legge e propone le **schede** (clienti, fornitori, "
            "commesse, mail importanti)\n"
            "3. Tu **controlli e correggi**\n"
            "4. La **cartella finale** va al cliente\n\n"
            "Il valore consulenziale sta nel passo 3: le correzioni e le note "
            "che solo tu sai aggiungere."
        )

    st.sidebar.divider()
    return active


__all__ = ["render_sidebar"]
