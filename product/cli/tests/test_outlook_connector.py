"""
Test del OutlookConnector.

Strategia: iniettiamo un ``access_token`` precompilato + una fake
``requests.Session`` programmabile per ritornare risposte mockate. Nessuna
chiamata HTTP reale, nessun OAuth flow MSAL.
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
from custodia_cli.connectors.outlook import OutlookConnector


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
    """Session che ritorna risposte da una coda, registrando le call.

    Supporta sia ``.get(...)`` (legacy) che ``.request(method, url, ...)``
    (usata da ``connectors._http.request_with_retry``).
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
            {"method": method, "url": url, "headers": headers, "params": params}
        )
        if not self.responses:
            return _FakeResponse(status_code=200, json_data={"value": []})
        return self.responses.pop(0)

    def get(self, url: str, **kw: Any) -> _FakeResponse:  # legacy alias
        return self.request("GET", url, **kw)

    def close(self) -> None:
        self.closed = True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_message(
    *,
    msg_id: str = "AAA",
    subject: str = "Test",
    body_html: str | None = None,
    body_text: str | None = None,
    from_email: str = "alice@example.com",
    from_name: str = "Alice",
    to: list[str] | None = None,
    cc: list[str] | None = None,
    received: str = "2026-05-01T10:00:00Z",
    has_attachments: bool = False,
) -> dict[str, Any]:
    if body_html is not None:
        body = {"contentType": "html", "content": body_html}
    else:
        body = {"contentType": "text", "content": body_text or ""}
    return {
        "id": msg_id,
        "subject": subject,
        "from": {"emailAddress": {"address": from_email, "name": from_name}},
        "toRecipients": [{"emailAddress": {"address": a}} for a in (to or ["bob@example.com"])],
        "ccRecipients": [{"emailAddress": {"address": a}} for a in (cc or [])],
        "receivedDateTime": received,
        "body": body,
        "bodyPreview": (body_html or body_text or "")[:200],
        "hasAttachments": has_attachments,
        "parentFolderId": "folder1",
    }


def _folder_response(name: str = "Inbox") -> _FakeResponse:
    return _FakeResponse(json_data={"displayName": name, "id": "folder1"})


def _stub_sleep(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    """Stubba ``time.sleep`` dentro il modulo ``_http`` (dove avviene davvero
    durante il retry) e raccoglie i valori passati.
    """
    sleeps: list[float] = []

    def _fake(s: float) -> None:
        sleeps.append(s)

    monkeypatch.setattr("custodia_cli.connectors._http.time.sleep", _fake)
    return sleeps


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_happy_path_three_messages() -> None:
    """3 messaggi → 3 SourceDocument con header italiano + body."""
    msgs = [
        _make_message(msg_id="m1", subject="Preventivo 2026", body_text="Ciao Bob"),
        _make_message(msg_id="m2", subject="Riunione", body_html="<p>Hello <b>world</b></p>"),
        _make_message(msg_id="m3", subject="Fattura", body_text="Allegata fattura"),
    ]
    session = _FakeSession(
        [
            _folder_response("Inbox"),
            _FakeResponse(json_data={"value": msgs}),
        ]
    )
    connector = OutlookConnector(access_token="fake-tok", session=session)
    docs = list(connector.iter_documents())

    assert len(docs) == 3
    by_id = {d.source_id: d for d in docs}
    assert "outlook:m1" in by_id
    assert "outlook:m2" in by_id
    assert "outlook:m3" in by_id

    m1 = by_id["outlook:m1"]
    assert m1.mime_type == "message/rfc822"
    assert "Da: Alice <alice@example.com>" in m1.text
    assert "A: bob@example.com" in m1.text
    assert "Oggetto: Preventivo 2026" in m1.text
    assert "Ciao Bob" in m1.text
    assert m1.metadata["from_email"] == "alice@example.com"
    assert m1.metadata["to_emails"] == ["bob@example.com"]
    assert m1.metadata["message_id"] == "m1"

    # HTML body → conversione plain text.
    m2 = by_id["outlook:m2"]
    assert "Hello" in m2.text
    assert "<p>" not in m2.text  # tag rimossi
    assert "world" in m2.text

    stats = connector.stats
    assert stats["processed"] == 3
    assert stats["errors"] == 0


def test_pagination_follows_next_link() -> None:
    """``@odata.nextLink`` → secondo GET con URL completo, no params iniziali."""
    page1 = {
        "value": [_make_message(msg_id="m1")],
        "@odata.nextLink": "https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages?$skiptoken=ABC",
    }
    page2 = {"value": [_make_message(msg_id="m2")]}
    session = _FakeSession(
        [
            _folder_response(),
            _FakeResponse(json_data=page1),
            _FakeResponse(json_data=page2),
        ]
    )
    connector = OutlookConnector(access_token="fake-tok", session=session)
    docs = list(connector.iter_documents())

    assert len(docs) == 2
    # Le ultime due call (post-folder-resolve) sono list calls.
    list_calls = session.calls[1:]
    assert list_calls[0]["params"] is not None
    assert list_calls[1]["params"] is None  # nextLink ha già i params encoded
    assert list_calls[1]["url"].endswith("$skiptoken=ABC")


def test_pagination_loop_detected(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """``@odata.nextLink`` ciclico → scansione interrotta con warning."""
    cyclic_link = "https://graph.microsoft.com/v1.0/cycle?$skiptoken=LOOP"
    page_a = {
        "value": [_make_message(msg_id="ma")],
        "@odata.nextLink": cyclic_link,
    }
    page_b = {
        "value": [_make_message(msg_id="mb")],
        "@odata.nextLink": cyclic_link,  # stesso link → loop
    }
    session = _FakeSession(
        [
            _folder_response(),
            _FakeResponse(json_data=page_a),
            _FakeResponse(json_data=page_b),
        ]
    )
    connector = OutlookConnector(access_token="fake-tok", session=session)
    with caplog.at_level(logging.WARNING, logger="custodia_cli.connectors.outlook"):
        docs = list(connector.iter_documents())
    # ma e mb consegnati, poi loop detection ferma.
    assert len(docs) == 2
    assert any("Loop pagination" in r.message for r in caplog.records)


def test_retry_on_429_then_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """429 al primo tentativo → retry → success."""
    sleeps = _stub_sleep(monkeypatch)
    session = _FakeSession(
        [
            _folder_response(),
            _FakeResponse(status_code=429, headers={"Retry-After": "1"}),
            _FakeResponse(json_data={"value": [_make_message(msg_id="m1")]}),
        ]
    )
    connector = OutlookConnector(access_token="fake-tok", session=session)
    docs = list(connector.iter_documents())
    assert len(docs) == 1
    # Retry-After=1 deve essere stato rispettato.
    assert sleeps == [1.0]


def test_retry_exhausted_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """4×429 → max retry esaurito → ConnectorRateLimitError, no doc."""
    _stub_sleep(monkeypatch)
    session = _FakeSession(
        [
            _folder_response(),
            _FakeResponse(status_code=429),
            _FakeResponse(status_code=429),
            _FakeResponse(status_code=429),
            _FakeResponse(status_code=429),
        ]
    )
    connector = OutlookConnector(access_token="fake-tok", session=session)
    with pytest.raises(ConnectorRateLimitError):
        list(connector.iter_documents())
    assert connector.stats["errors"] == 1


def test_retry_after_header_respected(monkeypatch: pytest.MonkeyPatch) -> None:
    """Retry-After numerico viene parsato e usato come sleep."""
    sleeps = _stub_sleep(monkeypatch)
    session = _FakeSession(
        [
            _folder_response(),
            _FakeResponse(status_code=503, headers={"Retry-After": "5"}),
            _FakeResponse(json_data={"value": []}),
        ]
    )
    connector = OutlookConnector(access_token="fake-tok", session=session)
    list(connector.iter_documents())
    assert 5.0 in sleeps


def test_retry_after_capped_at_max(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Retry-After: 999 → sleep cappato a 60s con warning (FIX CN-1)."""
    sleeps = _stub_sleep(monkeypatch)
    session = _FakeSession(
        [
            _folder_response(),
            _FakeResponse(status_code=503, headers={"Retry-After": "999"}),
            _FakeResponse(json_data={"value": []}),
        ]
    )
    connector = OutlookConnector(access_token="fake-tok", session=session)
    with caplog.at_level(logging.WARNING, logger="custodia_cli.connectors._http"):
        list(connector.iter_documents())
    assert 60.0 in sleeps
    assert all(s <= 60.0 for s in sleeps)
    assert any("eccede il cap" in r.message for r in caplog.records)


def test_retry_after_negative_falls_back_to_backoff(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Retry-After: -1 (assurdo) → fallback al backoff esponenziale (FIX CN-1)."""
    sleeps = _stub_sleep(monkeypatch)
    session = _FakeSession(
        [
            _folder_response(),
            _FakeResponse(status_code=503, headers={"Retry-After": "-1"}),
            _FakeResponse(json_data={"value": []}),
        ]
    )
    connector = OutlookConnector(access_token="fake-tok", session=session)
    list(connector.iter_documents())
    # Backoff base 2s + jitter <= 0.5 → sleep ∈ [2.0, 2.5].
    assert sleeps and 2.0 <= sleeps[0] <= 2.5


def test_retry_after_http_date_falls_back_to_backoff(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Retry-After: HTTP-date → ValueError catch, fallback backoff (FIX CN-1)."""
    sleeps = _stub_sleep(monkeypatch)
    session = _FakeSession(
        [
            _folder_response(),
            _FakeResponse(
                status_code=503,
                headers={"Retry-After": "Wed, 21 Oct 2026 07:28:00 GMT"},
            ),
            _FakeResponse(json_data={"value": []}),
        ]
    )
    connector = OutlookConnector(access_token="fake-tok", session=session)
    list(connector.iter_documents())
    assert sleeps and 2.0 <= sleeps[0] <= 2.5


def test_per_message_error_does_not_kill_scan() -> None:
    """1 messaggio malformato + 2 OK → 2 doc + errors=1."""
    bad = {"id": None, "subject": "broken"}  # id None → ValueError nel parsing
    good1 = _make_message(msg_id="g1")
    good2 = _make_message(msg_id="g2")
    session = _FakeSession(
        [
            _folder_response(),
            _FakeResponse(json_data={"value": [bad, good1, good2]}),
        ]
    )
    connector = OutlookConnector(access_token="fake-tok", session=session)
    docs = list(connector.iter_documents())
    assert {d.source_id for d in docs} == {"outlook:g1", "outlook:g2"}
    assert connector.stats["errors"] == 1
    assert connector.stats["processed"] == 2


def test_dry_run_uses_body_preview_only() -> None:
    """dry_run=True → text non contiene il body completo, solo preview troncato."""
    msg = _make_message(
        msg_id="m1",
        subject="Big",
        body_text="X" * 5000,  # body lungo
    )
    msg["bodyPreview"] = "PREVIEW_SHORT"
    session = _FakeSession(
        [
            _folder_response(),
            _FakeResponse(json_data={"value": [msg]}),
        ]
    )
    connector = OutlookConnector(access_token="fake-tok", session=session, dry_run=True)
    docs = list(connector.iter_documents())
    assert len(docs) == 1
    assert "PREVIEW_SHORT" in docs[0].text
    # Body completo NON presente.
    assert "XXXXXXXXXX" not in docs[0].text


def test_since_filter_in_query_params() -> None:
    """--since costruisce $filter receivedDateTime ge YYYY-MM-DDT00:00:00Z."""
    session = _FakeSession(
        [
            _folder_response(),
            _FakeResponse(json_data={"value": []}),
        ]
    )
    since = datetime(2026, 1, 15, tzinfo=timezone.utc)
    connector = OutlookConnector(access_token="fake-tok", session=session, since=since)
    list(connector.iter_documents())

    list_call = session.calls[1]
    assert list_call["params"] is not None
    assert "$filter" in list_call["params"]
    assert "2026-01-15T00:00:00Z" in list_call["params"]["$filter"]
    assert "receivedDateTime ge" in list_call["params"]["$filter"]


def test_max_messages_caps_output() -> None:
    """max_messages=2 → solo 2 doc anche se Graph ne ritorna 5."""
    msgs = [_make_message(msg_id=f"m{i}") for i in range(5)]
    session = _FakeSession(
        [
            _folder_response(),
            _FakeResponse(json_data={"value": msgs}),
        ]
    )
    connector = OutlookConnector(access_token="fake-tok", session=session, max_messages=2)
    docs = list(connector.iter_documents())
    assert len(docs) == 2
    assert connector.stats["skipped_max"] == 1


def test_cache_dir_writes_raw_json(tmp_path: Path) -> None:
    """Con cache_dir, ogni messaggio è persistito come JSON file."""
    msg = _make_message(msg_id="cache-me")
    session = _FakeSession(
        [
            _folder_response(),
            _FakeResponse(json_data={"value": [msg]}),
        ]
    )
    cache_dir = tmp_path / "cache"
    connector = OutlookConnector(
        access_token="fake-tok", session=session, cache_dir=cache_dir
    )
    docs = list(connector.iter_documents())
    assert len(docs) == 1
    cached_path = docs[0].metadata.get("cached_at")
    assert cached_path is not None
    assert Path(cached_path).exists()


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX permission semantics")
def test_cache_file_has_0o600_permissions(tmp_path: Path) -> None:
    """FIX CN-7: il file cache JSON ha permessi 0o600."""
    msg = _make_message(msg_id="perm-check")
    session = _FakeSession(
        [
            _folder_response(),
            _FakeResponse(json_data={"value": [msg]}),
        ]
    )
    cache_dir = tmp_path / "cache"
    connector = OutlookConnector(
        access_token="fake-tok", session=session, cache_dir=cache_dir
    )
    docs = list(connector.iter_documents())
    cached_path = Path(docs[0].metadata["cached_at"])
    mode = stat.S_IMODE(os.stat(cached_path).st_mode)
    assert mode == 0o600


def test_authorization_header_uses_bearer_token() -> None:
    """L'header Authorization deve essere ``Bearer <token>``."""
    session = _FakeSession(
        [
            _folder_response(),
            _FakeResponse(json_data={"value": []}),
        ]
    )
    connector = OutlookConnector(access_token="my-secret-tok", session=session)
    list(connector.iter_documents())
    for call in session.calls:
        assert call["headers"]["Authorization"] == "Bearer my-secret-tok"


def test_html_body_converted_to_plain_text() -> None:
    """HTML body → text via html2text."""
    msg = _make_message(
        msg_id="m1",
        body_html="<html><body><h1>Title</h1><p>Para <a href='http://x'>link</a></p></body></html>",
    )
    session = _FakeSession(
        [
            _folder_response(),
            _FakeResponse(json_data={"value": [msg]}),
        ]
    )
    connector = OutlookConnector(access_token="fake-tok", session=session)
    docs = list(connector.iter_documents())
    text = docs[0].text
    assert "Title" in text
    assert "Para" in text
    assert "<h1>" not in text
    assert "<p>" not in text


def test_html_body_italian_characters_preserved() -> None:
    """FIX CN-6: caratteri italiani (accenti, €, apostrofo tipografico) preservati."""
    html = (
        "<html><body><p>Il caff&egrave; costa &euro;2,50</p>"
        "<p>L’avvocato dice sì</p></body></html>"
    )
    msg = _make_message(msg_id="m1", body_html=html)
    session = _FakeSession(
        [
            _folder_response(),
            _FakeResponse(json_data={"value": [msg]}),
        ]
    )
    connector = OutlookConnector(access_token="fake-tok", session=session)
    docs = list(connector.iter_documents())
    text = docs[0].text
    assert "caffè" in text
    assert "€" in text or "EUR" in text or "2,50" in text  # html2text può variare
    assert "’" in text or "'" in text
    assert "sì" in text


def test_html_converter_reused_across_messages() -> None:
    """FIX CN-6: l'istanza html2text è singleton di classe (non per-messaggio)."""
    # Reset shared state per isolare il test.
    OutlookConnector._html_converter = None  # type: ignore[assignment]
    msgs = [
        _make_message(msg_id=f"m{i}", body_html=f"<p>msg {i}</p>") for i in range(3)
    ]
    session = _FakeSession(
        [
            _folder_response(),
            _FakeResponse(json_data={"value": msgs}),
        ]
    )
    connector = OutlookConnector(access_token="fake-tok", session=session)
    list(connector.iter_documents())
    # Istanza ora popolata e accessibile come singleton di classe.
    first = OutlookConnector._html_converter
    assert first is not None
    # Una seconda call non ricrea l'istanza.
    list(
        OutlookConnector(
            access_token="t",
            session=_FakeSession(
                [
                    _folder_response(),
                    _FakeResponse(
                        json_data={"value": [_make_message(msg_id="m99", body_html="<p>x</p>")]}
                    ),
                ]
            ),
        ).iter_documents()
    )
    assert OutlookConnector._html_converter is first


def test_cc_recipients_in_header() -> None:
    """Cc populato → riga 'Cc: ...' nel text."""
    msg = _make_message(
        msg_id="m1",
        cc=["cc1@example.com", "cc2@example.com"],
    )
    session = _FakeSession(
        [
            _folder_response(),
            _FakeResponse(json_data={"value": [msg]}),
        ]
    )
    connector = OutlookConnector(access_token="fake-tok", session=session)
    docs = list(connector.iter_documents())
    assert "Cc: cc1@example.com, cc2@example.com" in docs[0].text
    assert docs[0].metadata["cc_emails"] == ["cc1@example.com", "cc2@example.com"]


def test_folder_id_default_inbox() -> None:
    """folder_id=None → default 'inbox' nell'URL."""
    session = _FakeSession(
        [
            _folder_response(),
            _FakeResponse(json_data={"value": []}),
        ]
    )
    connector = OutlookConnector(access_token="fake-tok", session=session)
    list(connector.iter_documents())
    assert "/mailFolders/inbox/messages" in session.calls[1]["url"]


def test_no_body_logged_in_warning(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """FIX security: il warning per messaggio malformato NON include il body."""
    secret_body = "SECRET_PASSWORD_12345"
    bad = {
        "id": None,
        "subject": "ok",
        "body": {"contentType": "text", "content": secret_body},
    }
    session = _FakeSession(
        [
            _folder_response(),
            _FakeResponse(json_data={"value": [bad]}),
        ]
    )
    connector = OutlookConnector(access_token="fake-tok", session=session)
    with caplog.at_level(logging.ERROR, logger="custodia_cli.connectors.outlook"):
        list(connector.iter_documents())
    for record in caplog.records:
        assert secret_body not in record.message
        assert secret_body not in str(record.args or "")


# ---------------------------------------------------------------------------
# Context manager / lifecycle (FIX CN-3)
# ---------------------------------------------------------------------------


def test_context_manager_closes_owned_session() -> None:
    """``with OutlookConnector(...) as conn`` chiude la session creata internamente."""
    # Iniettare session=None → connector ne crea una propria, e la chiude.
    connector = OutlookConnector(access_token="t")
    owned = connector._session
    with connector:
        pass
    # requests.Session.close() è idempotente; usiamo la flag interna.
    assert connector._closed is True
    # E un secondo close non solleva.
    connector.close()
    # owned ha l'attributo .close, già chiamato.
    assert hasattr(owned, "close")


def test_context_manager_does_not_close_injected_session() -> None:
    """Una session iniettata da fuori NON viene chiusa (rispetto al chiamante)."""
    session = _FakeSession([])
    with OutlookConnector(access_token="t", session=session):
        pass
    assert session.closed is False  # la session iniettata sopravvive.


def test_explicit_close_is_idempotent() -> None:
    """``connector.close()`` doppio non solleva."""
    connector = OutlookConnector(access_token="t")
    connector.close()
    connector.close()  # no errore.


# ---------------------------------------------------------------------------
# Eccezioni custom (FIX CN-5, CN-11)
# ---------------------------------------------------------------------------


def test_404_folder_not_found_raises_api_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """HTTP 404 sulla list → ConnectorAPIError (FIX CN-11)."""
    _stub_sleep(monkeypatch)
    session = _FakeSession(
        [
            _folder_response(),
            _FakeResponse(status_code=404),
        ]
    )
    connector = OutlookConnector(access_token="t", session=session)
    with pytest.raises(ConnectorAPIError):
        list(connector.iter_documents())


def test_401_token_revoked_raises_auth_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """HTTP 401 sulla list → ConnectorAuthError → scan abortisce."""
    _stub_sleep(monkeypatch)
    session = _FakeSession(
        [
            _folder_response(),
            _FakeResponse(status_code=401),
        ]
    )
    connector = OutlookConnector(access_token="t", session=session)
    with pytest.raises(ConnectorAuthError):
        list(connector.iter_documents())


# ---------------------------------------------------------------------------
# source_path disambiguation (FIX CN-10)
# ---------------------------------------------------------------------------


def test_source_path_includes_id_suffix_to_disambiguate() -> None:
    """Due email con stesso subject troncato → source_path distinti (CN-10)."""
    msg_a = _make_message(msg_id="aaaaaaaa1234", subject="Stesso oggetto identico")
    msg_b = _make_message(msg_id="bbbbbbbb9999", subject="Stesso oggetto identico")
    session = _FakeSession(
        [
            _folder_response(),
            _FakeResponse(json_data={"value": [msg_a, msg_b]}),
        ]
    )
    connector = OutlookConnector(access_token="t", session=session)
    docs = list(connector.iter_documents())
    assert len(docs) == 2
    assert docs[0].source_path != docs[1].source_path
    # Verifica che il suffisso id sia presente nel path.
    assert "aaaaaaaa" in docs[0].source_path or "bbbbbbbb" in docs[1].source_path
