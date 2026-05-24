"""
Page header coerente per ogni pagina di Custodia.

Pattern: eyebrow (microlabel teal uppercase) → title (32px bold) → subtitle (16px slate).
Separa visivamente l'header dal corpo della pagina con un bordo sottile.
"""

from __future__ import annotations

import html

import streamlit as st


def render_page_header(*, eyebrow: str, title: str, subtitle: str) -> None:
    """Header coerente per ogni pagina.

    Args:
        eyebrow: microlabel uppercase (es. "Step 1 · Raccolta")
        title: H1 della pagina
        subtitle: descrizione breve sotto al titolo
    """
    st.markdown(
        f"""
        <div style="margin-bottom: 2.5rem; padding-bottom: 1.5rem;
                    border-bottom: 1px solid #E2E8F0;">
            <div style="color: #0F766E; font-size: 11px; font-weight: 600;
                        text-transform: uppercase; letter-spacing: 0.08em;
                        margin-bottom: 0.5rem;">
                {html.escape(eyebrow)}
            </div>
            <h1 style="font-size: 32px; font-weight: 700; color: #0F172A;
                       letter-spacing: -0.02em; margin: 0 0 0.5rem 0;
                       line-height: 1.2;">
                {html.escape(title)}
            </h1>
            <p style="font-size: 16px; color: #64748B; margin: 0;
                      line-height: 1.6; max-width: 720px;">
                {html.escape(subtitle)}
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


__all__ = ["render_page_header"]
