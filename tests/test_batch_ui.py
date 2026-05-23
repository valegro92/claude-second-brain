"""Test del batch_ui: lista batch, cambio stato, flush al vault."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from batch_ui.server import create_app
from categorizers._enums import StatoBozza


# ----------------------------- fixtures ------------------------------------

DRAFT_SCHEDA = """\
---
tipo: scheda-cliente
slug: rossi-srl
confidence: 0.92
warnings:
  - Telefono mancante
generato-da: reconcilers/schede.py
---

# Rossi Srl

TODO: verificare partita IVA.

## Storia

Cliente attivo dal 2018.

## Generato

Sezione popolata automaticamente. Da rivedere.
"""

DRAFT_DEDUP = """\
---
tipo: scheda-fornitore
slug: bianchi-spa
confidence: 0.65
---

# Bianchi SpA

Note libere.
"""

DRAFT_PERSONA = """\
---
tipo: persona
slug: mario-rossi
confidence: 0.40
---

# Mario Rossi

TODO: assegnare ruolo aziendale.
"""


@pytest.fixture()
def fake_workspace(tmp_path: Path) -> dict[str, Path]:
    """Crea un workspace temporaneo con `_status/drafts/test-batch/` e 3 bozze."""
    status = tmp_path / "_status"
    vault = tmp_path / "vault"
    batch = status / "drafts" / "test-batch"
    batch.mkdir(parents=True)
    vault.mkdir()
    (batch / "scheda-rossi-srl.md").write_text(DRAFT_SCHEDA, encoding="utf-8")
    (batch / "dedup-bianchi.md").write_text(DRAFT_DEDUP, encoding="utf-8")
    (batch / "persona-rossi.md").write_text(DRAFT_PERSONA, encoding="utf-8")
    return {"root": tmp_path, "status": status, "vault": vault, "batch": batch}


@pytest.fixture()
def client(fake_workspace):
    app = create_app(
        status_dir=fake_workspace["status"],
        vault_root=fake_workspace["vault"],
        testing=True,
    )
    return app.test_client()


# ----------------------------- test ----------------------------------------

def test_healthz_ok(client):
    """Il watcher fa ping a /healthz: deve sempre rispondere 200."""
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.data == b"ok"


def test_index_lista_batch(client):
    """GET / ritorna 200 e elenca il batch creato dalla fixture."""
    resp = client.get("/")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "test-batch" in body
    # Le 3 bozze tutte pending
    assert "Pending" in body or "pending" in body
    # Il totale e' 3
    assert ">3<" in body


def test_batch_view_mostra_bozze(client):
    """GET /batch/test-batch elenca tutte le bozze e i conteggi."""
    resp = client.get("/batch/test-batch")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "scheda-rossi-srl.md" in body
    assert "dedup-bianchi.md" in body
    assert "persona-rossi.md" in body


def test_draft_view_diff_viewer(client):
    """GET sulla singola bozza ritorna il partial con highlighting."""
    resp = client.get("/batch/test-batch/draft/scheda-rossi-srl.md")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    # Highlighting classi CSS attese
    assert "todo-marker" in body
    assert "warning-marker" in body
    assert "generated" in body
    # Target derivato
    assert "vault/clienti/rossi-srl/rossi-srl.md" in body


def test_approve_cambia_stato(client, fake_workspace):
    """POST .../approve sposta lo stato della bozza in APPROVED."""
    resp = client.post("/batch/test-batch/draft/scheda-rossi-srl.md/approve")
    assert resp.status_code == 200
    # Il partial della riga riporta lo stato approved
    assert "approved" in resp.get_data(as_text=True)

    # Stato persistito su disco
    state_file = fake_workspace["batch"] / "_state.json"
    assert state_file.exists()
    state = json.loads(state_file.read_text(encoding="utf-8"))
    assert state["scheda-rossi-srl.md"]["stato"] == StatoBozza.APPROVED.value


def test_reject_cambia_stato(client, fake_workspace):
    resp = client.post("/batch/test-batch/draft/persona-rossi.md/reject")
    assert resp.status_code == 200
    state = json.loads((fake_workspace["batch"] / "_state.json").read_text(encoding="utf-8"))
    assert state["persona-rossi.md"]["stato"] == StatoBozza.REJECTED.value


def test_edit_richiede_contenuto(client):
    """POST edit senza form 'edits' restituisce 400."""
    resp = client.post("/batch/test-batch/draft/scheda-rossi-srl.md/edit", data={})
    assert resp.status_code == 400


def test_edit_salva_contenuto(client, fake_workspace):
    new_content = "---\ntipo: scheda-cliente\nslug: rossi-srl\n---\n\n# Rossi (editato)\n"
    resp = client.post(
        "/batch/test-batch/draft/scheda-rossi-srl.md/edit",
        data={"edits": new_content},
    )
    assert resp.status_code == 200
    state = json.loads((fake_workspace["batch"] / "_state.json").read_text(encoding="utf-8"))
    assert state["scheda-rossi-srl.md"]["stato"] == StatoBozza.EDITED.value
    assert state["scheda-rossi-srl.md"]["edits"] == new_content


def test_bulk_approve_soglia(client, fake_workspace):
    """Bulk-approve con soglia 0.85: solo la bozza con conf 0.92 e' approvata."""
    resp = client.post("/batch/test-batch/bulk-approve", data={"threshold": "0.85"})
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["approved"] == 1
    state = json.loads((fake_workspace["batch"] / "_state.json").read_text(encoding="utf-8"))
    assert state["scheda-rossi-srl.md"]["stato"] == StatoBozza.APPROVED.value
    # le altre restano pending (non in state)
    assert "dedup-bianchi.md" not in state or state["dedup-bianchi.md"]["stato"] == StatoBozza.PENDING.value


def test_flush_sposta_approved_e_logga(client, fake_workspace):
    """Flush: la bozza approvata finisce nel vault, la rejected in audit, decisions loggate."""
    # Setup stati
    client.post("/batch/test-batch/draft/scheda-rossi-srl.md/approve")
    client.post("/batch/test-batch/draft/persona-rossi.md/reject")

    resp = client.post("/batch/test-batch/flush")
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["n_applied"] == 1
    assert payload["n_rejected"] == 1

    # File nel vault
    vault = fake_workspace["vault"]
    target = vault / "clienti" / "rossi-srl" / "rossi-srl.md"
    assert target.exists(), f"target non creato: {target}"
    content = target.read_text(encoding="utf-8")
    assert "Rossi Srl" in content

    # Bozza approved rimossa dal batch
    assert not (fake_workspace["batch"] / "scheda-rossi-srl.md").exists()

    # Bozza rejected archiviata
    archived = fake_workspace["status"] / "audit" / "rejected" / "test-batch" / "persona-rossi.md"
    assert archived.exists()

    # Decisions log scritto
    decisions = fake_workspace["status"] / "audit" / "decisions.jsonl"
    assert decisions.exists()
    lines = decisions.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    parsed = [json.loads(line) for line in lines]
    actions = {p["action"] for p in parsed}
    assert StatoBozza.APPROVED.value in actions
    assert StatoBozza.REJECTED.value in actions
    # Tutti citano il batch giusto
    assert all(p["batch"] == "test-batch" for p in parsed)


def test_flush_conflict_skip(client, fake_workspace):
    """Flush con policy=skip: se il target esiste gia', la bozza non viene applicata."""
    # Pre-esistente
    target = fake_workspace["vault"] / "clienti" / "rossi-srl" / "rossi-srl.md"
    target.parent.mkdir(parents=True)
    target.write_text("# Esistente\n", encoding="utf-8")

    client.post("/batch/test-batch/draft/scheda-rossi-srl.md/approve")
    resp = client.post("/batch/test-batch/flush", data={"conflict_policy": "skip"})
    payload = resp.get_json()
    assert payload["n_skipped"] == 1
    assert payload["n_applied"] == 0
    # Contenuto pre-esistente intatto
    assert "Esistente" in target.read_text(encoding="utf-8")


def test_flush_conflict_overwrite(client, fake_workspace):
    """Flush con policy=overwrite: la bozza sovrascrive il file esistente."""
    target = fake_workspace["vault"] / "clienti" / "rossi-srl" / "rossi-srl.md"
    target.parent.mkdir(parents=True)
    target.write_text("# Esistente\n", encoding="utf-8")

    client.post("/batch/test-batch/draft/scheda-rossi-srl.md/approve")
    resp = client.post("/batch/test-batch/flush", data={"conflict_policy": "overwrite"})
    payload = resp.get_json()
    assert payload["n_applied"] == 1
    assert "Rossi Srl" in target.read_text(encoding="utf-8")


def test_batch_inesistente_404(client):
    assert client.get("/batch/non-esiste").status_code == 404


def test_azione_non_valida_400(client):
    resp = client.post("/batch/test-batch/draft/scheda-rossi-srl.md/zap")
    assert resp.status_code == 400


def test_path_traversal_bloccato(client):
    """Tentativo di salire fuori dal batch_dir deve dare 404."""
    resp = client.get("/batch/test-batch/draft/..%2Fnon-esiste.md")
    assert resp.status_code == 404
