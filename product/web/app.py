"""
Entry point Streamlit della webapp Custodia.

Run::

    streamlit run app.py

oppure tramite lo script ``custodia-web`` installato da pyproject.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from custodia_web import state as web_state
from custodia_web.components.empty_state import render_empty_state
from custodia_web.components.project_picker import render_sidebar
from custodia_web.services import projects as projects_svc
from custodia_web.services import scan as scan_svc
from custodia_web.styles import inject_global_styles
from custodia_web.pages import (
    build as page_build,
    dashboard as page_dashboard,
    review as page_review,
    scan as page_scan,
    settings as page_settings,
    vault_browser as page_vault,
)


def _setup_page() -> None:
    st.set_page_config(
        page_title="Custodia",
        page_icon="📦",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    # CSS globale: fonts, hide dev-tool chrome, buttons, custom classes.
    # DEVE essere chiamato subito dopo set_page_config per coprire tutto il rendering.
    inject_global_styles()


def _render_nav() -> None:
    """Nav orizzontale: una row di bottoni che impostano `current_page`."""
    current = st.session_state.get("current_page", "Dashboard")
    cols = st.columns(len(web_state.PAGES))
    for col, page in zip(cols, web_state.PAGES):
        is_active = page == current
        label = f"**{page}**" if is_active else page
        if col.button(label, key=f"nav_{page}", use_container_width=True):
            web_state.navigate_to(page)
            st.rerun()


def _render_page(active) -> None:  # type: ignore[no-untyped-def]
    """Dispatch alla pagina corrente."""
    page = st.session_state.get("current_page", "Dashboard")

    # Settings non richiede un progetto attivo.
    if page == "Settings":
        page_settings.render(active)
        return

    if active is None:
        render_empty_state()
        return

    if page == "Dashboard":
        page_dashboard.render(active)
    elif page == "Scan":
        page_scan.render(active)
    elif page == "Build":
        page_build.render(active)
    elif page == "Review":
        page_review.render(active)
    elif page == "Vault":
        page_vault.render(active)
    else:
        st.error(f"Pagina sconosciuta: {page}")


def _reap_interrupted_once() -> None:
    """All'avvio della sessione, marca come ``interrupted`` i run abbandonati.

    Idempotente per sessione: usa una flag in ``st.session_state``. Itera
    su tutti i progetti registrati e chiama
    :func:`scan_svc.reap_interrupted_runs_for_vault` per ciascun vault.
    Silenzioso: se un vault è inaccessibile, si ignora l'errore.
    """
    if st.session_state.get("_reaped_at_startup"):
        return
    st.session_state["_reaped_at_startup"] = True
    try:
        for proj in projects_svc.list_projects():
            try:
                scan_svc.reap_interrupted_runs_for_vault(
                    Path(proj.vault_path), threshold_minutes=5
                )
            except Exception:  # noqa: BLE001 — best effort, mai bloccare l'avvio
                pass
    except Exception:  # noqa: BLE001
        pass


def main() -> None:
    """Entry point."""
    _setup_page()
    web_state.init()
    _reap_interrupted_once()
    active = render_sidebar()
    # Nascondi il nav quando non c'è progetto attivo: l'empty state vuole
    # essere la prima cosa che l'utente vede, senza distrazioni.
    if active is not None or st.session_state.get("current_page") == "Settings":
        _render_nav()
        st.divider()
    _render_page(active)


if __name__ == "__main__":
    main()
