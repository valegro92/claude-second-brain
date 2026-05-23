"""Reconciler: genera bozze di schede oggetto (clienti / fornitori / commesse).

Vedi brief sezione 5.3.

Algoritmo:
  1. Filtra i record categorizzati ``VIVO`` o ``DA_CONSULTARE``.
  2. Raggruppa per "probabile oggetto" usando segnali:
     - nome di cartella nel path (es. ``clienti/rossi-srl/``)
     - menzione dell'oggetto nel nome file (es. ``rossi-srl_offerta_*``)
     - dominio email del mittente per i record di tipo email
  3. Per ogni gruppo plausibile, genera 5 file Regola 01-PMI
     (``<slug>.md``, ``CLAUDE.md``, ``MEMORY.md``, ``tasks.md``, ``persone.md``)
     in ``_status/drafts/<batch-id>/scheda-<slug>/``, parzialmente compilati.
  4. Per le sezioni "Storia" e "Decisioni estratte" (sole sezioni a costo)
     chiama Claude Sonnet con uno snippet del main.md di ciascun file. Logga
     la chiamata in ``_status/cost.jsonl``.

Niente auto-flush sul vault: la cartella ``_status/drafts/...`` resta in
mano alla batch UI per l'approvazione manuale.
"""
from __future__ import annotations

import json
import logging
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from scanners._base import FileRecord

from categorizers._enums import Categoria
from categorizers.claude import _estimate_cost_eur, _extract_text, _extract_usage, _log_cost

logger = logging.getLogger(__name__)

# Modello di default per la sezione narrativa.
DEFAULT_NARRATIVE_MODEL: str = "claude-sonnet-4-5"

# Cartelle del vault da riconoscere nei path.
_FOLDER_HINTS: dict[str, str] = {
    "client": "cliente",
    "clienti": "cliente",
    "customer": "cliente",
    "fornitor": "fornitore",
    "fornitori": "fornitore",
    "supplier": "fornitore",
    "commess": "commessa",
    "commesse": "commessa",
    "project": "commessa",
    "progett": "commessa",
}

# Email che parlano di un oggetto se il path contiene una di queste.
_OBJECT_PATH_TOKENS: tuple[str, ...] = (
    "/clienti/",
    "/fornitori/",
    "/commesse/",
)

# Domini di posta da ignorare per il clustering "oggetto da email".
_GENERIC_EMAIL_DOMAINS: frozenset[str] = frozenset(
    {
        "gmail.com",
        "yahoo.it",
        "yahoo.com",
        "libero.it",
        "hotmail.it",
        "hotmail.com",
        "outlook.it",
        "outlook.com",
        "pec.it",
        "tin.it",
        "tiscali.it",
        "alice.it",
        "virgilio.it",
        "icloud.com",
    }
)


# ---------------------------------------------------------------- modello
@dataclass
class ObjectGroup:
    """Cluster di file che si pensa parlino dello stesso oggetto."""

    slug: str
    tipo: str  # "cliente" | "fornitore" | "commessa"
    records: list[FileRecord] = field(default_factory=list)
    signals: list[str] = field(default_factory=list)

    @property
    def confidence(self) -> float:
        """Confidence grossolana: tanti file + tanti segnali = più fiducia."""
        base = min(1.0, len(self.records) / 10.0)
        sig_bonus = min(0.3, 0.05 * len(set(self.signals)))
        return round(min(1.0, base + sig_bonus), 2)


# -------------------------------------------------------------- helpers
def slugify(value: str) -> str:
    """Slug kebab-case ASCII, robusto su nomi italiani con accenti."""
    normalized = unicodedata.normalize("NFKD", value)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    ascii_only = ascii_only.lower()
    ascii_only = re.sub(r"[^a-z0-9]+", "-", ascii_only)
    return ascii_only.strip("-") or "ignoto"


def _domain_to_slug(domain: str) -> str:
    """``rossi-srl.it`` → ``rossi-srl``. Rimuove TLD."""
    base = domain.lower().split("@")[-1]
    parts = base.split(".")
    if len(parts) >= 2:
        return slugify(parts[0])
    return slugify(base)


def _detect_tipo_from_path(path: str) -> str | None:
    p = path.lower().replace("\\", "/")
    for token, tipo in _FOLDER_HINTS.items():
        if f"/{token}" in p or p.startswith(f"{token}/"):
            return tipo
    return None


def _extract_object_folder_from_path(path: str) -> tuple[str, str] | None:
    """Se il path è tipo ``clienti/rossi-srl/...`` ritorna ``("cliente", "rossi-srl")``."""
    p = path.replace("\\", "/")
    parts = p.split("/")
    for i, part in enumerate(parts):
        plower = part.lower()
        tipo = _FOLDER_HINTS.get(plower)
        if tipo and i + 1 < len(parts):
            child = parts[i + 1]
            if child and not child.startswith("_"):
                return tipo, slugify(child)
    return None


def _extract_email_domain(record: FileRecord) -> str | None:
    """Estrae il dominio dell'oggetto da un record email/attachment."""
    if record.source not in {"email", "email-attachment"}:
        return None
    sender = record.extras.get("from") if record.extras else None
    if not sender:
        return None
    m = re.search(r"@([\w.-]+)", str(sender))
    if not m:
        return None
    domain = m.group(1).lower()
    if domain in _GENERIC_EMAIL_DOMAINS:
        return None
    return domain


# --------------------------------------------------------------- grouping
def group_records(records: Iterable[FileRecord]) -> list[ObjectGroup]:
    """Raggruppa i record per probabile oggetto.

    Strategia: per ogni record raccolto tutti i segnali (cartella, dominio
    email, prefisso del nome). Lo slug derivato dal segnale più affidabile
    diventa la chiave di cluster.
    """
    groups: dict[tuple[str, str], ObjectGroup] = {}

    for r in records:
        if r.categoria not in {Categoria.VIVO.value, Categoria.DA_CONSULTARE.value}:
            continue

        candidates: list[tuple[str, str, str]] = []  # (tipo, slug, signal_label)

        # Segnale 1: cartella nel path.
        folder = _extract_object_folder_from_path(r.path)
        if folder:
            tipo, slug = folder
            candidates.append((tipo, slug, f"folder:{tipo}"))

        # Segnale 2: dominio email.
        domain = _extract_email_domain(r)
        if domain:
            slug = _domain_to_slug(domain)
            tipo = "cliente"  # default: ufficio del mittente è quasi sempre cliente
            candidates.append((tipo, slug, f"email-domain:{domain}"))

        # Segnale 3: prefisso nel nome file (``rossi-srl_offerta_*``).
        stem = r.name.split(".", 1)[0]
        m = re.match(r"^([a-z0-9]+(?:[-_][a-z0-9]+)*)[_-](?:offerta|ordine|contratto|fattura|capitolato|preventivo)",
                     stem.lower())
        if m:
            slug = slugify(m.group(1).replace("_", "-"))
            tipo = _detect_tipo_from_path(r.path) or "cliente"
            candidates.append((tipo, slug, f"name-prefix:{slug}"))

        if not candidates:
            continue
        # Tiene il primo (priorità folder > email > name).
        tipo, slug, signal = candidates[0]
        if not slug or slug == "ignoto":
            continue
        key = (tipo, slug)
        if key not in groups:
            groups[key] = ObjectGroup(slug=slug, tipo=tipo)
        groups[key].records.append(r)
        groups[key].signals.append(signal)

    # Filtra cluster troppo piccoli per essere significativi.
    return [g for g in groups.values() if len(g.records) >= 2]


# ----------------------------------------------------------------- LLM
_NARRATIVE_SYSTEM = (
    "Sei un consulente che scrive note di onboarding per una PMI italiana. "
    "Riceverai snippet di file (markdown) relativi a un singolo oggetto "
    "(cliente, fornitore o commessa). Produci due brevi sezioni in italiano: "
    "1) ## Storia (max 5 bullet datati), 2) ## Decisioni estratte (max 5 bullet). "
    "Niente preamboli, niente inventato: se un fatto non è nei dati, non scriverlo. "
    "Formato di output: markdown puro, due sezioni nell'ordine indicato."
)


def _build_narrative_prompt(group: ObjectGroup, state_dir: Path, max_files: int = 8) -> str:
    """Costruisce il prompt utente con snippet dei main.md correlati."""
    blocks: list[str] = [
        f"Oggetto: {group.tipo} `{group.slug}`",
        f"File rilevanti ({len(group.records)} totali, allegati i primi {max_files}):",
        "",
    ]
    for r in group.records[:max_files]:
        blocks.append(f"### {r.name} ({r.source}, {r.mtime.isoformat()})")
        snippet = _read_main_snippet(state_dir, r.sha256)
        blocks.append(snippet or "_(estrazione non disponibile)_")
        blocks.append("")
    return "\n".join(blocks)


def _read_main_snippet(state_dir: Path, sha256: str | None, chars: int = 1500) -> str | None:
    if not sha256:
        return None
    p = state_dir / "extracted" / sha256[:12] / "main.md"
    if not p.exists():
        return None
    try:
        return p.read_text(encoding="utf-8")[:chars]
    except OSError:
        return None


def _call_narrative(
    group: ObjectGroup,
    state_dir: Path,
    model: str,
    client: Any | None,
    config: dict[str, Any] | None = None,
) -> str:
    """Chiama Claude Sonnet per generare la sezione Storia + Decisioni.

    Restituisce sempre un markdown (vuoto se la call fallisce, mai eccezione
    propagata: la bozza viene comunque generata con placeholder).

    Step 3: il client è ottenuto via :func:`wiki.llm.get_llm_client`, che
    sceglie il backend (anthropic_api standard o bedrock) in base al
    ``config`` del cliente.
    """
    if client is None:
        # Import locale per evitare import circolari (wiki/llm dipende da
        # categorizers/_enums in trasparenza via futuri test).
        from wiki.llm import get_llm_client

        try:
            client = get_llm_client(config or {}, state_dir=state_dir)
        except RuntimeError as exc:
            logger.warning("LLM non disponibile (%s), niente sezione narrativa", exc)
            return _narrative_placeholder()

    user_prompt = _build_narrative_prompt(group, state_dir)
    try:
        response = client.messages.create(
            model=model,
            max_tokens=800,
            system=_NARRATIVE_SYSTEM,
            messages=[{"role": "user", "content": user_prompt}],
        )
    except Exception as exc:  # pragma: no cover - fail-soft
        logger.exception("Errore chiamata narrativa per %s: %s", group.slug, exc)
        return _narrative_placeholder()

    text = _extract_text(response)
    tokens_in, tokens_out = _extract_usage(response)
    if state_dir is not None:
        cost = _estimate_cost_eur(model, tokens_in, tokens_out)
        _log_cost(
            state_dir,
            {
                "ts": datetime.now(timezone.utc).isoformat(),
                "stage": "scheda-narrativa",
                "model": model,
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "cost_eur": cost,
                "slug": group.slug,
                "tipo": group.tipo,
            },
        )
    return text or _narrative_placeholder()


def _narrative_placeholder() -> str:
    return (
        "## Storia\n\n"
        "_TODO: nessuna sezione narrativa generata (LLM non disponibile)._\n\n"
        "## Decisioni estratte\n\n"
        "_TODO: nessuna decisione estratta automaticamente._\n"
    )


# ------------------------------------------------------------ rendering
def _frontmatter(tipo_scheda: str, slug: str, group: ObjectGroup) -> str:
    """Frontmatter YAML standard per le bozze."""
    today = datetime.now(timezone.utc).date().isoformat()
    lines = [
        "---",
        f"tipo: {tipo_scheda}",
        f"{group.tipo}: {slug}",
        "owner: TODO",
        "editor: [TODO]",
        "visibilita: azienda",
        "stato: bozza-generata-da-scandagliamento",
        f"confidence: {group.confidence}",
        f"ultima-revisione: {today}",
        "revisore: TODO",
        "---",
        "",
    ]
    return "\n".join(lines)


def _render_moc(group: ObjectGroup, narrative: str) -> str:
    """File principale: ``<slug>.md`` (MOC dell'oggetto)."""
    tipo_label = {
        "cliente": "scheda cliente",
        "fornitore": "scheda fornitore",
        "commessa": "scheda commessa",
    }.get(group.tipo, "scheda")
    tipo_scheda = {
        "cliente": "scheda-cliente",
        "fornitore": "scheda-fornitore",
        "commessa": "scheda-commessa",
    }.get(group.tipo, "scheda")
    head = _frontmatter(tipo_scheda, group.slug, group)
    body = [
        f"# {group.slug} — {tipo_label} (MOC) — BOZZA",
        "",
        f"> Bozza generata dallo scandagliamento (confidence {group.confidence}).",
        f"> Cluster di {len(group.records)} file (segnali: "
        f"{', '.join(sorted(set(group.signals)))}).",
        "",
        "## Dati anagrafica",
        "",
        "- **Ragione sociale**: TODO",
        "- **P.IVA**: TODO",
        "- **Sede**: TODO",
        "- **Settore**: TODO",
        "- **Stato**: TODO",
        "",
        "## I 5 file Regola 01-PMI",
        "",
        f"- [[{group.slug}|{group.slug}.md]] — questo file, MOC",
        "- [[CLAUDE]] — istruzioni Claude specifiche",
        "- [[MEMORY]] — decisioni datate",
        "- [[tasks]] — task aperti",
        "- [[persone]] — chi è chi",
        "",
        narrative.strip(),
        "",
        "## File rilevati dallo scandagliamento",
        "",
        "| Nome | Source | Mtime | Categoria | Confidence |",
        "|---|---|---|---|---|",
    ]
    for r in group.records[:50]:
        body.append(
            f"| `{r.name}` | {r.source} | {r.mtime.isoformat()} | "
            f"{r.categoria or '-'} | {r.confidence or '-'} |"
        )
    if len(group.records) > 50:
        body.append(f"| ... | ... | ... | ... | ... ({len(group.records) - 50} altri) |")
    body.extend(
        [
            "",
            "## TODO espliciti",
            "",
            "- [ ] Validare ragione sociale e P.IVA",
            "- [ ] Confermare slug (`" + group.slug + "`) o rinominare prima del flush",
            "- [ ] Compilare persone.md con la tabella referenti",
            "- [ ] Rivedere le decisioni estratte (sezione sopra) prima di approvare",
            "",
        ]
    )
    return head + "\n".join(body) + "\n"


def _render_claude_md(group: ObjectGroup) -> str:
    head = _frontmatter("claude-istruzioni", group.slug, group)
    body = [
        f"# CLAUDE.md — {group.slug} (BOZZA)",
        "",
        "> Istruzioni Claude specifiche per questo oggetto. Bozza autogenerata,",
        "> da compilare con il Custode.",
        "",
        "## Contesto",
        "",
        "TODO: scrivere 3-5 righe di contesto.",
        "",
        "## Regole specifiche",
        "",
        "- TODO: regola tono comunicazioni",
        "- TODO: cosa non menzionare",
        "- TODO: chi approva cosa",
        "",
        "## Persone chiave",
        "",
        "Vedi [[persone]] per la tabella completa.",
        "",
        "## Output tipici di Claude",
        "",
        "- TODO",
        "",
    ]
    return head + "\n".join(body) + "\n"


def _render_memory(group: ObjectGroup, narrative: str) -> str:
    head = _frontmatter("memory-oggetto", group.slug, group)
    body = [
        f"# MEMORY — {group.slug} (BOZZA)",
        "",
        "> Decisioni datate. Bozza autogenerata dallo scandagliamento, da",
        "> validare prima di rendere ``stato: vivo``.",
        "",
        narrative.strip(),
        "",
        "## Vincoli e preferenze",
        "",
        "_TODO: estratti manualmente o da successive call._",
        "",
        "## Storia / contesto",
        "",
        "_TODO_.",
        "",
    ]
    return head + "\n".join(body) + "\n"


def _render_tasks(group: ObjectGroup) -> str:
    head = _frontmatter("tasks", group.slug, group)
    body = [
        f"# Tasks — {group.slug} (BOZZA)",
        "",
        "> Task aperti sull'oggetto. Bozza autogenerata: la prima riga è il",
        "> task di validazione della scheda stessa.",
        "",
        "## Aperti",
        "",
        f"- [ ] **alta** — Validare e approvare la scheda `{group.slug}` "
        "(confidence " + str(group.confidence) + "). Owner: TODO.",
        "- [ ] **media** — Compilare persone.md con i referenti reali. Owner: TODO.",
        "",
        "## Fatti (ultimi 30 giorni)",
        "",
        "_(vuoto)_",
        "",
    ]
    return head + "\n".join(body) + "\n"


def _render_persone(group: ObjectGroup) -> str:
    head = _frontmatter("persone-oggetto", group.slug, group)
    body = [
        f"# Persone — {group.slug} (BOZZA)",
        "",
        "> Chi è chi. Bozza autogenerata: i nomi qui sotto sono solo i",
        "> mittenti email rilevati dallo scandagliamento, da verificare uno",
        "> per uno.",
        "",
        f"## Lato {group.tipo}",
        "",
        "| Nome | Ruolo | Email | Note |",
        "|---|---|---|---|",
    ]
    # Estrae mittenti dai record email del gruppo, dedup.
    senders: dict[str, str] = {}
    for r in group.records:
        if r.source in {"email", "email-attachment"}:
            sender = (r.extras or {}).get("from") if r.extras else None
            if sender:
                m = re.match(r"\s*([^<]+)?<([^>]+)>", str(sender))
                if m:
                    name = (m.group(1) or "TODO").strip()
                    email = m.group(2).strip().lower()
                else:
                    name = "TODO"
                    email = str(sender).strip().lower()
                senders.setdefault(email, name)
    if not senders:
        body.append("| TODO | TODO | TODO | _nessun mittente estratto_ |")
    else:
        for email, name in sorted(senders.items()):
            body.append(f"| {name} | TODO | {email} | _da validare_ |")
    body.extend(
        [
            "",
            "## Lato nostro",
            "",
            "| Iniziali | Nome | Ruolo verso questo oggetto |",
            "|---|---|---|",
            "| TODO | TODO | TODO |",
            "",
        ]
    )
    return head + "\n".join(body) + "\n"


# --------------------------------------------------------- entry point
def run_schede(
    state_dir: Path,
    batch_id: str,
    *,
    model: str = DEFAULT_NARRATIVE_MODEL,
    client: Any | None = None,
    call_llm: bool = True,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Esegue il reconciler schede.

    Args:
        state_dir: cartella ``_status/``.
        batch_id: identificativo del batch (es. ``2026-05-23-001``).
        model: modello Sonnet per la sezione narrativa.
        client: client LLM preconfezionato (per test). Se ``None``, viene
            costruito via :func:`wiki.llm.get_llm_client` dal ``config``.
        call_llm: se False, salta la chiamata LLM e usa solo placeholder
            (utile in test E2E e per dry-run).
        config: config cliente (per scelta provider LLM in Step 3).

    Returns:
        Dict con statistiche: ``{n_groups, slugs}``.
    """
    inv = state_dir / "inventory"
    if not inv.exists():
        logger.warning("Nessun inventory in %s", inv)
        return {"n_groups": 0, "slugs": []}

    records: list[FileRecord] = []
    for jsonl in inv.glob("*.jsonl"):
        if jsonl.name.startswith("_"):
            continue
        with jsonl.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                records.append(FileRecord.from_jsonl(line))

    groups = group_records(records)
    drafts_root = state_dir / "drafts" / batch_id
    drafts_root.mkdir(parents=True, exist_ok=True)

    written_slugs: list[str] = []
    for group in groups:
        if call_llm:
            narrative = _call_narrative(group, state_dir, model, client, config=config)
        else:
            narrative = _narrative_placeholder()
        out_dir = drafts_root / f"scheda-{group.tipo}-{group.slug}"
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / f"{group.slug}.md").write_text(_render_moc(group, narrative), encoding="utf-8")
        (out_dir / "CLAUDE.md").write_text(_render_claude_md(group), encoding="utf-8")
        (out_dir / "MEMORY.md").write_text(_render_memory(group, narrative), encoding="utf-8")
        (out_dir / "tasks.md").write_text(_render_tasks(group), encoding="utf-8")
        (out_dir / "persone.md").write_text(_render_persone(group), encoding="utf-8")
        # Index del gruppo, per la batch UI.
        (out_dir / "_group.json").write_text(
            json.dumps(
                {
                    "slug": group.slug,
                    "tipo": group.tipo,
                    "confidence": group.confidence,
                    "n_records": len(group.records),
                    "signals": sorted(set(group.signals)),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        written_slugs.append(group.slug)
        logger.info(
            "scheda generata: tipo=%s slug=%s n=%d conf=%.2f",
            group.tipo,
            group.slug,
            len(group.records),
            group.confidence,
        )

    return {"n_groups": len(groups), "slugs": written_slugs}


__all__ = [
    "DEFAULT_NARRATIVE_MODEL",
    "ObjectGroup",
    "group_records",
    "run_schede",
    "slugify",
]
