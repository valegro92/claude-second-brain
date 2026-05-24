"""Test della dashboard di sintesi (cantiere DASHBOARD, Step 3).

Coperture:
  * ``generate_dashboard`` produce HTML valido + INDEX.md non vuoto.
  * Le metriche aggregate sono corrette dato l'input.
  * Il subcomando ``wiki dashboard --client SLUG`` del CLI esegue
    senza errori e crea gli output attesi.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from html.parser import HTMLParser
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from scanners._base import FileRecord
from wiki import cli as cli_module
from wiki.cli import main
from wiki.dashboard import collect_metrics, generate_dashboard

# ----------------------------------------------------------------- utils


class _HtmlSanityChecker(HTMLParser):
    """Mini parser stdlib: conta tag aperti/chiusi e raccoglie testo."""

    def __init__(self) -> None:
        super().__init__()
        self.opened: list[str] = []
        self.has_h1 = False
        self.text_chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        # Tag void HTML5: non vanno chiusi.
        void = {
            "area",
            "base",
            "br",
            "col",
            "embed",
            "hr",
            "img",
            "input",
            "link",
            "meta",
            "param",
            "source",
            "track",
            "wbr",
        }
        if tag not in void:
            self.opened.append(tag)
        if tag == "h1":
            self.has_h1 = True

    def handle_endtag(self, tag: str) -> None:
        if self.opened and self.opened[-1] == tag:
            self.opened.pop()

    def handle_data(self, data: str) -> None:
        self.text_chunks.append(data)

    @property
    def text(self) -> str:
        return "".join(self.text_chunks)


def _assert_html_well_formed(html: str) -> _HtmlSanityChecker:
    """Verifica che l'HTML sia parsabile e bilanciato dal parser stdlib."""
    assert html.lstrip().lower().startswith("<!doctype html>")
    p = _HtmlSanityChecker()
    p.feed(html)
    # Tag rimasti aperti = sbilanciamento. Tolleriamo solo l'html iniziale.
    assert p.opened == [] or p.opened == ["html"], f"tag sbilanciati: {p.opened}"
    assert p.has_h1, "manca <h1> nella dashboard"
    return p


# ----------------------------------------------------------- fixture


@pytest.fixture
def state_dir(tmp_path: Path) -> Path:
    """Costruisce uno ``_status/<slug>/`` finto e completo per i test."""
    state = tmp_path / "_status" / "acme"
    state.mkdir(parents=True)
    inv = state / "inventory"
    inv.mkdir()
    extracted = state / "extracted"
    extracted.mkdir()
    audit = state / "audit"
    audit.mkdir()

    now = datetime.now(UTC)
    # 3 record nas: 1 vivo, 1 archivio, 1 da-chiarire.
    r1 = FileRecord(
        source="nas",
        source_id="/n/a.pdf",
        path="commerciale/a.pdf",
        name="a.pdf",
        size=1000,
        mtime=now,
        sha256="a" * 64,
        categoria="vivo",
        confidence=0.9,
        reason="rules: path",
    )
    r2 = FileRecord(
        source="nas",
        source_id="/n/b.pdf",
        path="vecchio/b.pdf",
        name="b.pdf",
        size=1000,
        mtime=now - timedelta(days=2000),
        sha256="b" * 64,
        categoria="archivio",
        confidence=0.7,
        reason="rules: age",
    )
    r3 = FileRecord(
        source="nas",
        source_id="/n/c.pdf",
        path="boh/c.pdf",
        name="c.pdf",
        size=1000,
        mtime=now,
        sha256="c" * 64,
        categoria="da-chiarire",
        confidence=0.3,
        reason="rules: unclear",
    )
    (inv / "nas.jsonl").write_text(
        "\n".join(r.to_jsonl() for r in (r1, r2, r3)) + "\n", encoding="utf-8"
    )
    # 2 record gdrive non categorizzati.
    r4 = FileRecord(
        source="gdrive",
        source_id="g1",
        path="Drive/x.docx",
        name="x.docx",
        size=2000,
        mtime=now,
        sha256="d" * 64,
    )
    r5 = FileRecord(
        source="gdrive",
        source_id="g2",
        path="Drive/y.docx",
        name="y.docx",
        size=2000,
        mtime=now,
        sha256="e" * 64,
    )
    (inv / "gdrive.jsonl").write_text(
        "\n".join(r.to_jsonl() for r in (r4, r5)) + "\n", encoding="utf-8"
    )

    # Estratti: r1 e r2 (2 cartelle sha12).
    (extracted / ("a" * 12)).mkdir()
    (extracted / ("a" * 12) / "main.md").write_text("contenuto a", encoding="utf-8")
    (extracted / ("b" * 12)).mkdir()
    (extracted / ("b" * 12) / "main.md").write_text("contenuto b", encoding="utf-8")

    # Cost.jsonl: 3 chiamate, 2 modelli, 2 stage.
    cost = state / "cost.jsonl"
    cost.write_text(
        "\n".join(
            json.dumps(e)
            for e in [
                {
                    "ts": "2026-01-01T00:00",
                    "stage": "categorize",
                    "model": "claude-haiku-4-5",
                    "tokens_in": 1000,
                    "tokens_out": 200,
                    "cost_eur": 0.01,
                },
                {
                    "ts": "2026-01-02T00:00",
                    "stage": "categorize",
                    "model": "claude-haiku-4-5",
                    "tokens_in": 1500,
                    "tokens_out": 300,
                    "cost_eur": 0.015,
                },
                {
                    "ts": "2026-01-03T00:00",
                    "stage": "scheda-narrativa",
                    "model": "claude-sonnet-4-5",
                    "tokens_in": 3000,
                    "tokens_out": 800,
                    "cost_eur": 0.04,
                },
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    # Decisions.jsonl (presente ma non strettamente necessario al calcolo metriche).
    (audit / "decisions.jsonl").write_text(
        json.dumps(
            {
                "ts": "2026-01-04T00:00",
                "batch": "b1",
                "draft": "d.md",
                "action": "approved",
                "user": "valentino",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    # Drafts: 2 batch, totale 3 bozze (1 approved, 1 pending, 1 rejected).
    drafts = state / "drafts"
    drafts.mkdir()
    b1 = drafts / "2026-05-01"
    b1.mkdir()
    (b1 / "draft-1.md").write_text("# 1", encoding="utf-8")
    (b1 / "draft-2.md").write_text("# 2", encoding="utf-8")
    (b1 / "_state.json").write_text(
        json.dumps(
            {
                "draft-1.md": {"stato": "approved"},
                "draft-2.md": {"stato": "pending"},
            }
        ),
        encoding="utf-8",
    )
    b2 = drafts / "2026-05-08"
    b2.mkdir()
    (b2 / "draft-3.md").write_text("# 3", encoding="utf-8")
    (b2 / "_state.json").write_text(
        json.dumps({"draft-3.md": {"stato": "rejected"}}),
        encoding="utf-8",
    )
    return state


@pytest.fixture
def vault_dir(tmp_path: Path) -> Path:
    """Vault finto: 1 cliente conforme, 1 cliente non conforme, 1 dormiente."""
    vault = tmp_path / "vault"
    vault.mkdir()

    # references/persone.md interno con due iniziali registrate.
    (vault / "references").mkdir()
    (vault / "references" / "persone.md").write_text(
        "---\ntipo: persone-aziendali\n---\n# Persone\n- VG Valentino Grossi\n- MR Mario Rossi\n",
        encoding="utf-8",
    )

    clienti = vault / "clienti"
    clienti.mkdir()
    # Cliente conforme.
    ok = clienti / "rossi-srl"
    ok.mkdir()
    for fname in ("CLAUDE.md", "MEMORY.md", "tasks.md", "persone.md", "rossi-srl.md"):
        (ok / fname).write_text("---\ntipo: scheda-cliente\n---\n# ok\n", encoding="utf-8")
    # Cliente non conforme: mancano MEMORY.md e tasks.md.
    miss = clienti / "bianchi-srl"
    miss.mkdir()
    (miss / "CLAUDE.md").write_text("---\ntipo: scheda-cliente\n---\n", encoding="utf-8")
    (miss / "persone.md").write_text("---\ntipo: persone-oggetto\n---\n", encoding="utf-8")
    (miss / "bianchi-srl.md").write_text("---\ntipo: scheda-cliente\n---\n", encoding="utf-8")

    # File orfano: .md senza frontmatter in references/.
    (vault / "references" / "orfano.md").write_text("# nessun frontmatter qui\n", encoding="utf-8")

    return vault


# ------------------------------------------------------- test collect


def test_collect_metrics_counts(state_dir: Path, vault_dir: Path) -> None:
    data = collect_metrics(state_dir, vault_dir, "acme")
    # Sorgenti: 2 (gdrive + nas), ordinate.
    assert [s.name for s in data.sources] == ["gdrive", "nas"]
    nas = next(s for s in data.sources if s.name == "nas")
    assert nas.discovered == 3
    assert nas.filtered_in_perimetro == 3
    assert nas.extracted == 2  # solo r1 e r2 hanno cartella extracted/<sha12>/
    assert nas.categorized == 3
    gdrive = next(s for s in data.sources if s.name == "gdrive")
    assert gdrive.discovered == 2
    assert gdrive.extracted == 0
    assert gdrive.categorized == 0

    # Categorie.
    assert data.categorie.counts["vivo"] == 1
    assert data.categorie.counts["archivio"] == 1
    assert data.categorie.counts["da-chiarire"] == 1
    assert data.categorie.total == 3
    # 100/3 = 33.3% ciascuno.
    assert abs(data.categorie.percent("vivo") - 33.3) < 0.1

    # Bozze: 1 approved, 1 pending, 1 rejected.
    assert data.bozze.counts["approved"] == 1
    assert data.bozze.counts["pending"] == 1
    assert data.bozze.counts["rejected"] == 1
    assert data.bozze.total == 3
    assert sorted(data.bozze.batches) == ["2026-05-01", "2026-05-08"]

    # Costo: 0.01 + 0.015 + 0.04 = 0.065.
    assert abs(data.costi.totale_eur - 0.065) < 1e-9
    assert data.costi.n_chiamate == 3
    assert "claude-haiku-4-5" in data.costi.per_modello
    assert "claude-sonnet-4-5" in data.costi.per_modello
    assert abs(data.costi.per_modello["claude-haiku-4-5"] - 0.025) < 1e-9
    assert abs(data.costi.per_modello["claude-sonnet-4-5"] - 0.04) < 1e-9
    assert set(data.costi.per_stage.keys()) == {"categorize", "scheda-narrativa"}

    # Salute vault.
    # - 1 file orfano in references/orfano.md
    assert any("orfano.md" in f for f in data.salute.file_orfani)
    # - bianchi-srl non conforme (mancano MEMORY.md e tasks.md)
    non_conformi = {item["oggetto"] for item in data.salute.regola_01_pmi_mancanti}
    assert "bianchi-srl" in non_conformi
    assert "rossi-srl" not in non_conformi
    bianchi = next(i for i in data.salute.regola_01_pmi_mancanti if i["oggetto"] == "bianchi-srl")
    assert set(bianchi["mancanti"]) == {"MEMORY.md", "tasks.md"}


def test_collect_metrics_handles_missing_dirs(tmp_path: Path) -> None:
    """``collect_metrics`` deve tollerare state_dir vuota / vault assente."""
    empty_state = tmp_path / "_status" / "vuoto"
    empty_state.mkdir(parents=True)
    data = collect_metrics(empty_state, None, "vuoto")
    assert data.sources == []
    assert data.categorie.total == 0
    assert data.bozze.total == 0
    assert data.costi.totale_eur == 0.0
    assert data.salute.regola_01_pmi_mancanti == []
    # Next actions sempre non vuoto.
    assert data.next_actions


# ------------------------------------------------------- test render


def test_generate_dashboard_writes_files(state_dir: Path, vault_dir: Path, tmp_path: Path) -> None:
    out_html = state_dir / "dashboard.html"
    paths = generate_dashboard(state_dir, vault_dir, out_html, cliente="acme")
    assert paths["html"].exists()
    assert paths["md"].exists()
    assert paths["md"].name == "INDEX.md"

    html = paths["html"].read_text(encoding="utf-8")
    checker = _assert_html_well_formed(html)
    # Verifica che alcune metriche chiave compaiano nel testo.
    assert "acme" in checker.text
    assert "Sorgenti" in checker.text
    assert "Categorizzazione" in checker.text
    assert "Bozze" in checker.text
    assert "Salute vault" in checker.text
    # SVG inline (no CDN, no JS) per il bar chart.
    assert "<svg" in html
    # Nessun CDN / nessun JS esterno.
    assert "http://" not in html.replace("http://www.w3.org/2000/svg", "")
    assert "<script" not in html.lower()
    # Categoria con count > 0 deve apparire come numero nel template.
    assert ">1<" in html or ">3<" in html

    md = paths["md"].read_text(encoding="utf-8")
    assert md.startswith("# Dashboard")
    assert "acme" in md
    assert "## Sorgenti" in md
    assert "## Categorizzazione" in md
    assert "## Bozze" in md
    assert "## Salute vault" in md
    assert "## Costi" in md
    assert "## Prossime azioni" in md
    # Almeno uno dei valori di costo conosciuti compare.
    assert "0.065" in md or "0.06" in md or "0.07" in md


def test_generate_dashboard_minimal_state(tmp_path: Path) -> None:
    """Dashboard generabile anche con state_dir essenzialmente vuota."""
    state = tmp_path / "_status" / "x"
    state.mkdir(parents=True)
    out_html = state / "dashboard.html"
    paths = generate_dashboard(state, None, out_html, cliente="x")
    html = paths["html"].read_text(encoding="utf-8")
    _assert_html_well_formed(html)
    md = paths["md"].read_text(encoding="utf-8")
    assert md.strip()
    # Suggerisce di lanciare scan.
    assert "wiki scan" in md or "azione urgente" in md


# ------------------------------------------------------- test CLI


@pytest.fixture
def isolated_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Replica della fixture di test_cli.py per il subcomando dashboard."""
    clients_dir = tmp_path / "bootstrap" / "clients"
    clients_dir.mkdir(parents=True)
    state_dir = tmp_path / "_status"
    state_dir.mkdir()
    inbox_dir = tmp_path / "_inbox"
    inbox_dir.mkdir()
    vault_dir = tmp_path / "vault"
    vault_dir.mkdir()
    # Template reale per coerenza con altre fixture.
    real_template = Path(__file__).resolve().parents[1] / "bootstrap" / "config.template.yml"
    template_path = tmp_path / "bootstrap" / "config.template.yml"
    template_path.write_text(real_template.read_text(encoding="utf-8"), encoding="utf-8")

    monkeypatch.setattr(cli_module, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(cli_module, "CLIENTS_DIR", clients_dir)
    monkeypatch.setattr(cli_module, "DEFAULT_STATE_DIR", state_dir)
    monkeypatch.setattr(cli_module, "DEFAULT_INBOX_DIR", inbox_dir)
    monkeypatch.setattr(cli_module, "TEMPLATE_PATH", template_path)
    return tmp_path


def _make_client(repo: Path, slug: str = "test") -> Path:
    cdir = repo / "bootstrap" / "clients" / slug
    cdir.mkdir(parents=True, exist_ok=True)
    config = {
        "cliente": {"slug": slug, "nome": "Test Srl", "custode": "TT", "owner": "VG"},
        "sorgenti": {k: {"enabled": False} for k in ("gdrive", "m365", "email", "nas", "server")},
        "filtri_globali": {"max_file_mb": 50, "exclude_extensions": []},
        "privacy": {"modalita": "safe"},
        "batch": {"size": 50, "cost_alert_eur": 50, "cost_hard_stop_eur": 200},
    }
    (cdir / "config.yml").write_text(yaml.dump(config), encoding="utf-8")
    (repo / "_status" / slug).mkdir(parents=True, exist_ok=True)
    return cdir


def test_cli_dashboard_smoke(isolated_repo: Path) -> None:
    """`wiki dashboard --client test` deve generare html + md senza errori."""
    _make_client(isolated_repo, "test")
    runner = CliRunner()
    result = runner.invoke(main, ["dashboard", "--client", "test"])
    assert result.exit_code == 0, result.output
    html_path = isolated_repo / "_status" / "test" / "dashboard.html"
    md_path = isolated_repo / "_status" / "test" / "INDEX.md"
    assert html_path.exists(), result.output
    assert md_path.exists(), result.output
    assert "Dashboard generata" in result.output

    html = html_path.read_text(encoding="utf-8")
    _assert_html_well_formed(html)
    assert "test" in html  # slug compare nel titolo


def test_cli_dashboard_help() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["dashboard", "--help"])
    assert result.exit_code == 0
    assert "--client" in result.output
    assert "--open" in result.output


def test_cli_reconcile_auto_dashboard(isolated_repo: Path) -> None:
    """Con ``dashboard.auto: true`` il reconcile rigenera la dashboard."""
    cdir = _make_client(isolated_repo, "test")
    # Aggiungo l'opt-in nella config.
    cfg = yaml.safe_load((cdir / "config.yml").read_text())
    cfg["dashboard"] = {"auto": True}
    (cdir / "config.yml").write_text(yaml.dump(cfg), encoding="utf-8")
    # Inventory minima.
    inv = isolated_repo / "_status" / "test" / "inventory"
    inv.mkdir(parents=True, exist_ok=True)
    r = FileRecord(
        source="nas",
        source_id="/n/x.pdf",
        path="x.pdf",
        name="x.pdf",
        size=10,
        mtime=datetime.now(UTC),
        sha256="f" * 64,
    )
    (inv / "nas.jsonl").write_text(r.to_jsonl() + "\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(main, ["reconcile", "--client", "test"])
    assert result.exit_code == 0, result.output
    assert (isolated_repo / "_status" / "test" / "dashboard.html").exists()
