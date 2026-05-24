"""Dashboard di sintesi per il Custode (Step 3).

Aggrega lo stato di un cliente leggendo i file di runtime in ``_status/``:

  * ``_status/inventory/*.jsonl`` — record per sorgente (uno per scanner)
  * ``_status/audit/decisions.jsonl`` — decisioni della batch UI (Valentino)
  * ``_status/audit/categorize.jsonl`` — log decisioni categorizer
  * ``_status/cost.jsonl`` — token + costo Claude per call
  * ``_status/drafts/<batch>/_state.json`` — stato bozze in approvazione

Calcola metriche e renderizza un report ``dashboard.html`` (auto-contenuto,
CSS inline, SVG inline per le bar-chart, niente CDN) e in parallelo un
``INDEX.md`` per chi preferisce leggere in markdown.

Note di perimetro:
  * Il modulo non scrive mai dentro ``vault/``: lo legge in sola lettura
    per calcolare la "salute" (file orfani, persone orfane, conformità
    Regola 01-PMI).
  * Tutto idempotente: rigenerabile dopo ogni stage. Costo computazionale
    O(n_record) dove n è dell'ordine di 50k file al massimo.
  * Niente emoji nei testi prodotti (regola di delivery).
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Cinque categorie operative del Custode (vedi docs/05-manuale-custode.md Fase 2).
CATEGORIE = ("vivo", "da-consultare", "archivio", "cestino", "da-chiarire")

# Stati delle bozze nella batch UI (vedi categorizers/_enums.StatoBozza).
STATI_BOZZA = ("pending", "approved", "rejected", "edited", "parked")

# I 5 file Regola 01-PMI che ogni cartella di oggetto (cliente/fornitore/commessa) deve avere.
REGOLA_01_PMI = ("CLAUDE.md", "MEMORY.md", "tasks.md", "persone.md")
# Il quinto file ha nome variabile (lo slug.md): controllato a parte.

# Soglia di dormienza per un oggetto del vault: nessuna modifica da N giorni.
DORMIENTE_GIORNI = 90


# ---------------------------------------------------------------- modello


@dataclass
class SourceStats:
    """Contatori aggregati per una singola sorgente di inventory."""

    name: str
    discovered: int = 0
    filtered_in_perimetro: int = 0
    extracted: int = 0
    categorized: int = 0


@dataclass
class CategoryStats:
    """Conteggi per categoria, con percentuali."""

    counts: dict[str, int] = field(default_factory=lambda: dict.fromkeys(CATEGORIE, 0))

    @property
    def total(self) -> int:
        return sum(self.counts.values())

    def percent(self, cat: str) -> float:
        tot = self.total
        if tot == 0:
            return 0.0
        return round(100.0 * self.counts.get(cat, 0) / tot, 1)


@dataclass
class DraftStats:
    """Conteggi bozze (per stato) e batch attivi."""

    counts: dict[str, int] = field(default_factory=lambda: dict.fromkeys(STATI_BOZZA, 0))
    batches: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return sum(self.counts.values())


@dataclass
class VaultHealth:
    """Indicatori di salute del vault (sola lettura su vault/)."""

    file_orfani: list[str] = field(default_factory=list)
    persone_orfane: list[str] = field(default_factory=list)
    clienti_dormienti: list[str] = field(default_factory=list)
    regola_01_pmi_mancanti: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class CostStats:
    """Riepilogo costi Claude letto da cost.jsonl."""

    totale_eur: float = 0.0
    per_modello: dict[str, float] = field(default_factory=dict)
    per_stage: dict[str, float] = field(default_factory=dict)
    n_chiamate: int = 0


@dataclass
class DashboardData:
    """Tutte le metriche aggregate per il rendering."""

    cliente: str
    generato_il: datetime
    sources: list[SourceStats]
    categorie: CategoryStats
    bozze: DraftStats
    salute: VaultHealth
    costi: CostStats
    next_actions: list[str]


# -------------------------------------------------------- helper lettura


def _iter_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    """Itera le righe JSON di un .jsonl, tollerante a righe corrotte."""
    if not path.exists():
        return
    try:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue
    except OSError as exc:  # pragma: no cover - difensivo
        logger.warning("Impossibile leggere %s: %s", path, exc)


def _load_inventory(state_dir: Path) -> dict[str, list[dict[str, Any]]]:
    """Carica tutti i ``_status/inventory/*.jsonl`` indicizzati per sorgente.

    Restituisce ``{source_name: [record, ...]}``. I file il cui nome inizia
    con ``_`` (es. ``_by_hash.json``) sono saltati.
    """
    inv = state_dir / "inventory"
    if not inv.exists():
        return {}
    out: dict[str, list[dict[str, Any]]] = {}
    for jsonl in sorted(inv.glob("*.jsonl")):
        if jsonl.name.startswith("_"):
            continue
        out[jsonl.stem] = list(_iter_jsonl(jsonl))
    return out


# ------------------------------------------------------- calcolo metriche


def _compute_source_stats(
    inventory: dict[str, list[dict[str, Any]]],
    extracted_dir: Path,
) -> list[SourceStats]:
    """Conteggi per sorgente: scoperti / perimetro / estratti / categorizzati."""
    extracted_shas: set[str] = set()
    if extracted_dir.exists():
        for sha_dir in extracted_dir.iterdir():
            if sha_dir.is_dir():
                extracted_shas.add(sha_dir.name)

    stats: list[SourceStats] = []
    for source, records in sorted(inventory.items()):
        ss = SourceStats(name=source)
        ss.discovered = len(records)
        # "Filtrato per perimetro" = ha passato i filtri scanner ed è nel JSONL.
        # Nei nostri scanner i record finiscono in JSONL solo se passano i
        # filtri (vedi Scanner.apply_filters), quindi tutti i record letti
        # sono già nel perimetro.
        ss.filtered_in_perimetro = len(records)
        for rec in records:
            sha = rec.get("sha256")
            if sha and sha[:12] in extracted_shas:
                ss.extracted += 1
            if rec.get("categoria"):
                ss.categorized += 1
        stats.append(ss)
    return stats


def _compute_category_stats(
    inventory: dict[str, list[dict[str, Any]]],
) -> CategoryStats:
    """Conteggio per categoria su tutti i record categorizzati."""
    out = CategoryStats()
    for records in inventory.values():
        for rec in records:
            cat = rec.get("categoria")
            if not cat:
                continue
            if cat in out.counts:
                out.counts[cat] += 1
            else:
                # Categoria sconosciuta -> da-chiarire.
                out.counts["da-chiarire"] += 1
    return out


def _compute_draft_stats(state_dir: Path) -> DraftStats:
    """Aggrega ``_state.json`` di ogni batch in ``_status/drafts/``."""
    out = DraftStats()
    drafts_dir = state_dir / "drafts"
    if not drafts_dir.exists():
        return out
    for batch in sorted(drafts_dir.iterdir()):
        if not batch.is_dir():
            continue
        out.batches.append(batch.name)
        drafts = list(batch.glob("*.md"))
        # Includi anche le bozze annidate (es. scheda-cliente-<slug>/*.md).
        for sub in batch.iterdir():
            if sub.is_dir():
                drafts.extend(sub.glob("*.md"))
        state_file = batch / "_state.json"
        state: dict[str, dict[str, Any]] = {}
        if state_file.exists():
            try:
                state = json.loads(state_file.read_text(encoding="utf-8")) or {}
            except (json.JSONDecodeError, OSError):
                state = {}
        # Per ogni draft conta lo stato registrato, o PENDING come default.
        for draft in drafts:
            entry = state.get(draft.name, {})
            stato = entry.get("stato", "pending")
            if stato in out.counts:
                out.counts[stato] += 1
            else:
                out.counts["pending"] += 1
    return out


def _compute_cost_stats(state_dir: Path) -> CostStats:
    """Aggrega ``_status/cost.jsonl`` per modello e stage."""
    out = CostStats()
    cost_file = state_dir / "cost.jsonl"
    for rec in _iter_jsonl(cost_file):
        out.n_chiamate += 1
        # Tolleranza chiavi: ``eur`` (vecchio) o ``cost_eur`` (nuovo).
        eur_raw = rec.get("cost_eur", rec.get("eur", 0)) or 0
        try:
            eur = float(eur_raw)
        except (TypeError, ValueError):
            eur = 0.0
        out.totale_eur += eur
        model = str(rec.get("model", "unknown"))
        stage = str(rec.get("stage", "unknown"))
        out.per_modello[model] = round(out.per_modello.get(model, 0.0) + eur, 6)
        out.per_stage[stage] = round(out.per_stage.get(stage, 0.0) + eur, 6)
    out.totale_eur = round(out.totale_eur, 6)
    return out


# -------------------------------------------------- salute vault (read-only)

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)


def _read_frontmatter(md_path: Path) -> dict[str, str]:
    """Legge il blocco YAML in testa a un .md, parsing line-based (no PyYAML).

    Sufficiente per estrarre chiavi semplici ``key: value``; ignora le
    strutture annidate (che qui non ci servono).
    """
    try:
        text = md_path.read_text(encoding="utf-8")
    except OSError:
        return {}
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}
    out: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        out[key.strip()] = value.strip().strip('"').strip("'")
    return out


def _compute_vault_health(vault_dir: Path | None) -> VaultHealth:
    """Calcola gli indicatori di salute del vault.

    Se ``vault_dir`` non esiste (caso test / pre-bootstrap) ritorna metriche
    vuote ma valide.
    """
    out = VaultHealth()
    if vault_dir is None or not vault_dir.exists():
        return out

    # 1) File orfani: .md senza frontmatter (o senza chiave "tipo") nelle
    #    aree principali del vault. Escludiamo i template ``_esempio``.
    aree = ("clienti", "fornitori", "commesse", "reparti", "decisioni", "references")
    for area in aree:
        area_dir = vault_dir / area
        if not area_dir.exists():
            continue
        for md in area_dir.rglob("*.md"):
            # Salta i template _esempio.
            if any(part.startswith("_esempio") for part in md.relative_to(vault_dir).parts):
                continue
            fm = _read_frontmatter(md)
            if not fm or "tipo" not in fm:
                out.file_orfani.append(str(md.relative_to(vault_dir)))

    # 2) Persone orfane: persone citate nei persone.md degli oggetti che non
    #    compaiono nel registro ``vault/references/persone.md`` (per i
    #    referenti interni) o che hanno un marker "TODO".
    riferimento_interno = vault_dir / "references" / "persone.md"
    interni: set[str] = set()
    if riferimento_interno.exists():
        try:
            txt = riferimento_interno.read_text(encoding="utf-8")
            # Cattura email interne (formato "<x>@<dominio>") e iniziali maiuscole.
            for m in re.finditer(r"\b([A-Z]{2,3})\b", txt):
                interni.add(m.group(1))
        except OSError:
            pass

    for persone_md in vault_dir.rglob("persone.md"):
        rel = persone_md.relative_to(vault_dir)
        # Skip il registro interno stesso e i template _esempio.
        if str(rel) == "references/persone.md":
            continue
        if any(part.startswith("_esempio") for part in rel.parts):
            continue
        try:
            txt = persone_md.read_text(encoding="utf-8")
        except OSError:
            continue
        # Cerca iniziali interne menzionate che non sono nel registro.
        for m in re.finditer(r"\bIniziali[^\n]*\n.*?\|\s*([A-Z]{2,3})\s*\|", txt, re.DOTALL):
            iniz = m.group(1)
            if iniz != "TODO" and iniz not in interni:
                out.persone_orfane.append(f"{rel}: {iniz}")

    # 3) Clienti dormienti: cartelle ``vault/clienti/<slug>/`` con file
    #    modificati l'ultima volta più di N giorni fa.
    soglia = datetime.now(UTC) - timedelta(days=DORMIENTE_GIORNI)
    clienti_dir = vault_dir / "clienti"
    if clienti_dir.exists():
        for client in sorted(clienti_dir.iterdir()):
            if not client.is_dir() or client.name.startswith("_"):
                continue
            mtimes = [
                datetime.fromtimestamp(p.stat().st_mtime, tz=UTC)
                for p in client.rglob("*")
                if p.is_file()
            ]
            if not mtimes:
                continue
            ultima = max(mtimes)
            if ultima < soglia:
                out.clienti_dormienti.append(
                    f"{client.name} (ultima mod: {ultima.date().isoformat()})"
                )

    # 4) Regola 01-PMI: per ogni oggetto (clienti/fornitori/commesse) verifica
    #    che esistano i 5 file canonici.
    for area in ("clienti", "fornitori", "commesse"):
        area_dir = vault_dir / area
        if not area_dir.exists():
            continue
        for obj in sorted(area_dir.iterdir()):
            if not obj.is_dir() or obj.name.startswith("_"):
                continue
            mancanti = [name for name in REGOLA_01_PMI if not (obj / name).exists()]
            # Il "5o file" è lo slug del cliente.md.
            slug_md = obj / f"{obj.name}.md"
            if not slug_md.exists():
                mancanti.append(f"{obj.name}.md")
            if mancanti:
                out.regola_01_pmi_mancanti.append(
                    {"area": area, "oggetto": obj.name, "mancanti": mancanti}
                )

    return out


# ---------------------------------------------------- prossime azioni


def _suggest_next_actions(
    sources: list[SourceStats],
    categorie: CategoryStats,
    bozze: DraftStats,
    salute: VaultHealth,
) -> list[str]:
    """Lista breve di prossime azioni suggerite (priorità top-down)."""
    out: list[str] = []
    # 1) Inventory vuoto.
    if not sources:
        out.append("Lanciare `wiki scan` per popolare l'inventory.")
    # 2) Estrazione mancante.
    da_estrarre = sum(s.discovered - s.extracted for s in sources)
    if da_estrarre > 0:
        out.append(f"Estrarre i {da_estrarre} file ancora non processati (`wiki extract`).")
    # 3) Categorizzazione mancante.
    da_categorizzare = sum(s.discovered - s.categorized for s in sources)
    if da_categorizzare > 0:
        out.append(
            f"Categorizzare i {da_categorizzare} file ancora senza categoria (`wiki categorize`)."
        )
    # 4) Bozze pending da approvare.
    if bozze.counts.get("pending", 0) > 0:
        out.append(
            f"Approvare le {bozze.counts['pending']} bozze pending in batch UI (`wiki approve`)."
        )
    # 5) DA_CHIARIRE alti.
    if categorie.total > 0 and categorie.percent("da-chiarire") > 20.0:
        out.append(
            f"DA-CHIARIRE al {categorie.percent('da-chiarire')}%: rivedere le regole categorizer."
        )
    # 6) File orfani.
    if salute.file_orfani:
        out.append(f"{len(salute.file_orfani)} file nel vault senza frontmatter: ripulire.")
    # 7) Regola 01-PMI.
    if salute.regola_01_pmi_mancanti:
        out.append(f"{len(salute.regola_01_pmi_mancanti)} oggetti non conformi alla Regola 01-PMI.")
    if not out:
        out.append("Nessuna azione urgente: vault in salute.")
    return out


# ------------------------------------------------------- entry point


def collect_metrics(state_dir: Path, vault_dir: Path | None, cliente: str) -> DashboardData:
    """Aggrega tutte le metriche in un :class:`DashboardData`.

    Args:
        state_dir: cartella ``_status/<slug>/`` del cliente corrente.
        vault_dir: cartella ``vault/`` (sola lettura). ``None`` se non disponibile.
        cliente: slug del cliente, per il titolo.

    Returns:
        Snapshot pronto per il rendering.
    """
    inventory = _load_inventory(state_dir)
    sources = _compute_source_stats(inventory, state_dir / "extracted")
    categorie = _compute_category_stats(inventory)
    bozze = _compute_draft_stats(state_dir)
    costi = _compute_cost_stats(state_dir)
    salute = _compute_vault_health(vault_dir)
    next_actions = _suggest_next_actions(sources, categorie, bozze, salute)
    return DashboardData(
        cliente=cliente,
        generato_il=datetime.now(UTC),
        sources=sources,
        categorie=categorie,
        bozze=bozze,
        salute=salute,
        costi=costi,
        next_actions=next_actions,
    )


# ------------------------------------------------------- rendering

# Palette discreta, coerente con stile Pico minimal. Niente CDN.
_CAT_COLORS = {
    "vivo": "#2e7d32",
    "da-consultare": "#1565c0",
    "archivio": "#6d4c41",
    "cestino": "#9e9e9e",
    "da-chiarire": "#ef6c00",
}


def _render_bar_chart_svg(counts: dict[str, int], width: int = 480, height: int = 180) -> str:
    """Renderizza un bar chart SVG inline a partire da un mapping categoria→count."""
    items = [(k, counts.get(k, 0)) for k in CATEGORIE]
    max_val = max((v for _, v in items), default=0) or 1
    bar_w = width // (len(items) + 1)
    pad = bar_w // 2
    parts: list[str] = [
        f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" '
        f'role="img" aria-label="categorie">',
        "<style>text{font-family:system-ui,sans-serif;font-size:11px;fill:#333}</style>",
    ]
    for i, (cat, val) in enumerate(items):
        bar_h = int((val / max_val) * (height - 40))
        x = pad + i * bar_w
        y = height - bar_h - 20
        color = _CAT_COLORS.get(cat, "#666")
        parts.append(
            f'<rect x="{x}" y="{y}" width="{bar_w - 8}" height="{bar_h}" fill="{color}" rx="2"/>'
        )
        parts.append(
            f'<text x="{x + (bar_w - 8) // 2}" y="{y - 4}" text-anchor="middle">{val}</text>'
        )
        parts.append(
            f'<text x="{x + (bar_w - 8) // 2}" y="{height - 4}" text-anchor="middle">{cat}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


def _render_html(data: DashboardData) -> str:
    """Renderizza la dashboard HTML usando il template Jinja in ``wiki/templates/``."""
    try:
        from jinja2 import Environment, FileSystemLoader, select_autoescape
    except ImportError as exc:  # pragma: no cover - jinja2 è in dipendenze hard
        raise RuntimeError("jinja2 non disponibile: installa le dipendenze del toolkit") from exc

    tpl_dir = Path(__file__).resolve().parent / "templates"
    env = Environment(
        loader=FileSystemLoader(str(tpl_dir)),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["eur"] = lambda v: f"{float(v):.2f}"
    env.filters["pct"] = lambda v: f"{float(v):.1f}%"
    tpl = env.get_template("dashboard.html.j2")
    chart_svg = _render_bar_chart_svg(data.categorie.counts)
    return tpl.render(
        data=data,
        chart_svg=chart_svg,
        categorie_lista=CATEGORIE,
        cat_colors=_CAT_COLORS,
        stati_bozza=STATI_BOZZA,
    )


def _render_index_md(data: DashboardData) -> str:
    """Versione markdown equivalente, per chi preferisce leggere a riga di comando."""
    lines: list[str] = [
        f"# Dashboard — {data.cliente}",
        "",
        f"Generata: {data.generato_il.isoformat(timespec='seconds')}",
        f"Costo Claude cumulativo: EUR {data.costi.totale_eur:.2f} "
        f"({data.costi.n_chiamate} chiamate)",
        "",
        "## Sorgenti",
        "",
        "| Sorgente | Scoperti | Perimetro | Estratti | Categorizzati |",
        "|---|---:|---:|---:|---:|",
    ]
    if not data.sources:
        lines.append("| _(nessuna sorgente)_ | - | - | - | - |")
    for s in data.sources:
        lines.append(
            f"| {s.name} | {s.discovered} | {s.filtered_in_perimetro} | "
            f"{s.extracted} | {s.categorized} |"
        )
    lines.extend(["", "## Categorizzazione", ""])
    if data.categorie.total == 0:
        lines.append("_(nessun file categorizzato)_")
    else:
        lines.append("| Categoria | Count | % |")
        lines.append("|---|---:|---:|")
        for cat in CATEGORIE:
            lines.append(
                f"| {cat} | {data.categorie.counts[cat]} | {data.categorie.percent(cat):.1f}% |"
            )
    lines.extend(["", "## Bozze", ""])
    lines.append("| Stato | Count |")
    lines.append("|---|---:|")
    for st in STATI_BOZZA:
        lines.append(f"| {st} | {data.bozze.counts[st]} |")
    lines.append(f"\nBatch totali: {len(data.bozze.batches)}.")

    lines.extend(["", "## Salute vault", ""])
    lines.append(f"- File orfani (no frontmatter): {len(data.salute.file_orfani)}")
    lines.append(f"- Persone orfane: {len(data.salute.persone_orfane)}")
    lines.append(
        f"- Clienti dormienti (>{DORMIENTE_GIORNI}gg): {len(data.salute.clienti_dormienti)}"
    )
    lines.append(f"- Oggetti non conformi Regola 01-PMI: {len(data.salute.regola_01_pmi_mancanti)}")

    if data.salute.regola_01_pmi_mancanti:
        lines.extend(["", "### Dettaglio non conformi", ""])
        for item in data.salute.regola_01_pmi_mancanti:
            lines.append(
                f"- `{item['area']}/{item['oggetto']}/`: mancano {', '.join(item['mancanti'])}"
            )

    lines.extend(["", "## Costi", "", f"Totale: EUR {data.costi.totale_eur:.2f}", ""])
    if data.costi.per_modello:
        lines.append("**Per modello**")
        for m, v in sorted(data.costi.per_modello.items()):
            lines.append(f"- {m}: EUR {v:.4f}")
        lines.append("")
    if data.costi.per_stage:
        lines.append("**Per stage**")
        for st, v in sorted(data.costi.per_stage.items()):
            lines.append(f"- {st}: EUR {v:.4f}")
        lines.append("")

    lines.extend(["## Prossime azioni", ""])
    for action in data.next_actions:
        lines.append(f"- {action}")
    lines.append("")
    return "\n".join(lines)


def generate_dashboard(
    state_dir: Path,
    vault_dir: Path | None,
    output_path: Path,
    *,
    cliente: str | None = None,
    index_md_path: Path | None = None,
) -> dict[str, Path]:
    """Genera la dashboard HTML + INDEX.md per un cliente.

    Args:
        state_dir: cartella ``_status/<slug>/`` del cliente corrente.
        vault_dir: cartella ``vault/`` (read-only). ``None`` se non disponibile.
        output_path: path di destinazione dell'HTML (es. ``_status/<slug>/dashboard.html``).
        cliente: slug del cliente; se omesso si deduce dal nome di ``state_dir``.
        index_md_path: path di destinazione dell'INDEX.md; default = stessa
            cartella di ``output_path`` con nome ``INDEX.md``.

    Returns:
        Mappa ``{"html": ..., "md": ...}`` con i path scritti.
    """
    state_dir = Path(state_dir)
    output_path = Path(output_path)
    if cliente is None:
        cliente = state_dir.name or "ignoto"
    if index_md_path is None:
        index_md_path = output_path.parent / "INDEX.md"

    data = collect_metrics(state_dir, vault_dir, cliente)
    html = _render_html(data)
    md = _render_index_md(data)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    index_md_path.parent.mkdir(parents=True, exist_ok=True)
    index_md_path.write_text(md, encoding="utf-8")
    logger.info(
        "Dashboard generata: html=%s md=%s (categorie tot=%d, bozze tot=%d, costo=EUR %.2f)",
        output_path,
        index_md_path,
        data.categorie.total,
        data.bozze.total,
        data.costi.totale_eur,
    )
    return {"html": output_path, "md": index_md_path}


__all__ = [
    "CATEGORIE",
    "DORMIENTE_GIORNI",
    "REGOLA_01_PMI",
    "STATI_BOZZA",
    "CategoryStats",
    "CostStats",
    "DashboardData",
    "DraftStats",
    "SourceStats",
    "VaultHealth",
    "collect_metrics",
    "generate_dashboard",
]
