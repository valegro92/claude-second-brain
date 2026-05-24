"""Wrapper safe-mode: redact PII pre-call, de-redact post-call.

Sovrascrive qualsiasi :class:`wiki.llm._base.LLMClient` (anthropic_api,
bedrock, futuri) con due passate:

1. **Pre-call**: tutti i messaggi (e ``system``) vengono passati attraverso
   :func:`redact_text` che sostituisce le PII rilevate con placeholder
   tipo ``<email-1>``, ``<cf-2>``, ``<iban-3>``, ``<phone-4>``. Il modello
   non vede mai il valore reale.

2. **Post-call**: il testo di risposta viene passato attraverso
   :func:`unredact_text` che rimappa i placeholder ai valori originali.

La mappa redact ↔ valore viene salvata in
``_status/audit/redact-map.json`` (mai inviata al modello, mai a log esterni).
Una sola mappa globale per cliente: i placeholder sono stabili tra chiamate
e tra rerun (un certo email genererà sempre lo stesso ``<email-N>``).

Pattern coperti:

* **Email**: regex standard;
* **Codice fiscale italiano**: 16 caratteri, schema lettere+cifre+lettere+cifre+lettera;
* **IBAN**: formato a 27 cifre per IT, generico per Europa (15-34 char);
* **Telefono**: italiano (con o senza prefisso +39, con separatori).

Note di design:

* Non si chiama "anonimizzazione GDPR completa": è una **mitigazione di
  rischio** che riduce il dato esposto al modello. Non sostituisce
  l'esclusione perimetrale (vedi brief 06 sezione B.1.5).
* L'ordine dei pattern conta: applichiamo CF e IBAN PRIMA del telefono
  per evitare che un CF venga letto come telefono.
"""

from __future__ import annotations

import json
import logging
import re
import threading
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from ._base import AnthropicCompatibleMixin, LLMClient

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------- regex
# Email: standard RFC-light, sufficiente per i dati di una PMI italiana.
_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")

# Codice fiscale italiano: 6 lettere + 2 cifre + 1 lettera + 2 cifre +
# 1 lettera + 3 alfanumerici + 1 lettera (16 char totali). Case-insensitive.
_CF_RE = re.compile(
    r"\b[A-Z]{6}\d{2}[A-Z]\d{2}[A-Z][A-Z0-9]{3}[A-Z]\b",
    re.IGNORECASE,
)

# IBAN: 2 lettere paese + 2 check + 11-30 alfanumerici. Tolleriamo spazi
# (es. "IT60 X054 2811 1010 0000 0123 456").
_IBAN_RE = re.compile(
    r"\b[A-Z]{2}\d{2}[ ]?(?:[A-Z0-9][ ]?){11,30}\b",
    re.IGNORECASE,
)

# Telefono italiano: opzionale +39, poi 6-13 cifre con separatori
# (spazi, punti, trattini). Evitiamo di matchare numeri brevi tipo anni.
_PHONE_RE = re.compile(
    r"(?:(?<!\d)\+?39[ \-./]?)?(?<!\d)\d{2,4}[ \-./]\d{2,4}[ \-./]?\d{2,5}(?!\d)",
)


# Ordine: IBAN > CF > email > phone. Quello con pattern più specifico/lungo
# per primo, così non viene "mangiato" dal pattern più generico.
_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("iban", _IBAN_RE),
    ("cf", _CF_RE),
    ("email", _EMAIL_RE),
    ("phone", _PHONE_RE),
)


# ----------------------------------------------------------------- redact map
class RedactMap:
    """Mappa bidirezionale placeholder ↔ valore PII, persistente su disco.

    Una mappa per cliente, persistita su
    ``<state_dir>/audit/redact-map.json``. Mai inviata al modello.

    Thread-safe per uso single-process (i caller del toolkit sono
    sequenziali a livello di pipeline).
    """

    def __init__(self, state_dir: Path | None) -> None:
        self._state_dir = state_dir
        self._lock = threading.Lock()
        # ``_forward``: valore reale → placeholder. Permette di riusare lo
        # stesso placeholder per la stessa PII tra chiamate.
        self._forward: dict[str, str] = {}
        # ``_reverse``: placeholder → valore reale. Usato per la de-redact.
        self._reverse: dict[str, str] = {}
        # Contatori per generare placeholder progressivi per categoria.
        self._counters: dict[str, int] = {kind: 0 for kind, _ in _PATTERNS}
        self._load()

    # ---------------------------------------------------- persistence
    def _map_path(self) -> Path | None:
        if self._state_dir is None:
            return None
        return self._state_dir / "audit" / "redact-map.json"

    def _load(self) -> None:
        path = self._map_path()
        if path is None or not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Impossibile caricare redact-map %s: %s", path, exc)
            return
        forward = data.get("forward", {})
        if isinstance(forward, dict):
            self._forward = {str(k): str(v) for k, v in forward.items()}
            self._reverse = {v: k for k, v in self._forward.items()}
        counters = data.get("counters", {})
        if isinstance(counters, dict):
            for kind, _ in _PATTERNS:
                try:
                    self._counters[kind] = int(counters.get(kind, 0))
                except (TypeError, ValueError):
                    self._counters[kind] = 0

    def save(self) -> None:
        """Persiste la mappa su disco. No-op se ``state_dir`` è ``None``."""
        path = self._map_path()
        if path is None:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "forward": self._forward,
            "counters": self._counters,
            # Versione del formato, per evolvere senza rompere.
            "_format_version": 1,
        }
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # ----------------------------------------------------- lookup
    def get_placeholder(self, kind: str, value: str) -> str:
        """Ritorna il placeholder per ``value``, generandolo se mancante."""
        with self._lock:
            existing = self._forward.get(value)
            if existing is not None:
                return existing
            self._counters[kind] = self._counters.get(kind, 0) + 1
            placeholder = f"<{kind}-{self._counters[kind]}>"
            self._forward[value] = placeholder
            self._reverse[placeholder] = value
            return placeholder

    def reverse_lookup(self, placeholder: str) -> str | None:
        """Ritorna il valore originale per un placeholder, o ``None``."""
        return self._reverse.get(placeholder)

    def items(self) -> Iterable[tuple[str, str]]:
        """Iter di ``(valore, placeholder)`` per debug/test."""
        return self._forward.items()


# ----------------------------------------------------------------- redact
def redact_text(text: str, redact_map: RedactMap) -> str:
    """Sostituisce le PII in ``text`` con placeholder stabili.

    L'ordine di applicazione è quello di :data:`_PATTERNS` (IBAN prima
    di CF prima di email prima di telefono).
    """
    if not text:
        return text
    result = text
    for kind, pattern in _PATTERNS:

        def _replace(match: re.Match[str], _kind: str = kind) -> str:
            value = match.group(0)
            return redact_map.get_placeholder(_kind, value)

        result = pattern.sub(_replace, result)
    return result


def unredact_text(text: str, redact_map: RedactMap) -> str:
    """Rimappa i placeholder in ``text`` al valore originale.

    Cerca tutti i pattern tipo ``<kind-N>`` e li sostituisce con il valore
    se presente nella mappa, altrimenti li lascia invariati (es. il modello
    potrebbe averli citati come letterali in un contesto non-PII).
    """
    if not text:
        return text
    return re.sub(
        r"<(email|cf|iban|phone)-\d+>",
        lambda m: redact_map.reverse_lookup(m.group(0)) or m.group(0),
        text,
    )


def _redact_messages(messages: list[dict[str, Any]], redact_map: RedactMap) -> list[dict[str, Any]]:
    """Redact ricorsivo di ``content`` (stringa o lista di blocchi)."""
    out: list[dict[str, Any]] = []
    for msg in messages:
        new = dict(msg)
        content = new.get("content")
        if isinstance(content, str):
            new["content"] = redact_text(content, redact_map)
        elif isinstance(content, list):
            new_blocks: list[Any] = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    block = dict(block)
                    block["text"] = redact_text(block.get("text", ""), redact_map)
                new_blocks.append(block)
            new["content"] = new_blocks
        out.append(new)
    return out


# ----------------------------------------------------------------- wrapper
class SafeModeClient(AnthropicCompatibleMixin, LLMClient):
    """Wrapper safe-mode su un :class:`LLMClient` qualunque.

    Esempio:

    .. code-block:: python

        inner = AnthropicApiClient()
        client = SafeModeClient(inner, state_dir=Path("_status"))
        text, usage = client.complete(messages=[{"role": "user", "content": "..."}])

    L'``inner`` viene chiamato con messaggi redacted; la response viene
    de-redacted prima di tornare al caller.
    """

    def __init__(self, inner: LLMClient, state_dir: Path | None = None) -> None:
        """Args:
        inner: provider sottostante da wrappare.
        state_dir: cartella ``_status/`` dove salvare la mappa redact.
            Se ``None``, la mappa vive solo in memoria (utile in test).
        """
        self._inner = inner
        self.models = dict(inner.models)
        self.redact_map = RedactMap(state_dir)

    def complete(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        max_tokens: int = 1024,
        **kwargs: Any,
    ) -> tuple[str, dict[str, int]]:
        """Redact → inner.complete → unredact → save map."""
        redacted_messages = _redact_messages(messages, self.redact_map)
        redacted_kwargs = dict(kwargs)
        if "system" in redacted_kwargs:
            redacted_kwargs["system"] = redact_text(redacted_kwargs["system"], self.redact_map)

        text, usage = self._inner.complete(
            messages=redacted_messages,
            model=model,
            max_tokens=max_tokens,
            **redacted_kwargs,
        )

        # Persiste la mappa anche se la chiamata fallisce successivamente:
        # i placeholder devono essere stabili tra rerun.
        self.redact_map.save()

        # De-redact della risposta (di norma il modello non rigetta i
        # placeholder, ma se lo fa li ri-espande in valori reali).
        return unredact_text(text, self.redact_map), usage

    def vision(
        self,
        image_path: Path,
        prompt: str,
        model: str | None = None,
        **kwargs: Any,
    ) -> tuple[str, dict[str, int]]:
        """Vision wrapped: il prompt testuale è redacted; l'immagine no.

        Nota: il safe-mode NON tocca le immagini. Se il cliente vuole anche
        protezione visiva (volti, documenti), va combinato con una pipeline
        di blur/redact pre-OCR fuori da questo modulo.
        """
        redacted_prompt = redact_text(prompt, self.redact_map)
        text, usage = self._inner.vision(
            image_path=image_path,
            prompt=redacted_prompt,
            model=model,
            **kwargs,
        )
        self.redact_map.save()
        return unredact_text(text, self.redact_map), usage


__all__ = [
    "RedactMap",
    "SafeModeClient",
    "redact_text",
    "unredact_text",
]
