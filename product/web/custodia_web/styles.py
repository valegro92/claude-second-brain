"""
CSS injection globale per Custodia webapp.

Trasforma il look "default Streamlit" in un look "premium SaaS italiano":
- Font Inter + JetBrains Mono via Google Fonts
- Palette teal + slate + accenti amber
- Nasconde gli elementi dev-tool di Streamlit (deploy button, hamburger, footer)
- Pulsanti CTA con gradient + shadow + hover lift
- Custom classes: .hero-card, .step-card, .metric-card, .chip-amber, .eyebrow, .pipeline-step

Chiamare ``inject_global_styles()`` UNA VOLTA in ``app.py`` subito dopo
``st.set_page_config()``.
"""

from __future__ import annotations

import streamlit as st


_GLOBAL_CSS = """
<style>
/* ============================================================
   1. FONTS — Inter + JetBrains Mono
   ============================================================ */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,400..700,0..1,-50..200');

html, body, [class*="css"], [class*="st-"], .stMarkdown, .stText,
button, input, select, textarea {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, system-ui, sans-serif !important;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}

/* Material Symbols (icone Streamlit per expander/checkbox/select). NON sovrascrivere font-family qui. */
.material-symbols-rounded,
.material-symbols-outlined,
[class*="material-icons"],
[class*="MaterialSymbols"],
span[data-icon],
[data-testid="stIconMaterial"],
.st-emotion-cache-1xulwhk span,
[data-testid="stExpanderToggleIcon"],
[data-testid="stCheckbox"] svg + span,
[data-testid="stExpander"] [data-testid="stIconMaterial"] {
    font-family: 'Material Symbols Rounded', 'Material Symbols Outlined' !important;
    font-feature-settings: 'liga';
    font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24;
    -webkit-font-feature-settings: 'liga';
    font-style: normal;
    line-height: 1;
}

code, pre, .stCodeBlock, [data-testid="stCodeBlock"] {
    font-family: 'JetBrains Mono', 'SF Mono', Menlo, monospace !important;
    font-size: 13.5px;
}

/* ============================================================
   2. HIDE STREAMLIT DEV-TOOL CHROME
   ============================================================ */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; height: 0; }
header[data-testid="stHeader"] {
    background: transparent !important;
    height: 0 !important;
}
[data-testid="stToolbar"] { display: none !important; }
[data-testid="stDecoration"] { display: none !important; }
.stDeployButton { display: none !important; }
[data-testid="manage-app-button"] { display: none !important; }
.stApp > header { display: none !important; }

/* ============================================================
   3. LAYOUT — container width + padding
   ============================================================ */
.main .block-container {
    max-width: 1200px !important;
    padding-top: 2rem !important;
    padding-bottom: 4rem !important;
    padding-left: 2rem !important;
    padding-right: 2rem !important;
}

.stApp {
    background: #FAFAF9;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: #F1F5F9 !important;
    border-right: 1px solid #E2E8F0;
}
[data-testid="stSidebar"] > div:first-child {
    padding-top: 1.5rem;
}

/* ============================================================
   4. TYPOGRAPHY
   ============================================================ */
h1, .stMarkdown h1 {
    font-size: 40px !important;
    font-weight: 700 !important;
    letter-spacing: -0.03em !important;
    color: #0F172A !important;
    line-height: 1.15 !important;
}
h2, .stMarkdown h2 {
    font-size: 32px !important;
    font-weight: 700 !important;
    letter-spacing: -0.02em !important;
    color: #0F172A !important;
    line-height: 1.2 !important;
}
h3, .stMarkdown h3 {
    font-size: 24px !important;
    font-weight: 600 !important;
    letter-spacing: -0.01em !important;
    color: #0F172A !important;
    line-height: 1.3 !important;
}
h4, .stMarkdown h4 {
    font-size: 18px !important;
    font-weight: 600 !important;
    color: #0F172A !important;
}
p, .stMarkdown p, [data-testid="stMarkdownContainer"] p {
    font-size: 16px;
    color: #334155;
    line-height: 1.65;
}

.eyebrow {
    font-size: 11px !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #0F766E;
}

/* ============================================================
   5. BUTTONS — primary gradient + hover lift
   ============================================================ */
.stButton > button {
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 15px !important;
    letter-spacing: -0.01em !important;
    transition: all 0.15s ease !important;
    border: 1px solid #E2E8F0 !important;
    padding: 0.65rem 1.25rem !important;
    background: white !important;
    color: #0F172A !important;
}

.stButton > button:hover {
    border-color: #0F766E !important;
    color: #0F766E !important;
    transform: translateY(-1px);
}

.stButton > button[kind="primary"] {
    background: linear-gradient(180deg, #0F766E 0%, #0E6B63 100%) !important;
    color: white !important;
    border: none !important;
    padding: 0.75rem 1.5rem !important;
    box-shadow: 0 1px 2px rgba(15,118,110,.2), 0 2px 4px rgba(15,118,110,.1) !important;
}

.stButton > button[kind="primary"]:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 6px rgba(15,118,110,.25), 0 10px 15px rgba(15,118,110,.15) !important;
    color: white !important;
}

.stButton > button[kind="primary"]:active {
    transform: translateY(0) !important;
}

/* Disabled buttons */
.stButton > button:disabled {
    opacity: 0.5 !important;
    cursor: not-allowed !important;
    transform: none !important;
}

/* ============================================================
   6. INPUTS — text, select, textarea
   ============================================================ */
.stTextInput > div > div > input,
.stTextArea textarea,
.stSelectbox > div > div,
.stNumberInput > div > div > input {
    border-radius: 8px !important;
    border: 1px solid #E2E8F0 !important;
    font-size: 15px !important;
    transition: all 0.15s ease !important;
}

.stTextInput > div > div > input:focus,
.stTextArea textarea:focus,
.stNumberInput > div > div > input:focus {
    border-color: #0F766E !important;
    box-shadow: 0 0 0 3px rgba(15,118,110,.1) !important;
}

/* ============================================================
   7. EXPANDER + ALERTS
   ============================================================ */
.streamlit-expanderHeader, [data-testid="stExpander"] details > summary {
    font-weight: 600 !important;
    border-radius: 8px !important;
}

[data-testid="stExpander"] {
    border: 1px solid #E2E8F0 !important;
    border-radius: 12px !important;
    background: white !important;
}

[data-testid="stAlert"] {
    border-radius: 12px !important;
    border: 1px solid #E2E8F0;
    padding: 1rem 1.25rem !important;
}

/* ============================================================
   8. CUSTOM CLASSES per components
   ============================================================ */
.hero-card {
    background: linear-gradient(135deg, rgba(15,118,110,.04) 0%, rgba(15,118,110,0) 100%);
    border: 1px solid rgba(15,118,110,.12);
    border-radius: 16px;
    padding: 3rem 2.5rem;
    margin-bottom: 2.5rem;
}

.step-card {
    background: white;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
    padding: 1.5rem;
    transition: all 0.2s ease;
    height: 100%;
    box-shadow: 0 1px 2px rgba(15,23,42,.04), 0 1px 3px rgba(15,23,42,.06);
}
.step-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 6px rgba(15,23,42,.05), 0 10px 15px rgba(15,23,42,.07);
    border-color: #0F766E;
}

.metric-card {
    background: white;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
    padding: 1.25rem;
    box-shadow: 0 1px 2px rgba(15,23,42,.04);
}

.chip-amber {
    display: inline-block;
    background: #FEF3C7;
    color: #92400E;
    padding: 0.25rem 0.75rem;
    border-radius: 9999px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}

.chip-teal {
    display: inline-block;
    background: #CCFBF1;
    color: #0F766E;
    padding: 0.25rem 0.75rem;
    border-radius: 9999px;
    font-size: 11px;
    font-weight: 600;
}

.pipeline-step {
    border-radius: 10px;
    padding: 0.85rem 1rem;
    transition: all 0.15s ease;
    height: 100%;
}
.pipeline-step--done {
    background: #ECFDF5;
    border: 1px solid #A7F3D0;
    border-left: 4px solid #059669;
}
.pipeline-step--active {
    background: white;
    border: 2px solid #0F766E;
    box-shadow: 0 0 0 4px rgba(15,118,110,.08);
}
.pipeline-step--todo {
    background: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-left: 4px solid #CBD5E1;
}

/* ============================================================
   9. DIVIDER + TABS
   ============================================================ */
hr, [data-testid="stDivider"] {
    border-color: #E2E8F0 !important;
    margin: 1.5rem 0 !important;
}

.stTabs [data-baseweb="tab-list"] {
    gap: 0.5rem;
    border-bottom: 1px solid #E2E8F0;
}
.stTabs [data-baseweb="tab"] {
    font-weight: 600 !important;
    color: #64748B !important;
    padding: 0.65rem 1rem !important;
}
.stTabs [aria-selected="true"] {
    color: #0F766E !important;
    border-bottom-color: #0F766E !important;
}

/* ============================================================
   10. CAPTIONS + small text
   ============================================================ */
.stCaption, [data-testid="stCaptionContainer"] {
    color: #64748B !important;
    font-size: 13.5px !important;
}

/* Code inline */
code:not(pre code) {
    background: #F1F5F9 !important;
    color: #0F766E !important;
    padding: 0.15rem 0.4rem !important;
    border-radius: 4px !important;
    font-size: 0.9em !important;
}
</style>
"""


def inject_global_styles() -> None:
    """Inietta il CSS globale. Da chiamare una sola volta in ``app.py``."""
    st.markdown(_GLOBAL_CSS, unsafe_allow_html=True)


__all__ = ["inject_global_styles"]
