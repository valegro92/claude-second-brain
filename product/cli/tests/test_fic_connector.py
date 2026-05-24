"""
Test del FattureInCloudConnector.

Strategia: iniettiamo un ``access_token`` precompilato + una fake
``requests.Session`` programmabile. Nessuna chiamata HTTP reale, nessun
OAuth flow.
"""

from __future__ import annotations

import logging
import os
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
import requests

from custodia_cli.connectors.base import (
    ConnectorAPIError,
    ConnectorAuthError,
    ConnectorRateLimitError,
)
from custodia_cli.connectors.fatture_in_cloud import FattureInCloudConnector


# ---------------------------------------------------------------------------
# Fake requests.Session
# ---------------------------------------------------------------------------


class _FakeResponse:
    def __init__(
        self,
        *,
        status_code: int = 200,
        json_data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self._json = json_data or {}
        self.headers = headers or {}

    def json(self) -> dict[str, Any]:
        return self._json

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}", response=self)  # type: ignore[arg-type]


class _FakeSession:
    """Session-like che supporta ``.request(method, url, ...)`` (usata da
    ``connectors._http.request_with_retry``).
    """

    def __init__(self, responses: list[_FakeResponse]) -> None:
        self.responses = list(responses)
        self.calls: list[dict[str, Any]] = []
        self.closed = False

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
        timeout: float | int = 30,
    ) -> _FakeResponse:
        self.calls.append(
            {
                "method": method,
                "url": url,
                "headers": headers,
                "params": dict(params or {}),
            }
        )
        if not self.responses:
            return _FakeResponse(status_code=200, json_data={"data": []})
        return self.responses.pop(0)

    def get(self, url: str, **kw: Any) -> _FakeResponse:  # legacy alias
        return self.request("GET", url, **kw)

    def close(self) -> None:
        self.closed = True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _client(
    *,
    cid: int = 1,
    name: str = "ACME Srl",
    vat: str | None = "IT01234567890",
    email: str | None = "info@acme.it",
) -> dict[str, Any]:
    return {
        "id": cid,
        "name": name,
        "vat_number": vat,
        "tax_code": "CMECMP00A01H501Z",
        "address_street": "Via Roma 1",
        "address_postal_code": "00100",
        "address_city": "Roma",
        "address_province": "RM",
        "email": email,
        "phone": "+39 06 1234567",
        "code": "C001",
    }


def _supplier(*, sid: int = 100, name: str = "Fornitore SpA") -> dict[str, Any]:
    return {
        "id": sid,
        "name": name,
        "vat_number": "IT09876543210",
        "tax_code": None,
        "address_street": "Via Milano 5",
        "address_city": "Milano",
        "address_province": "MI",
        "email": "fornitore@example.it",
        "phone": None,
        "code": None,
    }


def _invoice(
    *,
    iid: int = 500,
    number: str = "1/2026",
    date: str = "2026-03-15",
    entity_name: str = "ACME Srl",
    amount_net: float = 1000.0,
    amount_vat: float = 220.0,
    amount_gross: float = 1220.0,
    items: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if items is None:
        items = [
            {"product_name": "Consulenza", "qty": 10, "net_price": 100.0},
        ]
    return {
        "id": iid,
        "number": number,
        "date": date,
        "amount_net": amount_net,
        "amount_vat": amount_vat,
        "amount_gross": amount_gross,
        "status": "paid",
        "entity": {
            "id": 1,
            "name": entity_name,
            "vat_number": "IT01234567890",
        },
        "items_list": items,
    }


def _stub_sleep(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    """Stubba ``time.sleep`` dentro il modulo ``_http`` (dove avviene davvero)."""
    sleeps: list[float] = []

    def _fake(s: float) -> None:
        sleeps.append(s)

    monkeypatch.setattr("custodia_cli.connectors._http.time.sleep", _fake)
    return sleeps


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_happy_path_clients_suppliers_invoices() -> None:
    """3 clienti + 2 fornitori + 5 fatture → 10 SourceDocument."""
    clients = [_client(cid=i, name=f"Cliente {i}") for i in range(1, 4)]
    suppliers = [_supplier(sid=100 + i, name=f"Fornitore {i}") for i in range(1, 3)]
    invoices = [_invoice(iid=500 + i, number=f"{i}/2026") for i in range(1, 6)]

    session = _FakeSession(
        [
            _FakeResponse(json_data={"data": clients, "current_page": 1, "last_page": 1}),
            _FakeResponse(json_data={"data": suppliers, "current_page": 1, "last_page": 1}),
            _FakeResponse(json_data={"data": invoices, "current_page": 1, "last_page": 1}),
        ]
    )
    connector = FattureInCloudConnector(
        company_id=12345, access_token="tok", session=session
    )
    docs = list(connector.iter_documents())

    assert len(docs) == 10
    by_id = {d.source_id: d for d in docs}
    assert "fic:client:1" in by_id
    assert "fic:client:3" in by_id
    assert "fic:supplier:101" in by_id
    assert "fic:invoice:501" in by_id
    assert "fic:invoice:505" in by_id

    c1 = by_id["fic:client:1"]
    assert c1.mime_type == "application/vnd.custodia.fic-client"
    assert "Cliente: Cliente 1" in c1.text
    assert "P.IVA: IT01234567890" in c1.text
    assert "Email: info@acme.it" in c1.text
    assert c1.metadata["type"] == "client"
    assert c1.metadata["fic_id"] == 1

    s = by_id["fic:supplier:101"]
    assert s.mime_type == "application/vnd.custodia.fic-supplier"
    assert "Fornitore: Fornitore 1" in s.text
    assert "/FattureInCloud/fornitori/" in s.source_path
    assert s.metadata["type"] == "supplier"

    inv = by_id["fic:invoice:501"]
    assert inv.mime_type == "application/vnd.custodia.fic-invoice"
    assert "Fattura n. 1/2026 del 2026-03-15" in inv.text
    assert "Importo lordo: € 1220.00" in inv.text
    assert "Consulenza" in inv.text
    assert "/FattureInCloud/fatture-emesse/2026/" in inv.source_path
    assert inv.metadata["type"] == "invoice"
    assert inv.metadata["entity_name"] == "ACME Srl"

    stats = connector.stats
    assert stats["processed"] == 10
    assert stats["processed_clients"] == 3
    assert stats["processed_suppliers"] == 2
    assert stats["processed_invoices"] == 5
    assert stats["errors"] == 0


def test_pagination_follows_last_page() -> None:
    """current_page/last_page → itera N pagine clienti finché current >= last."""
    page1 = {
        "data": [_client(cid=1), _client(cid=2)],
        "current_page": 1,
        "last_page": 2,
    }
    page2 = {
        "data": [_client(cid=3)],
        "current_page": 2,
        "last_page": 2,
    }
    session = _FakeSession([
        _FakeResponse(json_data=page1),
        _FakeResponse(json_data=page2),
    ])
    connector = FattureInCloudConnector(
        company_id=1, access_token="tok", session=session, resources=["clients"],
    )
    docs = list(connector.iter_documents())
    assert len(docs) == 3
    assert len(session.calls) == 2
    assert session.calls[0]["params"]["page"] == "1"
    assert session.calls[1]["params"]["page"] == "2"


def test_pagination_no_metadata_loop_detection(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """FIX CN-2: pagination metadata assente + items full-page identici → abort."""
    # Pagina full (== _PAGE_SIZE=100) MA con id che si ripetono.
    page_items = [{"id": i, "name": f"C{i}", "vat_number": None,
                   "tax_code": None, "address_street": "", "address_city": "",
                   "address_province": "", "address_postal_code": "",
                   "email": None, "phone": None, "code": None}
                  for i in range(1, 101)]
    # Stessa pagina ritornata sempre (loop infinito senza fix).
    responses = [_FakeResponse(json_data={"data": page_items}) for _ in range(5)]
    session = _FakeSession(responses)
    connector = FattureInCloudConnector(
        company_id=1, access_token="tok", session=session, resources=["clients"],
    )
    with caplog.at_level(logging.WARNING, logger="custodia_cli.connectors.fatture_in_cloud"):
        docs = list(connector.iter_documents())
    # Senza fix CN-2 questo loop sarebbe infinito (le 5 risposte si
    # esaurirebbero e poi il _FakeSession ritornerebbe risposte vuote senza
    # mai uscire). Con il fix: si ferma dopo aver scoperto il loop.
    # I primi 100 doc vengono emessi dalla pagina1; pagina2 emette altri 100
    # (i `seen_item_ids` si popolano dopo il yield), pagina3 rileva il loop e
    # abortisce. Quindi ci aspettiamo ≤ 200 doc, NON infiniti.
    assert len(docs) <= 200
    assert any("loop pagination rilevato" in r.message.lower() for r in caplog.records)
    # Più importante: NON ha consumato tutte le 5 risposte fake (sarebbe stato
    # loop infinito).
    assert len(session.responses) > 0


def test_invoice_since_filter_adds_date_after() -> None:
    """since → date_after=YYYY-MM-DD nei query params della richiesta fatture."""
    session = _FakeSession(
        [_FakeResponse(json_data={"data": [], "current_page": 1, "last_page": 1})]
    )
    since = datetime(2024, 6, 1, tzinfo=timezone.utc)
    connector = FattureInCloudConnector(
        company_id=1, access_token="tok", session=session, since=since,
        resources=["invoices"],
    )
    list(connector.iter_documents())
    call = session.calls[0]
    assert call["params"]["date_after"] == "2024-06-01"
    assert call["params"]["type"] == "invoice"


def test_retry_on_429_then_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """429 + Retry-After → backoff e retry."""
    sleeps = _stub_sleep(monkeypatch)
    session = _FakeSession([
        _FakeResponse(status_code=429, headers={"Retry-After": "1"}),
        _FakeResponse(json_data={"data": [_client(cid=1)], "current_page": 1, "last_page": 1}),
    ])
    connector = FattureInCloudConnector(
        company_id=1, access_token="tok", session=session, resources=["clients"],
    )
    docs = list(connector.iter_documents())
    assert len(docs) == 1
    assert sleeps == [1.0]


def test_retry_exhausted_raises_rate_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """4×429 → max retry esaurito → ConnectorRateLimitError + errors+=1."""
    _stub_sleep(monkeypatch)
    session = _FakeSession([
        _FakeResponse(status_code=429),
        _FakeResponse(status_code=429),
        _FakeResponse(status_code=429),
        _FakeResponse(status_code=429),
    ])
    connector = FattureInCloudConnector(
        company_id=1, access_token="tok", session=session, resources=["clients"],
    )
    with pytest.raises(ConnectorRateLimitError):
        list(connector.iter_documents())
    assert connector.stats["errors"] == 1


def test_retry_after_capped_at_max(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """FIX CN-1: Retry-After: 999 → cap a 60s con warning."""
    sleeps = _stub_sleep(monkeypatch)
    session = _FakeSession([
        _FakeResponse(status_code=429, headers={"Retry-After": "999"}),
        _FakeResponse(json_data={"data": [_client(cid=1)], "current_page": 1, "last_page": 1}),
    ])
    connector = FattureInCloudConnector(
        company_id=1, access_token="tok", session=session, resources=["clients"],
    )
    with caplog.at_level(logging.WARNING, logger="custodia_cli.connectors._http"):
        list(connector.iter_documents())
    assert 60.0 in sleeps
    assert all(s <= 60.0 for s in sleeps)
    assert any("eccede il cap" in r.message for r in caplog.records)


def test_401_raises_auth_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """HTTP 401 → ConnectorAuthError (FIX CN-5)."""
    _stub_sleep(monkeypatch)
    session = _FakeSession([_FakeResponse(status_code=401)])
    connector = FattureInCloudConnector(
        company_id=1, access_token="tok", session=session, resources=["clients"],
    )
    with pytest.raises(ConnectorAuthError):
        list(connector.iter_documents())


def test_403_raises_auth_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """HTTP 403 → ConnectorAuthError."""
    _stub_sleep(monkeypatch)
    session = _FakeSession([_FakeResponse(status_code=403)])
    connector = FattureInCloudConnector(
        company_id=1, access_token="tok", session=session, resources=["clients"],
    )
    with pytest.raises(ConnectorAuthError):
        list(connector.iter_documents())


def test_500_persistent_raises_api_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """HTTP 500 persistente → ConnectorAPIError (dopo retry esauriti)."""
    _stub_sleep(monkeypatch)
    session = _FakeSession([
        _FakeResponse(status_code=500),
        _FakeResponse(status_code=500),
        _FakeResponse(status_code=500),
    ])
    connector = FattureInCloudConnector(
        company_id=1, access_token="tok", session=session, resources=["clients"],
    )
    with pytest.raises(ConnectorAPIError):
        list(connector.iter_documents())


def test_per_item_error_isolated() -> None:
    """1 fattura malformata + 4 OK → 4 doc + errors=1."""
    bad = {"foo": "no id field"}
    good = [_invoice(iid=500 + i, number=f"{i}/2026") for i in range(1, 5)]
    items = [bad] + good
    session = _FakeSession([
        _FakeResponse(json_data={"data": items, "current_page": 1, "last_page": 1}),
    ])
    connector = FattureInCloudConnector(
        company_id=1, access_token="tok", session=session, resources=["invoices"],
    )
    docs = list(connector.iter_documents())
    assert len(docs) == 4
    assert connector.stats["errors"] == 1
    assert connector.stats["processed_invoices"] == 4


def test_dry_run_empty_text_but_metadata_present() -> None:
    """dry_run=True → text vuoto, ma metadata popolata."""
    session = _FakeSession([
        _FakeResponse(json_data={"data": [_client(cid=1)], "current_page": 1, "last_page": 1}),
    ])
    connector = FattureInCloudConnector(
        company_id=1, access_token="tok", session=session,
        resources=["clients"], dry_run=True,
    )
    docs = list(connector.iter_documents())
    assert len(docs) == 1
    assert docs[0].text == ""
    assert docs[0].metadata["name"] == "ACME Srl"
    assert docs[0].metadata["fic_id"] == 1


def test_resources_subset_only_clients() -> None:
    """resources=['clients'] → no fornitori/fatture, 1 chiamata sola."""
    session = _FakeSession([
        _FakeResponse(json_data={"data": [_client(cid=1)], "current_page": 1, "last_page": 1}),
    ])
    connector = FattureInCloudConnector(
        company_id=1, access_token="tok", session=session, resources=["clients"],
    )
    docs = list(connector.iter_documents())
    assert len(docs) == 1
    assert len(session.calls) == 1
    assert "/entities/clients" in session.calls[0]["url"]


def test_invalid_resource_raises() -> None:
    """resources contiene un valore non valido → ValueError."""
    with pytest.raises(ValueError, match="resources non valide"):
        FattureInCloudConnector(
            company_id=1, access_token="tok", resources=["clients", "bogus"],
        )


def test_max_per_resource_caps_output() -> None:
    """max_per_resource=2 → solo 2 doc per risorsa anche se API ne ritorna 5."""
    items = [_client(cid=i, name=f"C{i}") for i in range(1, 6)]
    session = _FakeSession([
        _FakeResponse(json_data={"data": items, "current_page": 1, "last_page": 1}),
    ])
    connector = FattureInCloudConnector(
        company_id=1, access_token="tok", session=session,
        resources=["clients"], max_per_resource=2,
    )
    docs = list(connector.iter_documents())
    assert len(docs) == 2
    assert connector.stats["skipped_max"] == 1


def test_cache_dir_writes_raw_json(tmp_path: Path) -> None:
    """Con cache_dir, ogni item viene persistito come JSON file separato."""
    session = _FakeSession([
        _FakeResponse(json_data={"data": [_client(cid=42)], "current_page": 1, "last_page": 1}),
    ])
    cache_dir = tmp_path / "fic_cache"
    connector = FattureInCloudConnector(
        company_id=1, access_token="tok", session=session,
        resources=["clients"], cache_dir=cache_dir,
    )
    list(connector.iter_documents())
    cached = cache_dir / "clients" / "42.json"
    assert cached.exists()
    import json as _json

    data = _json.loads(cached.read_text(encoding="utf-8"))
    assert data["id"] == 42


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX permission semantics")
def test_cache_file_has_0o600_permissions(tmp_path: Path) -> None:
    """FIX CN-7: il file cache JSON ha permessi 0o600."""
    session = _FakeSession([
        _FakeResponse(json_data={"data": [_client(cid=42)], "current_page": 1, "last_page": 1}),
    ])
    cache_dir = tmp_path / "fic_cache"
    connector = FattureInCloudConnector(
        company_id=1, access_token="tok", session=session,
        resources=["clients"], cache_dir=cache_dir,
    )
    list(connector.iter_documents())
    cached = cache_dir / "clients" / "42.json"
    mode = stat.S_IMODE(os.stat(cached).st_mode)
    assert mode == 0o600


def test_cache_sanitizes_fic_id(tmp_path: Path) -> None:
    """FIX CN-8: fic_id con caratteri pericolosi (..,/) → sanitized."""
    # id contenente "../" → senza sanitize uscirebbe dalla cache_dir.
    bad_client = {
        "id": "../../etc/passwd",
        "name": "Malicious",
        "vat_number": None,
        "tax_code": None,
        "address_street": "", "address_city": "", "address_province": "",
        "address_postal_code": "", "email": None, "phone": None, "code": None,
    }
    session = _FakeSession([
        _FakeResponse(json_data={"data": [bad_client], "current_page": 1, "last_page": 1}),
    ])
    cache_dir = tmp_path / "fic_cache"
    connector = FattureInCloudConnector(
        company_id=1, access_token="tok", session=session,
        resources=["clients"], cache_dir=cache_dir,
    )
    list(connector.iter_documents())
    # Tutti i file cache devono essere sotto cache_dir.
    written = list(cache_dir.rglob("*.json"))
    assert len(written) == 1
    written_abs = written[0].resolve()
    cache_abs = cache_dir.resolve()
    # Verifica path containment.
    assert str(written_abs).startswith(str(cache_abs))


def test_authorization_header_bearer() -> None:
    """Ogni request usa Authorization: Bearer <token>."""
    session = _FakeSession([
        _FakeResponse(json_data={"data": [], "current_page": 1, "last_page": 1}),
    ])
    connector = FattureInCloudConnector(
        company_id=1, access_token="my-secret-tok", session=session, resources=["clients"],
    )
    list(connector.iter_documents())
    for call in session.calls:
        assert call["headers"]["Authorization"] == "Bearer my-secret-tok"


def test_no_pii_in_error_logs(caplog: pytest.LogCaptureFixture) -> None:
    """FIX security: body sensibile NON deve apparire nei warning."""
    bad = {
        "foo": "no id",
        "tax_code": "SECRETCF99XYZ",
    }
    session = _FakeSession([
        _FakeResponse(json_data={"data": [bad], "current_page": 1, "last_page": 1}),
    ])
    connector = FattureInCloudConnector(
        company_id=1, access_token="tok", session=session, resources=["clients"],
    )
    with caplog.at_level(logging.ERROR, logger="custodia_cli.connectors.fatture_in_cloud"):
        list(connector.iter_documents())
    for record in caplog.records:
        assert "SECRETCF99XYZ" not in record.message
        assert "SECRETCF99XYZ" not in str(record.args or "")


def test_company_id_must_be_positive_int() -> None:
    """company_id 0/negativo/non-int → ValueError chiaro."""
    with pytest.raises(ValueError, match="company_id"):
        FattureInCloudConnector(company_id=0, access_token="tok")
    with pytest.raises(ValueError, match="company_id"):
        FattureInCloudConnector(company_id=-1, access_token="tok")


def test_invoice_with_missing_amounts_still_produces_doc() -> None:
    """Fattura con amount_* None non crasha: formattati come 0.00."""
    invoice = _invoice(iid=999, number="X/2026")
    invoice["amount_net"] = None
    invoice["amount_vat"] = None
    invoice["amount_gross"] = None
    session = _FakeSession([
        _FakeResponse(json_data={"data": [invoice], "current_page": 1, "last_page": 1}),
    ])
    connector = FattureInCloudConnector(
        company_id=1, access_token="tok", session=session, resources=["invoices"],
    )
    docs = list(connector.iter_documents())
    assert len(docs) == 1
    assert "€ 0.00" in docs[0].text
    assert connector.stats["errors"] == 0


def test_entity_omits_empty_optional_fields() -> None:
    """Cliente con email None → riga 'Email:' assente nel text (no None letterale)."""
    c = _client(cid=1, email=None)
    c["phone"] = None
    c["tax_code"] = None
    session = _FakeSession([
        _FakeResponse(json_data={"data": [c], "current_page": 1, "last_page": 1}),
    ])
    connector = FattureInCloudConnector(
        company_id=1, access_token="tok", session=session, resources=["clients"],
    )
    docs = list(connector.iter_documents())
    text = docs[0].text
    assert "Email:" not in text
    assert "Telefono:" not in text
    assert "Codice Fiscale:" not in text
    assert "None" not in text


def test_company_id_in_url() -> None:
    """L'URL di richiesta contiene la company_id passata."""
    session = _FakeSession([
        _FakeResponse(json_data={"data": [], "current_page": 1, "last_page": 1}),
    ])
    connector = FattureInCloudConnector(
        company_id=987654, access_token="tok", session=session, resources=["clients"],
    )
    list(connector.iter_documents())
    assert "/c/987654/" in session.calls[0]["url"]


# ---------------------------------------------------------------------------
# FIX CN-3: context manager / close()
# ---------------------------------------------------------------------------


def test_context_manager_closes_owned_session() -> None:
    connector = FattureInCloudConnector(company_id=1, access_token="t")
    with connector:
        pass
    assert connector._closed is True


def test_context_manager_does_not_close_injected_session() -> None:
    session = _FakeSession([])
    with FattureInCloudConnector(company_id=1, access_token="t", session=session):
        pass
    assert session.closed is False


def test_explicit_close_idempotent() -> None:
    connector = FattureInCloudConnector(company_id=1, access_token="t")
    connector.close()
    connector.close()  # no errore


# ---------------------------------------------------------------------------
# FIX CN-9: Field aliasing (parametric tests, drift detection)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "preferred_key,alias_key",
    [
        ("items_list", "items"),
        ("number", "numeration"),
    ],
)
def test_invoice_alias_field_used_when_preferred_missing(
    preferred_key: str, alias_key: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """FIX CN-9: alias di campo letti correttamente con debug logging."""
    invoice = _invoice()
    # Sposta il valore preferito sotto l'alias.
    if preferred_key in invoice:
        invoice[alias_key] = invoice.pop(preferred_key)

    session = _FakeSession([
        _FakeResponse(json_data={"data": [invoice], "current_page": 1, "last_page": 1}),
    ])
    connector = FattureInCloudConnector(
        company_id=1, access_token="t", session=session, resources=["invoices"],
    )
    with caplog.at_level(logging.DEBUG, logger="custodia_cli.connectors.fatture_in_cloud"):
        docs = list(connector.iter_documents())
    assert len(docs) == 1
    # Verifica che il debug log abbia tracciato l'alias.
    assert any(
        alias_key in r.message and "alias" in r.message.lower()
        for r in caplog.records
    )


@pytest.mark.parametrize(
    "qty_key", ["qty", "quantity"],
)
def test_invoice_item_qty_alias(qty_key: str) -> None:
    """qty vs quantity letti correttamente."""
    invoice = _invoice(
        items=[{"product_name": "X", qty_key: 7, "net_price": 50.0}]
    )
    session = _FakeSession([
        _FakeResponse(json_data={"data": [invoice], "current_page": 1, "last_page": 1}),
    ])
    connector = FattureInCloudConnector(
        company_id=1, access_token="t", session=session, resources=["invoices"],
    )
    docs = list(connector.iter_documents())
    assert "qty: 7" in docs[0].text


@pytest.mark.parametrize(
    "price_key", ["net_price", "gross_price", "price"],
)
def test_invoice_item_price_alias(price_key: str) -> None:
    """net_price / gross_price / price aliased."""
    invoice = _invoice(
        items=[{"product_name": "X", "qty": 1, price_key: 42.0}]
    )
    session = _FakeSession([
        _FakeResponse(json_data={"data": [invoice], "current_page": 1, "last_page": 1}),
    ])
    connector = FattureInCloudConnector(
        company_id=1, access_token="t", session=session, resources=["invoices"],
    )
    docs = list(connector.iter_documents())
    assert "€ 42.00" in docs[0].text
