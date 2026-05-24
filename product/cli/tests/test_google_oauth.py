"""Test del modulo `custodia_cli.auth.google_oauth`. Nessuna chiamata di rete."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from custodia_cli.auth import google_oauth


SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


def _write_token(path: Path, *, expired: bool = False, has_refresh: bool = True) -> None:
    """Scrive un token JSON minimo, compatibile con Credentials.from_authorized_user_file."""
    payload = {
        "token": "fake-access-token",
        "refresh_token": "fake-refresh" if has_refresh else None,
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": "fake-client-id.apps.googleusercontent.com",
        "client_secret": "fake-secret",
        "scopes": SCOPES,
    }
    # Marker semplice "expired" che il nostro mock di Credentials interpreterà.
    payload["_test_expired"] = expired
    path.write_text(json.dumps(payload), encoding="utf-8")


@pytest.fixture
def fake_creds_class(monkeypatch: pytest.MonkeyPatch):
    """Patch ``Credentials`` di google_oauth con un mock controllabile."""

    class _FakeCreds:
        def __init__(self, *, valid: bool, expired: bool, refresh_token: str | None) -> None:
            self.valid = valid
            self.expired = expired
            self.refresh_token = refresh_token
            self.refresh_calls: int = 0

        @classmethod
        def from_authorized_user_file(cls, path_str: str, _scopes: list[str]) -> "_FakeCreds":
            data = json.loads(Path(path_str).read_text(encoding="utf-8"))
            expired = data.get("_test_expired", False)
            return cls(
                valid=not expired,
                expired=expired,
                refresh_token=data.get("refresh_token"),
            )

        def refresh(self, _request: object) -> None:
            self.refresh_calls += 1
            self.expired = False
            self.valid = True

        def to_json(self) -> str:
            return json.dumps({"token": "refreshed"})

    monkeypatch.setattr(google_oauth, "Credentials", _FakeCreds)
    return _FakeCreds


def test_valid_token_returns_without_flow(
    tmp_path: Path, fake_creds_class: type, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Token cache valido → no flow, no refresh."""
    token = tmp_path / "google_token.json"
    _write_token(token, expired=False)

    flow_mock = MagicMock()
    monkeypatch.setattr(google_oauth, "InstalledAppFlow", flow_mock)

    creds = google_oauth.get_credentials(
        credentials_path=None, token_cache_path=token, scopes=SCOPES
    )
    assert creds.valid
    flow_mock.from_client_secrets_file.assert_not_called()


def test_expired_token_with_refresh_succeeds(
    tmp_path: Path, fake_creds_class: type, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Token scaduto + refresh OK → refresh, scrivi cache, no flow."""
    token = tmp_path / "google_token.json"
    _write_token(token, expired=True, has_refresh=True)

    flow_mock = MagicMock()
    monkeypatch.setattr(google_oauth, "InstalledAppFlow", flow_mock)
    monkeypatch.setattr(google_oauth, "Request", MagicMock)

    creds = google_oauth.get_credentials(
        credentials_path=None, token_cache_path=token, scopes=SCOPES
    )
    assert creds.valid
    assert creds.refresh_calls == 1
    flow_mock.from_client_secrets_file.assert_not_called()

    # Cache deve essere stato sovrascritto.
    assert json.loads(token.read_text())["token"] == "refreshed"


def test_missing_credentials_raises_runtime_error_with_helpful_message(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Senza credentials_path valido e senza env var → RuntimeError parlante."""
    monkeypatch.delenv("CUSTODIA_GOOGLE_CREDENTIALS_JSON", raising=False)
    token = tmp_path / "absent_token.json"  # non esiste → forza il flow

    with pytest.raises(RuntimeError, match="CUSTODIA_GOOGLE_CREDENTIALS_JSON"):
        google_oauth.get_credentials(
            credentials_path=Path("/non/esiste/credentials.json"),
            token_cache_path=token,
            scopes=SCOPES,
        )


def test_refresh_failure_triggers_full_flow(
    tmp_path: Path, fake_creds_class: type, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Refresh fallisce → rilancia il flow interattivo con credentials_path."""
    from google.auth.exceptions import RefreshError

    token = tmp_path / "google_token.json"
    _write_token(token, expired=True)

    # Patch della classe per far fallire refresh.
    class _FailingCreds(fake_creds_class):  # type: ignore[misc, valid-type]
        def refresh(self, _request: object) -> None:
            raise RefreshError("refresh failed")

    monkeypatch.setattr(google_oauth, "Credentials", _FailingCreds)
    monkeypatch.setattr(google_oauth, "Request", MagicMock)

    # Mock del flow che restituisce un cred valido.
    new_creds = SimpleNamespace(
        valid=True,
        to_json=lambda: json.dumps({"token": "from-flow"}),
    )
    flow_instance = MagicMock()
    flow_instance.run_local_server.return_value = new_creds
    flow_class_mock = MagicMock()
    flow_class_mock.from_client_secrets_file.return_value = flow_instance
    monkeypatch.setattr(google_oauth, "InstalledAppFlow", flow_class_mock)

    creds_file = tmp_path / "credentials.json"
    creds_file.write_text('{"installed": {}}', encoding="utf-8")

    result = google_oauth.get_credentials(
        credentials_path=creds_file, token_cache_path=token, scopes=SCOPES
    )
    assert result is new_creds
    flow_class_mock.from_client_secrets_file.assert_called_once()
    assert json.loads(token.read_text())["token"] == "from-flow"


def test_env_var_credentials_used_when_path_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Se credentials_path è None ma env var punta a un file valido → usa quello."""
    env_creds = tmp_path / "from_env.json"
    env_creds.write_text('{"installed": {}}', encoding="utf-8")
    monkeypatch.setenv("CUSTODIA_GOOGLE_CREDENTIALS_JSON", str(env_creds))

    resolved = google_oauth._resolve_credentials_path(None)
    assert resolved == env_creds


# ---------------------------------------------------------------------------
# Nuovi test: hardening (FIX A13 chmod 600, A14 headless, A15 refresh fail)
# ---------------------------------------------------------------------------


def test_token_cache_written_with_mode_600(
    tmp_path: Path, fake_creds_class: type, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FIX A13: dopo la scrittura, il token cache ha permessi 0o600.

    Solo significativo su sistemi POSIX (Linux/macOS). Su Windows skippato.
    """
    import sys

    if sys.platform == "win32":
        pytest.skip("permessi POSIX non significativi su Windows")

    token = tmp_path / "subdir" / "google_token.json"  # forza creazione dir padre
    # Token cache esiste già (skipperemmo il flow) → simuliamo refresh OK.
    token.parent.mkdir(parents=True, exist_ok=True)
    _write_token(token, expired=True, has_refresh=True)
    monkeypatch.setattr(google_oauth, "Request", MagicMock)

    google_oauth.get_credentials(
        credentials_path=None, token_cache_path=token, scopes=SCOPES
    )

    mode = oct(token.stat().st_mode)[-3:]
    assert mode == "600", f"atteso 0o600, ottenuto 0o{mode}"


def test_token_cache_parent_dir_created_with_mode_700(
    tmp_path: Path, fake_creds_class: type, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FIX A13: la directory padre del token cache viene creata con 0o700."""
    import sys

    if sys.platform == "win32":
        pytest.skip("permessi POSIX non significativi su Windows")

    parent = tmp_path / "new_state_dir"
    token = parent / "google_token.json"
    assert not parent.exists()

    # Simuliamo il flow path: nessun token esistente → flow interattivo.
    new_creds = SimpleNamespace(
        valid=True,
        to_json=lambda: json.dumps({"token": "fresh"}),
    )
    flow_instance = MagicMock()
    flow_instance.run_local_server.return_value = new_creds
    flow_class_mock = MagicMock()
    flow_class_mock.from_client_secrets_file.return_value = flow_instance
    monkeypatch.setattr(google_oauth, "InstalledAppFlow", flow_class_mock)
    # Garantisce che il check headless passi (impostiamo DISPLAY per Linux).
    monkeypatch.setenv("DISPLAY", ":0")

    creds_file = tmp_path / "credentials.json"
    creds_file.write_text('{"installed": {}}', encoding="utf-8")

    google_oauth.get_credentials(
        credentials_path=creds_file, token_cache_path=token, scopes=SCOPES
    )

    assert parent.is_dir()
    parent_mode = oct(parent.stat().st_mode)[-3:]
    assert parent_mode == "700", f"atteso 0o700 su dir padre, ottenuto 0o{parent_mode}"


def test_headless_environment_raises_helpful_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FIX A14: in ambiente Linux senza DISPLAY/WAYLAND_DISPLAY, il flow
    interattivo solleva ``RuntimeError`` con istruzioni chiare prima di
    bloccarsi su un server di callback senza browser.
    """
    # Simuliamo Linux senza display.
    monkeypatch.setattr("sys.platform", "linux")
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)

    token = tmp_path / "no_token.json"  # non esiste → forza flow
    creds_file = tmp_path / "credentials.json"
    creds_file.write_text('{"installed": {}}', encoding="utf-8")

    # InstalledAppFlow non deve essere chiamato — fail prima.
    flow_class_mock = MagicMock()
    monkeypatch.setattr(google_oauth, "InstalledAppFlow", flow_class_mock)

    with pytest.raises(RuntimeError, match="browser"):
        google_oauth.get_credentials(
            credentials_path=creds_file,
            token_cache_path=token,
            scopes=SCOPES,
        )
    flow_class_mock.from_client_secrets_file.assert_not_called()


def test_macos_does_not_require_display(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FIX A14: su macOS il check headless è bypassato (browser sempre disponibile)."""
    monkeypatch.setattr("sys.platform", "darwin")
    monkeypatch.delenv("DISPLAY", raising=False)
    # Il check non deve sollevare nulla.
    google_oauth._ensure_browser_available()


def test_refresh_failure_without_credentials_file_raises_helpful_error(
    tmp_path: Path, fake_creds_class: type, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FIX A15: se il token è scaduto e il refresh fallisce, ma non abbiamo
    né ``credentials_path`` valido né env var, l'errore guida l'utente.
    """
    from google.auth.exceptions import RefreshError

    monkeypatch.delenv("CUSTODIA_GOOGLE_CREDENTIALS_JSON", raising=False)

    token = tmp_path / "google_token.json"
    _write_token(token, expired=True, has_refresh=True)

    class _FailingCreds(fake_creds_class):  # type: ignore[misc, valid-type]
        def refresh(self, _request: object) -> None:
            raise RefreshError("token revocato")

    monkeypatch.setattr(google_oauth, "Credentials", _FailingCreds)
    monkeypatch.setattr(google_oauth, "Request", MagicMock)
    # Assicuriamoci che il check headless non sia il primo a fallire.
    monkeypatch.setattr("sys.platform", "darwin")

    # credentials_path = None e env var assente → RuntimeError con stringa chiara.
    with pytest.raises(RuntimeError, match="CUSTODIA_GOOGLE_CREDENTIALS_JSON"):
        google_oauth.get_credentials(
            credentials_path=None,
            token_cache_path=token,
            scopes=SCOPES,
        )
