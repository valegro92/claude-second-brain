"""Test del modulo ``custodia_cli.auth.microsoft_oauth``. Nessuna chiamata di rete."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from custodia_cli.auth import microsoft_oauth

SCOPES = ["Mail.Read"]


def _write_credentials(path: Path, *, tenant: str = "common") -> Path:
    path.write_text(
        json.dumps({"client_id": "fake-client-id", "tenant_id": tenant}),
        encoding="utf-8",
    )
    return path


class _FakeApp:
    """Mock di msal.PublicClientApplication controllabile dai test."""

    def __init__(
        self,
        *,
        silent_result: dict[str, Any] | None = None,
        interactive_result: dict[str, Any] | None = None,
        has_accounts: bool = False,
    ) -> None:
        self.silent_result = silent_result
        self.interactive_result = interactive_result
        self._has_accounts = has_accounts
        self.silent_calls = 0
        self.interactive_calls = 0

    def get_accounts(self) -> list[dict[str, Any]]:
        return [{"username": "user@example.com"}] if self._has_accounts else []

    def acquire_token_silent(self, scopes: list[str], account: Any) -> dict[str, Any] | None:
        self.silent_calls += 1
        return self.silent_result

    def acquire_token_interactive(
        self, *, scopes: list[str], prompt: str, port: int, timeout: int | None = None
    ) -> dict[str, Any]:
        self.interactive_calls += 1
        self.last_interactive_timeout = timeout
        if self.interactive_result is None:
            return {"error": "no_result", "error_description": "test fail"}
        return self.interactive_result


@pytest.fixture(autouse=True)
def _stub_browser_check(monkeypatch: pytest.MonkeyPatch) -> None:
    """Default: forza platform=darwin così i test interactive non sono bloccati."""
    monkeypatch.setattr("sys.platform", "darwin")


def _install_fake_app(monkeypatch: pytest.MonkeyPatch, fake_app: _FakeApp) -> dict[str, Any]:
    """Patcha _build_app e cattura il cache passato."""
    captured: dict[str, Any] = {}

    def _builder(creds_path: Path, cache: Any) -> _FakeApp:
        captured["creds_path"] = creds_path
        captured["cache"] = cache
        return fake_app

    monkeypatch.setattr(microsoft_oauth, "_build_app", _builder)
    return captured


def test_silent_success_returns_token_without_interactive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    creds_file = _write_credentials(tmp_path / "ms.json")
    token_cache = tmp_path / "ms_token.json"

    fake_app = _FakeApp(
        silent_result={"access_token": "silent-tok"},
        has_accounts=True,
    )
    _install_fake_app(monkeypatch, fake_app)

    tok = microsoft_oauth.get_access_token(
        credentials_path=creds_file,
        token_cache_path=token_cache,
        scopes=SCOPES,
    )
    assert tok == "silent-tok"
    assert fake_app.silent_calls == 1
    assert fake_app.interactive_calls == 0


def test_no_token_cache_triggers_interactive_flow(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    creds_file = _write_credentials(tmp_path / "ms.json")
    token_cache = tmp_path / "absent.json"

    fake_app = _FakeApp(
        silent_result=None,
        interactive_result={"access_token": "interactive-tok"},
        has_accounts=False,
    )
    _install_fake_app(monkeypatch, fake_app)

    tok = microsoft_oauth.get_access_token(
        credentials_path=creds_file,
        token_cache_path=token_cache,
        scopes=SCOPES,
    )
    assert tok == "interactive-tok"
    assert fake_app.interactive_calls == 1


def test_silent_failure_falls_back_to_interactive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Token cache esiste + account presente ma silent ritorna None → interactive."""
    creds_file = _write_credentials(tmp_path / "ms.json")
    token_cache = tmp_path / "ms_token.json"
    token_cache.write_text("{}", encoding="utf-8")

    fake_app = _FakeApp(
        silent_result=None,  # refresh fallito
        interactive_result={"access_token": "fresh-tok"},
        has_accounts=True,
    )
    _install_fake_app(monkeypatch, fake_app)

    tok = microsoft_oauth.get_access_token(
        credentials_path=creds_file,
        token_cache_path=token_cache,
        scopes=SCOPES,
    )
    assert tok == "fresh-tok"
    assert fake_app.silent_calls == 1
    assert fake_app.interactive_calls == 1


def test_missing_credentials_raises_runtime_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("CUSTODIA_MICROSOFT_CREDENTIALS_JSON", raising=False)
    with pytest.raises(RuntimeError, match="CUSTODIA_MICROSOFT_CREDENTIALS_JSON"):
        microsoft_oauth.get_access_token(
            credentials_path=Path("/non/esiste/ms.json"),
            token_cache_path=tmp_path / "tok.json",
            scopes=SCOPES,
        )


def test_env_var_credentials_used_when_path_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_creds = _write_credentials(tmp_path / "env.json")
    monkeypatch.setenv("CUSTODIA_MICROSOFT_CREDENTIALS_JSON", str(env_creds))
    resolved = microsoft_oauth._resolve_credentials_path(None)
    assert resolved == env_creds


def test_headless_linux_raises_helpful_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Linux senza DISPLAY → RuntimeError con riferimento a 'browser'."""
    creds_file = _write_credentials(tmp_path / "ms.json")
    token_cache = tmp_path / "absent.json"

    monkeypatch.setattr("sys.platform", "linux")
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)

    fake_app = _FakeApp(silent_result=None, has_accounts=False)
    _install_fake_app(monkeypatch, fake_app)

    with pytest.raises(RuntimeError, match="browser"):
        microsoft_oauth.get_access_token(
            credentials_path=creds_file,
            token_cache_path=token_cache,
            scopes=SCOPES,
        )
    # Non deve aver tentato l'interactive flow.
    assert fake_app.interactive_calls == 0


def test_macos_does_not_require_display(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.platform", "darwin")
    monkeypatch.delenv("DISPLAY", raising=False)
    # Non deve sollevare.
    microsoft_oauth._ensure_browser_available()


def test_token_cache_written_with_mode_600(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FIX security: dopo la scrittura, il token cache ha permessi 0o600."""
    import sys

    if sys.platform == "win32":
        pytest.skip("permessi POSIX non significativi su Windows")

    creds_file = _write_credentials(tmp_path / "ms.json")
    token_cache = tmp_path / "subdir" / "ms_token.json"

    # FakeApp ritorna interactive token. Cache MSAL ha has_state_changed=True
    # solo dopo che app aggiunge il token al cache: simuliamo iniettando un cache
    # con state forzato. Più semplice: patcha _persist_cache per controllarlo.
    fake_app = _FakeApp(
        silent_result=None,
        interactive_result={"access_token": "tok"},
        has_accounts=False,
    )

    captured: dict[str, Any] = {}

    def _builder(creds_path: Path, cache: Any) -> _FakeApp:
        # Forziamo has_state_changed=True così _persist_cache viene chiamato.
        cache.has_state_changed = True
        cache.serialize = lambda: '{"fake": "cache"}'  # type: ignore[method-assign]
        captured["cache"] = cache
        return fake_app

    monkeypatch.setattr(microsoft_oauth, "_build_app", _builder)

    microsoft_oauth.get_access_token(
        credentials_path=creds_file,
        token_cache_path=token_cache,
        scopes=SCOPES,
    )

    assert token_cache.exists()
    mode = oct(token_cache.stat().st_mode)[-3:]
    assert mode == "600", f"atteso 0o600, ottenuto 0o{mode}"
    # Parent dir creata.
    parent_mode = oct(token_cache.parent.stat().st_mode)[-3:]
    assert parent_mode == "700", f"atteso 0o700 sulla dir, ottenuto 0o{parent_mode}"


def test_invalid_credentials_json_raises_runtime_error(tmp_path: Path) -> None:
    """credentials JSON malformato → RuntimeError con context."""
    bad = tmp_path / "bad.json"
    bad.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(RuntimeError, match="illegibili|illeggibili"):
        microsoft_oauth._load_client_config(bad)


def test_credentials_json_missing_client_id_raises(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"tenant_id": "common"}), encoding="utf-8")
    with pytest.raises(RuntimeError, match="client_id"):
        microsoft_oauth._load_client_config(bad)


def test_interactive_timeout_default_passed_to_msal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FIX OA-9: ``acquire_token_interactive`` riceve un timeout esplicito."""
    creds_file = _write_credentials(tmp_path / "ms.json")
    token_cache = tmp_path / "absent.json"

    fake_app = _FakeApp(
        silent_result=None,
        interactive_result={"access_token": "tok"},
        has_accounts=False,
    )
    _install_fake_app(monkeypatch, fake_app)

    microsoft_oauth.get_access_token(
        credentials_path=creds_file,
        token_cache_path=token_cache,
        scopes=SCOPES,
    )

    # Default = 300s (5 minuti). Non None — il blocco indefinito è la vuln.
    assert fake_app.last_interactive_timeout == 300


def test_interactive_timeout_custom_passed_to_msal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FIX OA-9: timeout custom propagato a MSAL."""
    creds_file = _write_credentials(tmp_path / "ms.json")
    token_cache = tmp_path / "absent.json"

    fake_app = _FakeApp(
        silent_result=None,
        interactive_result={"access_token": "tok"},
        has_accounts=False,
    )
    _install_fake_app(monkeypatch, fake_app)

    microsoft_oauth.get_access_token(
        credentials_path=creds_file,
        token_cache_path=token_cache,
        scopes=SCOPES,
        timeout=60,
    )
    assert fake_app.last_interactive_timeout == 60


def test_authenticated_username_logged_to_console(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """FIX OA-8: dopo auth, lo username dell'account è visibile sulla console."""
    creds_file = _write_credentials(tmp_path / "ms.json")
    token_cache = tmp_path / "absent.json"

    fake_app = _FakeApp(
        silent_result=None,
        interactive_result={
            "access_token": "tok",
            "id_token_claims": {"preferred_username": "consulente@cliente.it"},
        },
        has_accounts=False,
    )
    _install_fake_app(monkeypatch, fake_app)

    microsoft_oauth.get_access_token(
        credentials_path=creds_file,
        token_cache_path=token_cache,
        scopes=SCOPES,
    )
    captured = capsys.readouterr()
    assert "consulente@cliente.it" in captured.out
    assert "Verifica" in captured.out


def test_authenticated_username_logged_from_account_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """FIX OA-8: fallback su ``account.username`` se ``id_token_claims`` assente."""
    creds_file = _write_credentials(tmp_path / "ms.json")
    token_cache = tmp_path / "absent.json"

    fake_app = _FakeApp(
        silent_result=None,
        interactive_result={
            "access_token": "tok",
            "account": {"username": "fallback@cliente.it"},
        },
        has_accounts=False,
    )
    _install_fake_app(monkeypatch, fake_app)

    microsoft_oauth.get_access_token(
        credentials_path=creds_file,
        token_cache_path=token_cache,
        scopes=SCOPES,
    )
    captured = capsys.readouterr()
    assert "fallback@cliente.it" in captured.out


def test_no_username_in_result_does_not_crash(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """FIX OA-8: result senza username → nessun log username, nessun crash."""
    creds_file = _write_credentials(tmp_path / "ms.json")
    token_cache = tmp_path / "absent.json"

    fake_app = _FakeApp(
        silent_result=None,
        interactive_result={"access_token": "tok"},  # niente claims/account
        has_accounts=False,
    )
    _install_fake_app(monkeypatch, fake_app)

    tok = microsoft_oauth.get_access_token(
        credentials_path=creds_file,
        token_cache_path=token_cache,
        scopes=SCOPES,
    )
    assert tok == "tok"
    captured = capsys.readouterr()
    assert "Microsoft autenticato" not in captured.out


def test_interactive_failure_raises_runtime_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Se interactive ritorna error dict, solleva RuntimeError chiaro."""
    creds_file = _write_credentials(tmp_path / "ms.json")
    token_cache = tmp_path / "tok.json"

    fake_app = _FakeApp(
        silent_result=None,
        interactive_result={"error": "consent_required", "error_description": "user said no"},
        has_accounts=False,
    )
    _install_fake_app(monkeypatch, fake_app)

    with pytest.raises(RuntimeError, match="consent_required"):
        microsoft_oauth.get_access_token(
            credentials_path=creds_file,
            token_cache_path=token_cache,
            scopes=SCOPES,
        )
