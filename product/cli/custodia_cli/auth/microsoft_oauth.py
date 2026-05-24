"""
OAuth 2.0 desktop flow per Microsoft Graph (Outlook 365).

Strategia (replica del pattern Google in ``google_oauth.py``):
- Primo run: ``msal.PublicClientApplication.acquire_token_interactive`` apre
  browser → login Microsoft → consent → callback su ``http://localhost``
  → token salvato in ``<state_dir>/microsoft_token.json``.
- Run successivi: token cache caricato; refresh trasparente via
  ``acquire_token_silent``.
- Se entrambi falliscono → ri-lanciamo il flow interattivo.

Config client OAuth (``credentials.json``) può essere passato:
- via parametro ``credentials_path``
- in alternativa via env ``CUSTODIA_MICROSOFT_CREDENTIALS_JSON``

Formato atteso del JSON::

    {
      "client_id": "...",
      "tenant_id": "common",
      "authority": "https://login.microsoftonline.com/common"
    }

``tenant_id``/``authority`` sono opzionali; default ``"common"`` (supporta sia
account work/school che personal).

Sicurezza:
- Token cache (con refresh-token) scritto con permessi ``0o600``, dentro
  directory ``0o700``.
- Ambiente headless (Linux senza ``$DISPLAY``/``$WAYLAND_DISPLAY``) →
  ``RuntimeError`` con istruzioni prima di tentare il browser.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

import msal
from rich.console import Console

logger = logging.getLogger(__name__)

# Console Rich condivisa per messaggi user-visible (account selezionato, ecc.).
_console = Console()

DEFAULT_AUTHORITY = "https://login.microsoftonline.com/common"

# Timeout di default per ``acquire_token_interactive`` (secondi). Senza timeout
# il flow si bloccherebbe indefinitamente se l'utente non completa il consent
# nel browser. 5 minuti è un compromesso ragionevole.
_DEFAULT_INTERACTIVE_TIMEOUT = 300


def _resolve_credentials_path(credentials_path: Path | None) -> Path:
    """Determina il path al credentials JSON, con fallback su env var."""
    if credentials_path is not None and credentials_path.exists():
        return credentials_path

    env_value = os.environ.get("CUSTODIA_MICROSOFT_CREDENTIALS_JSON")
    if env_value:
        env_path = Path(env_value).expanduser()
        if env_path.exists():
            return env_path

    raise RuntimeError(
        "Credentials Microsoft OAuth non trovate. Passa --credentials PATH o "
        "imposta la env var CUSTODIA_MICROSOFT_CREDENTIALS_JSON con il path "
        "al file JSON contenente client_id e tenant_id (Azure AD App "
        "Registration → Authentication → Mobile and desktop applications)."
    )


def _ensure_browser_available() -> None:
    """Solleva ``RuntimeError`` se l'ambiente non può aprire un browser.

    Stesso pattern di ``google_oauth._ensure_browser_available``: su Linux
    senza display il flow interattivo si bloccherebbe in attesa di una
    callback che non arriverà mai.
    """
    if sys.platform in ("darwin", "win32"):
        return
    if os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"):
        return
    raise RuntimeError(
        "Il flow OAuth Microsoft richiede un browser interattivo. Esegui dal "
        "Mac/Windows con browser, oppure pre-genera il token su una macchina "
        "con browser e copia il file `microsoft_token.json` nello state_dir "
        "di Custodia."
    )


def _load_client_config(credentials_path: Path) -> dict[str, str]:
    """Carica e valida il credentials JSON.

    Ritorna dict con almeno ``client_id`` e ``authority``. ``tenant_id`` viene
    usato per costruire authority se non presente esplicitamente.
    """
    try:
        data = json.loads(credentials_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(
            f"Credentials Microsoft illeggibili ({credentials_path}): {exc}"
        ) from exc

    if not isinstance(data, dict):
        raise RuntimeError(
            f"Credentials Microsoft non valide ({credentials_path}): "
            f"atteso oggetto JSON, ottenuto {type(data).__name__}."
        )

    client_id = data.get("client_id")
    if not isinstance(client_id, str) or not client_id:
        raise RuntimeError(
            f"Credentials Microsoft mancanti del campo 'client_id' "
            f"({credentials_path})."
        )

    authority = data.get("authority")
    if not isinstance(authority, str) or not authority:
        tenant_id = data.get("tenant_id") or "common"
        authority = f"https://login.microsoftonline.com/{tenant_id}"

    return {"client_id": client_id, "authority": authority}


def _persist_cache(token_cache_path: Path, cache: msal.SerializableTokenCache) -> None:
    """Persiste il token cache su disco con permessi restrittivi (0o600).

    Usa ``os.open(O_CREAT|O_TRUNC|O_WRONLY, mode=0o600)`` per evitare la
    finestra TOCTOU che avrebbe ``write_text`` + ``chmod`` successivo (un
    processo concorrente potrebbe leggere il file mentre è ancora a 0o644).
    Su Windows ``os.open`` ignora i bits POSIX ma la chiamata resta sicura.
    """
    parent = token_cache_path.parent
    if not parent.exists():
        parent.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(parent, 0o700)
        except OSError as exc:  # pragma: no cover — best effort
            logger.debug("Impossibile chmod 0o700 su %s: %s", parent, exc)

    content = cache.serialize()
    try:
        fd = os.open(
            str(token_cache_path),
            os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
            0o600,
        )
    except OSError as exc:
        raise RuntimeError(
            f"Impossibile creare token cache {token_cache_path}: {exc}"
        ) from exc
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception:
        # ``os.fdopen`` consuma fd anche in caso di errore di write: nessun
        # close manuale necessario qui.
        raise

    # Re-applica esplicitamente i permessi: su alcune piattaforme la umask
    # può intercettare i bits passati a ``os.open``. È idempotente e safe.
    try:
        os.chmod(token_cache_path, 0o600)
    except OSError as exc:  # pragma: no cover — best effort
        logger.warning(
            "⚠️  Impossibile impostare permessi 0o600 su %s: %s",
            token_cache_path,
            exc,
        )


def _load_cache(token_cache_path: Path) -> msal.SerializableTokenCache:
    """Carica un token cache esistente o ne crea uno vuoto."""
    cache = msal.SerializableTokenCache()
    if token_cache_path.exists():
        try:
            cache.deserialize(token_cache_path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "⚠️  Token cache Microsoft illeggibile (%s), rilancio il flow.",
                exc,
            )
    return cache


def _build_app(
    credentials_path: Path, cache: msal.SerializableTokenCache
) -> msal.PublicClientApplication:
    """Costruisce ``PublicClientApplication`` con cache iniettata."""
    config = _load_client_config(credentials_path)
    return msal.PublicClientApplication(
        client_id=config["client_id"],
        authority=config["authority"],
        token_cache=cache,
    )


def _extract_account_username(result: dict[str, Any]) -> str | None:
    """Estrae lo username (UPN/email) dal token result MSAL, se disponibile.

    MSAL espone l'identità via ``id_token_claims.preferred_username`` oppure
    via ``account.username``. Usato solo per logging — mai per autorizzazione.
    """
    claims = result.get("id_token_claims")
    if isinstance(claims, dict):
        username = claims.get("preferred_username") or claims.get("upn")
        if isinstance(username, str) and username:
            return username
    account = result.get("account")
    if isinstance(account, dict):
        username = account.get("username")
        if isinstance(username, str) and username:
            return username
    return None


def get_access_token(
    credentials_path: Path | None,
    token_cache_path: Path,
    scopes: list[str],
    *,
    timeout: int = _DEFAULT_INTERACTIVE_TIMEOUT,
) -> str:
    """Ottiene un access token Microsoft Graph valido, ri-usando cache locale.

    Args:
        credentials_path: path al credentials JSON (può essere None se fornito
            via env ``CUSTODIA_MICROSOFT_CREDENTIALS_JSON``).
        token_cache_path: dove salvare/leggere il token cache MSAL.
            Tipicamente ``<state_dir>/microsoft_token.json``.
        scopes: lista di scope Graph (es. ``["Mail.Read"]``). NON includere
            ``offline_access`` / ``openid`` / ``profile``: MSAL li aggiunge.
        timeout: timeout in secondi per il flow interattivo
            (``acquire_token_interactive``). Default 300s = 5 minuti.
            Senza timeout il processo si bloccherebbe se l'utente abbandona
            il browser senza completare il consent.

    Returns:
        ``access_token`` stringa, pronto per ``Authorization: Bearer ...``.

    Raises:
        RuntimeError: se credentials non risolvibili, ambiente headless, o se
            tutti i tentativi (silent + interactive) falliscono.

    Note (security):
        Dopo l'autenticazione, l'account selezionato (preferred_username) è
        stampato sulla console. Il consulente DEVE verificare che sia
        l'account corretto del cliente prima di procedere — un click sul
        wrong-account picker in Azure AD ruoterebbe altrimenti silenziosamente
        l'identità per le prossime chiamate Graph.
    """
    resolved_creds = _resolve_credentials_path(credentials_path)
    cache = _load_cache(token_cache_path)
    app = _build_app(resolved_creds, cache)

    # Step 1: prova silent (usa refresh token se presente).
    accounts = app.get_accounts()
    result: dict[str, Any] | None = None
    if accounts:
        result = app.acquire_token_silent(scopes, account=accounts[0])

    # Step 2: fallback flow interattivo.
    if not result or "access_token" not in result:
        _ensure_browser_available()
        logger.info("🔐 Avvio flow OAuth interattivo Microsoft (browser)...")
        # port=0 → MSAL sceglie porta libera. prompt="select_account" permette
        # di switchare account se il consulente ha più tenant.
        # ``timeout`` previene blocco indefinito se il consent viene abbandonato.
        result = app.acquire_token_interactive(
            scopes=scopes,
            prompt="select_account",
            port=0,
            timeout=timeout,
        )

    if not result or "access_token" not in result:
        error = (result or {}).get("error", "unknown_error")
        desc = (result or {}).get("error_description", "no description")
        raise RuntimeError(
            f"Microsoft OAuth fallito: {error} — {desc}. "
            f"Verifica client_id, tenant_id e scope nei credentials."
        )

    # Persisti cache solo se cambiata (MSAL flag).
    if cache.has_state_changed:
        _persist_cache(token_cache_path, cache)

    # Security: logga (sempre, anche su silent) l'account selezionato così il
    # consulente può accorgersi di un account swap accidentale. Non solleva
    # mai eccezioni — fail-open su side-effect di logging.
    username = _extract_account_username(result)
    if username:
        _console.print(
            f"[yellow]Account Microsoft autenticato: {username}[/yellow]"
        )
        _console.print(
            "[yellow]Verifica che sia l'account corretto del cliente prima "
            "di procedere.[/yellow]"
        )

    return str(result["access_token"])


__all__ = ["get_access_token", "DEFAULT_AUTHORITY"]
