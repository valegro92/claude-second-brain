"""
Empty state per quando non c'è progetto attivo: spiega il modello mentale di
Custodia e offre un bottone "Prova con demo" che pre-popola un progetto
funzionante in pochi click.

Design: hero card teal-subtle + 4 step cards (Raccolta → Estrazione → Revisione
→ Consegna) + CTA con pulsanti tipizzati. Look "premium SaaS", non "default
Streamlit".
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import streamlit as st

from custodia_web.services import projects as projects_svc


# Path della fixture finto-drive nel repo. Risaliamo dal file corrente:
# custodia_web/components/empty_state.py → product/cli/tests/fixtures/finto-drive
_FIXTURE_FINTO_DRIVE = (
    Path(__file__).resolve().parents[3] / "cli" / "tests" / "fixtures" / "finto-drive"
)


def _demo_filesystem_root() -> Path | None:
    """Ritorna il path della fixture finto-drive se esiste sul disco."""
    if _FIXTURE_FINTO_DRIVE.exists():
        return _FIXTURE_FINTO_DRIVE
    return None


def _create_demo_project() -> projects_svc.Project:
    """Crea (o riusa) il progetto Demo (finto-drive) pre-configurato."""
    demo_name = "Demo (finto-drive)"
    vault_path = Path(tempfile.gettempdir()) / "custodia-demo" / "vault"
    vault_path.mkdir(parents=True, exist_ok=True)

    for p in projects_svc.list_projects():
        if p.name == demo_name:
            projects_svc.set_active_project(p.id)
            proj = p
            break
    else:
        proj = projects_svc.create_project(demo_name, vault_path, color="#0F766E")

    fs_root = _demo_filesystem_root()
    if fs_root is not None:
        st.session_state["fs_form_prefill_root"] = str(fs_root)
    st.session_state["demo_just_created"] = True
    st.session_state["current_page"] = "Scan"
    return proj


# Step della pipeline (allineati ai nuovi nomi italiani usati ovunque).
_FLOW = [
    ("1", "Raccolta", "Connetti Drive, Outlook, Fatture in Cloud, NAS o cartelle locali."),
    ("2", "Estrazione", "L'AI legge i documenti e propone schede di clienti, fornitori, commesse."),
    ("3", "Revisione", "Tu valuti ciascuna scheda con human-in-the-loop. Accetti o correggi."),
    ("4", "Consegna", "Il vault `.md` Obsidian è il deliverable: leggibile da Claude Code via MCP."),
]


def _render_hero() -> None:
    """Hero card teal-subtle con titolo grande + chip versione."""
    st.markdown(
        """
        <div class="hero-card" style="
            background: linear-gradient(135deg, rgba(15,118,110,.05) 0%, rgba(15,118,110,0) 60%);
            border: 1px solid rgba(15,118,110,.14);
            border-radius: 16px;
            padding: 3rem 2.5rem;
            margin-bottom: 2.5rem;
        ">
            <div style="display: flex; justify-content: space-between;
                        align-items: flex-start; gap: 2rem; flex-wrap: wrap;">
                <div style="flex: 1; min-width: 320px;">
                    <div style="color: #0F766E; font-size: 11px; font-weight: 600;
                                text-transform: uppercase; letter-spacing: 0.08em;
                                margin-bottom: 1rem;">
                        Second brain · Agent-ready
                    </div>
                    <h1 style="font-size: 56px; font-weight: 700;
                               letter-spacing: -0.04em; color: #0F172A;
                               margin: 0 0 1rem 0; line-height: 1.05;">
                        Custodia
                    </h1>
                    <p style="font-size: 20px; color: #334155; font-weight: 500;
                              line-height: 1.5; margin: 0 0 1rem 0;
                              max-width: 640px;">
                        Trasforma il caos documentale di una PMI italiana in un
                        vault Obsidian leggibile da agenti AI.
                    </p>
                    <p style="font-size: 16px; color: #64748B; line-height: 1.65;
                              margin: 0; max-width: 640px;">
                        Connetti Drive, NAS, Outlook e Fatture in Cloud — l'AI
                        estrae le schede del cliente, tu le valuti e le consegni
                        come deliverable.
                    </p>
                </div>
                <span style="
                    background: #FEF3C7;
                    color: #92400E;
                    padding: 0.3rem 0.85rem;
                    border-radius: 9999px;
                    font-size: 11px;
                    font-weight: 600;
                    letter-spacing: 0.06em;
                    text-transform: uppercase;
                    white-space: nowrap;
                    flex-shrink: 0;
                ">v1.5 beta</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_flow() -> None:
    """4 step cards con numero gigante teal a basso opacity."""
    st.markdown(
        """
        <div style="color: #0F766E; font-size: 11px; font-weight: 600;
                    text-transform: uppercase; letter-spacing: 0.08em;
                    margin-bottom: 0.5rem;">
            Il flusso
        </div>
        <h3 style="font-size: 24px; font-weight: 600; color: #0F172A;
                   letter-spacing: -0.01em; margin: 0 0 1.5rem 0;">
            Quattro atti, da sorgente caotica a deliverable consultabile
        </h3>
        """,
        unsafe_allow_html=True,
    )

    cols = st.columns(4, gap="medium")
    for col, (num, label, detail) in zip(cols, _FLOW):
        col.markdown(
            f"""
            <div class="step-card" style="
                background: white;
                border: 1px solid #E2E8F0;
                border-radius: 12px;
                padding: 1.5rem;
                height: 100%;
                box-shadow: 0 1px 2px rgba(15,23,42,.04), 0 1px 3px rgba(15,23,42,.06);
                transition: all 0.2s ease;
            ">
                <div style="font-size: 56px; font-weight: 700;
                            color: #0F766E; opacity: 0.18;
                            line-height: 1; margin-bottom: 0.5rem;
                            letter-spacing: -0.04em;">
                    {num}
                </div>
                <div style="font-size: 18px; font-weight: 600;
                            color: #0F172A; margin-bottom: 0.5rem;
                            letter-spacing: -0.01em;">
                    {label}
                </div>
                <div style="font-size: 14px; color: #64748B;
                            line-height: 1.55;">
                    {detail}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_empty_state() -> None:
    """Mostra l'empty state quando nessun progetto è selezionato/registrato."""
    _render_hero()
    _render_flow()

    st.markdown(
        """
        <div style="height: 2.5rem;"></div>
        <div style="color: #0F766E; font-size: 11px; font-weight: 600;
                    text-transform: uppercase; letter-spacing: 0.08em;
                    margin-bottom: 0.5rem;">
            Inizia
        </div>
        <h3 style="font-size: 24px; font-weight: 600; color: #0F172A;
                   letter-spacing: -0.01em; margin: 0 0 1.25rem 0;">
            Crea il primo progetto o prova la demo offline
        </h3>
        """,
        unsafe_allow_html=True,
    )

    btn_cols = st.columns([1, 1, 2])
    with btn_cols[0]:
        if st.button("➕ Crea progetto vuoto", use_container_width=True):
            st.session_state["open_new_project_form"] = True
            st.info(
                "Apri **➕ Nuovo progetto** nella sidebar per inserire "
                "nome e path del vault."
            )
    with btn_cols[1]:
        fixture_ok = _demo_filesystem_root() is not None
        label = "▶ Prova con demo" if fixture_ok else "▶ Demo (fixture mancante)"
        if st.button(
            label,
            use_container_width=True,
            type="primary",
            disabled=not fixture_ok,
        ):
            _create_demo_project()
            st.rerun()
    with btn_cols[2]:
        if not _demo_filesystem_root():
            st.caption(
                "Fixture `product/cli/tests/fixtures/finto-drive` non trovata: "
                "puoi comunque creare un progetto manualmente."
            )
        else:
            st.caption(
                "La demo usa una cartella finta-drive del repo + provider LLM "
                "`fake` con risposte canned. Tutto offline, niente API key."
            )

    with st.expander("❓ Come funziona — modello mentale"):
        st.markdown(
            "- **Un progetto = un cliente.** Ogni cliente PMI ha il suo vault Obsidian.\n"
            "- **Più sorgenti per progetto.** Filesystem (NAS, Drive locale), "
            "Google Drive, Outlook 365, Fatture in Cloud — connetti quelle che ha "
            "il cliente.\n"
            "- **Extractor LLM.** Custodia legge i documenti accumulati e propone "
            "entità candidate (cliente, fornitore, commessa, comunicazione) con "
            "frontmatter YAML.\n"
            "- **Tu approvi.** Pagina Revisione: vedi ciascun candidato, accetti o "
            "modifichi.\n"
            "- **Vault Obsidian = deliverable.** I file `.md` finali sono leggibili "
            "da Claude Code via MCP — diventano la memoria che il cliente può "
            "interrogare in linguaggio naturale."
        )


__all__ = ["render_empty_state"]
