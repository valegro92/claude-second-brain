"""
Test del sub-comando ``custodia scan outlook`` e ``custodia scan fic``,
focalizzati sulla redaction del path credentials in ``runs.args_json``.

FIX OA-6 / SEC-5: il path raw del credentials JSON NON deve essere persistito
nella tabella ``runs`` (potrebbe leakare info sensibili sul cliente).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from custodia_cli.commands.init import (
    run_init,
    state_db_path_for_vault,
)
from custodia_cli.main import app
from custodia_cli.state import StateStore

runner = CliRunner()


class _FakeOutlookConnector:
    """Minimal stub del OutlookConnector — non chiama Graph."""

    def __init__(self, **_kwargs: Any) -> None:
        self.stats = {
            "processed": 0,
            "skipped_since": 0,
            "skipped_max": 0,
            "errors": 0,
        }

    def iter_documents(self) -> list[Any]:
        return []


class _FakeFICConnector:
    """Minimal stub del FattureInCloudConnector — non chiama API FIC."""

    def __init__(self, **_kwargs: Any) -> None:
        self.stats = {
            "processed_clients": 0,
            "processed_suppliers": 0,
            "processed_invoices": 0,
            "skipped_max": 0,
            "errors": 0,
        }

    def iter_documents(self) -> list[Any]:
        return []


def test_scan_outlook_redacts_credentials_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FIX OA-6: ``credentials`` path NON deve apparire in ``runs.args_json``,
    sostituito da ``credentials_provided: bool``.
    """
    vault = tmp_path / "vault"
    vault.mkdir()
    run_init(vault)

    # Path credentials sensibile (simulato — contiene info clienti).
    creds_file = tmp_path / "secret-customer-name-credentials.json"
    creds_file.write_text('{"client_id": "fake"}', encoding="utf-8")

    # Patcha OutlookConnector per evitare chiamate Graph.
    import custodia_cli.connectors.outlook as outlook_mod

    monkeypatch.setattr(outlook_mod, "OutlookConnector", _FakeOutlookConnector)

    result = runner.invoke(
        app,
        [
            "scan",
            "outlook",
            "--vault",
            str(vault),
            "--credentials",
            str(creds_file),
        ],
    )
    assert result.exit_code == 0, result.output

    db_path = state_db_path_for_vault(vault)
    with StateStore(db_path) as store:
        row = store._conn.execute(  # type: ignore[attr-defined]
            "SELECT command, args_json FROM runs ORDER BY id DESC LIMIT 1"
        ).fetchone()
    assert row is not None
    assert row["command"] == "scan outlook"

    args = json.loads(row["args_json"])
    # NON deve esserci né la chiave "credentials" né il path raw.
    assert "credentials" not in args, f"credentials raw leakato: {args}"
    assert "secret-customer-name" not in row["args_json"], (
        f"path sensibile leakato in args_json: {row['args_json']}"
    )
    # Deve esserci il flag bool.
    assert args.get("credentials_provided") is True


def test_scan_outlook_credentials_provided_false_when_omitted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Senza ``--credentials``, args registra ``credentials_provided: False``."""
    vault = tmp_path / "vault"
    vault.mkdir()
    run_init(vault)

    import custodia_cli.connectors.outlook as outlook_mod

    monkeypatch.setattr(outlook_mod, "OutlookConnector", _FakeOutlookConnector)
    # Env var fallback default — non serve passare credentials, ma il connector
    # è stubbato quindi non importa.
    monkeypatch.setenv("CUSTODIA_MICROSOFT_CREDENTIALS_JSON", "/tmp/fake.json")

    result = runner.invoke(
        app,
        ["scan", "outlook", "--vault", str(vault)],
    )
    assert result.exit_code == 0, result.output

    db_path = state_db_path_for_vault(vault)
    with StateStore(db_path) as store:
        row = store._conn.execute(  # type: ignore[attr-defined]
            "SELECT args_json FROM runs ORDER BY id DESC LIMIT 1"
        ).fetchone()
    args = json.loads(row["args_json"])
    assert args.get("credentials_provided") is False


def test_scan_fic_redacts_credentials_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FIX OA-6: stesso check su ``scan fic``."""
    vault = tmp_path / "vault"
    vault.mkdir()
    run_init(vault)

    creds_file = tmp_path / "sensitive-fic-customer.json"
    creds_file.write_text('{"client_id": "fake"}', encoding="utf-8")

    import custodia_cli.connectors.fatture_in_cloud as fic_mod

    monkeypatch.setattr(fic_mod, "FattureInCloudConnector", _FakeFICConnector)

    result = runner.invoke(
        app,
        [
            "scan",
            "fic",
            "--vault",
            str(vault),
            "--company-id",
            "12345",
            "--credentials",
            str(creds_file),
        ],
    )
    assert result.exit_code == 0, result.output

    db_path = state_db_path_for_vault(vault)
    with StateStore(db_path) as store:
        row = store._conn.execute(  # type: ignore[attr-defined]
            "SELECT command, args_json FROM runs ORDER BY id DESC LIMIT 1"
        ).fetchone()
    assert row is not None
    assert row["command"] == "scan fic"

    args = json.loads(row["args_json"])
    assert "credentials" not in args, f"credentials raw leakato: {args}"
    assert "sensitive-fic-customer" not in row["args_json"], (
        f"path sensibile leakato: {row['args_json']}"
    )
    assert args.get("credentials_provided") is True
