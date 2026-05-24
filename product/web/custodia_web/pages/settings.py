"""
Pagina Settings: stato env vars, MCP snippet, versioni.
"""

from __future__ import annotations

import json
import os
from importlib import metadata
from pathlib import Path

import streamlit as st

from custodia_web.components.find_data_help import (
    render_env_vars_setup_help,
    render_fic_credentials_help,
    render_google_drive_credentials_help,
    render_llm_provider_help,
    render_outlook_credentials_help,
)
from custodia_web.services import projects as projects_svc


_ENV_VARS = [
    ("CUSTODIA_ANTHROPIC_API_KEY", "Anthropic API key (build LLM cloud)"),
    ("CUSTODIA_GOOGLE_CREDENTIALS_JSON", "Google Drive OAuth credentials path"),
    ("CUSTODIA_MICROSOFT_CREDENTIALS_JSON", "Outlook 365 OAuth credentials path"),
    ("CUSTODIA_FIC_CREDENTIALS_JSON", "Fatture in Cloud credentials path"),
    ("CUSTODIA_LLM_PROVIDER", "Provider LLM di default (anthropic | fake)"),
]


def _mcp_snippet(vault: Path) -> str:
    """Snippet JSON pronto da incollare in `~/.config/claude/mcp.json`."""
    cfg = {
        "mcpServers": {
            "custodia": {
                "command": "python",
                "args": [
                    "-m",
                    "custodia_mcp",
                    "--vault",
                    str(vault),
                ],
                "env": {},
            }
        }
    }
    return json.dumps(cfg, indent=2, ensure_ascii=False)


def _version(pkg: str) -> str:
    try:
        return metadata.version(pkg)
    except metadata.PackageNotFoundError:
        return "n/a"


def render(active: projects_svc.Project | None) -> None:
    """Renderizza la pagina Settings."""
    st.title("Settings")
    st.caption("Stato env vars, snippet MCP per Claude Code, versioni.")

    st.subheader("Variabili d'ambiente")
    for var, desc in _ENV_VARS:
        is_set = bool(os.environ.get(var))
        icon = "✅" if is_set else "⚪"
        st.markdown(
            f"{icon} **`{var}`** — {desc}" +
            (f"<br/><code style='font-size:0.7rem;color:#475569;'>{os.environ[var][:40]}…</code>" if is_set else "")
            ,
            unsafe_allow_html=True,
        )

    render_env_vars_setup_help()
    st.caption("Guide per ottenere ciascuna credenziale:")
    render_llm_provider_help()
    render_google_drive_credentials_help()
    render_outlook_credentials_help()
    render_fic_credentials_help()

    st.divider()

    st.subheader("🔌 Consegna al cliente — MCP per Claude Code")
    if active is None:
        st.info("Seleziona un progetto attivo per generare lo snippet MCP.")
    else:
        vault = Path(active.vault_path).expanduser().resolve()
        snippet = _mcp_snippet(vault)
        st.success(
            "**Come consegnare il vault all'agente.** "
            "1) Incolla il blocco qui sotto in `~/.config/claude/mcp.json` "
            "(o nel file equivalente del tuo client MCP). "
            "2) Riavvia Claude Code. "
            "3) L'agente del cliente potrà cercare nel vault con i tool "
            "`list_clients`, `get_client`, `search_vault`, `recent_communications`."
        )
        st.code(snippet, language="json")

    st.divider()

    st.subheader("Versioni")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("custodia-web", _version("custodia-web"))
    with col2:
        st.metric("custodia-cli", _version("custodia-cli"))

    st.divider()
    st.caption(
        f"File config webapp: `{projects_svc.PROJECTS_FILE}` · "
        "modifica manualmente solo se sai cosa stai facendo."
    )


__all__ = ["render"]
