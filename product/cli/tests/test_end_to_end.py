"""Integration test E2E: pipeline completa offline su finto-drive.

Esegue, via CliRunner, l'intero loop:

    init → scan fs → build clients → build communications →
    build fornitori → review --yes → write

usando il `FakeLLMProvider` con la fixture
`tests/fixtures/llm/extractor_responses.yaml`.

Verifica:
- Il vault prodotto contiene i file `.md` attesi (clienti, fornitori, inbox).
- I frontmatter sono ben formati e contengono i campi chiave (P.IVA, nome).
- Il vault è consumabile dal `parse_frontmatter` / `Vault` dell'MCP server
  (riusa la stessa tecnica di `test_write_command::_load_mcp_vault_class`).

Questo è la regression test definitiva di Sprint 1: se passa, l'intera
pipeline funziona offline senza dipendenze da API esterne.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from typer.testing import CliRunner

from custodia_cli.main import app

runner = CliRunner()

FIXTURE_DRIVE = Path(__file__).parent / "fixtures" / "finto-drive"
FIXTURE_LLM = Path(__file__).parent / "fixtures" / "llm" / "extractor_responses.yaml"


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Replica della `parse_frontmatter` dell'MCP server.

    Tenuta locale per non importare il package `custodia_mcp` (dipendenze
    distinte dal venv del CLI).
    """
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    fm = yaml.safe_load(parts[1]) or {}
    body = parts[2].lstrip("\n")
    return fm, body


def _load_mcp_vault_class():
    """Carica la classe `Vault` dal sorgente di `custodia_mcp.py`.

    Riusa la stessa strategia di `test_write_command::_load_mcp_vault_class`:
    legge il file, isola le definizioni `parse_frontmatter`+`Vault` ed esegue
    in un namespace minimale per evitare l'import di `fastmcp`.
    """
    mcp_path = (
        Path(__file__).resolve().parents[2] / "mcp-server" / "custodia_mcp.py"
    )
    src = mcp_path.read_text(encoding="utf-8")
    pf_start = src.index("def parse_frontmatter")
    vault_end = src.index("\ndef build_server")
    snippet = src[pf_start:vault_end]
    ns: dict = {"__name__": "_mcp_vault_subset"}
    exec(
        "from __future__ import annotations\n"
        "import re\n"
        "from pathlib import Path\n"
        "from typing import Any\n"
        "import yaml\n"
        + snippet,
        ns,
    )
    return ns["Vault"]


def test_end_to_end_offline_pipeline_on_finto_drive(tmp_path: Path) -> None:
    """Esegue init→scan→build×3→review→write su finto-drive con FakeLLM."""
    vault = tmp_path / "vault"

    # 1) init.
    result = runner.invoke(app, ["init", "--vault", str(vault)])
    assert result.exit_code == 0, result.output

    # 2) scan fs sul finto-drive (5 documenti).
    result = runner.invoke(
        app,
        ["scan", "fs", "--vault", str(vault), "--root", str(FIXTURE_DRIVE)],
    )
    assert result.exit_code == 0, result.output
    assert "Scan completato" in result.output

    # 3) build per i tre entity_type rilevanti (commesse non ha entità nel corpus).
    common = [
        "--vault", str(vault),
        "--llm-provider", "fake",
        "--fixture", str(FIXTURE_LLM),
    ]
    for sub in ("clients", "fornitori", "communications"):
        result = runner.invoke(app, ["build", sub, *common])
        assert result.exit_code == 0, f"build {sub} failed:\n{result.output}"

    # 4) review --yes: accetta tutti i candidati pending.
    result = runner.invoke(app, ["review", "--vault", str(vault), "--yes"])
    assert result.exit_code == 0, result.output
    assert "accept" in result.output

    # 5) write: materializza i .md nel vault.
    result = runner.invoke(app, ["write", "--vault", str(vault)])
    assert result.exit_code == 0, result.output

    # -- ASSERZIONI SUL VAULT PRODOTTO --

    # Path attesi (slug derivati dai nomi dei docs).
    expected_paths = [
        vault / "clienti" / "rossetto-laminazioni.md",
        vault / "clienti" / "bianchi-impianti.md",
        vault / "fornitori" / "torrelli-meccanica.md",
        vault / "inbox" / "conferma-ordine-pompe-idrauliche.md",
    ]
    for p in expected_paths:
        assert p.is_file(), f"file atteso mancante: {p}"

    # Frontmatter Rossetto: nome + piva (campo chiave per il consulente).
    fm, _ = _parse_frontmatter(
        (vault / "clienti" / "rossetto-laminazioni.md").read_text(encoding="utf-8")
    )
    assert fm["tipo"] == "cliente"
    assert fm["nome"] == "Rossetto Laminazioni SRL"
    assert str(fm["piva"]) == "03421560289"
    assert fm["sede"] == "Vicenza"

    # Frontmatter Bianchi.
    fm, _ = _parse_frontmatter(
        (vault / "clienti" / "bianchi-impianti.md").read_text(encoding="utf-8")
    )
    assert fm["nome"] == "Bianchi Impianti SpA"
    assert fm["settore"] == "impiantistica"

    # Frontmatter Torrelli (fornitore).
    fm, _ = _parse_frontmatter(
        (vault / "fornitori" / "torrelli-meccanica.md").read_text(encoding="utf-8")
    )
    assert fm["tipo"] == "fornitore"
    assert fm["nome"] == "Torrelli Meccanica S.r.l."
    assert fm["email_referente"] == "g.torrelli@torrelli-meccanica.it"

    # Frontmatter comunicazione (email Torrelli).
    fm, _ = _parse_frontmatter(
        (vault / "inbox" / "conferma-ordine-pompe-idrauliche.md").read_text(
            encoding="utf-8"
        )
    )
    assert fm["oggetto"] == "Conferma ordine pompe idrauliche"
    assert fm["da"] == "g.torrelli@torrelli-meccanica.it"


def test_end_to_end_vault_consumable_by_mcp_server(tmp_path: Path) -> None:
    """Il vault prodotto E2E deve essere leggibile dall'MCP server.

    Esegue la pipeline completa, poi istanzia la classe `Vault` dell'MCP
    server sullo stesso path e verifica che `list_clients()` e `get_client()`
    ritornino dati coerenti.
    """
    vault = tmp_path / "vault"

    # Pipeline (compressed: già coperta dal test sopra, qui solo per setup).
    runner.invoke(app, ["init", "--vault", str(vault)])
    runner.invoke(
        app,
        ["scan", "fs", "--vault", str(vault), "--root", str(FIXTURE_DRIVE)],
    )
    common = [
        "--vault", str(vault),
        "--llm-provider", "fake",
        "--fixture", str(FIXTURE_LLM),
    ]
    runner.invoke(app, ["build", "clients", *common])
    runner.invoke(app, ["build", "communications", *common])
    runner.invoke(app, ["review", "--vault", str(vault), "--yes"])
    runner.invoke(app, ["write", "--vault", str(vault)])

    # Consumo lato MCP server.
    Vault = _load_mcp_vault_class()
    mcp_vault = Vault(vault)
    clients = mcp_vault.list_clients()
    ids = sorted(c["id"] for c in clients)
    assert ids == ["bianchi-impianti", "rossetto-laminazioni"]

    detail = mcp_vault.get_client("rossetto-laminazioni")
    assert "error" not in detail
    assert detail["frontmatter"]["nome"] == "Rossetto Laminazioni SRL"

    # Anche la comunicazione è consumabile via recent_communications.
    recent = mcp_vault.recent_communications(5)
    oggetti = [r.get("oggetto") for r in recent]
    assert "Conferma ordine pompe idrauliche" in oggetti
