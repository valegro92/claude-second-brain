"""
Pagina Vault Browser: tree dei file .md + viewer markdown + search.

Permette anche di triggerare il `write` (materializza approved → .md).
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from custodia_web.components.pipeline_header import render_pipeline_header
from custodia_web.services import projects as projects_svc
from custodia_web.services import vault as vault_svc
from custodia_web.services import write as write_svc


def _render_md_viewer(path: Path) -> None:
    """Visualizza una scheda: campi strutturati + note libere."""
    try:
        fm, body = vault_svc.parse_md(path)
    except OSError as exc:
        st.error(f"Impossibile leggere {path}: {exc}")
        return

    st.markdown(f"#### `{path.name}`")
    st.caption(str(path))

    if fm:
        with st.expander("Campi strutturati della scheda", expanded=True):
            st.json(fm)
    else:
        st.caption("Nessun campo strutturato.")

    st.markdown("---")
    st.markdown(body or "_(nessuna nota)_")


def render(active: projects_svc.Project) -> None:
    """Renderizza la pagina Vault."""
    render_pipeline_header(active, "Vault")
    st.divider()

    st.title(f"Consegna — {active.name}")
    st.caption(
        f"`{active.vault_path}` — questa è la cartella che consegnerai al cliente. "
        "Dentro ci sono le schede già pronte per essere usate da un assistente AI "
        "(come Claude). Mostragliela in azione durante l'Atto 3 del progetto."
    )

    vault = Path(active.vault_path)

    # Write button: materializza approved-pending-write
    bcol1, bcol2, bcol3 = st.columns([1, 1, 2])
    with bcol1:
        if st.button("📝 Scrivi nel vault", type="primary",
                     help="Porta nel vault tutte le schede approvate in Revisione."):
            summary = write_svc.write_pending(vault=vault, backup=True)
            if summary.error:
                st.error(summary.error)
            elif summary.pending_count == 0:
                st.info("Niente da scrivere: nessuna scheda approvata in attesa.")
            else:
                st.success(
                    f"✓ {len(summary.written)} schede scritte · "
                    f"{len(summary.skipped)} saltate · "
                    f"{len(summary.backups)} versioni salvate · "
                    f"{len(summary.errors)} errori"
                )
                if summary.written:
                    with st.expander("Schede scritte", expanded=False):
                        for p in summary.written:
                            st.code(p)
    with bcol2:
        if st.button("🔄 Aggiorna elenco"):
            st.rerun()

    # Search box
    query = st.text_input(
        "🔍 Cerca nelle schede",
        placeholder="es. nome cliente, partita IVA, numero commessa...",
    )
    if query.strip():
        results = vault_svc.search_vault(vault, query, limit=30)
        if not results:
            st.caption("Nessun risultato.")
        else:
            st.markdown(f"**{len(results)}** risultati")
            for path, snippet in results:
                rel = path.relative_to(vault) if vault in path.parents else path
                st.markdown(
                    f"<div style='padding:6px 8px;margin-bottom:4px;"
                    f"background:#f1f5f9;border-radius:4px;font-size:0.85rem;'>"
                    f"<strong>{rel}</strong><br/>"
                    f"<code style='font-size:0.75rem;'>...{snippet}...</code></div>",
                    unsafe_allow_html=True,
                )
        return

    # Tree view per subdir
    counts = vault_svc.count_md_files(vault)
    cols = st.columns(len(counts))
    for col, (sub, n) in zip(cols, counts.items()):
        col.metric(sub, n)

    st.divider()

    selected_subdir = st.selectbox(
        "Cartella",
        options=list(vault_svc.VAULT_SUBDIRS),
        index=0,
    )
    files = vault_svc.list_vault_files(vault, subdir=selected_subdir)
    if not files:
        st.caption(f"Nessuna scheda in `{selected_subdir}/`.")
        return

    file_labels = [p.name for p in files]
    chosen = st.selectbox(f"Schede in `{selected_subdir}/`", options=file_labels)
    chosen_path = files[file_labels.index(chosen)]
    _render_md_viewer(chosen_path)


__all__ = ["render"]
