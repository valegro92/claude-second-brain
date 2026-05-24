"""
Connettore Fatture in Cloud (FIC) v2 read-only.

Sister del Outlook connector, ma sorgente è il software di fatturazione
elettronica FIC: scarichiamo clienti, fornitori e fatture emesse di una
``company_id``. L'extractor U5 esistente categorizzerà ogni
``SourceDocument`` correttamente (cliente / fornitore / fattura).

Pipeline per risorsa:
- Clienti: ``GET /c/{company_id}/entities/clients?page=N&per_page=100``
- Fornitori: ``GET /c/{company_id}/entities/suppliers?page=N&per_page=100``
- Fatture emesse: ``GET /c/{company_id}/issued_documents?type=invoice
  &date_after=YYYY-MM-DD&page=N&per_page=100``

Per ogni item produciamo 1 ``SourceDocument`` con ``text`` strutturato in
italiano (formato leggibile + parsable downstream).

Retry: 429 + 5xx con backoff esponenziale + jitter, cap 3 tentativi, rispetta
``Retry-After`` (cappato a 60s per evitare blocchi). Per-item errors isolati
(singolo item malformato → log + ``stats.errors += 1`` + continue).

Auth: ``Authorization: Bearer <access_token>`` via
``custodia_cli.auth.fic_oauth.get_fic_access_token``.

Uso preferito (context manager)::

    with FattureInCloudConnector(...) as conn:
        for doc in conn.iter_documents():
            store.add_document(...)

⚠️  NOTA SULLA SHAPE DEI CAMPI FIC v2:
La struttura dei field di response qui usata (``id, name, vat_number,
tax_code, address_*, email, phone, code`` per clienti/fornitori; ``id,
number, date, amount_net, amount_gross, entity, items`` per le fatture)
è basata sul pattern OpenAPI documentato. Va verificata al primo dogfood
reale: in caso di discrepanze i parser ``_build_client_doc`` /
``_build_invoice_doc`` vanno aggiornati di conseguenza. Gli alias di campo
(``items`` vs ``items_list``, ``qty`` vs ``quantity``, ecc.) emettono un
``logger.debug`` quando usati per facilitare la detection di drift.
"""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from types import TracebackType
from typing import Any, Iterator

import requests

from custodia_cli.auth.fic_oauth import get_fic_access_token
from custodia_cli.connectors._http import request_with_retry
from custodia_cli.connectors.base import (
    ConnectorAPIError,
    ConnectorAuthError,
    ConnectorRateLimitError,
    SourceDocument,
)

logger = logging.getLogger(__name__)

FIC_BASE_URL = "https://api-v2.fattureincloud.it"
FIC_SCOPES = [
    "entity.clients:r",
    "entity.suppliers:r",
    "issued_documents:r",
]

_PAGE_SIZE = 100
_RETRY_MAX_ATTEMPTS = 3
_RETRIABLE_STATUSES = frozenset({429, 500, 502, 503, 504})

# Cap massimo per Retry-After (vedi CN-1).
_RETRY_AFTER_MAX = 60.0

# Safety net per pagination loop / metadata bug del server.
_MAX_PAGES_PER_RESOURCE = 1000

_VALID_RESOURCES = ("clients", "suppliers", "invoices")
_DEFAULT_RESOURCES = list(_VALID_RESOURCES)


# ---------------------------------------------------------------------------
# Path / text formatting helpers
# ---------------------------------------------------------------------------


def _sanitize_for_path(value: str) -> str:
    """Trasforma una stringa in un nome safe per il filesystem virtuale."""
    return "".join(c if c.isalnum() or c in "._- " else "_" for c in value).strip() or "unnamed"


def _sanitize_id_for_filename(value: Any) -> str:
    """Sanitizza un id (es. ``fic_id``) per uso come nome file.

    Sostituisce qualsiasi cosa non sia ``\\w`` o ``-`` con ``_``. Previene
    path traversal (``..``, ``/``) e caratteri problematici su filesystem.
    """
    return re.sub(r"[^\w\-]", "_", str(value)) or "noid"


def _kv_line(label: str, value: Any) -> str | None:
    """Ritorna ``"label: value"`` se ``value`` non è vuoto, altrimenti None."""
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    return f"{label}: {s}"


def _format_address(entity: dict[str, Any]) -> str | None:
    """Combina i campi ``address_street/postal_code/city/province`` in una stringa.

    Ritorna None se tutti vuoti.
    """
    street = (entity.get("address_street") or "").strip()
    postal = (entity.get("address_postal_code") or "").strip()
    city = (entity.get("address_city") or "").strip()
    province = (entity.get("address_province") or "").strip()
    if not any((street, postal, city, province)):
        return None
    locality = " ".join(p for p in (postal, city) if p)
    parts: list[str] = []
    if street:
        parts.append(street)
    if locality or province:
        loc = locality
        if province:
            loc = f"{loc} ({province})" if loc else f"({province})"
        parts.append(loc)
    return ", ".join(parts)


def _amount(value: Any) -> str:
    """Formatta un importo numerico stile italiano: ``€ 1234.56``."""
    if value is None:
        return "0.00"
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return str(value)


def _alias_get(
    item: dict[str, Any],
    preferred: str,
    *aliases: str,
) -> Any:
    """Ritorna ``item[preferred]`` se non-None, altrimenti il primo alias non-None.

    Emette ``logger.debug`` quando si usa un alias per facilitare drift detection
    al primo dogfood reale dell'API FIC.
    """
    val = item.get(preferred)
    if val is not None:
        return val
    for alias in aliases:
        alt = item.get(alias)
        if alt is not None:
            logger.debug(
                "FIC field alias usato: '%s' (preferito: '%s')", alias, preferred
            )
            return alt
    return None


def _write_cache_json(cache_path: Path, payload: dict[str, Any]) -> None:
    """Scrive ``payload`` come JSON in ``cache_path`` con permessi 0o600.

    Pattern atomic via ``os.open`` (no finestra TOCTOU tra create e chmod).
    """
    parent = cache_path.parent
    parent.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(parent, 0o700)
    except OSError as exc:  # pragma: no cover — best effort
        logger.debug("Impossibile chmod 0o700 su %s: %s", parent, exc)
    fd = os.open(
        str(cache_path),
        os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
        0o600,
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False)
    except Exception:
        try:
            os.close(fd)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------------------
# Document builders
# ---------------------------------------------------------------------------


def _build_entity_doc(
    entity: dict[str, Any],
    *,
    kind: str,
    dry_run: bool,
) -> SourceDocument:
    """Costruisce un SourceDocument per cliente o fornitore.

    Args:
        entity: dict ritornato dall'API FIC.
        kind: ``"client"`` o ``"supplier"``.
    """
    entity_id = entity.get("id")
    if entity_id is None:
        raise ValueError("entity senza id")

    name = (entity.get("name") or "").strip() or f"<senza-nome-{entity_id}>"
    vat_number = entity.get("vat_number")
    tax_code = entity.get("tax_code")
    email = entity.get("email")
    phone = entity.get("phone")
    code = entity.get("code")
    notes = entity.get("notes")
    address = _format_address(entity)

    label_kind = "Cliente" if kind == "client" else "Fornitore"
    folder = "clienti" if kind == "client" else "fornitori"
    mime = (
        "application/vnd.custodia.fic-client"
        if kind == "client"
        else "application/vnd.custodia.fic-supplier"
    )

    lines: list[str] = [f"{label_kind}: {name}"]
    for lbl, val in (
        ("P.IVA", vat_number),
        ("Codice Fiscale", tax_code),
        ("Indirizzo", address),
        ("Email", email),
        ("Telefono", phone),
        ("Codice", code),
        ("Note", notes),
    ):
        line = _kv_line(lbl, val)
        if line is not None:
            lines.append(line)
    text = "" if dry_run else "\n".join(lines)

    source_id = f"fic:{kind}:{entity_id}"
    source_path = f"/FattureInCloud/{folder}/{_sanitize_for_path(name)}"

    metadata: dict[str, Any] = {
        "fic_id": entity_id,
        "name": name,
        "vat_number": vat_number,
        "tax_code": tax_code,
        "email": email,
        "phone": phone,
        "code": code,
        "type": kind,
    }

    return SourceDocument(
        source_id=source_id,
        source_path=source_path,
        mime_type=mime,
        text=text,
        metadata=metadata,
    )


def _build_invoice_doc(
    invoice: dict[str, Any],
    *,
    dry_run: bool,
) -> SourceDocument:
    """Costruisce un SourceDocument per una fattura emessa."""
    invoice_id = invoice.get("id")
    if invoice_id is None:
        raise ValueError("invoice senza id")

    # Aliasing con debug logging: `number` è il campo OpenAPI preferito;
    # `numeration` appare in alcune response legacy.
    number = _alias_get(invoice, "number", "numeration") or f"#{invoice_id}"
    date_str = str(invoice.get("date") or "")

    amount_net = invoice.get("amount_net")
    amount_vat = invoice.get("amount_vat")
    amount_gross = invoice.get("amount_gross")
    status_field = invoice.get("status")

    entity = invoice.get("entity") or {}
    entity_id = entity.get("id")
    entity_name = (entity.get("name") or "").strip() or f"<cliente-{entity_id}>"
    entity_vat = entity.get("vat_number")

    # `items_list` (preferred) vs `items` (legacy alias).
    items_raw = _alias_get(invoice, "items_list", "items") or []
    items: list[dict[str, Any]] = [
        item for item in items_raw if isinstance(item, dict)
    ]

    # Anno dalla data (per source_path /YYYY/...). Fallback "unknown".
    year = "unknown"
    if date_str and len(date_str) >= 4 and date_str[:4].isdigit():
        year = date_str[:4]

    header_lines = [
        f"Fattura n. {number} del {date_str or 'data sconosciuta'}",
        f"Cliente: {entity_name}"
        + (f" (P.IVA {entity_vat})" if entity_vat else ""),
        f"Importo netto: € {_amount(amount_net)}",
        f"IVA: € {_amount(amount_vat)}",
        f"Importo lordo: € {_amount(amount_gross)}",
    ]

    if items:
        header_lines.append("")
        header_lines.append("Voci:")
        for item in items:
            product_name = (
                item.get("product_name")
                or item.get("name")
                or item.get("description")
                or "<voce senza nome>"
            )
            qty = _alias_get(item, "qty", "quantity") or 1
            price = _alias_get(
                item, "net_price", "gross_price", "price"
            ) or 0
            header_lines.append(
                f"- {product_name} | qty: {qty} | prezzo: € {_amount(price)}"
            )

    text = "" if dry_run else "\n".join(header_lines)

    source_id = f"fic:invoice:{invoice_id}"
    sanitized_number = _sanitize_for_path(str(number))
    source_path = (
        f"/FattureInCloud/fatture-emesse/{year}/fattura-{sanitized_number}.txt"
    )

    metadata: dict[str, Any] = {
        "fic_id": invoice_id,
        "invoice_number": number,
        "invoice_date": date_str,
        "amount_net": amount_net,
        "amount_vat": amount_vat,
        "amount_gross": amount_gross,
        "entity_id": entity_id,
        "entity_name": entity_name,
        "entity_vat": entity_vat,
        "status": status_field,
        "type": "invoice",
    }

    return SourceDocument(
        source_id=source_id,
        source_path=source_path,
        mime_type="application/vnd.custodia.fic-invoice",
        text=text,
        metadata=metadata,
    )


# ---------------------------------------------------------------------------
# Connector
# ---------------------------------------------------------------------------


class FattureInCloudConnector:
    """Connettore Fatture in Cloud v2 read-only.

    Esempio d'uso (raccomandato: context manager)::

        with FattureInCloudConnector(
            company_id=123456,
            credentials_path=Path("/path/to/fic_credentials.json"),
            token_cache_path=state_dir / "fic_token.json",
            since=datetime(2024, 1, 1, tzinfo=timezone.utc),
        ) as connector:
            for doc in connector.iter_documents():
                store.add_document(...)

    Se non si usa il ``with``, chiamare ``connector.close()`` esplicitamente
    al termine per chiudere la ``requests.Session`` sottostante.
    """

    name = "fatture_in_cloud"

    def __init__(
        self,
        *,
        company_id: int,
        credentials_path: Path | None = None,
        token_cache_path: Path | None = None,
        cache_dir: Path | None = None,
        dry_run: bool = False,
        max_per_resource: int | None = None,
        since: datetime | None = None,
        resources: list[str] | None = None,
        access_token: str | None = None,
        session: requests.Session | None = None,
    ) -> None:
        """
        Args:
            company_id: ID company FIC (numerico). Scopribile via
                ``GET /user/companies`` se non noto.
            credentials_path: path al credentials JSON FIC.
            token_cache_path: dove cachare il token. Default
                ``./fic_token.json``.
            cache_dir: directory opzionale per il raw JSON di ogni item.
            dry_run: se True, ``text`` vuoto ma metadata popolata.
            max_per_resource: limite hard al numero di item per risorsa.
            since: filtra fatture con ``date >= since`` (server-side via
                ``date_after``). Ignorato per clienti/fornitori.
            resources: lista risorse da scaricare (subset di
                ``["clients", "suppliers", "invoices"]``). Default: tutte.
            access_token: token già acquisito (testing).
            session: ``requests.Session`` da iniettare (testing).
        """
        if not isinstance(company_id, int) or company_id <= 0:
            raise ValueError(
                f"company_id deve essere int positivo, ottenuto {company_id!r}"
            )
        self.company_id = company_id
        self.credentials_path = credentials_path
        self.token_cache_path = (
            token_cache_path
            if token_cache_path is not None
            else Path("./fic_token.json")
        )
        self.cache_dir = cache_dir
        self.dry_run = dry_run
        self.max_per_resource = max_per_resource
        self.since = since
        self._access_token = access_token
        self._session = session or requests.Session()
        self._owns_session = session is None
        self._closed = False

        if resources is None:
            self.resources = list(_DEFAULT_RESOURCES)
        else:
            invalid = [r for r in resources if r not in _VALID_RESOURCES]
            if invalid:
                raise ValueError(
                    f"resources non valide: {invalid}. "
                    f"Ammesse: {list(_VALID_RESOURCES)}"
                )
            self.resources = list(resources)

        self._stats: dict[str, int] = {
            "processed": 0,
            "processed_clients": 0,
            "processed_suppliers": 0,
            "processed_invoices": 0,
            "skipped_max": 0,
            "errors": 0,
        }

    # ------------------------------------------------------------------
    # Context manager / cleanup
    # ------------------------------------------------------------------

    def __enter__(self) -> "FattureInCloudConnector":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        """Chiude la session HTTP sottostante (idempotente)."""
        if self._closed:
            return
        if self._owns_session:
            try:
                self._session.close()
            except Exception as exc:  # noqa: BLE001 - best effort
                logger.debug("session.close() ha sollevato: %s", exc)
        self._closed = True

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def stats(self) -> dict[str, int]:
        return dict(self._stats)

    def iter_documents(self) -> Iterator[SourceDocument]:
        """Itera clienti → fornitori → fatture (per default), in ordine."""
        headers = {
            "Authorization": f"Bearer {self._get_access_token()}",
            "Accept": "application/json",
        }
        for resource in self.resources:
            yield from self._iter_resource(resource, headers)

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    def _get_access_token(self) -> str:
        if self._access_token is not None:
            return self._access_token
        try:
            self._access_token = get_fic_access_token(
                credentials_path=self.credentials_path,
                token_cache_path=self.token_cache_path,
                scopes=FIC_SCOPES,
                session=self._session,
            )
        except Exception as exc:  # noqa: BLE001
            raise ConnectorAuthError(
                f"Impossibile ottenere access token FIC: {exc}"
            ) from exc
        return self._access_token

    # ------------------------------------------------------------------
    # Resource iteration
    # ------------------------------------------------------------------

    def _iter_resource(
        self, resource: str, headers: dict[str, str]
    ) -> Iterator[SourceDocument]:
        """Itera tutte le pagine di una risorsa, producendo SourceDocument."""
        endpoint, params = self._build_initial_request(resource)
        produced_for_resource = 0
        page = 1
        seen_item_ids: set[Any] = set()
        page_count = 0

        while True:
            page_count += 1
            if page_count > _MAX_PAGES_PER_RESOURCE:
                logger.warning(
                    "⚠️  FIC %s: cap _MAX_PAGES_PER_RESOURCE=%d raggiunto, abort.",
                    resource,
                    _MAX_PAGES_PER_RESOURCE,
                )
                return

            params["page"] = str(page)
            try:
                response = self._request(endpoint, headers, params)
            except requests.HTTPError as exc:
                self._stats["errors"] += 1
                self._raise_for_http_error(exc)
                return  # pragma: no cover
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "❌  Errore fatale su FIC %s (%s): %s",
                    resource,
                    type(exc).__name__,
                    exc,
                )
                self._stats["errors"] += 1
                raise ConnectorAPIError(
                    f"Errore fatale su FIC {resource}: {type(exc).__name__}: {exc}"
                ) from exc

            data: dict[str, Any] = response.json()
            items = data.get("data", []) or []

            for item in items:
                if (
                    self.max_per_resource is not None
                    and produced_for_resource >= self.max_per_resource
                ):
                    self._stats["skipped_max"] += 1
                    return
                doc = self._process_item(item, resource)
                if doc is not None:
                    produced_for_resource += 1
                    yield doc

            # Paginazione: usa metadata se presenti, altrimenti dimensione pagina.
            pagination = data.get("current_page"), data.get("last_page")
            if pagination[1] is not None:
                last_page = int(pagination[1])
                current = int(pagination[0] or page)
                if current >= last_page:
                    return
                page = current + 1
            else:
                # Fallback: se la pagina è "corta", finita.
                if len(items) < _PAGE_SIZE:
                    return
                # Loop detection: con pagination metadata assenti, se l'API
                # ritorna sempre gli stessi item ci sarebbe loop infinito.
                page_ids = [
                    item.get("id")
                    for item in items
                    if isinstance(item, dict) and item.get("id") is not None
                ]
                if page_ids and all(pid in seen_item_ids for pid in page_ids):
                    logger.warning(
                        "⚠️  FIC %s: loop pagination rilevato (id ripetuti), abort.",
                        resource,
                    )
                    return
                seen_item_ids.update(page_ids)
                page += 1

    def _build_initial_request(
        self, resource: str
    ) -> tuple[str, dict[str, str]]:
        """Costruisce URL e query params per la prima pagina della risorsa."""
        params: dict[str, str] = {"per_page": str(_PAGE_SIZE)}
        if resource == "clients":
            url = f"{FIC_BASE_URL}/c/{self.company_id}/entities/clients"
        elif resource == "suppliers":
            url = f"{FIC_BASE_URL}/c/{self.company_id}/entities/suppliers"
        elif resource == "invoices":
            url = f"{FIC_BASE_URL}/c/{self.company_id}/issued_documents"
            params["type"] = "invoice"
            if self.since is not None:
                since_utc = (
                    self.since.astimezone(timezone.utc)
                    if self.since.tzinfo
                    else self.since.replace(tzinfo=timezone.utc)
                )
                params["date_after"] = since_utc.strftime("%Y-%m-%d")
        else:  # pragma: no cover — guardato in __init__
            raise ValueError(f"resource non gestita: {resource}")
        return url, params

    # ------------------------------------------------------------------
    # Retry
    # ------------------------------------------------------------------

    def _request(
        self,
        url: str,
        headers: dict[str, str],
        params: dict[str, str],
    ) -> requests.Response:
        """GET wrapper su ``request_with_retry``."""
        return request_with_retry(
            self._session,
            "GET",
            url,
            headers=headers,
            params=params,
            timeout=30.0,
            retriable_statuses=_RETRIABLE_STATUSES,
            max_attempts=_RETRY_MAX_ATTEMPTS,
            retry_after_max=_RETRY_AFTER_MAX,
        )

    @staticmethod
    def _raise_for_http_error(exc: requests.HTTPError) -> None:
        """Mappa ``HTTPError`` in eccezioni semantiche del connector."""
        response = exc.response
        status = getattr(response, "status_code", None)
        if status in (401, 403):
            raise ConnectorAuthError(
                f"Token FIC non valido o senza permessi (HTTP {status})."
            ) from exc
        if status == 429:
            raise ConnectorRateLimitError(
                "Rate limit FIC superato (HTTP 429)."
            ) from exc
        raise ConnectorAPIError(
            f"Errore FIC API (HTTP {status})."
        ) from exc

    # ------------------------------------------------------------------
    # Per-item processing
    # ------------------------------------------------------------------

    def _process_item(
        self, item: dict[str, Any], resource: str
    ) -> SourceDocument | None:
        """Trasforma un item API in SourceDocument. Per-item errors isolati."""
        try:
            if not isinstance(item, dict):
                raise ValueError(f"item non-dict: {type(item).__name__}")
            if resource == "clients":
                doc = _build_entity_doc(item, kind="client", dry_run=self.dry_run)
                self._stats["processed_clients"] += 1
            elif resource == "suppliers":
                doc = _build_entity_doc(item, kind="supplier", dry_run=self.dry_run)
                self._stats["processed_suppliers"] += 1
            else:  # invoices
                doc = _build_invoice_doc(item, dry_run=self.dry_run)
                self._stats["processed_invoices"] += 1

            # Cache raw JSON opzionale (chmod 0o600 + sanitize id).
            if self.cache_dir is not None and not self.dry_run:
                try:
                    sub_dir = self.cache_dir / resource
                    fic_id = item.get("id")
                    safe_name = _sanitize_id_for_filename(fic_id)
                    cache_path = sub_dir / f"{safe_name}.json"
                    if not cache_path.exists():
                        _write_cache_json(cache_path, item)
                except OSError as exc:
                    logger.warning(
                        "⚠️  Cache FIC scrittura fallita per %s/%s: %s",
                        resource,
                        item.get("id"),
                        exc,
                    )

            self._stats["processed"] += 1
            return doc
        except Exception as exc:  # noqa: BLE001
            # NON loggare il body in clear (PII clienti).
            item_id_safe = (
                item.get("id", "<no-id>") if isinstance(item, dict) else "<malformed>"
            )
            logger.error(
                "❌  errore parsing FIC %s id=%s (%s): %s",
                resource,
                item_id_safe,
                type(exc).__name__,
                exc,
            )
            self._stats["errors"] += 1
            return None


__all__ = [
    "FattureInCloudConnector",
    "FIC_BASE_URL",
    "FIC_SCOPES",
]
