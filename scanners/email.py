"""Scanner email (Gmail / Outlook) con modalità reale stub-bata + mock funzionante.

In modalità mock il fixture punta a una cartella di file ``.eml`` o a un singolo
JSON con la lista di messaggi. I file ``.eml`` vengono parsati con lo
``email`` stdlib; ogni allegato viene emesso come :class:`FileRecord` separato
con ``source="email-attachment"``.
"""
from __future__ import annotations

import email
import json
import logging
import mimetypes
import re
from datetime import datetime
from email.message import Message
from email.utils import parseaddr, parsedate_to_datetime
from pathlib import Path
from typing import Any, Iterator

from scanners._base import FileRecord, Scanner

logger = logging.getLogger(__name__)


_BODY_SNIPPET_CHARS = 500
_SAFE_CHARS = re.compile(r"[^A-Za-z0-9._-]+")


def _safe_name(name: str) -> str:
    return _SAFE_CHARS.sub("_", name).strip("_") or "untitled"


def _parse_date(value: str | None) -> datetime:
    if not value:
        return datetime.fromtimestamp(0)
    try:
        return parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return datetime.fromtimestamp(0)


def _record_from_eml(msg: Message, source_id: str, eml_path: Path | None = None) -> FileRecord:
    """Costruisce il record per il messaggio principale (senza allegati)."""
    from_addr = parseaddr(msg.get("From", ""))[1]
    to_addr = msg.get("To", "")
    subject = msg.get("Subject", "")
    date = _parse_date(msg.get("Date"))
    body_text = _extract_body(msg)
    size = len(body_text.encode("utf-8")) if body_text else 0
    if eml_path is not None:
        try:
            size = eml_path.stat().st_size
        except OSError:
            pass
    return FileRecord(
        source="email",
        source_id=source_id,
        path=f"{from_addr}/{_safe_name(subject)[:80]}.eml",
        name=f"{_safe_name(subject)[:80]}.eml",
        size=size,
        mtime=date,
        mime="message/rfc822",
        author=from_addr or None,
        last_modified_by=None,
        permissions=None,
        sha256=None,
        extras={
            "subject": subject,
            "from": from_addr,
            "to": to_addr,
            "snippet": (body_text or "")[:_BODY_SNIPPET_CHARS],
            "has_attachments": _has_attachments(msg),
        },
    )


def _extract_body(msg: Message) -> str:
    """Estrae il body testuale: preferenza per ``text/plain``, fallback ``text/html``."""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain" and not part.get_filename():
                try:
                    return part.get_payload(decode=True).decode(  # type: ignore[union-attr]
                        part.get_content_charset() or "utf-8", errors="replace"
                    )
                except Exception:  # pragma: no cover - difensivo
                    continue
        # fallback html
        for part in msg.walk():
            if part.get_content_type() == "text/html" and not part.get_filename():
                try:
                    return part.get_payload(decode=True).decode(  # type: ignore[union-attr]
                        part.get_content_charset() or "utf-8", errors="replace"
                    )
                except Exception:  # pragma: no cover - difensivo
                    continue
        return ""
    try:
        payload = msg.get_payload(decode=True)
        if payload is None:
            return ""
        return payload.decode(msg.get_content_charset() or "utf-8", errors="replace")
    except Exception:  # pragma: no cover - difensivo
        return ""


def _has_attachments(msg: Message) -> bool:
    if not msg.is_multipart():
        return False
    return any(part.get_filename() for part in msg.walk())


def _records_from_attachments(msg: Message, parent_id: str, mtime: datetime) -> Iterator[FileRecord]:
    """Un :class:`FileRecord` per ogni allegato, ``source="email-attachment"``."""
    if not msg.is_multipart():
        return
    for idx, part in enumerate(msg.walk()):
        filename = part.get_filename()
        if not filename:
            continue
        payload = part.get_payload(decode=True) or b""
        mime = part.get_content_type() or mimetypes.guess_type(filename)[0]
        yield FileRecord(
            source="email-attachment",
            source_id=f"{parent_id}#att{idx}",
            path=f"attachments/{parent_id}/{_safe_name(filename)}",
            name=filename,
            size=len(payload),
            mtime=mtime,
            mime=mime,
            author=parseaddr(msg.get("From", ""))[1] or None,
            last_modified_by=None,
            permissions=None,
            sha256=None,
            extras={
                "parent_message_id": parent_id,
                "subject": msg.get("Subject", ""),
            },
        )


class EmailScanner(Scanner):
    """Scanner mailbox con modalità mock pienamente funzionante + reale stub.

    Mock supporta due forme:

    * directory con file ``.eml`` (uno per messaggio)
    * file JSON con lista di ``{"path": "...eml"}`` o messaggi inline
    """

    source_name = "email"

    def __init__(self, config: dict[str, Any], state_dir: Path) -> None:
        super().__init__(config, state_dir)
        sorgente = config.get("sorgenti", {}).get(self.source_name, {})
        self.provider: str = sorgente.get("provider", "gmail")
        self.accounts: list[str] = list(sorgente.get("accounts", []))
        self.folders: list[str] = list(sorgente.get("folders", []))
        self.mock_data_path: str | None = sorgente.get("mock_data_path")
        self.skip_short_no_attachments: bool = bool(
            sorgente.get("skip_short_no_attachments", True)
        )
        self.min_body_chars: int = int(sorgente.get("min_body_chars", 500))

    # ------------------------------------------------------------ modalità mock
    def _is_mock(self) -> bool:
        if not self.mock_data_path:
            return False
        return Path(self.mock_data_path).expanduser().exists()

    def _iter_mock_messages(self) -> Iterator[tuple[str, Message, Path | None]]:
        """Restituisce coppie ``(source_id, Message, eml_path?)``."""
        root = Path(self.mock_data_path).expanduser()  # type: ignore[arg-type]
        if root.is_dir():
            for eml_path in sorted(root.glob("*.eml")):
                with eml_path.open("rb") as f:
                    msg = email.message_from_binary_file(f)
                source_id = msg.get("Message-ID") or eml_path.name
                yield source_id, msg, eml_path
            return
        # File JSON: lista di {"path": "..."} oppure {"messages": [{...}]}
        data = json.loads(root.read_text(encoding="utf-8"))
        items = data["messages"] if isinstance(data, dict) and "messages" in data else data
        for item in items:
            if "path" in item:
                eml_path = (root.parent / item["path"]).resolve()
                with eml_path.open("rb") as f:
                    msg = email.message_from_binary_file(f)
                source_id = item.get("message_id") or msg.get("Message-ID") or eml_path.name
                yield source_id, msg, eml_path
            else:
                # Messaggio inline (utile per smoke test)
                msg = email.message_from_string(item.get("raw", ""))
                source_id = item.get("message_id") or msg.get("Message-ID") or "inline"
                yield source_id, msg, None

    # ------------------------------------------------------------ modalità real
    def _iter_real_messages(self) -> Iterator[tuple[str, Message, Path | None]]:
        """Real mode: stub esplicito.

        L'OAuth flow per Gmail / Graph è gestito in ``bootstrap/auth/*.py``
        (cantiere AUTH). Qui ci limitiamo a un TODO marcato che lancia un
        errore chiaro se invocato.
        """
        # TODO: implementare OAuth flow (gmail + graph) e paginazione history/delta.
        raise NotImplementedError(
            f"Email real mode ({self.provider}) non ancora implementato: "
            "vedi bootstrap/auth/. In CI / dev usare mock_data_path."
        )

    # --------------------------------------------------------------------- API
    def scan(self) -> Iterator[FileRecord]:
        msg_iter = self._iter_mock_messages() if self._is_mock() else self._iter_real_messages()
        count_msg = 0
        count_att = 0
        for source_id, msg, eml_path in msg_iter:
            record = _record_from_eml(msg, source_id, eml_path)
            # Filtro: messaggi corti senza allegati spesso rumore (es. notifiche)
            if (
                self.skip_short_no_attachments
                and not record.extras["has_attachments"]
                and len(record.extras["snippet"]) < self.min_body_chars
            ):
                continue
            if not self.apply_filters(record):
                continue
            self.write_record(record)
            count_msg += 1
            yield record
            # Allegati come record separati
            for att in _records_from_attachments(msg, source_id, record.mtime):
                if not self.apply_filters(att):
                    continue
                self.write_record(att)
                count_att += 1
                yield att
        logger.info("Email scan done — %d messaggi, %d allegati", count_msg, count_att)
