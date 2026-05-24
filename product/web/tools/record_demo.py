"""
Walkthrough recorder per la webapp Custodia.

Esegue uno scenario end-to-end via Playwright headless e salva uno screenshot
per ogni step in `docs/onboarding-screenshots/frames/NNN.png`.
Lo script assume che Streamlit sia gia` in ascolto su http://localhost:8501.

Run::

    python product/web/tools/record_demo.py
"""

from __future__ import annotations

import shutil
import sys
import time
from pathlib import Path

from playwright.sync_api import Page, TimeoutError as PWTimeout, sync_playwright

REPO_ROOT = Path(__file__).resolve().parents[3]
FRAMES_DIR = REPO_ROOT / "docs" / "onboarding-screenshots" / "frames"
APP_URL = "http://localhost:8501"

FINTO_DRIVE = (
    REPO_ROOT
    / "product"
    / "cli"
    / "tests"
    / "fixtures"
    / "finto-drive"
)
FIXTURE_LLM = (
    REPO_ROOT
    / "product"
    / "cli"
    / "tests"
    / "fixtures"
    / "llm"
    / "extractor_responses.yaml"
)

DEMO_VAULT = Path("/tmp/onboarding-demo/vault")
PROJECTS_FILE = Path.home() / ".custodia" / "projects.json"

VIEWPORT = {"width": 1280, "height": 800}
SETTLE_BEFORE_SHOT = 2.5  # secondi


def reset_state() -> None:
    """Rimuove progetti registrati e vault demo per partire fresh."""
    if PROJECTS_FILE.exists():
        PROJECTS_FILE.unlink()
    shutil.rmtree(DEMO_VAULT.parent, ignore_errors=True)
    if FRAMES_DIR.exists():
        shutil.rmtree(FRAMES_DIR)
    FRAMES_DIR.mkdir(parents=True, exist_ok=True)


class Recorder:
    def __init__(self, page: Page) -> None:
        self.page = page
        self.idx = 0

    def shot(self, label: str) -> None:
        self.idx += 1
        # lascia il tempo a Streamlit di renderizzare
        try:
            self.page.wait_for_load_state("networkidle", timeout=8000)
        except PWTimeout:
            pass
        time.sleep(SETTLE_BEFORE_SHOT)
        name = f"{self.idx:03d}"
        png = FRAMES_DIR / f"{name}.png"
        txt = FRAMES_DIR / f"{name}.txt"
        self.page.screenshot(path=str(png), full_page=False)
        txt.write_text(label, encoding="utf-8")
        print(f"  [{name}] {label}")


def click_button_by_text(page: Page, text: str, exact: bool = False) -> None:
    """Click sul primo bottone visibile che contiene il testo."""
    loc = page.get_by_role("button", name=text, exact=exact).first
    loc.scroll_into_view_if_needed()
    loc.click()


def fill_input_by_label(page: Page, label: str, value: str) -> None:
    loc = page.locator(f'input[aria-label="{label}"]').first
    loc.scroll_into_view_if_needed()
    loc.fill(value)


def run() -> None:
    reset_state()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport=VIEWPORT, device_scale_factor=2)
        page = ctx.new_page()
        page.set_default_timeout(15000)
        rec = Recorder(page)

        print(f"Navigating to {APP_URL}")
        page.goto(APP_URL, wait_until="networkidle")
        # Streamlit ha bisogno di tempo extra al primo load
        time.sleep(3)

        # ----- 1. stato iniziale -----
        rec.shot("Step 1 — Stato iniziale (form vuoto)")

        # ----- 2. compila form nuovo progetto -----
        fill_input_by_label(page, "Nome cliente", "Demo Onboarding")
        fill_input_by_label(page, "Path vault", str(DEMO_VAULT))
        rec.shot("Step 2 — Form nuovo progetto compilato")

        # ----- 3. crea progetto -----
        click_button_by_text(page, "Crea")
        rec.shot("Step 3 — Dashboard con progetto attivo")

        # ----- 4. Scan tab -----
        click_button_by_text(page, "Scan")
        rec.shot("Step 4 — Pagina Scan (tab Filesystem)")

        # ----- 5. Root path -----
        fill_input_by_label(page, "Root path", str(FINTO_DRIVE))
        rec.shot("Step 5 — Root path compilato")

        # ----- 6. esegui scan -----
        click_button_by_text(page, "🔍 Scan")
        rec.shot("Step 6 — Scan completato")

        # ----- 7. Build -----
        click_button_by_text(page, "Build")
        # imposta fixture path
        try:
            fixture_input = page.locator(
                'input[aria-label*="Fixture"], input[aria-label*="fixture"]'
            ).first
            fixture_input.scroll_into_view_if_needed()
            fixture_input.fill(str(FIXTURE_LLM))
        except Exception as exc:  # noqa: BLE001
            print(f"  ! fixture input non trovato: {exc}")
        rec.shot("Step 7 — Pagina Build")

        # ----- 8. Estrai -----
        click_button_by_text(page, "🚀 Estrai")
        rec.shot("Step 8 — Estrazione completata")

        # ----- 9. Review -----
        click_button_by_text(page, "Review")
        rec.shot("Step 9 — Pagina Review (pending)")

        # ----- 10. Accept all visible -----
        try:
            click_button_by_text(page, "✓ Accept all visible")
        except Exception as exc:  # noqa: BLE001
            print(f"  ! Accept all non disponibile: {exc}")
        rec.shot("Step 10 — Tutti accettati")

        # ----- 11. Vault -----
        click_button_by_text(page, "Vault")
        rec.shot("Step 11 — Pagina Vault (metriche)")

        # ----- 12. Write pending -----
        try:
            click_button_by_text(page, "📝 Write pending")
        except Exception as exc:  # noqa: BLE001
            print(f"  ! Write pending non disponibile: {exc}")
        rec.shot("Step 12 — File scritti")

        # ----- 13. Settings -----
        click_button_by_text(page, "Settings")
        rec.shot("Step 13 — Pagina Settings (env vars)")

        # ----- 14. Scroll a MCP -----
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        rec.shot("Step 14 — Blocco MCP config JSON")

        browser.close()

    print(f"\nDone. {rec.idx} frames in {FRAMES_DIR}")


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:  # noqa: BLE001
        print(f"FATAL: {exc}", file=sys.stderr)
        raise
