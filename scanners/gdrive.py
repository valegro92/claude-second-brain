"""Scanner per Google Drive / Workspace.

Due modalità:

* ``real`` — usa ``google-api-python-client`` con un service account
  (auth via JSON key, opzionale domain-wide delegation per Workspace).
* ``mock`` — se ``sorgenti.gdrive.mock_data_path`` è valorizzato e il file
  esiste, legge i record da JSON locale. Permette di testare la pipeline
  end-to-end senza credenziali Google.

Output: ``_status/inventory/gdrive.jsonl`` (formato uniforme :class:`FileRecord`).
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Iterator

from scanners._base import FileRecord, Scanner

logger = logging.getLogger(__name__)


# Campi richiesti all'API Drive (vedi brief sezione 2.1)
_DRIVE_FIELDS = (
    "nextPageToken, files("
    "id, name, mimeType, size, modifiedTime, parents, owners, "
    "lastModifyingUser, md5Checksum, webViewLink, permissions, trashed"
    ")"
)


def _parse_iso(value: str | None) -> datetime:
    if not value:
        return datetime.fromtimestamp(0)
    # Google ritorna ISO con 'Z'; Python 3.11 accetta con sostituzione
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _record_from_drive_item(item: dict[str, Any]) -> FileRecord:
    owners = item.get("owners") or []
    last_mod = item.get("lastModifyingUser") or {}
    return FileRecord(
        source="gdrive",
        source_id=item["id"],
        path="/".join(item.get("parents", []) + [item.get("name", "")]),
        name=item.get("name", ""),
        size=int(item.get("size") or 0),
        mtime=_parse_iso(item.get("modifiedTime")),
        mime=item.get("mimeType"),
        author=(owners[0].get("emailAddress") if owners else None),
        last_modified_by=last_mod.get("emailAddress"),
        permissions={"raw": item.get("permissions")} if item.get("permissions") else None,
        sha256=None,  # Google espone solo md5; SHA256 calcolato in fase di download
        extras={
            "md5Checksum": item.get("md5Checksum"),
            "webViewLink": item.get("webViewLink"),
            "trashed": item.get("trashed", False),
        },
    )


class GDriveScanner(Scanner):
    """Scanner Drive con modalità reale + mock from JSON."""

    source_name = "gdrive"

    def __init__(self, config: dict[str, Any], state_dir: Path) -> None:
        super().__init__(config, state_dir)
        sorgente = config.get("sorgenti", {}).get(self.source_name, {})
        self.mock_data_path: str | None = sorgente.get("mock_data_path")
        self.service_account_path: str | None = sorgente.get("service_account_path")
        self.workspace: str | None = sorgente.get("workspace")
        self.corpora: str = sorgente.get("corpora", "user")  # "user" | "allDrives"
        self.page_size: int = int(sorgente.get("page_size", 1000))
        # Il client viene creato lazy: serve solo in modalità reale
        self._service: Any | None = None

    # ------------------------------------------------------------ modalità mock
    def _is_mock(self) -> bool:
        if not self.mock_data_path:
            return False
        return Path(self.mock_data_path).expanduser().exists()

    def _iter_mock(self) -> Iterator[dict[str, Any]]:
        path = Path(self.mock_data_path).expanduser()  # type: ignore[arg-type]
        logger.info("GDrive mock attivo: leggo %s", path)
        data = json.loads(path.read_text(encoding="utf-8"))
        # Supportiamo sia {"files": [...]} sia direttamente una lista
        items: Iterable[dict[str, Any]] = data["files"] if isinstance(data, dict) else data
        for item in items:
            yield item

    # ------------------------------------------------------------ modalità real
    def _build_service(self) -> Any:
        """Costruisce il client Drive v3. Import lazy per non rompere ambienti mock-only."""
        if self._service is not None:
            return self._service
        if not self.service_account_path:
            raise RuntimeError(
                "Credenziali Drive mancanti: imposta "
                "sorgenti.gdrive.service_account_path nel config"
            )
        # Import lazy
        from google.oauth2 import service_account  # type: ignore
        from googleapiclient.discovery import build  # type: ignore

        scopes = ["https://www.googleapis.com/auth/drive.readonly"]
        creds = service_account.Credentials.from_service_account_file(
            self.service_account_path, scopes=scopes
        )
        self._service = build("drive", "v3", credentials=creds, cache_discovery=False)
        return self._service

    def _iter_real(self) -> Iterator[dict[str, Any]]:
        """Paginazione su Drive API v3 ``files.list``."""
        service = self._build_service()
        page_token = self.read_cursor()
        params: dict[str, Any] = {
            "pageSize": self.page_size,
            "fields": _DRIVE_FIELDS,
            "q": "trashed = false",
        }
        if self.corpora == "allDrives":
            params.update(
                {
                    "corpora": "allDrives",
                    "includeItemsFromAllDrives": True,
                    "supportsAllDrives": True,
                }
            )
        while True:
            if page_token:
                params["pageToken"] = page_token
            response = service.files().list(**params).execute()
            for item in response.get("files", []):
                yield item
            page_token = response.get("nextPageToken")
            if not page_token:
                break
            # Checkpoint pagina-pagina
            self.write_cursor(page_token)

    # --------------------------------------------------------------------- API
    def scan(self) -> Iterator[FileRecord]:
        """Itera i file Drive (mock o reale), applica filtri, scrive JSONL."""
        source_iter = self._iter_mock() if self._is_mock() else self._iter_real()
        count = 0
        for item in source_iter:
            record = _record_from_drive_item(item)
            if not self.apply_filters(record):
                continue
            self.write_record(record)
            count += 1
            yield record
        logger.info("GDrive scan done — %d record", count)
