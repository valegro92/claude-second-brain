"""Test del modulo ``custodia_cli.auth.fic_oauth``. Nessuna chiamata di rete."""

from __future__ import annotations

import base64
import hashlib
import json
import time
from pathlib import Path
from typing import Any

import pytest

from custodia_cli.auth import fic_oauth

SCOPES = ["entity.clients:r", "entity.suppliers:r", "issued_documents:r"]


def _write_credentials(path: Path) -> Path:
    path.write_text(
        json.dumps(
            {
                "client_id": "fic-client-id",
                "client_secret": None,
                "redirect_uri_port": 0,
            }
        ),
        encoding="utf-8",
    )
    return path


def _write_token_cache(
    path: Path,
    *,
    access_token: str = "cached-tok",
    refresh_token: str | None = "refresh-tok",
    expires_in: int = 3600,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_at": time.time() + expires_in,
        "scopes": SCOPES,
        "client_id": "fic-client-id",
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


class _FakeResponse:
    def __init__(
        self, status_code: int = 200, json_data: dict[str, Any] | None = None
    ) -> None:
        self.status_code = status_code
        self._json = json_data or {}

    def json(self) -> dict[str, Any]:
        return self._json


class _FakeSession:
    def __init__(self, post_responses: list[_FakeResponse]) -> None:
        self.post_responses = list(post_responses)
        self.post_calls: list[dict[str, Any]] = []

    def post(self, url: str, *, data: dict[str, str], timeout: int = 30) -> _FakeResponse:
        self.post_calls.append({"url": url, "data": data})
        if not self.post_responses:
            return _FakeResponse(status_code=500, json_data={})
        return self.post_responses.pop(0)


@pytest.fixture(autouse=True)
def _stub_browser_check(monkeypatch: pytest.MonkeyPatch) -> None:
    """Default: platform=darwin (no headless block)."""
    monkeypatch.setattr("sys.platform", "darwin")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_valid_cached_token_returned_without_flow(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cache valida + non scaduto → ritorna subito, no HTTP."""
    creds = _write_credentials(tmp_path / "fic.json")
    cache = tmp_path / "fic_token.json"
    _write_token_cache(cache, access_token="ok-tok", expires_in=3600)

    sess = _FakeSession([])
    tok = fic_oauth.get_fic_access_token(
        credentials_path=creds,
        token_cache_path=cache,
        scopes=SCOPES,
        session=sess,
    )
    assert tok == "ok-tok"
    assert sess.post_calls == []


def test_expired_token_with_refresh_succeeds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Token scaduto + refresh_token → refresh trasparente via POST /oauth/token."""
    creds = _write_credentials(tmp_path / "fic.json")
    cache = tmp_path / "fic_token.json"
    _write_token_cache(cache, access_token="old", refresh_token="rt", expires_in=-10)

    sess = _FakeSession(
        [
            _FakeResponse(
                status_code=200,
                json_data={
                    "access_token": "new-tok",
                    "refresh_token": "new-rt",
                    "expires_in": 3600,
                    "token_type": "Bearer",
                },
            )
        ]
    )

    tok = fic_oauth.get_fic_access_token(
        credentials_path=creds,
        token_cache_path=cache,
        scopes=SCOPES,
        session=sess,
    )
    assert tok == "new-tok"
    assert len(sess.post_calls) == 1
    assert sess.post_calls[0]["data"]["grant_type"] == "refresh_token"
    assert sess.post_calls[0]["data"]["refresh_token"] == "rt"

    # Cache aggiornato su disco.
    saved = json.loads(cache.read_text(encoding="utf-8"))
    assert saved["access_token"] == "new-tok"
    assert saved["refresh_token"] == "new-rt"


def test_refresh_failure_falls_back_to_interactive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Refresh HTTP 401 → fallback al flow interattivo."""
    creds = _write_credentials(tmp_path / "fic.json")
    cache = tmp_path / "fic_token.json"
    _write_token_cache(cache, access_token="old", refresh_token="rt", expires_in=-10)

    sess = _FakeSession([_FakeResponse(status_code=401, json_data={})])

    # Stubba il flow interattivo per non aprire browser.
    called: dict[str, Any] = {}

    def _fake_flow(*, config: dict[str, Any], scopes: list[str], session: Any) -> dict[str, Any]:
        called["yes"] = True
        return {
            "access_token": "interactive-tok",
            "refresh_token": "new-rt",
            "expires_at": time.time() + 3600,
            "scopes": scopes,
            "client_id": config["client_id"],
        }

    monkeypatch.setattr(fic_oauth, "_run_interactive_flow", _fake_flow)

    tok = fic_oauth.get_fic_access_token(
        credentials_path=creds,
        token_cache_path=cache,
        scopes=SCOPES,
        session=sess,
    )
    assert tok == "interactive-tok"
    assert called.get("yes") is True


def test_no_cache_triggers_interactive_flow(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Token cache mancante → flow interattivo."""
    creds = _write_credentials(tmp_path / "fic.json")
    cache = tmp_path / "absent.json"

    def _fake_flow(*, config: dict[str, Any], scopes: list[str], session: Any) -> dict[str, Any]:
        return {
            "access_token": "fresh-tok",
            "refresh_token": "rt",
            "expires_at": time.time() + 3600,
            "scopes": scopes,
            "client_id": config["client_id"],
        }

    monkeypatch.setattr(fic_oauth, "_run_interactive_flow", _fake_flow)

    tok = fic_oauth.get_fic_access_token(
        credentials_path=creds,
        token_cache_path=cache,
        scopes=SCOPES,
    )
    assert tok == "fresh-tok"
    assert cache.exists()


def test_headless_linux_raises_helpful_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Linux senza DISPLAY → RuntimeError con 'browser'."""
    creds = _write_credentials(tmp_path / "fic.json")
    cache = tmp_path / "absent.json"

    monkeypatch.setattr("sys.platform", "linux")
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)

    with pytest.raises(RuntimeError, match="browser"):
        fic_oauth.get_fic_access_token(
            credentials_path=creds,
            token_cache_path=cache,
            scopes=SCOPES,
        )


def test_token_cache_written_with_mode_600(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FIX security: dopo persistenza, token cache ha permessi 0o600."""
    import sys

    if sys.platform == "win32":
        pytest.skip("permessi POSIX non significativi su Windows")

    creds = _write_credentials(tmp_path / "fic.json")
    cache = tmp_path / "subdir" / "fic_token.json"

    def _fake_flow(*, config: dict[str, Any], scopes: list[str], session: Any) -> dict[str, Any]:
        return {
            "access_token": "tok",
            "refresh_token": "rt",
            "expires_at": time.time() + 3600,
            "scopes": scopes,
            "client_id": config["client_id"],
        }

    monkeypatch.setattr(fic_oauth, "_run_interactive_flow", _fake_flow)

    fic_oauth.get_fic_access_token(
        credentials_path=creds,
        token_cache_path=cache,
        scopes=SCOPES,
    )

    assert cache.exists()
    mode = oct(cache.stat().st_mode)[-3:]
    assert mode == "600", f"atteso 0o600, ottenuto 0o{mode}"
    parent_mode = oct(cache.parent.stat().st_mode)[-3:]
    assert parent_mode == "700"


def test_missing_credentials_raises_with_env_hint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """credentials path mancante + env var unset → RuntimeError con regex env."""
    monkeypatch.delenv("CUSTODIA_FIC_CREDENTIALS_JSON", raising=False)
    with pytest.raises(RuntimeError, match="CUSTODIA_FIC_CREDENTIALS_JSON"):
        fic_oauth.get_fic_access_token(
            credentials_path=Path("/non/esiste/fic.json"),
            token_cache_path=tmp_path / "tok.json",
            scopes=SCOPES,
        )


def test_env_var_credentials_used_when_path_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_creds = _write_credentials(tmp_path / "env.json")
    monkeypatch.setenv("CUSTODIA_FIC_CREDENTIALS_JSON", str(env_creds))
    resolved = fic_oauth._resolve_credentials_path(None)
    assert resolved == env_creds


def test_pkce_challenge_is_sha256_of_verifier() -> None:
    """code_challenge = base64url(SHA256(code_verifier)), senza padding."""
    verifier, challenge = fic_oauth._generate_pkce_pair()
    expected = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest())
        .rstrip(b"=")
        .decode("ascii")
    )
    assert challenge == expected
    # Verifier deve essere lungo (≥ 43 char, raccomandazione RFC 7636).
    assert len(verifier) >= 43


def test_invalid_credentials_json_raises(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(RuntimeError, match="illeggibili"):
        fic_oauth._load_client_config(bad)


def test_credentials_missing_client_id_raises(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"redirect_uri_port": 0}), encoding="utf-8")
    with pytest.raises(RuntimeError, match="client_id"):
        fic_oauth._load_client_config(bad)


def test_credentials_invalid_port_raises(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text(
        json.dumps({"client_id": "x", "redirect_uri_port": -1}), encoding="utf-8"
    )
    with pytest.raises(RuntimeError, match="redirect_uri_port"):
        fic_oauth._load_client_config(bad)


def test_refresh_response_preserves_existing_refresh_token_if_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Refresh response senza refresh_token → preserva quello esistente in cache."""
    creds = _write_credentials(tmp_path / "fic.json")
    cache = tmp_path / "fic_token.json"
    _write_token_cache(cache, access_token="old", refresh_token="keep-me", expires_in=-10)

    sess = _FakeSession(
        [
            _FakeResponse(
                status_code=200,
                json_data={"access_token": "new", "expires_in": 3600},
                # NB: NO refresh_token nella response
            )
        ]
    )
    tok = fic_oauth.get_fic_access_token(
        credentials_path=creds,
        token_cache_path=cache,
        scopes=SCOPES,
        session=sess,
    )
    assert tok == "new"
    saved = json.loads(cache.read_text(encoding="utf-8"))
    # Il refresh_token vecchio deve essere preservato.
    assert saved["refresh_token"] == "keep-me"


# ---------------------------------------------------------------------------
# FIX OA-1, OA-10: state validation strict + branch coverage
# ---------------------------------------------------------------------------


def test_capture_callback_state_mismatch_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FIX OA-1: state ricevuto diverso da quello atteso → RuntimeError CSRF."""
    import socketserver

    # Server fake non avviato: ci basta passare il dict ``captured`` già
    # pre-popolato (il _serve loop esce subito perché "code" è presente).
    captured = {"code": "abc", "state": "WRONG"}

    # ``_capture_authorization_code`` ritorna il dict; la validazione strict
    # avviene in ``_run_interactive_flow``. Replichiamo qui il check del flow.
    # Approach: chiamiamo direttamente _run_interactive_flow ma stubbando
    # _start_callback_server per restituire un server fittizio + il captured
    # già popolato.
    class _FakeServer:
        server_address = ("127.0.0.1", 9999)

        def handle_request(self) -> None:
            pass

        def server_close(self) -> None:
            pass

    def _fake_start(port: int) -> tuple[_FakeServer, int, dict[str, str]]:
        return _FakeServer(), 9999, captured

    monkeypatch.setattr(fic_oauth, "_start_callback_server", _fake_start)
    monkeypatch.setattr("webbrowser.open", lambda url: True)

    with pytest.raises(RuntimeError, match="State mismatch"):
        fic_oauth._run_interactive_flow(
            config={
                "client_id": "cid",
                "client_secret": None,
                "redirect_uri_port": 0,
            },
            scopes=SCOPES,
            session=_FakeSession([]),  # type: ignore[arg-type]
        )


def test_capture_callback_state_missing_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FIX OA-1: state assente nel callback → RuntimeError (no bypass)."""
    # Provider che ha omesso state → la vecchia logica passava (bypass CSRF).
    captured = {"code": "abc"}  # NO "state"

    class _FakeServer:
        server_address = ("127.0.0.1", 9999)

        def handle_request(self) -> None:
            pass

        def server_close(self) -> None:
            pass

    def _fake_start(port: int) -> tuple[_FakeServer, int, dict[str, str]]:
        return _FakeServer(), 9999, captured

    monkeypatch.setattr(fic_oauth, "_start_callback_server", _fake_start)
    monkeypatch.setattr("webbrowser.open", lambda url: True)

    with pytest.raises(RuntimeError, match="State mismatch"):
        fic_oauth._run_interactive_flow(
            config={
                "client_id": "cid",
                "client_secret": None,
                "redirect_uri_port": 0,
            },
            scopes=SCOPES,
            session=_FakeSession([]),  # type: ignore[arg-type]
        )


def test_capture_callback_provider_error_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FIX OA-10: error redirect dal provider → RuntimeError con messaggio."""
    captured = {"error": "access_denied", "error_description": "user denied"}

    class _FakeServer:
        server_address = ("127.0.0.1", 9999)

        def handle_request(self) -> None:
            pass

        def server_close(self) -> None:
            pass

    def _fake_start(port: int) -> tuple[_FakeServer, int, dict[str, str]]:
        return _FakeServer(), 9999, captured

    monkeypatch.setattr(fic_oauth, "_start_callback_server", _fake_start)
    monkeypatch.setattr("webbrowser.open", lambda url: True)

    with pytest.raises(RuntimeError, match="access_denied"):
        fic_oauth._run_interactive_flow(
            config={
                "client_id": "cid",
                "client_secret": None,
                "redirect_uri_port": 0,
            },
            scopes=SCOPES,
            session=_FakeSession([]),  # type: ignore[arg-type]
        )


def test_capture_callback_timeout_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FIX OA-10: nessuna callback entro il timeout → RuntimeError."""
    import socketserver

    # Server vero su porta random — niente client che lo contatta.
    captured: dict[str, str] = {}
    handler_class = fic_oauth._make_callback_handler_class(captured)
    httpd = socketserver.TCPServer(("127.0.0.1", 0), handler_class)

    # Timeout cortissimo: il loop interno fa sleep(0.1), 0.3s basta.
    with pytest.raises(RuntimeError, match="Timeout"):
        fic_oauth._capture_authorization_code(
            httpd, captured, expected_state="X", timeout_seconds=0  # 0 = scade subito
        )


def test_state_param_present_in_authorize_url(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FIX OA-10: l'URL di authorize include sempre ``state``."""
    captured = {"code": "ok", "state": "WILL_BE_PATCHED"}

    class _FakeServer:
        server_address = ("127.0.0.1", 9999)

        def handle_request(self) -> None:
            pass

        def server_close(self) -> None:
            pass

    def _fake_start(port: int) -> tuple[_FakeServer, int, dict[str, str]]:
        return _FakeServer(), 9999, captured

    opened_urls: list[str] = []

    def _fake_open(url: str) -> bool:
        opened_urls.append(url)
        # Patch captured state per matchare quello effettivo nell'URL.
        import urllib.parse as _u

        parsed = _u.urlparse(url)
        qs = dict(_u.parse_qsl(parsed.query))
        captured["state"] = qs["state"]
        return True

    monkeypatch.setattr(fic_oauth, "_start_callback_server", _fake_start)
    monkeypatch.setattr("webbrowser.open", _fake_open)

    # Stubba token exchange.
    sess = _FakeSession(
        [_FakeResponse(200, {"access_token": "a", "expires_in": 3600})]
    )
    fic_oauth._run_interactive_flow(
        config={
            "client_id": "cid",
            "client_secret": None,
            "redirect_uri_port": 0,
        },
        scopes=SCOPES,
        session=sess,  # type: ignore[arg-type]
    )
    assert opened_urls, "browser non aperto"
    assert "state=" in opened_urls[0]
    # FIX OA-5: redirect_uri usa 127.0.0.1, non localhost.
    assert "127.0.0.1" in opened_urls[0]
    assert "localhost" not in opened_urls[0]


# ---------------------------------------------------------------------------
# FIX OA-4: handler-class isolation via factory closure
# ---------------------------------------------------------------------------


def test_callback_handler_factory_isolates_captured_state() -> None:
    """FIX OA-4: handler-class diversi hanno ``captured`` dict isolati."""
    captured_a: dict[str, str] = {}
    captured_b: dict[str, str] = {}

    handler_a_cls = fic_oauth._make_callback_handler_class(captured_a)
    handler_b_cls = fic_oauth._make_callback_handler_class(captured_b)

    # I due handler-class sono oggetti distinti.
    assert handler_a_cls is not handler_b_cls

    # Mutare captured_a non deve toccare captured_b — verifichiamo via closure
    # esterna che il binding sia per-istanza.
    captured_a["code"] = "AAA"
    assert "code" not in captured_b


# ---------------------------------------------------------------------------
# FIX OA-11: PKCE non-determinismo + RFC 7636 character set
# ---------------------------------------------------------------------------


def test_pkce_pair_changes_between_invocations() -> None:
    """FIX OA-11: ogni invocazione genera un verifier+challenge nuovo."""
    v1, c1 = fic_oauth._generate_pkce_pair()
    v2, c2 = fic_oauth._generate_pkce_pair()
    assert v1 != v2
    assert c1 != c2


def test_pkce_verifier_respects_rfc7636_charset() -> None:
    """FIX OA-11: code_verifier usa solo unreserved chars [A-Za-z0-9._~-]."""
    import re

    verifier, _ = fic_oauth._generate_pkce_pair()
    # ``secrets.token_urlsafe`` produce [A-Za-z0-9_-] — subset di RFC 7636.
    assert re.fullmatch(r"[A-Za-z0-9._~\-]+", verifier), (
        f"verifier contiene char non-RFC7636: {verifier}"
    )
    # RFC 7636 §4.1: 43 ≤ len(verifier) ≤ 128.
    assert 43 <= len(verifier) <= 128


def test_expired_token_without_refresh_runs_interactive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cache scaduta + refresh_token=None → flow interattivo."""
    creds = _write_credentials(tmp_path / "fic.json")
    cache = tmp_path / "fic_token.json"
    _write_token_cache(cache, access_token="old", refresh_token=None, expires_in=-10)

    def _fake_flow(*, config: dict[str, Any], scopes: list[str], session: Any) -> dict[str, Any]:
        return {
            "access_token": "via-flow",
            "refresh_token": "rt",
            "expires_at": time.time() + 3600,
            "scopes": scopes,
            "client_id": config["client_id"],
        }

    monkeypatch.setattr(fic_oauth, "_run_interactive_flow", _fake_flow)
    tok = fic_oauth.get_fic_access_token(
        credentials_path=creds,
        token_cache_path=cache,
        scopes=SCOPES,
    )
    assert tok == "via-flow"
