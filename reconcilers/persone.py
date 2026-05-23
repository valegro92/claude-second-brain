"""Reconciler persone — estrazione da email.

Vedi brief sezione 5.4.

Algoritmo:
  1. Per ogni record ``.eml`` (source ``email`` o ``email-attachment``),
     estrae ``from``/``to``/``cc``/``reply-to`` dagli ``extras``. Se è
     disponibile il file ``extracted/<sha>/main.md``, prova anche un
     parsing minimale della firma email.
  2. Cluster per dominio: dominio interno (config: ``cliente.dominio``)
     finisce in ``references/persone.md``; dominio esterno finisce in
     ``persone-<dominio-slug>.md``.
  3. Produce bozza per cluster in
     ``_status/drafts/<batch-id>/persone-<slug>.md``.

Privacy:
  * ``safe``: Claude (se mai usato) vedrebbe solo conteggi aggregati,
    mai liste con email. In questo modulo, la modalità ``safe`` evita di
    chiamare l'LLM e si limita a un rendering deterministico.
  * ``full``: gli output contengono liste complete email.
"""
from __future__ import annotations

import logging
import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from scanners._base import FileRecord

logger = logging.getLogger(__name__)


EMAIL_RE = re.compile(r"([A-Za-z0-9._%+-]+)@([A-Za-z0-9.-]+\.[A-Za-z]{2,})")
NAME_EMAIL_RE = re.compile(r"\s*\"?([^<\"]+?)\"?\s*<([^>]+)>")

# Pattern firma sciapo: "Cordiali saluti / Nome Cognome / Ruolo / Tel..."
SIGNATURE_HINTS: tuple[str, ...] = (
    "cordiali saluti",
    "distinti saluti",
    "saluti",
    "best regards",
    "regards",
    "grazie",
    "buona giornata",
)


@dataclass
class PersonaRecord:
    """Una persona estratta. Email è la chiave primaria."""

    email: str
    nomi: set[str] = field(default_factory=set)
    ruoli: set[str] = field(default_factory=set)
    telefoni: set[str] = field(default_factory=set)
    primo_visto: datetime | None = None
    ultimo_visto: datetime | None = None
    n_messaggi: int = 0

    @property
    def dominio(self) -> str:
        return self.email.split("@", 1)[-1].lower() if "@" in self.email else ""

    def best_name(self) -> str:
        if not self.nomi:
            return ""
        # Preferisce il nome più lungo (di solito più completo).
        return max(self.nomi, key=len)


# ---------------------------------------------------------------- helpers
def _slug_dominio(domain: str) -> str:
    """``rossi-srl.it`` → ``rossi-srl``."""
    base = domain.lower().split(".")
    if len(base) >= 2:
        normalized = unicodedata.normalize("NFKD", base[0]).encode("ascii", "ignore").decode("ascii")
        return re.sub(r"[^a-z0-9]+", "-", normalized).strip("-") or "dominio"
    normalized = unicodedata.normalize("NFKD", domain).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", normalized).strip("-") or "dominio"


def _parse_addresses(raw: str | None) -> list[tuple[str, str]]:
    """Estrae lista ``(nome, email)`` da un header tipo ``"A. Rossi" <a@b.it>, ...``."""
    if not raw:
        return []
    out: list[tuple[str, str]] = []
    parts = re.split(r",(?![^<]*>)", str(raw))
    for part in parts:
        part = part.strip()
        if not part:
            continue
        m = NAME_EMAIL_RE.match(part)
        if m:
            out.append((m.group(1).strip(), m.group(2).strip().lower()))
            continue
        em = EMAIL_RE.search(part)
        if em:
            out.append(("", em.group(0).lower()))
    return out


def _read_main(state_dir: Path, sha256: str | None) -> str | None:
    if not sha256:
        return None
    p = state_dir / "extracted" / sha256[:12] / "main.md"
    if not p.exists():
        return None
    try:
        return p.read_text(encoding="utf-8")
    except OSError:
        return None


def _parse_signature(body: str) -> tuple[str | None, str | None]:
    """Best-effort: ritorna (ruolo, telefono) dalla firma email.

    Cerca dopo l'ultimo "Cordiali saluti" o simili, e prende le 6 righe
    successive. Estrae il primo numero di telefono italiano-like e la
    riga immediatamente successiva al nome come ruolo.
    """
    if not body:
        return None, None
    lower = body.lower()
    idx = -1
    for hint in SIGNATURE_HINTS:
        i = lower.rfind(hint)
        if i > idx:
            idx = i
    if idx == -1:
        return None, None
    tail = body[idx : idx + 800]
    phone_match = re.search(r"(?:\+39\s*)?(?:\d[\d\s./-]{6,}\d)", tail)
    phone = phone_match.group(0).strip() if phone_match else None
    # Per il ruolo, prendiamo la seconda riga non-vuota dopo l'hint.
    lines = [ln.strip() for ln in tail.splitlines() if ln.strip()]
    role: str | None = None
    if len(lines) >= 3:
        # lines[0] = "Cordiali saluti", lines[1] tipicamente il nome,
        # lines[2] spesso ruolo / azienda.
        role = lines[2]
    return role, phone


# --------------------------------------------------------------- extract
def extract_persone(
    records: Iterable[FileRecord],
    state_dir: Path,
) -> dict[str, PersonaRecord]:
    """Costruisce il dict ``email → PersonaRecord`` dai record email."""
    persone: dict[str, PersonaRecord] = {}

    def upsert(email: str, name: str, when: datetime | None) -> PersonaRecord:
        email = email.lower().strip()
        if email not in persone:
            persone[email] = PersonaRecord(email=email)
        p = persone[email]
        if name:
            p.nomi.add(name.strip())
        if when is not None:
            if p.primo_visto is None or when < p.primo_visto:
                p.primo_visto = when
            if p.ultimo_visto is None or when > p.ultimo_visto:
                p.ultimo_visto = when
        return p

    for r in records:
        if r.source not in {"email", "email-attachment"}:
            continue
        extras = r.extras or {}
        when = r.mtime
        for header in ("from", "to", "cc", "reply-to"):
            for name, email in _parse_addresses(extras.get(header)):
                p = upsert(email, name, when)
                if header == "from":
                    p.n_messaggi += 1
                    body = _read_main(state_dir, r.sha256)
                    if body:
                        role, phone = _parse_signature(body)
                        if role:
                            p.ruoli.add(role)
                        if phone:
                            p.telefoni.add(phone)
    return persone


def _cluster_by_dominio(
    persone: dict[str, PersonaRecord],
    dominio_interno: str | None,
) -> tuple[dict[str, list[PersonaRecord]], list[PersonaRecord]]:
    """Restituisce ``(cluster_esterni, persone_interne)``."""
    esterni: dict[str, list[PersonaRecord]] = defaultdict(list)
    interni: list[PersonaRecord] = []
    for p in persone.values():
        if dominio_interno and p.dominio == dominio_interno.lower():
            interni.append(p)
        else:
            esterni[p.dominio].append(p)
    return esterni, interni


# ------------------------------------------------------------ rendering
def _render_persone_cluster(
    dominio: str,
    persone: list[PersonaRecord],
    *,
    mode: str,
) -> str:
    """Markdown della bozza ``persone-<dominio>.md``."""
    slug = _slug_dominio(dominio)
    today = datetime.now(timezone.utc).date().isoformat()
    lines = [
        "---",
        "tipo: persone-oggetto",
        f"dominio: {dominio}",
        "owner: TODO",
        "editor: [TODO]",
        "visibilita: azienda",
        "stato: bozza-generata-da-scandagliamento",
        f"privacy: {mode}",
        f"ultima-revisione: {today}",
        "---",
        "",
        f"# Persone — {slug} (BOZZA)",
        "",
        f"> Bozza generata da scandagliamento email. Dominio `{dominio}`, "
        f"{len(persone)} persone rilevate.",
        "> **Validare prima di promuovere a `stato: vivo`** (le note sono "
        "best-effort: nomi e ruoli vanno controllati).",
        "",
    ]
    if mode == "safe":
        lines.extend(
            [
                "## Conteggi aggregati",
                "",
                f"- Persone uniche: {len(persone)}",
                f"- Messaggi totali (solo `from`): {sum(p.n_messaggi for p in persone)}",
                "",
                "_Modalità `safe`: liste con email non incluse. Switch a `full`_",
                "_per averle._",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "## Tabella",
                "",
                "| Nome | Ruolo | Telefono | Email | #msg | Primo | Ultimo |",
                "|---|---|---|---|---|---|---|",
            ]
        )
        for p in sorted(persone, key=lambda x: x.email):
            ruolo = "; ".join(sorted(p.ruoli)) if p.ruoli else "TODO"
            tel = "; ".join(sorted(p.telefoni)) if p.telefoni else "TODO"
            primo = p.primo_visto.date().isoformat() if p.primo_visto else "—"
            ultimo = p.ultimo_visto.date().isoformat() if p.ultimo_visto else "—"
            lines.append(
                f"| {p.best_name() or 'TODO'} | {ruolo} | {tel} | "
                f"{p.email} | {p.n_messaggi} | {primo} | {ultimo} |"
            )
        lines.append("")
    lines.extend(
        [
            "## TODO",
            "",
            "- [ ] Validare ogni riga con il Custode (i ruoli sono estratti da firma email)",
            "- [ ] Decidere se promuovere a `vault/clienti/<slug>/persone.md` o a `references/persone.md`",
            "",
        ]
    )
    return "\n".join(lines) + "\n"


# ------------------------------------------------------------ entry
def run_persone(
    state_dir: Path,
    batch_id: str,
    config: dict,
) -> dict[str, int]:
    """Esegue l'estrazione persone su tutto l'inventario email.

    Args:
        state_dir: cartella ``_status/``.
        batch_id: id del batch corrente.
        config: dict del wizard (legge ``privacy.modalita`` e
            ``cliente.dominio_interno``).

    Returns:
        Stats ``{n_persone, n_cluster_esterni, n_interni}``.
    """
    mode = config.get("privacy", {}).get("modalita", "safe")
    dominio_interno = config.get("cliente", {}).get("dominio_interno")

    inv = state_dir / "inventory"
    records: list[FileRecord] = []
    if inv.exists():
        for jsonl in inv.glob("*.jsonl"):
            if jsonl.name.startswith("_"):
                continue
            with jsonl.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    records.append(FileRecord.from_jsonl(line))

    persone = extract_persone(records, state_dir)
    esterni, interni = _cluster_by_dominio(persone, dominio_interno)

    drafts_dir = state_dir / "drafts" / batch_id
    drafts_dir.mkdir(parents=True, exist_ok=True)

    for dominio, gruppo in esterni.items():
        slug = _slug_dominio(dominio)
        path = drafts_dir / f"persone-{slug}.md"
        path.write_text(_render_persone_cluster(dominio, gruppo, mode=mode), encoding="utf-8")

    if interni:
        path = drafts_dir / "persone-interni.md"
        path.write_text(
            _render_persone_cluster(dominio_interno or "interno", interni, mode=mode),
            encoding="utf-8",
        )

    stats = {
        "n_persone": len(persone),
        "n_cluster_esterni": len(esterni),
        "n_interni": len(interni),
    }
    logger.info("persone done: %s", stats)
    return stats


__all__ = [
    "PersonaRecord",
    "extract_persone",
    "run_persone",
]
