"""CLI principale del toolkit (entry point ``wiki``).

Comandi:
  * ``wiki init`` — bootstrap interattivo
  * ``wiki scan`` — lancia gli scanner attivi del cliente
  * ``wiki extract`` — estrae i file scoperti dall'inventory non ancora processati
  * ``wiki categorize`` — applica rules + Claude (rules-only per ora)
  * ``wiki reconcile`` — dedup hash + dedup soft + bozze
  * ``wiki approve`` — apre la batch UI (delega a ``batch_ui.cli``)
  * ``wiki watch`` — modalità sempre-in-ascolto sulla `_inbox/`
  * ``wiki status`` — riepilogo numerico (file/extracted/drafts/cost)
  * ``wiki dashboard`` — genera ``_status/<slug>/dashboard.html`` + ``INDEX.md``

Convenzioni:
  * Output sempre italiano, conciso, niente emoji.
  * Logging stdlib (no print fuori dai messaggi utente CLI).
  * `--client SLUG` selettiva: se assente e c'è un solo cliente in
    `bootstrap/clients/`, lo usa; se più di uno, errore esplicito.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import click
import yaml

from bootstrap.wizard import run_wizard, write_config

logger = logging.getLogger("wiki")


# --- costanti -------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
CLIENTS_DIR = REPO_ROOT / "bootstrap" / "clients"
DEFAULT_STATE_DIR = REPO_ROOT / "_status"
DEFAULT_INBOX_DIR = REPO_ROOT / "_inbox"
TEMPLATE_PATH = REPO_ROOT / "bootstrap" / "config.template.yml"

VERSION = "0.1.0"


# --- helper condivisi -----------------------------------------------------


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def _list_clients() -> list[str]:
    if not CLIENTS_DIR.exists():
        return []
    return sorted(
        p.name for p in CLIENTS_DIR.iterdir() if p.is_dir() and (p / "config.yml").exists()
    )


def _resolve_client(client: str | None) -> str:
    """Risolve lo slug: o lo passa esplicito o c'è un solo cliente configurato."""
    clients = _list_clients()
    if client:
        if client not in clients:
            raise click.BadParameter(
                f"Cliente '{client}' non trovato. Disponibili: {clients or '(nessuno)'}"
            )
        return client
    if len(clients) == 1:
        return clients[0]
    if not clients:
        raise click.ClickException(
            "Nessun cliente configurato. Lancia `wiki init` per creare il primo."
        )
    raise click.ClickException(
        f"Più clienti configurati ({clients}). Usa --client SLUG per selezionarne uno."
    )


def _load_config(slug: str) -> dict[str, Any]:
    path = CLIENTS_DIR / slug / "config.yml"
    if not path.exists():
        raise click.ClickException(f"Config non trovato: {path}")
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _state_dir_for(slug: str) -> Path:
    # Un `_status/` per cliente per evitare collisioni durante lavori paralleli.
    return DEFAULT_STATE_DIR / slug


def _inbox_dir_for(slug: str) -> Path:
    return DEFAULT_INBOX_DIR / slug


# --- gruppo root ----------------------------------------------------------


@click.group(help="wiki-toolkit — CLI di delivery consulenziale per PMI.")
@click.version_option(VERSION, prog_name="wiki")
@click.option("-v", "--verbose", is_flag=True, help="Logging dettagliato (DEBUG).")
@click.pass_context
def main(ctx: click.Context, verbose: bool) -> None:
    """Punto di ingresso. ``ctx.obj`` non usato, mantenuto per estensioni future."""
    _setup_logging(verbose)
    ctx.ensure_object(dict)


# --- wiki init ------------------------------------------------------------


@main.command()
@click.option("--overwrite", is_flag=True, help="Sovrascrive il config se esiste.")
def init(overwrite: bool) -> None:
    """Bootstrap interattivo: wizard + creazione cartelle + check ambiente."""
    click.echo("=== wiki init ===")
    answers = run_wizard()
    try:
        config_path = write_config(
            answers,
            repo_root=REPO_ROOT,
            template_path=TEMPLATE_PATH,
            overwrite=overwrite,
        )
    except FileExistsError as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(f"Config scritto: {config_path.relative_to(REPO_ROOT)}")

    # Crea anche `_status/<slug>/` (per-cliente)
    _state_dir_for(answers.slug).mkdir(parents=True, exist_ok=True)

    click.echo("")
    click.echo("Check ambiente:")
    _check_env()
    click.echo("")
    click.echo("Pronto. Prossimi passi:")
    click.echo(f"  wiki scan --client {answers.slug}")
    click.echo(f"  wiki watch --client {answers.slug}  # oppure modalità streaming")


def _check_env() -> None:
    """Controlla Python version + tool di sistema opzionali (pandoc, tesseract)."""
    py = sys.version_info
    if py < (3, 11):
        click.echo(f"  [!] Python {py.major}.{py.minor}: richiesto 3.11+")
    else:
        click.echo(f"  [ok] Python {py.major}.{py.minor}.{py.micro}")

    for dep in ("click", "watchdog", "yaml"):
        try:
            __import__(dep)
            click.echo(f"  [ok] dep '{dep}' disponibile")
        except ImportError:
            click.echo(f"  [!] dep '{dep}' MANCANTE")

    for tool, descr in (("pandoc", "DOCX→md"), ("tesseract", "OCR")):
        if shutil.which(tool):
            click.echo(f"  [ok] tool '{tool}' disponibile ({descr})")
        else:
            click.echo(f"  [opzionale] '{tool}' non trovato ({descr})")


# --- wiki scan ------------------------------------------------------------


@main.command()
@click.option("--client", default=None, help="Slug cliente.")
@click.option(
    "--source",
    default=None,
    help="Singola sorgente (gdrive|m365|email|nas|server). Default: tutte le attive.",
)
def scan(client: str | None, source: str | None) -> None:
    """Lancia gli scanner attivi (NAS/gdrive/m365/email/server) per il cliente."""
    slug = _resolve_client(client)
    config = _load_config(slug)
    state_dir = _state_dir_for(slug)
    state_dir.mkdir(parents=True, exist_ok=True)

    requested = [source] if source else None
    scanners = _build_active_scanners(config, state_dir, requested)
    if not scanners:
        click.echo("Nessuna sorgente attiva. Modifica il config o passa --source.")
        return

    totals: dict[str, int] = {}
    for name, scanner in scanners:
        click.echo(f"== scan {name} ==")
        n = 0
        try:
            for _ in scanner.scan():
                n += 1
        except Exception as exc:  # pragma: no cover - dipende da config reale
            logger.exception("Scanner %s fallito: %s", name, exc)
            click.echo(f"  ! errore: {exc}")
        totals[name] = n
        click.echo(f"  {n} record scoperti")
    click.echo("")
    click.echo(f"Totale: {sum(totals.values())} record su {len(totals)} sorgenti.")


def _build_active_scanners(
    config: dict[str, Any], state_dir: Path, requested: list[str] | None
) -> list[tuple[str, Any]]:
    """Istanzia gli scanner abilitati. Filtra per ``requested`` se passato."""
    out: list[tuple[str, Any]] = []
    sorgenti = config.get("sorgenti", {}) or {}
    # Import lazy: alcune dipendenze opzionali rompono se importate vuote.
    mapping: dict[str, str] = {
        "nas": "scanners.nas:NasScanner",
        "server": "scanners.server:ServerScanner",
        "gdrive": "scanners.gdrive:GDriveScanner",
        "m365": "scanners.m365:M365Scanner",
        "email": "scanners.email:EmailScanner",
    }
    for name, dotted in mapping.items():
        if requested and name not in requested:
            continue
        cfg = sorgenti.get(name, {})
        if not cfg.get("enabled"):
            continue
        try:
            module, cls = dotted.split(":")
            mod = __import__(module, fromlist=[cls])
            scanner_cls = getattr(mod, cls)
            out.append((name, scanner_cls(config, state_dir)))
        except Exception as exc:
            logger.warning("Scanner %s non istanziabile: %s", name, exc)
    return out


# --- wiki extract ---------------------------------------------------------


@main.command()
@click.option("--client", default=None, help="Slug cliente.")
def extract(client: str | None) -> None:
    """Estrae i file dell'inventory non ancora processati.

    Il batch CLI usa direttamente il registry extractor invece di
    ``run_pipeline_for_file`` (che fa dedup-skip sull'inventory: corretto per
    il watcher, sbagliato qui dove i record sono GIA' nell'inventory dopo lo
    scan). Skip solo se la cartella ``_status/extracted/<sha12>/`` esiste.
    """
    slug = _resolve_client(client)
    _load_config(slug)  # validazione lettura config
    state_dir = _state_dir_for(slug)
    inv_dir = state_dir / "inventory"
    if not inv_dir.exists():
        click.echo("Nessun inventory. Lancia prima `wiki scan`.")
        return

    from extractors._base import Extractor
    from extractors._registry import extractor_for_path

    n_done = 0
    n_skip = 0
    n_no_extractor = 0
    n_error = 0
    for jsonl in sorted(inv_dir.glob("*.jsonl")):
        for line in jsonl.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            abs_path = (rec.get("extras") or {}).get("abs_path") or rec.get("source_id")
            if not abs_path:
                n_skip += 1
                continue
            p = Path(abs_path)
            if not p.exists():
                n_skip += 1
                continue
            sha = rec.get("sha256")
            if sha and (state_dir / "extracted" / sha[:12]).exists():
                n_skip += 1
                continue
            extractor = extractor_for_path(p, mime=rec.get("mime"))
            if extractor is None:
                n_no_extractor += 1
                continue
            try:
                result = extractor.extract(p)
            except Exception as exc:  # pragma: no cover - difensivo
                logger.warning("Estrazione fallita su %s: %s", p, exc)
                n_error += 1
                continue
            if sha:
                Extractor.write_extraction(result, state_dir, sha, source_record=rec)
                n_done += 1
            else:
                n_skip += 1
    click.echo(
        f"Estrazione: {n_done} processati, {n_skip} skip, "
        f"{n_no_extractor} senza extractor, {n_error} errori."
    )


# --- wiki categorize ------------------------------------------------------


@main.command()
@click.option("--client", default=None, help="Slug cliente.")
def categorize(client: str | None) -> None:
    """Pipeline categorizer: regole (sempre) + Claude (se modulo disponibile)."""
    slug = _resolve_client(client)
    state_dir = _state_dir_for(slug)
    inv_dir = state_dir / "inventory"
    if not inv_dir.exists():
        click.echo("Nessun inventory. Lancia prima `wiki scan`.")
        return

    try:
        from categorizers.rules import classify
    except ImportError as exc:
        raise click.ClickException(f"Categorizer rules non disponibile: {exc}") from exc

    from scanners._base import FileRecord

    by_cat: Counter[str] = Counter()
    total = 0
    for jsonl in sorted(inv_dir.glob("*.jsonl")):
        for line in jsonl.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                rec = FileRecord.from_jsonl(line)
            except Exception:
                continue
            cat, conf, _ = classify(rec)
            by_cat[cat.value] += 1
            total += 1
    # Audit minimale
    audit_dir = state_dir / "audit"
    audit_dir.mkdir(parents=True, exist_ok=True)
    (audit_dir / "categorize.summary.json").write_text(
        json.dumps({"total": total, "by_category": dict(by_cat)}, indent=2),
        encoding="utf-8",
    )
    click.echo(f"Categorizzati: {total}")
    for k, v in sorted(by_cat.items()):
        click.echo(f"  {k}: {v}")


# --- wiki reconcile -------------------------------------------------------


@main.command()
@click.option("--client", default=None, help="Slug cliente.")
def reconcile(client: str | None) -> None:
    """Reconciler: dedup hash globale + dedup soft (naming pattern)."""
    slug = _resolve_client(client)
    config = _load_config(slug)
    state_dir = _state_dir_for(slug)
    inv_dir = state_dir / "inventory"
    if not inv_dir.exists():
        click.echo("Nessun inventory. Lancia prima `wiki scan`.")
        return

    by_hash: dict[str, list[dict[str, Any]]] = {}
    for jsonl in sorted(inv_dir.glob("*.jsonl")):
        for line in jsonl.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            sha = rec.get("sha256")
            if not sha:
                continue
            by_hash.setdefault(sha, []).append(rec)

    n_dup_groups = sum(1 for recs in by_hash.values() if len(recs) > 1)
    n_dup_files = sum(len(recs) - 1 for recs in by_hash.values() if len(recs) > 1)
    out_dir = state_dir / "drafts" / "_reconciler"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "by_hash.json").write_text(
        json.dumps(by_hash, indent=2, default=str), encoding="utf-8"
    )
    click.echo(
        f"Reconciler: {n_dup_groups} gruppi di duplicati, {n_dup_files} file da deduplicare."
    )
    click.echo(f"Output: {out_dir.relative_to(REPO_ROOT)}/by_hash.json")

    # Step 3: rigenerazione automatica dashboard se attiva nel config.
    if (config.get("dashboard") or {}).get("auto"):
        try:
            from wiki.dashboard import generate_dashboard

            vault_dir = REPO_ROOT / "vault"
            generate_dashboard(
                state_dir=state_dir,
                vault_dir=vault_dir if vault_dir.exists() else None,
                output_path=state_dir / "dashboard.html",
                cliente=slug,
            )
            logger.info("Dashboard rigenerata automaticamente per %s", slug)
        except Exception as exc:  # pragma: no cover - difensivo
            logger.warning("Rigenerazione dashboard fallita: %s", exc)


# --- wiki approve ---------------------------------------------------------


@main.command()
@click.option("--client", default=None, help="Slug cliente.")
def approve(client: str | None) -> None:
    """Apre la batch UI di approvazione (delega a ``batch_ui.cli``)."""
    slug = _resolve_client(client)
    # Esponiamo la state_dir via env var: la batch UI può leggere lì.
    os.environ["WIKI_STATE_DIR"] = str(_state_dir_for(slug))
    os.environ["WIKI_CLIENT"] = slug
    try:
        # Import lazy per non rompere il CLI se la batch UI ha dipendenze
        # opzionali non installate.
        from batch_ui.cli import main as batch_main
    except ImportError as exc:
        raise click.ClickException(
            f"Modulo batch_ui.cli non disponibile: {exc}. "
            "Assicurati che il cantiere BATCH-UI sia stato fuso."
        ) from exc
    batch_main()


# --- wiki watch -----------------------------------------------------------


@main.command()
@click.option("--client", default=None, help="Slug cliente.")
@click.option("--debounce", type=float, default=2.0, help="Secondi di debounce.")
@click.option(
    "--log-format",
    type=click.Choice(["text", "json"], case_sensitive=False),
    default="text",
    help="Formato log: text (default) o json (per ingest in osservabilità).",
)
@click.option(
    "--max-retries",
    type=int,
    default=3,
    help="Tentativi totali sul pipeline prima di mandare il file in DLQ.",
)
@click.option(
    "--retry-backoff",
    type=float,
    default=5.0,
    help="Pausa (s) fra un tentativo e il successivo.",
)
def watch(
    client: str | None,
    debounce: float,
    log_format: str,
    max_retries: int,
    retry_backoff: float,
) -> None:
    """Modalità sempre-in-ascolto sulla `_inbox/<cliente>/`."""
    slug = _resolve_client(client)
    config = _load_config(slug)
    state_dir = _state_dir_for(slug)
    inbox = _inbox_dir_for(slug)

    from wiki.watcher import start_watcher

    click.echo(f"Watcher attivo su {inbox.relative_to(REPO_ROOT)}/ (Ctrl-C per uscire)")
    start_watcher(
        inbox_dir=inbox,
        config=config,
        state_dir=state_dir,
        debounce_s=debounce,
        block=True,
        max_retries=max_retries,
        retry_backoff_s=retry_backoff,
        log_format=log_format,
    )
    click.echo("Watcher terminato.")


# --- wiki status ----------------------------------------------------------


@main.command()
@click.option("--client", default=None, help="Slug cliente.")
def status(client: str | None) -> None:
    """Riepilogo: file per sorgente, estratti, categorizzati, bozze, costo Claude."""
    slug = _resolve_client(client)
    state_dir = _state_dir_for(slug)
    click.echo(f"=== status cliente: {slug} ===")

    inv_dir = state_dir / "inventory"
    by_source: Counter[str] = Counter()
    if inv_dir.exists():
        for jsonl in sorted(inv_dir.glob("*.jsonl")):
            with jsonl.open("r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    by_source[jsonl.stem] += 1
    if not by_source:
        click.echo("Inventory: vuoto (lancia `wiki scan`).")
    else:
        click.echo("Inventory:")
        for src, n in sorted(by_source.items()):
            click.echo(f"  {src}: {n} file")

    extracted_dir = state_dir / "extracted"
    n_extracted = (
        sum(1 for p in extracted_dir.iterdir() if p.is_dir()) if extracted_dir.exists() else 0
    )
    click.echo(f"Estratti: {n_extracted}")

    drafts_dir = state_dir / "drafts"
    n_drafts = 0
    n_approved = 0
    n_rejected = 0
    n_pending = 0
    if drafts_dir.exists():
        for batch in drafts_dir.iterdir():
            if not batch.is_dir():
                continue
            drafts = list(batch.glob("*.md"))
            n_drafts += len(drafts)
            state_file = batch / "_state.json"
            if state_file.exists():
                try:
                    st = json.loads(state_file.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    st = {}
                for entry in st.values():
                    s = entry.get("stato", "pending")
                    if s == "approved":
                        n_approved += 1
                    elif s == "rejected":
                        n_rejected += 1
                    else:
                        n_pending += 1
            else:
                n_pending += len(drafts)
    click.echo(
        f"Bozze: {n_drafts} totali "
        f"(pending={n_pending} approved={n_approved} rejected={n_rejected})"
    )

    cost_file = state_dir / "cost.jsonl"
    cumulative = 0.0
    if cost_file.exists():
        for line in cost_file.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
                cumulative += float(rec.get("eur", 0) or 0)
            except (json.JSONDecodeError, ValueError):
                continue
    click.echo(f"Costo Claude cumulativo: €{cumulative:.2f}")


# --- wiki dashboard -------------------------------------------------------


@main.command()
@click.option("--client", default=None, help="Slug cliente.")
@click.option(
    "--open", "open_browser", is_flag=True, help="Apre la dashboard nel browser di default."
)
def dashboard(client: str | None, open_browser: bool) -> None:
    """Genera ``_status/<slug>/dashboard.html`` + ``INDEX.md`` per il cliente."""
    slug = _resolve_client(client)
    state_dir = _state_dir_for(slug)
    state_dir.mkdir(parents=True, exist_ok=True)
    vault_dir = REPO_ROOT / "vault"

    from wiki.dashboard import generate_dashboard

    out_html = state_dir / "dashboard.html"
    paths = generate_dashboard(
        state_dir=state_dir,
        vault_dir=vault_dir if vault_dir.exists() else None,
        output_path=out_html,
        cliente=slug,
    )
    click.echo(f"Dashboard generata: {paths['html'].relative_to(REPO_ROOT)}")
    click.echo(f"INDEX markdown: {paths['md'].relative_to(REPO_ROOT)}")

    if open_browser:
        import webbrowser

        webbrowser.open(paths["html"].resolve().as_uri())


# --- wiki doctor ----------------------------------------------------------


@main.command()
@click.option("--client", default=None, help="Slug cliente (opzionale per check globali).")
@click.option("--strict", is_flag=True, help="Exit code 1 anche su warning (oltre fail).")
def doctor(client: str | None, strict: bool) -> None:
    """Health-check: Python, tool di sistema, env, config, cartelle, disco."""
    from wiki.doctor import format_report, run_all_checks, summary_exit_code

    # client e' opzionale qui: se passato, valida anche il suo config
    slug = client
    if slug:
        try:
            slug = _resolve_client(slug)
        except click.ClickException:
            click.echo(f"Cliente '{client}' non valido o inesistente.")
            slug = None

    checks = run_all_checks(REPO_ROOT, slug=slug)
    click.echo(format_report(checks))
    click.echo("")
    n_ok = sum(1 for c in checks if c.stato == "ok")
    n_warn = sum(1 for c in checks if c.stato == "warn")
    n_fail = sum(1 for c in checks if c.stato == "fail")
    click.echo(f"Totale: {n_ok} ok, {n_warn} warning, {n_fail} fail.")
    exit_code = summary_exit_code(checks, strict=strict)
    if exit_code != 0:
        sys.exit(exit_code)


# --- wiki demo ------------------------------------------------------------


@main.command()
@click.option(
    "--reset",
    is_flag=True,
    help="Cancella eventuale demo esistente prima di rigenerare.",
)
def demo(reset: bool) -> None:
    """Demo end-to-end: genera dataset finto, lancia pipeline, apre dashboard.

    Crea un cliente "demo" con 48 file misti (3 clienti finti + 2 fornitori),
    esegue scan + extract + categorize + reconcile, genera la dashboard.
    Utile per training, screen-recording, valutazione del prodotto.
    """
    slug = "demo"
    client_dir = CLIENTS_DIR / slug
    state_dir = _state_dir_for(slug)
    inbox_dir = _inbox_dir_for(slug)

    if reset:
        for d in (client_dir, state_dir, inbox_dir):
            if d.exists():
                shutil.rmtree(d)
        click.echo("Demo esistente cancellata.")

    if client_dir.exists() and (client_dir / "config.yml").exists():
        if not click.confirm(
            "Demo gia' configurata. Sovrascrivere config e rigenerare dataset?", default=False
        ):
            click.echo("Annullato. Usa --reset per ricominciare da zero.")
            return

    # 1) Config demo (no API key necessaria — Claude e' mockabile, ma demo gira solo rules)
    client_dir.mkdir(parents=True, exist_ok=True)
    state_dir.mkdir(parents=True, exist_ok=True)
    inbox_dir.mkdir(parents=True, exist_ok=True)
    demo_config = f"""\
cliente:
  slug: {slug}
  nome: "Demo end-to-end"
  custode: VG
  owner: VG
sorgenti:
  nas:
    enabled: true
    mount: "{inbox_dir}"
    perimetro: {{ include: [], exclude: [] }}
  gdrive: {{ enabled: false }}
  m365: {{ enabled: false }}
  email: {{ enabled: false }}
  server: {{ enabled: false }}
filtri_globali:
  max_file_mb: 50
  exclude_extensions: [".dwg"]
  exclude_paths_glob: []
privacy:
  modalita: safe
  log_dati_a_anthropic: false
batch:
  size: 50
  cost_alert_eur: 50
  cost_hard_stop_eur: 200
llm:
  provider: anthropic_api
  redact_pii: false
dashboard:
  auto: true
"""
    (client_dir / "config.yml").write_text(demo_config, encoding="utf-8")
    click.echo(f"Config demo scritto: {(client_dir / 'config.yml').relative_to(REPO_ROOT)}")

    # 2) Genera dataset
    click.echo("Genero dataset finto (48 file)...")
    try:
        from tests.fixtures.build_pilot_dataset import build_pilot_dataset

        build_pilot_dataset(inbox_dir)
    except ImportError as exc:
        click.echo(f"Errore: impossibile importare build_pilot_dataset ({exc})")
        click.echo("Assicurati di aver installato dev deps: `uv sync --extra dev`")
        sys.exit(2)

    # 3) Pipeline completo invocando i comandi click programmaticamente
    click.echo("")
    click.echo("Pipeline:")
    from click.testing import CliRunner

    runner = CliRunner()
    for cmd_name in ("scan", "extract", "categorize", "reconcile"):
        click.echo(f"  > wiki {cmd_name} --client {slug}")
        result = runner.invoke(main, [cmd_name, "--client", slug], catch_exceptions=False)
        if result.exit_code != 0:
            click.echo(f"    [!] {cmd_name} ha exit {result.exit_code}: {result.output[:200]}")
            break

    # 4) Dashboard
    click.echo("")
    click.echo("Genero dashboard...")
    runner.invoke(main, ["dashboard", "--client", slug], catch_exceptions=False)
    dash_path = state_dir / "dashboard.html"
    if dash_path.exists():
        click.echo(f"Dashboard: {dash_path.relative_to(REPO_ROOT)}")
        click.echo("")
        click.echo("Demo completa.")
        click.echo("Per un cliente reale: `wiki init`")
    else:
        click.echo("Dashboard non generata (verifica errori sopra).")


# --- entry point ----------------------------------------------------------


if __name__ == "__main__":  # pragma: no cover
    main()
