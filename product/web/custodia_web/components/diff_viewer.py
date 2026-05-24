"""
Diff viewer: confronto visivo fra il frontmatter candidato e quello già nel vault.

Non usa librerie esterne (no `diff-match-patch`): semplice diff campo-per-campo
con styling HTML inline. È sufficiente per il dominio (frontmatter YAML
ragionevolmente piccolo: 10-30 chiavi).
"""

from __future__ import annotations

from typing import Any

import streamlit as st
import yaml


def _yaml_dump(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, str):
        return value
    return yaml.safe_dump(value, allow_unicode=True, default_flow_style=False, sort_keys=False).strip()


def render_field_diff(
    candidate: dict[str, Any],
    vault: dict[str, Any] | None,
) -> None:
    """Renderizza una tabella diff dei campi frontmatter.

    Tre stati per riga:
    - aggiunto (presente in candidate, assente in vault) → verde
    - modificato (presente in entrambi ma diverso) → giallo
    - invariato → grigio chiaro
    Mostriamo anche i campi solo-vault (rosso) per consapevolezza.
    """
    vault = vault or {}
    keys = list(candidate.keys()) + [k for k in vault if k not in candidate]

    if not keys:
        st.info("Nessun campo da confrontare.")
        return

    rows_html = []
    for key in keys:
        in_cand = key in candidate
        in_vault = key in vault
        cand_val = _yaml_dump(candidate.get(key))
        vault_val = _yaml_dump(vault.get(key))

        if in_cand and not in_vault:
            tag, bg = "NEW", "#dcfce7"
        elif not in_cand and in_vault:
            tag, bg = "ONLY-VAULT", "#fee2e2"
        elif cand_val != vault_val:
            tag, bg = "CHANGED", "#fef9c3"
        else:
            tag, bg = "=", "#f8fafc"

        rows_html.append(
            f"<tr style='background:{bg};'>"
            f"<td style='padding:6px 8px;vertical-align:top;font-weight:600;'>{key}</td>"
            f"<td style='padding:6px 8px;vertical-align:top;font-family:monospace;font-size:0.78rem;'>"
            f"<pre style='margin:0;white-space:pre-wrap;'>{cand_val}</pre></td>"
            f"<td style='padding:6px 8px;vertical-align:top;font-family:monospace;font-size:0.78rem;color:#475569;'>"
            f"<pre style='margin:0;white-space:pre-wrap;'>{vault_val}</pre></td>"
            f"<td style='padding:6px 8px;vertical-align:top;font-size:0.7rem;color:#0F766E;'>{tag}</td>"
            f"</tr>"
        )

    html = (
        "<table style='width:100%;border-collapse:collapse;font-size:0.85rem;'>"
        "<thead><tr style='background:#0F766E;color:white;'>"
        "<th style='padding:6px 8px;text-align:left;'>campo</th>"
        "<th style='padding:6px 8px;text-align:left;'>candidato</th>"
        "<th style='padding:6px 8px;text-align:left;'>vault</th>"
        "<th style='padding:6px 8px;text-align:left;'>stato</th>"
        "</tr></thead>"
        f"<tbody>{''.join(rows_html)}</tbody></table>"
    )
    st.markdown(html, unsafe_allow_html=True)


__all__ = ["render_field_diff"]
