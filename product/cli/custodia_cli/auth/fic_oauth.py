"""
OAuth 2.0 Authorization Code + PKCE flow per Fatture in Cloud (FIC v2).

Strategia (sister modulo di ``microsoft_oauth.py``, ma stack manuale invece di
MSAL perché FIC non ha un SDK ufficiale Python).

Flow:
1. Primo run: generiamo ``code_verifier`` random (64 byte URL-safe) e
   ``code_challenge = base64url(SHA256(code_verifier))``. Apriamo il browser
   sull'authorize endpoint con ``response_type=code, code_challenge=...``,
   avviamo un HTTP server locale su porta random (``socketserver.TCPServer((host, 0), ...)``)
   che cattura il ``code`` redirectato a ``http://localhost:<port>/callback``.
   Scambiamo poi ``code`` → ``access_token + refresh_token`` via
   ``POST /oauth/token``.
2. Run successivi: leggiamo token cache. Se ``access_token`` non scaduto
   ritorniamo. Se scaduto e ``refresh_token`` presente, refresh trasparente
   via ``grant_type=refresh_token``. Se anche il refresh fallisce → ri-lanciamo
   il flow interattivo.

Token cache:
- File JSON ``{access_token, refresh_token, expires_at, scopes, client_id}``
- Permessi ``0o600``, parent dir ``0o700``.

Credentials JSON (formato atteso)::

    {
      "client_id": "...",
      "client_secret": null,
      "redirect_uri_port": 0
    }

- ``client_secret``: opzionale (FIC public client PKCE non lo richiede).
- ``redirect_uri_port``: ``0`` = porta random, altrimenti forza una porta
  specifica (es. ``8765``). Utile se hai registrato un redirect_uri statico
  in console FIC.

Env var fallback: ``CUSTODIA_FIC_CREDENTIALS_JSON``.

Sicurezza:
- ``access_token``, ``refresh_token`` MAI loggati in clear.
- Token cache chmod ``0o600`` (parent ``0o700``).
- Ambiente headless (Linux senza ``$DISPLAY``) → ``RuntimeError`` italiano.

NOTE: la struttura di authorize/token endpoint segue il pattern documentato
per le API v2 di Fatture in Cloud. Va verificata al primo dogfood reale —
campi ``expires_in``, ``token_type``, ``scope`` sono standard OAuth2 e
dovrebbero combaciare.
"""

from __future__ import annotations

import base64
import hashlib
import http.server
import json
import logging
import os
import secrets
import socketserver
import sys
import threading
import time
import urllib.parse
import webbrowser
from pathlib import Path
from typing import Any

import requests

logger = logging.getLogger(__name__)


AUTHORIZE_URL = "https://api-v2.fattureincloud.it/oauth/authorize"
TOKEN_URL = "https://api-v2.fattureincloud.it/oauth/token"

# Margine di sicurezza: consideriamo scaduto un token che scade fra <60s,
# così evitiamo race condition tra "valido al check" e "scaduto alla request".
_EXPIRY_MARGIN_SECONDS = 60


# ---------------------------------------------------------------------------
# Credentials loading
# ---------------------------------------------------------------------------


def _resolve_credentials_path(credentials_path: Path | None) -> Path:
    """Determina il path al credentials JSON, con fallback su env var."""
    if credentials_path is not None and credentials_path.exists():
        return credentials_path

    env_value = os.environ.get("CUSTODIA_FIC_CREDENTIALS_JSON")
    if env_value:
        env_path = Path(env_value).expanduser()
        if env_path.exists():
            return env_path

    raise RuntimeError(
        "Credentials Fatture in Cloud non trovate. Passa --credentials PATH o "
        "imposta la env var CUSTODIA_FIC_CREDENTIALS_JSON con il path al file "
        "JSON contenente client_id (FIC Dev Console → OAuth App)."
    )


def _load_client_config(credentials_path: Path) -> dict[str, Any]:
    """Carica e valida il credentials JSON.

    Ritorna dict con ``client_id`` (str), ``client_secret`` (str | None),
    ``redirect_uri_port`` (int, default 0).
    """
    try:
        data = json.loads(credentials_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(
            f"Credentials FIC illeggibili ({credentials_path}): {exc}"
        ) from exc

    if not isinstance(data, dict):
        raise RuntimeError(
            f"Credentials FIC non valide ({credentials_path}): atteso oggetto "
            f"JSON, ottenuto {type(data).__name__}."
        )

    client_id = data.get("client_id")
    if not isinstance(client_id, str) or not client_id:
        raise RuntimeError(
            f"Credentials FIC mancanti del campo 'client_id' ({credentials_path})."
        )

    client_secret = data.get("client_secret")
    if client_secret is not None and not isinstance(client_secret, str):
        raise RuntimeError(
            f"Credentials FIC: client_secret deve essere stringa o null "
            f"({credentials_path})."
        )

    port_raw = data.get("redirect_uri_port", 0)
    if not isinstance(port_raw, int) or port_raw < 0 or port_raw > 65535:
        raise RuntimeError(
            f"Credentials FIC: redirect_uri_port deve essere int 0-65535 "
            f"({credentials_path})."
        )

    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri_port": port_raw,
    }


# ---------------------------------------------------------------------------
# Browser / headless guard
# ---------------------------------------------------------------------------


def _ensure_browser_available() -> None:
    """Solleva ``RuntimeError`` se l'ambiente non può aprire un browser."""
    if sys.platform in ("darwin", "win32"):
        return
    if os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"):
        return
    raise RuntimeError(
        "Il flow OAuth Fatture in Cloud richiede un browser interattivo. "
        "Esegui dal Mac/Windows con browser, oppure pre-genera il token su "
        "una macchina con browser e copia il file `fic_token.json` nello "
        "state_dir di Custodia."
    )


# ---------------------------------------------------------------------------
# Token cache I/O
# ---------------------------------------------------------------------------


def _persist_token_cache(token_cache_path: Path, payload: dict[str, Any]) -> None:
    """Persiste il token cache su disco con permessi restrittivi (0o600).

    Usa ``os.open(O_CREAT|O_TRUNC|O_WRONLY, mode=0o600)`` per evitare la
    finestra TOCTOU che avrebbe ``write_text`` + ``chmod`` successivo: un
    processo concorrente potrebbe leggere il file mentre è ancora a 0o644.
    Su Windows ``os.open`` ignora i bits POSIX, ma la sequenza resta sicura.
    """
    parent = token_cache_path.parent
    if not parent.exists():
        parent.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(parent, 0o700)
        except OSError as exc:  # pragma: no cover — best effort
            logger.debug("Impossibile chmod 0o700 su %s: %s", parent, exc)

    content = json.dumps(payload, ensure_ascii=False)
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
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(content)

    # Re-applica esplicitamente i permessi: la umask può intercettare i bits
    # passati a ``os.open`` su alcune piattaforme. Idempotente e safe.
    try:
        os.chmod(token_cache_path, 0o600)
    except OSError as exc:  # pragma: no cover — best effort
        logger.warning(
            "⚠️  Impossibile impostare permessi 0o600 su %s: %s",
            token_cache_path,
            exc,
        )


def _load_token_cache(token_cache_path: Path) -> dict[str, Any] | None:
    """Carica un token cache esistente. Ritorna None se assente/illeggibile."""
    if not token_cache_path.exists():
        return None
    try:
        data = json.loads(token_cache_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning(
            "⚠️  Token cache FIC illeggibile (%s), rilancio il flow.", exc
        )
        return None
    if not isinstance(data, dict):
        return None
    return data


def _is_token_valid(cache: dict[str, Any]) -> bool:
    """True se ``cache`` ha un access_token non scaduto (margine 60s)."""
    access = cache.get("access_token")
    expires_at = cache.get("expires_at")
    if not isinstance(access, str) or not access:
        return False
    if not isinstance(expires_at, (int, float)):
        return False
    return float(expires_at) > (time.time() + _EXPIRY_MARGIN_SECONDS)


# ---------------------------------------------------------------------------
# PKCE helpers
# ---------------------------------------------------------------------------


def _generate_pkce_pair() -> tuple[str, str]:
    """Genera ``(code_verifier, code_challenge)`` per PKCE S256.

    ``code_verifier``: 64 byte random URL-safe (~86 char base64url).
    ``code_challenge``: base64url(SHA256(code_verifier)).
    """
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


# ---------------------------------------------------------------------------
# Local callback HTTP server
# ---------------------------------------------------------------------------


def _make_callback_handler_class(
    captured: dict[str, str],
) -> type[http.server.BaseHTTPRequestHandler]:
    """Factory che crea un handler-class per-invocazione.

    FIX OA-4: il vecchio ``_CallbackHandler.captured`` era un attributo di
    classe (mutable shared state) — due flow concorrenti nello stesso processo
    avrebbero corrotto reciprocamente lo stato. Qui ``captured`` è un dict
    locale catturato in closure, quindi ogni chiamata ha il proprio storage.
    """

    class _Handler(http.server.BaseHTTPRequestHandler):
        """Handler che cattura il ``code`` dal redirect OAuth."""

        def do_GET(self) -> None:  # noqa: N802 — nome imposto dall'API
            parsed = urllib.parse.urlparse(self.path)
            params = dict(urllib.parse.parse_qsl(parsed.query))
            if "code" in params:
                captured["code"] = params["code"]
                # ``state`` deve sempre essere registrato (anche vuoto) così
                # il validator a monte può distinguere "assente" da "diverso".
                captured["state"] = params.get("state", "")
                body = (
                    "<html><body><h2>✓ Autenticazione completata</h2>"
                    "<p>Puoi chiudere questa scheda e tornare a Custodia.</p>"
                    "</body></html>"
                )
                self.send_response(200)
            elif "error" in params:
                captured["error"] = params.get("error", "unknown")
                captured["error_description"] = params.get(
                    "error_description", ""
                )
                body = (
                    f"<html><body><h2>✗ Errore OAuth</h2>"
                    f"<p>{params.get('error', 'unknown')}</p></body></html>"
                )
                self.send_response(400)
            else:
                body = "<html><body><h2>Richiesta non valida</h2></body></html>"
                self.send_response(400)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(body.encode("utf-8"))

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            """Silenzia il logging di default (stdout) — usiamo logger custom."""
            logger.debug("callback HTTP: " + format, *args)

    return _Handler


def _start_callback_server(
    requested_port: int,
) -> tuple[socketserver.TCPServer, int, dict[str, str]]:
    """Apre subito il TCPServer e ritorna ``(server, port, captured)``.

    FIX OA-3: niente probe socket + close + ribind (TOCTOU che permetteva ad
    un altro processo di rubare la porta nella finestra). Bindiamo direttamente
    il TCPServer (con ``port=0`` lasciamo che sia l'OS a scegliere), poi
    leggiamo ``server.server_address[1]`` per il port effettivo. Il chiamante
    costruisce ``redirect_uri`` DOPO il bind, garantendo che la porta nel
    redirect sia esattamente quella in ascolto.

    Args:
        requested_port: ``0`` = porta scelta dall'OS; ``>0`` = forza la porta.

    Returns:
        Tupla ``(httpd, chosen_port, captured_dict)``. ``captured_dict`` è
        passato in closure al handler-class restituito dalla factory.
    """
    captured: dict[str, str] = {}
    handler_class = _make_callback_handler_class(captured)
    # Bind diretto su 127.0.0.1 (loopback) — non "localhost", per evitare
    # risoluzioni DNS spurie su sistemi con /etc/hosts personalizzato.
    httpd = socketserver.TCPServer(("127.0.0.1", requested_port), handler_class)
    chosen_port = httpd.server_address[1]
    logger.debug("Callback server in ascolto su 127.0.0.1:%d", chosen_port)
    return httpd, chosen_port, captured


def _capture_authorization_code(
    httpd: socketserver.TCPServer,
    captured: dict[str, str],
    expected_state: str,
    *,
    timeout_seconds: int = 300,
) -> dict[str, str]:
    """Attende la callback OAuth sul server già avviato e valida lo state.

    Args:
        httpd: server creato da ``_start_callback_server`` (già in bind).
        captured: dict condiviso col handler-class via closure.
        expected_state: state token atteso. Confronto strict — niente
            ``if x and x != y``, perché ``state assente`` deve fallire.
        timeout_seconds: timeout totale per la callback.

    Returns:
        Dict con ``code`` e ``state`` se successo, o ``error``/``error_description``.

    Raises:
        RuntimeError: timeout (nessuna callback ricevuta).
    """
    stop_event = threading.Event()

    def _serve() -> None:
        while not stop_event.is_set() and "code" not in captured \
                and "error" not in captured:
            try:
                httpd.handle_request()
            except Exception:  # noqa: BLE001 — server_close interrompe handle_request
                break

    thread = threading.Thread(target=_serve, daemon=True)
    thread.start()

    deadline = time.time() + timeout_seconds
    try:
        while time.time() < deadline:
            if "code" in captured or "error" in captured:
                break
            time.sleep(0.1)
    finally:
        stop_event.set()
        try:
            httpd.server_close()
        except Exception:  # noqa: BLE001 — best effort
            pass

    if "code" not in captured and "error" not in captured:
        raise RuntimeError(
            f"Timeout ({timeout_seconds}s) in attesa della callback OAuth FIC. "
            "Il browser non ha completato il redirect."
        )
    return dict(captured)


# ---------------------------------------------------------------------------
# Token exchange / refresh
# ---------------------------------------------------------------------------


def _exchange_code_for_token(
    *,
    code: str,
    code_verifier: str,
    client_id: str,
    client_secret: str | None,
    redirect_uri: str,
    session: requests.Session,
) -> dict[str, Any]:
    """Scambia authorization code → access/refresh token via POST /oauth/token."""
    payload: dict[str, str] = {
        "grant_type": "authorization_code",
        "code": code,
        "code_verifier": code_verifier,
        "client_id": client_id,
        "redirect_uri": redirect_uri,
    }
    if client_secret:
        payload["client_secret"] = client_secret

    response = session.post(TOKEN_URL, data=payload, timeout=30)
    if response.status_code >= 400:
        # NB: NON includere il body nei messaggi user-visible (potrebbe contenere
        # error_description con dettagli sensibili in alcuni provider). Logghiamo
        # solo lo status code.
        raise RuntimeError(
            f"Token exchange FIC fallito: HTTP {response.status_code}."
        )
    return response.json()


def _refresh_access_token(
    *,
    refresh_token: str,
    client_id: str,
    client_secret: str | None,
    session: requests.Session,
) -> dict[str, Any]:
    """Esegue refresh del token via ``grant_type=refresh_token``."""
    payload: dict[str, str] = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": client_id,
    }
    if client_secret:
        payload["client_secret"] = client_secret

    response = session.post(TOKEN_URL, data=payload, timeout=30)
    if response.status_code >= 400:
        raise RuntimeError(
            f"Refresh token FIC fallito: HTTP {response.status_code}."
        )
    return response.json()


def _normalize_token_response(
    response: dict[str, Any], *, scopes: list[str], client_id: str
) -> dict[str, Any]:
    """Trasforma la response del token endpoint in payload cacheable.

    Calcola ``expires_at`` da ``expires_in`` (Unix epoch). Preserva
    ``refresh_token`` esistente se la nuova response non lo ridà (alcuni
    server lo riemettono solo al primo grant).
    """
    access_token = response.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        raise RuntimeError("Token response FIC senza access_token valido.")

    expires_in = response.get("expires_in", 3600)
    try:
        expires_in_int = int(expires_in)
    except (TypeError, ValueError):
        expires_in_int = 3600

    return {
        "access_token": access_token,
        "refresh_token": response.get("refresh_token"),
        "expires_at": time.time() + expires_in_int,
        "scopes": scopes,
        "client_id": client_id,
        "token_type": response.get("token_type", "Bearer"),
    }


# ---------------------------------------------------------------------------
# Interactive flow
# ---------------------------------------------------------------------------


def _run_interactive_flow(
    *,
    config: dict[str, Any],
    scopes: list[str],
    session: requests.Session,
) -> dict[str, Any]:
    """Esegue il full Authorization Code + PKCE flow. Ritorna payload cacheable.

    Sequence (security-critical):
    1. ``_start_callback_server`` bindi subito la porta — niente probe+rebind.
    2. Costruiamo ``redirect_uri`` DOPO il bind, con ``127.0.0.1`` (RFC 8252).
    3. Apriamo il browser.
    4. Aspettiamo la callback con timeout.
    5. Validiamo lo state STRICT (assente o diverso → CSRF).
    """
    _ensure_browser_available()

    code_verifier, code_challenge = _generate_pkce_pair()
    state = secrets.token_urlsafe(16)
    requested_port = int(config["redirect_uri_port"])

    # FIX OA-3: bind diretto, niente probe TOCTOU. Il server resta in
    # ascolto sulla porta scelta finché _capture_authorization_code non lo
    # chiude (via server_close in finally).
    httpd, chosen_port, captured = _start_callback_server(requested_port)

    # FIX OA-5: 127.0.0.1 esplicito (RFC 8252 §7.3) — niente "localhost"
    # che potrebbe risolvere ad ::1 o ad altro su /etc/hosts custom.
    redirect_uri = f"http://127.0.0.1:{chosen_port}/callback"

    authorize_params = {
        "response_type": "code",
        "client_id": config["client_id"],
        "redirect_uri": redirect_uri,
        "scope": " ".join(scopes),
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    authorize_url = f"{AUTHORIZE_URL}?{urllib.parse.urlencode(authorize_params)}"

    logger.info("🔐 Avvio flow OAuth interattivo Fatture in Cloud (browser)...")
    webbrowser.open(authorize_url)

    received = _capture_authorization_code(
        httpd, captured, expected_state=state
    )

    if "error" in received:
        raise RuntimeError(
            f"OAuth FIC errore: {received.get('error')} — "
            f"{received.get('error_description', '')}"
        )

    # FIX OA-1: validazione state strict. Il vecchio
    # ``if received_state and received_state != state`` permetteva bypass
    # se il provider ometteva ``state`` nel redirect (received_state falsy).
    # Confronto strict: assente → mismatch → CSRF.
    received_state = received.get("state")
    if received_state != state:
        raise RuntimeError(
            "State mismatch nel callback OAuth FIC (possibile CSRF). "
            "Riprova l'autenticazione."
        )

    code = received["code"]
    response = _exchange_code_for_token(
        code=code,
        code_verifier=code_verifier,
        client_id=config["client_id"],
        client_secret=config["client_secret"],
        redirect_uri=redirect_uri,
        session=session,
    )
    return _normalize_token_response(
        response, scopes=scopes, client_id=config["client_id"]
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_fic_access_token(
    credentials_path: Path | None,
    token_cache_path: Path,
    scopes: list[str],
    *,
    session: requests.Session | None = None,
) -> str:
    """Ritorna access_token FIC valido (refresh trasparente, flow se necessario).

    Args:
        credentials_path: path al credentials JSON. Può essere ``None`` se
            l'env ``CUSTODIA_FIC_CREDENTIALS_JSON`` è settata.
        token_cache_path: dove salvare/leggere il token cache.
            Tipicamente ``<state_dir>/fic_token.json``.
        scopes: lista di scope FIC (es.
            ``["entity.clients:r", "entity.suppliers:r", "issued_documents:r"]``).
        session: ``requests.Session`` da iniettare (testing).

    Returns:
        ``access_token`` stringa, pronto per ``Authorization: Bearer ...``.

    Raises:
        RuntimeError: se credentials non risolvibili, ambiente headless, o se
            tutti i tentativi (silent + interactive) falliscono.
    """
    resolved_creds = _resolve_credentials_path(credentials_path)
    config = _load_client_config(resolved_creds)
    sess = session or requests.Session()

    # Step 1: cache valido?
    cache = _load_token_cache(token_cache_path)
    if cache is not None and _is_token_valid(cache):
        return str(cache["access_token"])

    # Step 2: refresh trasparente se disponibile.
    if cache is not None and isinstance(cache.get("refresh_token"), str):
        try:
            response = _refresh_access_token(
                refresh_token=cache["refresh_token"],
                client_id=config["client_id"],
                client_secret=config["client_secret"],
                session=sess,
            )
            normalized = _normalize_token_response(
                response, scopes=scopes, client_id=config["client_id"]
            )
            # Se refresh response NON ha rifatto un refresh_token, preserva il
            # precedente (alcuni provider lo emettono one-shot).
            if not normalized.get("refresh_token"):
                normalized["refresh_token"] = cache["refresh_token"]
            _persist_token_cache(token_cache_path, normalized)
            return str(normalized["access_token"])
        except Exception as exc:  # noqa: BLE001
            # Refresh fallito (refresh_token revocato/scaduto/...). Log
            # diagnostico (senza token in clear) e fallback a flow interattivo.
            logger.warning(
                "⚠️  Refresh token FIC fallito (%s): %s — rilancio il flow.",
                type(exc).__name__,
                exc,
            )

    # Step 3: flow interattivo completo.
    normalized = _run_interactive_flow(config=config, scopes=scopes, session=sess)
    _persist_token_cache(token_cache_path, normalized)
    return str(normalized["access_token"])


__all__ = [
    "get_fic_access_token",
    "AUTHORIZE_URL",
    "TOKEN_URL",
]
