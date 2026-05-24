"""
Stato condiviso fra pagine Streamlit.

Usiamo ``st.session_state`` per:
- ``current_page``: tab selezionata dal nav
- ``review_focus_pk``: entity attualmente in editing nella pagina Review
- ``last_action_msg``: toast da mostrare dopo un'azione cross-page
"""

from __future__ import annotations

import streamlit as st


PAGES = ("Dashboard", "Scan", "Build", "Review", "Vault", "Settings")


def init() -> None:
    """Inizializza le chiavi di session_state al primo run."""
    st.session_state.setdefault("current_page", "Dashboard")
    st.session_state.setdefault("review_focus_pk", None)
    st.session_state.setdefault("last_action_msg", None)


def navigate_to(page: str) -> None:
    """Cambia pagina e forza un rerun."""
    if page not in PAGES:
        raise ValueError(f"Pagina sconosciuta: {page}")
    st.session_state["current_page"] = page


__all__ = ["init", "navigate_to", "PAGES"]
