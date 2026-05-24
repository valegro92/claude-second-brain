"""Extractor per email RFC 822 (.eml). stdlib email + markdownify."""

from __future__ import annotations

import logging
from email import message_from_bytes, policy
from email.message import EmailMessage
from email.utils import parseaddr
from pathlib import Path
from typing import Any

from ._base import ExtractionResult, Extractor

logger = logging.getLogger(__name__)

# Oltre questa soglia tronchiamo il body e produciamo nota.
_MAX_BODY_BYTES = 50 * 1024  # 50 KB


class EmlExtractor(Extractor):
    """EML → markdown con frontmatter YAML, allegati e corpo."""

    name = "eml"
    mimes = ["message/rfc822"]
    extensions = [".eml"]

    def extract(self, file_path: Path) -> ExtractionResult:
        warnings: list[str] = []
        raw = file_path.read_bytes()
        msg = message_from_bytes(raw, policy=policy.default)
        if not isinstance(msg, EmailMessage):
            # Si verifica solo se il parsing produce un Message legacy; convertiamo per compat.
            warnings.append("Parsing email senza policy moderna, alcuni header potrebbero mancare")

        headers = _extract_headers(msg)
        attachments = _list_attachments(msg)
        body_md, body_warnings, body_truncated, full_body = _extract_body(msg)
        warnings.extend(body_warnings)

        frontmatter = _build_frontmatter({**headers, "attachments": len(attachments)})

        parts = [frontmatter]
        if attachments:
            parts.append("## Allegati")
            for att in attachments:
                size_kb = att["size"] / 1024
                parts.append(f"- `{att['filename']}` ({att['content_type']}, {size_kb:.1f} KB)")
        else:
            parts.append("## Allegati\n\n_(nessuno)_")

        parts.append("## Corpo")
        parts.append(body_md or "_(corpo vuoto)_")
        if body_truncated:
            parts.append("> **Nota**: corpo troncato per dimensione; vedi body-full.txt")

        markdown = "\n\n".join(parts)
        metadata: dict[str, Any] = {
            **headers,
            "attachments": attachments,
            "body_chars": len(body_md or ""),
            "body_truncated": body_truncated,
        }
        if body_truncated and full_body is not None:
            # Esponiamo il body integrale tramite metadata per dump opzionale.
            metadata["body_full"] = full_body

        quality = 0.95 if (body_md or attachments) else 0.4
        return ExtractionResult(
            markdown=markdown,
            metadata=metadata,
            warnings=warnings,
            quality=quality,
        )


def _extract_headers(msg) -> dict[str, Any]:
    """Header rilevanti normalizzati."""

    def addr_list(value):
        if not value:
            return []
        # email.message.get_all può ritornare già strutture; fallback a parseaddr split.
        items = []
        for chunk in str(value).split(","):
            name, addr = parseaddr(chunk)
            if addr:
                items.append(addr if not name else f"{name} <{addr}>")
        return items

    return {
        "from": addr_list(msg.get("From"))[0] if msg.get("From") else None,
        "to": addr_list(msg.get("To")),
        "cc": addr_list(msg.get("Cc")),
        "date": str(msg.get("Date") or ""),
        "subject": str(msg.get("Subject") or ""),
        "message_id": str(msg.get("Message-ID") or ""),
    }


def _list_attachments(msg) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for part in msg.walk() if hasattr(msg, "walk") else []:
        if part.is_multipart():
            continue
        disp = (part.get_content_disposition() or "").lower()
        filename = part.get_filename()
        if disp == "attachment" or (filename and disp != "inline"):
            payload = part.get_payload(decode=True) or b""
            out.append(
                {
                    "filename": filename or "(senza nome)",
                    "content_type": part.get_content_type(),
                    "size": len(payload),
                }
            )
    return out


def _extract_body(msg) -> tuple[str, list[str], bool, str | None]:
    """Ritorna ``(markdown, warnings, truncated, full_body)``.

    Preferenza: text/plain. Se assente: text/html → markdownify.
    Reply quotati NON rimossi.
    """
    warnings: list[str] = []
    plain = None
    html = None
    if hasattr(msg, "iter_parts") or hasattr(msg, "walk"):
        parts = list(msg.walk()) if hasattr(msg, "walk") else [msg]
    else:  # pragma: no cover
        parts = [msg]

    for part in parts:
        if getattr(part, "is_multipart", lambda: False)():
            continue
        ctype = part.get_content_type() if hasattr(part, "get_content_type") else ""
        disp = (
            (part.get_content_disposition() or "").lower()
            if hasattr(part, "get_content_disposition")
            else ""
        )
        if disp == "attachment":
            continue
        if ctype == "text/plain" and plain is None:
            try:
                plain = part.get_content()
            except Exception as exc:
                warnings.append(f"Impossibile leggere text/plain: {exc}")
        elif ctype == "text/html" and html is None:
            try:
                html = part.get_content()
            except Exception as exc:
                warnings.append(f"Impossibile leggere text/html: {exc}")

    body_md: str | None = None
    full_body: str | None = None
    if plain:
        full_body = plain
        body_md = plain
    elif html:
        try:
            from markdownify import markdownify as md

            body_md = md(html, heading_style="ATX")
            full_body = body_md
        except ImportError:
            warnings.append("markdownify non installato: HTML restituito come testo grezzo")
            body_md = html
            full_body = html
        except Exception as exc:
            warnings.append(f"markdownify ha fallito: {exc}; uso HTML grezzo")
            body_md = html
            full_body = html

    body_md = (body_md or "").strip()
    truncated = False
    if body_md and len(body_md.encode("utf-8")) > _MAX_BODY_BYTES:
        # Troncamento conservativo basato su byte.
        encoded = body_md.encode("utf-8")[:_MAX_BODY_BYTES]
        body_md = encoded.decode("utf-8", errors="ignore") + "\n\n[...troncato...]"
        truncated = True
        warnings.append(
            f"Body email > {_MAX_BODY_BYTES // 1024} KB, troncato (full disponibile in body-full.txt)"
        )
    return body_md, warnings, truncated, full_body


def _build_frontmatter(data: dict[str, Any]) -> str:
    """YAML frontmatter minimale e leggibile (niente PyYAML per evitare dipendenze qui)."""
    lines = ["---"]
    for key in ("from", "to", "cc", "date", "subject", "message_id", "attachments"):
        value = data.get(key)
        if value is None or value == "":
            lines.append(f"{key.replace('_', '-')}: ")
            continue
        if isinstance(value, list):
            if not value:
                lines.append(f"{key}: []")
            else:
                lines.append(f"{key}:")
                for item in value:
                    lines.append(f"  - {_yaml_scalar(item)}")
        else:
            lines.append(f"{key.replace('_', '-')}: {_yaml_scalar(value)}")
    lines.append("---")
    return "\n".join(lines)


def _yaml_scalar(value: Any) -> str:
    """Quoting minimale per scalari YAML che contengono caratteri ambigui."""
    s = str(value)
    if any(ch in s for ch in [":", "#", "\n", "'", '"']) or s != s.strip():
        return '"' + s.replace('"', '\\"') + '"'
    return s
