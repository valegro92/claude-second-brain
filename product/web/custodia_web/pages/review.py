"""
Pagina Review: la sostituta GUI del REPL terminale.

UX rispetto al REPL:
- Tabella con tutte le pending; click su una row la mette in "focus".
- Form editabile del frontmatter (st.text_area con YAML) + body markdown.
- Diff visivo vs vault esistente (componente diff_viewer).
- Buttons espliciti: Accetta / Salva edit / Skip / Merge.
- "Accept all visible" come bulk action.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit as st
import yaml

from custodia_web.components.diff_viewer import render_field_diff
from custodia_web.components.pipeline_header import render_pipeline_header
from custodia_web.services import projects as projects_svc
from custodia_web.services import vault as vault_svc


def _load_vault_fm(vault: Path, entity_type: str, entity_id: str) -> dict[str, Any] | None:
    existing = vault_svc.existing_md_for_entity(vault, entity_type, entity_id)
    if existing is None:
        return None
    fm, _ = vault_svc.parse_md(existing)
    return fm


def _fm_to_yaml(fm: dict[str, Any]) -> str:
    return yaml.safe_dump(fm, allow_unicode=True, default_flow_style=False, sort_keys=False)


def _yaml_to_fm(text: str) -> dict[str, Any]:
    data = yaml.safe_load(text)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError("Il frontmatter deve essere un dict YAML, non lista/scalare.")
    return data


def _confidence_label(c: float) -> str:
    """Mappa il valore numerico in etichetta leggibile."""
    if c < 0.4:
        return "affidabilità bassa"
    if c < 0.7:
        return "affidabilità media"
    return "affidabilità alta"


def _render_focused_entity(vault: Path, entity: dict[str, Any]) -> None:
    """Pannello di editing per una singola scheda da rivedere."""
    st.markdown(
        f"### Scheda: `{entity['entity_type']}` — **{entity['entity_id']}** "
        f"· {_confidence_label(entity['confidence'])} ({entity['confidence']:.2f})"
    )
    st.caption(f"Estratta da {len(entity['source_doc_ids'])} documenti")

    vault_fm = _load_vault_fm(vault, entity["entity_type"], entity["entity_id"])
    if vault_fm is not None:
        st.info(
            f"Nel vault esiste già una scheda per `{entity['entity_id']}`. "
            "Confronta con quella nuova qui sotto e decidi se sostituire o unire."
        )

    tabs = st.tabs(["📝 Modifica", "🔀 Confronto col vault", "📄 Documenti di origine"])
    with tabs[0]:
        col1, col2 = st.columns([3, 2])
        with col1:
            yaml_key = f"yaml_edit_{entity['id']}"
            default_yaml = _fm_to_yaml(entity["frontmatter"])
            edited_yaml = st.text_area(
                "Campi strutturati della scheda",
                value=st.session_state.get(yaml_key, default_yaml),
                height=360,
                key=yaml_key,
                help="Modifica nome, partita IVA, telefono, e gli altri campi della scheda.",
            )
            body_key = f"body_edit_{entity['id']}"
            edited_body = st.text_area(
                "Note libere",
                value=st.session_state.get(body_key, entity.get("body_md") or ""),
                height=180,
                key=body_key,
                help="Appunti aggiuntivi. Vanno nel corpo del file, sotto i campi.",
            )
        with col2:
            st.markdown("**Anteprima dei campi**")
            try:
                preview = _yaml_to_fm(edited_yaml)
                st.json(preview, expanded=False)
            except yaml.YAMLError as exc:
                st.error(f"Formato non valido: {exc}")

        st.divider()
        bcol1, bcol2, bcol3, bcol4 = st.columns(4)
        with bcol1:
            if st.button("✓ Tieni così", type="primary", key=f"accept_{entity['id']}"):
                vault_svc.record_decision(vault, entity_pk=entity["id"], decision="approved")
                st.session_state["review_focus_pk"] = None
                st.success("Scheda approvata.")
                st.rerun()
        with bcol2:
            if st.button("✏ Salva correzioni", key=f"edit_{entity['id']}"):
                try:
                    fm = _yaml_to_fm(edited_yaml)
                except (yaml.YAMLError, ValueError) as exc:
                    st.error(f"Impossibile salvare: {exc}")
                else:
                    vault_svc.record_decision(
                        vault, entity_pk=entity["id"], decision="edited",
                        edited_frontmatter=fm,
                    )
                    st.session_state["review_focus_pk"] = None
                    st.success("Correzioni salvate. Scheda approvata.")
                    st.rerun()
        with bcol3:
            if st.button("⊘ Scarta", key=f"skip_{entity['id']}",
                         help="Non finirà nel vault."):
                vault_svc.record_decision(vault, entity_pk=entity["id"], decision="rejected")
                st.session_state["review_focus_pk"] = None
                st.info("Scheda scartata.")
                st.rerun()
        with bcol4:
            if vault_fm is not None and st.button("🔀 Unisci a quella nel vault",
                                                  key=f"merge_{entity['id']}"):
                # Unione: i campi della scheda nuova sovrascrivono quelli del vault,
                # i campi presenti solo nel vault restano.
                merged = {**vault_fm, **entity["frontmatter"]}
                st.session_state[yaml_key] = _fm_to_yaml(merged)
                st.info(
                    "Unione applicata nel form. Verifica i campi e premi "
                    "**Salva correzioni** per confermare."
                )

    with tabs[1]:
        st.markdown("**Confronto campo per campo** (scheda nuova vs scheda già nel vault)")
        render_field_diff(entity["frontmatter"], vault_fm)

    with tabs[2]:
        st.markdown(f"Documenti da cui è stata estratta: `{entity['source_doc_ids']}`")


def render(active: projects_svc.Project) -> None:
    """Renderizza la pagina Revisione."""
    render_pipeline_header(active, "Review")
    st.divider()

    st.title(f"Revisione — {active.name}")
    st.caption(
        "Qui controlli le schede che l'AI ha letto dai documenti del cliente. "
        "Per ogni scheda decidi: la tengo così, la correggo, la scarto, "
        "o la unisco a una già nel vault."
    )

    vault = Path(active.vault_path)

    fcol1, fcol2, fcol3 = st.columns([2, 2, 1])
    with fcol1:
        type_filter = st.selectbox(
            "Filtra per tipo",
            options=("all", "cliente", "fornitore", "commessa", "comunicazione"),
            index=0,
            format_func=lambda v: "Tutti i tipi" if v == "all" else v.capitalize(),
        )
    with fcol2:
        st.write("")  # spacer
        bulk = st.button("✓ Approva tutte quelle visibili")
    with fcol3:
        st.write("")
        if st.button("🔄 Aggiorna"):
            st.rerun()

    type_arg = None if type_filter == "all" else type_filter
    pending = vault_svc.list_pending_entities(vault, entity_type=type_arg)

    if bulk and pending:
        for ent in pending:
            vault_svc.record_decision(vault, entity_pk=ent["id"], decision="approved")
        st.success(f"{len(pending)} schede approvate in blocco.")
        st.rerun()

    if not pending:
        st.info(
            "Nessuna scheda da rivedere. Lancia un'**Estrazione** o cambia il filtro."
        )
        return

    st.markdown(f"**{len(pending)}** schede in attesa di revisione")

    # Tabella riepilogo con colonne in italiano leggibili
    rows = [
        {
            "Tipo": e["entity_type"],
            "Nome scheda": e["entity_id"],
            "Affidabilità": _confidence_label(e["confidence"]),
            "Documenti origine": len(e["source_doc_ids"]),
        }
        for e in pending
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True)

    # Selettore: lista compatta di id → pk
    options = [
        f"{e['entity_type']}: {e['entity_id']} ({_confidence_label(e['confidence'])})"
        for e in pending
    ]
    pks = [e["id"] for e in pending]
    focus_pk = st.session_state.get("review_focus_pk")
    default_idx = pks.index(focus_pk) if focus_pk in pks else 0
    chosen = st.selectbox("Scegli la scheda da rivedere", options, index=default_idx)
    chosen_pk = pks[options.index(chosen)]
    st.session_state["review_focus_pk"] = chosen_pk

    st.divider()
    focused = vault_svc.get_entity_by_pk(vault, chosen_pk)
    if focused is None:
        st.warning("Scheda non più disponibile (forse già rivista).")
        return
    _render_focused_entity(vault, focused)


__all__ = ["render"]
