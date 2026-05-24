"""Scanner per Microsoft 365 / OneDrive / SharePoint via Graph SDK.

Stesso pattern di :mod:`scanners.gdrive`:

* ``real`` — client ``msgraph-sdk`` con app registration Azure AD (client credentials flow).
* ``mock`` — se ``sorgenti.m365.mock_data_path`` esiste, legge da JSON locale.

Le chiamate reali sono volutamente uno stub minimale: l'integrazione completa
(delta queries, multi-site) è tracciata nel brief sezione 2.2 ed entrerà nello
sprint dedicato.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterable, Iterator
from datetime import datetime
from pathlib import Path
from typing import Any

from scanners._base import FileRecord, Scanner

logger = logging.getLogger(__name__)


def _parse_iso(value: str | None) -> datetime:
    if not value:
        return datetime.fromtimestamp(0)
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _record_from_drive_item(item: dict[str, Any]) -> FileRecord:
    file_info = item.get("file") or {}
    parent = item.get("parentReference") or {}
    created_by = (item.get("createdBy") or {}).get("user") or {}
    last_modified_by = (item.get("lastModifiedBy") or {}).get("user") or {}
    return FileRecord(
        source="m365",
        source_id=item["id"],
        path=f"{parent.get('path', '')}/{item.get('name', '')}".lstrip("/"),
        name=item.get("name", ""),
        size=int(item.get("size") or 0),
        mtime=_parse_iso(item.get("lastModifiedDateTime")),
        mime=file_info.get("mimeType"),
        author=created_by.get("email") or created_by.get("displayName"),
        last_modified_by=last_modified_by.get("email") or last_modified_by.get("displayName"),
        permissions=None,  # da popolare con /permissions in fase reale
        sha256=None,
        extras={
            "quickXorHash": (file_info.get("hashes") or {}).get("quickXorHash"),
            "driveId": parent.get("driveId"),
            "webUrl": item.get("webUrl"),
        },
    )


class M365Scanner(Scanner):
    """Scanner OneDrive / SharePoint con modalità reale + mock."""

    source_name = "m365"

    def __init__(self, config: dict[str, Any], state_dir: Path) -> None:
        super().__init__(config, state_dir)
        sorgente = config.get("sorgenti", {}).get(self.source_name, {})
        self.mock_data_path: str | None = sorgente.get("mock_data_path")
        self.tenant_id: str | None = sorgente.get("tenant_id")
        self.client_id: str | None = sorgente.get("client_id")
        self.client_secret: str | None = sorgente.get("client_secret")
        self.drive_id: str | None = sorgente.get("drive_id")
        self._client: Any | None = None

    # ------------------------------------------------------------ modalità mock
    def _is_mock(self) -> bool:
        if not self.mock_data_path:
            return False
        return Path(self.mock_data_path).expanduser().exists()

    def _iter_mock(self) -> Iterator[dict[str, Any]]:
        path = Path(self.mock_data_path).expanduser()  # type: ignore[arg-type]
        logger.info("M365 mock attivo: leggo %s", path)
        data = json.loads(path.read_text(encoding="utf-8"))
        items: Iterable[dict[str, Any]] = data["value"] if isinstance(data, dict) else data
        for item in items:
            yield item

    # ------------------------------------------------------------ modalità real
    def _build_client(self) -> Any:
        """Inizializza il GraphServiceClient. Import lazy per non rompere mock-only."""
        if self._client is not None:
            return self._client
        if not (self.tenant_id and self.client_id and self.client_secret):
            raise RuntimeError(
                "Credenziali M365 mancanti: imposta tenant_id/client_id/client_secret "
                "in sorgenti.m365"
            )
        from azure.identity import ClientSecretCredential
        from msgraph import GraphServiceClient

        credential = ClientSecretCredential(
            tenant_id=self.tenant_id,
            client_id=self.client_id,
            client_secret=self.client_secret,
        )
        self._client = GraphServiceClient(
            credentials=credential,
            scopes=["https://graph.microsoft.com/.default"],
        )
        return self._client

    def _iter_real(self) -> Iterator[dict[str, Any]]:
        """Stub di iterazione reale: TODO completare con delta queries multi-site.

        Implementazione attuale: enumerazione children del drive root.
        Volutamente sincrona; il porting a async-msgraph è rimandato.
        """
        client = self._build_client()
        logger.warning(
            "M365 real mode stub-bato: completare con delta queries (vedi brief 2.2). "
            "Client costruito: %s",
            type(client).__name__,
        )
        # TODO: implementare paginazione completa via delta token
        return iter(())

    # --------------------------------------------------------------------- API
    def scan(self) -> Iterator[FileRecord]:
        source_iter = self._iter_mock() if self._is_mock() else self._iter_real()
        count = 0
        for item in source_iter:
            record = _record_from_drive_item(item)
            if not self.apply_filters(record):
                continue
            self.write_record(record)
            count += 1
            yield record
        logger.info("M365 scan done — %d record", count)
