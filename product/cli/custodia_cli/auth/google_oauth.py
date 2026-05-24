"""
OAuth 2.0 desktop flow per Google Drive (e altre API Google read-only).

Strategia (design doc D2.1):
- Il consulente esegue il CLI dal proprio Mac, browser disponibile.
- Primo run: si apre browser → login Google → consent → callback su
  ``http://localhost:<random_port>`` → token salvato in
  ``<state_dir>/google_token.json``.
- Run successivi: token cache caricato; se scaduto, refresh automatico.
- Se refresh fallisce o token assente, ri-lanciamo il flow interattivo.

File credentials del client OAuth (``credentials.json`` scaricato dalla Google
Cloud Console) può essere passato:
- via parametro ``credentials_path``
- in alternativa via env ``CUSTODIA_GOOGLE_CREDENTIALS_JSON``

Sicurezza:
- Il file token cache contiene refresh-token sensibili: viene scritto con
  permessi ``0o600`` (read/write solo owner) e dentro una directory ``0o700``.
- In ambiente headless (Linux senza ``$DISPLAY``) il flow interattivo non può
  partire: solleviamo ``RuntimeError`` con istruzioni chiare prima di tentare.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

logger = logging.getLogger(__name__)


def _resolve_credentials_path(credentials_path: Path | None) -> Path:
    """Determina il path al file OAuth client config, con fallback su env var."""
    if credentials_path is not None and credentials_path.exists():
        return credentials_path

    env_value = os.environ.get("CUSTODIA_GOOGLE_CREDENTIALS_JSON")
    if env_value:
        env_path = Path(env_value).expanduser()
        if env_path.exists():
            return env_path

    raise RuntimeError(
        "Credentials Google OAuth non trovate. Passa --credentials PATH o "
        "imposta la env var CUSTODIA_GOOGLE_CREDENTIALS_JSON con il path al "
        "file credentials.json scaricato dalla Google Cloud Console "
        "(OAuth 2.0 Client ID → Desktop application)."
    )


def _ensure_browser_available() -> None:
    """Solleva ``RuntimeError`` se l'ambiente non può aprire un browser.

    Su Linux senza ``$DISPLAY`` (es. SSH senza X11 forwarding, container)
    ``flow.run_local_server`` apre il browser via ``webbrowser`` modulo, che
    fallisce silenziosamente lasciando il server in attesa di una callback che
    non arriverà mai. Meglio fallire forte e suggerire l'alternativa.

    Su macOS e Windows il browser è sempre disponibile via API di sistema.
    """
    if sys.platform in ("darwin", "win32"):
        return
    # Su Linux/altri Unix richiediamo almeno una delle env var di display.
    if os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"):
        return
    raise RuntimeError(
        "Il flow OAuth richiede un browser interattivo. Esegui dal Mac/Windows "
        "con browser, oppure pre-genera il token su una macchina con browser "
        "e copia il file `google_token.json` nello state_dir di Custodia."
    )


def _persist_credentials(token_cache_path: Path, creds: Credentials) -> None:
    """Persiste le credentials su disco con permessi restrittivi (0o600).

    Crea anche la directory padre se mancante con permessi ``0o700``. Su Windows
    ``os.chmod`` ha effetti limitati ma la chiamata è sicura (no-op funzionale).
    """
    parent = token_cache_path.parent
    if not parent.exists():
        # ``mode`` su ``mkdir`` rispetta umask, quindi forziamo chmod dopo.
        parent.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(parent, 0o700)
        except OSError as exc:  # pragma: no cover — best effort
            logger.debug("Impossibile chmod 0o700 su %s: %s", parent, exc)

    token_cache_path.write_text(creds.to_json(), encoding="utf-8")
    try:
        os.chmod(token_cache_path, 0o600)
    except OSError as exc:  # pragma: no cover — best effort
        logger.warning(
            "⚠️  Impossibile impostare permessi 0o600 su %s: %s "
            "(il refresh-token resta protetto solo dai permessi di default).",
            token_cache_path,
            exc,
        )


def get_credentials(
    credentials_path: Path | None,
    token_cache_path: Path,
    scopes: list[str],
) -> Credentials:
    """Ottiene credentials Google valide, ri-usando cache locale se possibile.

    Args:
        credentials_path: path al ``credentials.json`` OAuth client (può essere
            None se fornito via env ``CUSTODIA_GOOGLE_CREDENTIALS_JSON``).
        token_cache_path: dove salvare/leggere il token utente (refresh token
            incluso). Tipicamente ``<state_dir>/google_token.json``.
        scopes: lista di scope OAuth (es. ``["https://.../drive.readonly"]``).

    Returns:
        Credentials autenticate e valide (post-refresh se necessario).

    Raises:
        RuntimeError: se ``credentials_path`` non trovato e env var non set,
            o se l'ambiente è headless e serve il flow interattivo.
    """
    creds: Credentials | None = None

    # Step 1: prova a riusare il token cache.
    if token_cache_path.exists():
        try:
            creds = Credentials.from_authorized_user_file(
                str(token_cache_path), scopes
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("⚠️  Token cache illeggibile (%s), rilancio il flow.", exc)
            creds = None

    # Step 2: refresh se scaduto ma rinnovabile.
    if creds is not None and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except RefreshError as exc:
            logger.warning("⚠️  Refresh token Google fallito (%s), rilancio il flow.", exc)
            creds = None

    # Step 3: se nessun credentials valido → flow interattivo.
    if creds is None or not creds.valid:
        # Pre-check: fallisci forte in ambiente headless prima di toccare il browser.
        _ensure_browser_available()
        client_config_path = _resolve_credentials_path(credentials_path)
        flow = InstalledAppFlow.from_client_secrets_file(
            str(client_config_path), scopes=scopes
        )
        # port=0 → assegna porta libera, evita conflitti.
        creds = flow.run_local_server(port=0)

    # Step 4: persisti la cache con permessi restrittivi (0o600).
    _persist_credentials(token_cache_path, creds)
    return creds


__all__ = ["get_credentials"]
