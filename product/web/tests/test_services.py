"""
Smoke tests sui servizi della webapp.

Non testiamo l'UI Streamlit (troppo costoso e fragile): ci concentriamo sul
service layer, che è la parte critica di integrazione col CLI.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from custodia_web.services import projects as projects_svc
from custodia_web.services import scan as scan_svc
from custodia_web.services import vault as vault_svc
from custodia_web.services import write as write_svc


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def isolated_projects_file(tmp_path, monkeypatch):
    """Sposta ``~/.custodia/projects.json`` in tmp_path per isolare i test."""
    fake_config = tmp_path / "custodia_cfg"
    fake_file = fake_config / "projects.json"
    monkeypatch.setattr(projects_svc, "CONFIG_DIR", fake_config)
    monkeypatch.setattr(projects_svc, "PROJECTS_FILE", fake_file)
    return fake_file


@pytest.fixture
def sample_vault(tmp_path):
    """Crea un vault vuoto con la struttura canonica."""
    vault = tmp_path / "vault"
    for sub in ("clienti", "fornitori", "commesse", "inbox"):
        (vault / sub).mkdir(parents=True)
    return vault


# ---------------------------------------------------------------------------
# projects
# ---------------------------------------------------------------------------


def test_projects_empty_state(isolated_projects_file):
    assert projects_svc.list_projects() == []
    assert projects_svc.get_active_project() is None


def test_projects_create_and_activate(isolated_projects_file, tmp_path):
    p = projects_svc.create_project("Rossetto Lam", tmp_path / "rossetto-vault")
    assert p.id == "rossetto-lam"
    assert projects_svc.get_active_project().id == "rossetto-lam"

    p2 = projects_svc.create_project("Bianchi Impianti", tmp_path / "bianchi-vault")
    # Active si sposta sul nuovo
    assert projects_svc.get_active_project().id == p2.id
    # Tornare al primo
    projects_svc.set_active_project(p.id)
    assert projects_svc.get_active_project().id == p.id

    # File JSON well-formed
    data = json.loads(isolated_projects_file.read_text())
    assert data["version"] == 1
    assert {p["id"] for p in data["projects"]} == {p.id, p2.id}


def test_projects_id_collision(isolated_projects_file, tmp_path):
    a = projects_svc.create_project("Stesso Nome", tmp_path / "a")
    b = projects_svc.create_project("Stesso Nome", tmp_path / "b")
    assert a.id != b.id
    assert b.id.startswith("stesso-nome")


def test_projects_delete(isolated_projects_file, tmp_path):
    a = projects_svc.create_project("Cliente A", tmp_path / "a")
    projects_svc.delete_project(a.id)
    assert projects_svc.list_projects() == []
    assert projects_svc.get_active_project() is None


# ---------------------------------------------------------------------------
# scan + vault stats + write end-to-end
# ---------------------------------------------------------------------------


def test_scan_filesystem_creates_state_and_persists(sample_vault, tmp_path):
    # Sorgente con un paio di file di testo: il connettore filesystem
    # accetta plaintext senza problemi.
    source = tmp_path / "src"
    source.mkdir()
    (source / "nota1.txt").write_text("Cliente Rossetto: ordine 200 lamiere.")
    (source / "nota2.txt").write_text("Fornitore Acme: consegna prevista 2026-06-01.")

    result = scan_svc.scan_filesystem(
        vault=sample_vault,
        root=source,
        allow_dangerous_root=True,  # tmp_path non è una dangerous root ma stiamo sicuri
    )
    assert result.error is None, result.error
    assert result.new_docs == 2

    stats = vault_svc.vault_stats(sample_vault)
    assert stats.state_db_exists is True
    assert stats.docs_total == 2
    # Nessuna entity ancora
    assert stats.entities_by_status == {}
    # md files all zero (vault è vuoto)
    assert all(v == 0 for v in stats.md_by_subdir.values())

    # Re-scan: stessi file → tutti duplicati
    result2 = scan_svc.scan_filesystem(vault=sample_vault, root=source)
    assert result2.new_docs == 0
    assert result2.duplicates == 2


def test_scan_filesystem_invalid_root(sample_vault):
    result = scan_svc.scan_filesystem(
        vault=sample_vault, root=Path("/nope/does/not/exist")
    )
    assert result.error is not None
    assert "inesistente" in result.error.lower() or "non" in result.error.lower()


def test_write_pending_noop_when_empty(sample_vault):
    """Senza entity approvate, write deve ritornare un summary con pending=0."""
    # Inizializza state store
    scan_svc.ensure_state_initialized(sample_vault)
    summary = write_svc.write_pending(vault=sample_vault)
    assert summary.error is None
    assert summary.pending_count == 0
    assert summary.written == []


def test_vault_search_finds_text(sample_vault):
    """Verifica la search full-text sul vault."""
    md = sample_vault / "clienti" / "test-cliente.md"
    md.write_text(
        "---\ntipo: cliente\nnome: Test Cliente SRL\n---\n\n"
        "# Test Cliente SRL\n\nNote: importante per il fatturato 2025."
    )
    results = vault_svc.search_vault(sample_vault, "fatturato")
    assert len(results) == 1
    assert results[0][0] == md
    assert "fatturato" in results[0][1].lower()


def test_parse_md_handles_no_frontmatter(sample_vault):
    md = sample_vault / "inbox" / "nota.md"
    md.write_text("# Solo body\n\nnessun frontmatter qui.")
    fm, body = vault_svc.parse_md(md)
    assert fm == {}
    assert "Solo body" in body
