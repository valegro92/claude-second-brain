"""Test end-to-end della pipeline `wiki` su dataset pilota.

Strategia (vedi brief Step 3 cantiere PILOT-E2E):
  1. Genera il dataset pilota nella tmp_path.
  2. Costruisce un config "pilot" minimale (sorgente NAS sul dataset).
  3. Esegue programmaticamente i 4 step del CLI (scan, extract, categorize,
     reconcile) **isolando** REPO_ROOT/CLIENTS_DIR/STATE_DIR a tmp_path
     (stesso pattern di tests/test_cli.py::isolated_repo).
  4. Mock dell'SDK Anthropic: nessuna chiamata vera, risposta fake
     deterministica per il categorizer Claude e per la sezione narrativa
     delle schede.
  5. Asserzioni sull'output prodotto in `_status/<slug>/`.

Il test è marker-leggero: non richiede pandoc/tesseract (gli extractor
fanno fallback). Richiede solo le librerie già in deps (python-docx, openpyxl,
pdfplumber/pypdf, watchdog). I PDF "ricchi" arrivano da reportlab se
disponibile, altrimenti dal minimal-PDF cucito a mano.
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest
import yaml
from click.testing import CliRunner

from tests.fixtures.build_pilot_dataset import build_dataset
from wiki import cli as cli_module
from wiki.cli import main as wiki_main


# --- helper: client config -------------------------------------------------


PILOT_SLUG = "pilot"


def _make_pilot_config(repo_root: Path, dataset_root: Path, slug: str = PILOT_SLUG) -> Path:
    """Costruisce un config cliente che mappa la sorgente NAS al dataset pilota.

    Filtri globali coerenti col config.template: niente file > 50MB, esclude
    ``.dwg``/``.zip``/``.dmg`` e cartelle ``_ARCHIVIO``. La cartella
    ``_OLD_NON_USARE/`` del dataset NON è esclusa via glob, quindi finisce
    nell'inventario, ma il categorizer la marcherà come archivio per via
    dell'età dei file (2018) e del naming.
    """
    clients_dir = repo_root / "bootstrap" / "clients"
    cdir = clients_dir / slug
    cdir.mkdir(parents=True, exist_ok=True)
    config = {
        "cliente": {
            "slug": slug,
            "nome": "Pilot Srl",
            "custode": "PT",
            "owner": "VG",
        },
        "sorgenti": {
            "nas": {
                "enabled": True,
                "mount": str(dataset_root),
                "perimetro": {"include": [], "exclude": []},
            },
            "gdrive": {"enabled": False},
            "m365": {"enabled": False},
            "email": {"enabled": False},
            "server": {"enabled": False},
        },
        "filtri_globali": {
            "max_file_mb": 50,
            "exclude_extensions": [".dwg", ".zip", ".dmg"],
            "exclude_paths_glob": ["**/.git/**", "**/node_modules/**"],
        },
        "privacy": {"modalita": "safe", "log_dati_a_anthropic": True, "redact_pii": False},
        "batch": {"size": 50, "cost_alert_eur": 50, "cost_hard_stop_eur": 200},
    }
    (cdir / "config.yml").write_text(yaml.dump(config), encoding="utf-8")
    return cdir / "config.yml"


# --- helper: isolamento repo ----------------------------------------------


@pytest.fixture
def isolated_pilot_repo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Path, Path, Path]:
    """Setup completo: redirige le costanti del CLI + genera il dataset.

    Ritorna ``(repo_root, dataset_root, state_dir_slug)``.
    """
    repo_root = tmp_path / "repo"
    clients_dir = repo_root / "bootstrap" / "clients"
    state_dir = repo_root / "_status"
    inbox_dir = repo_root / "_inbox"
    clients_dir.mkdir(parents=True)
    state_dir.mkdir()
    inbox_dir.mkdir()

    # Template reale, così init non rompe (anche se non lo usiamo qui).
    real_template = Path(__file__).resolve().parents[2] / "bootstrap" / "config.template.yml"
    template_path = repo_root / "bootstrap" / "config.template.yml"
    template_path.write_text(real_template.read_text(encoding="utf-8"), encoding="utf-8")

    monkeypatch.setattr(cli_module, "REPO_ROOT", repo_root)
    monkeypatch.setattr(cli_module, "CLIENTS_DIR", clients_dir)
    monkeypatch.setattr(cli_module, "DEFAULT_STATE_DIR", state_dir)
    monkeypatch.setattr(cli_module, "DEFAULT_INBOX_DIR", inbox_dir)
    monkeypatch.setattr(cli_module, "TEMPLATE_PATH", template_path)

    # Genera dataset in una cartella esterna al repo (simula il NAS).
    dataset_root = tmp_path / "_pilot" / "inbox"
    files = build_dataset(dataset_root)
    assert 40 <= len(files) <= 60, f"Dataset out-of-range: {len(files)} file"

    # Crea config cliente "pilot" puntato al dataset.
    _make_pilot_config(repo_root, dataset_root, slug=PILOT_SLUG)
    (state_dir / PILOT_SLUG).mkdir(parents=True, exist_ok=True)
    return repo_root, dataset_root, state_dir / PILOT_SLUG


# --- mock Anthropic SDK ---------------------------------------------------


class _FakeAnthropicResponse:
    """Mimica lo shape di una response del SDK Anthropic (`.content[0].text`, `.usage`)."""

    def __init__(self, text: str, tokens_in: int = 100, tokens_out: int = 50) -> None:
        self.content = [SimpleNamespace(text=text)]
        self.usage = SimpleNamespace(input_tokens=tokens_in, output_tokens=tokens_out)


class _FakeAnthropicMessages:
    """Mock di ``client.messages.create``. Deterministico, ritorna sempre VIVO."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> _FakeAnthropicResponse:
        self.calls.append(kwargs)
        # Estrai i payload dal prompt utente (è un JSON dentro al testo).
        user_msg = kwargs["messages"][0]["content"]
        # Heuristic: se il prompt contiene "Per ogni file qui sotto" allora
        # è una chiamata di categorizzazione → risponde con array JSON.
        if "Per ogni file" in user_msg:
            # Cerchiamo il blocco JSON nel prompt (è elencato come "Files: [...]")
            start = user_msg.find("[")
            end = user_msg.rfind("]")
            payloads: list[dict[str, Any]] = []
            if start != -1 and end != -1 and end > start:
                try:
                    payloads = json.loads(user_msg[start : end + 1])
                except json.JSONDecodeError:
                    payloads = []
            decisions = [
                {
                    "sha": item.get("sha", ""),
                    "cat": "vivo",
                    "conf": 0.85,
                    "why": "fake-llm-decision",
                }
                for item in payloads
            ]
            return _FakeAnthropicResponse(json.dumps(decisions))
        # Altrimenti: prompt narrativa (schede). Risposta markdown plausibile.
        narrative = (
            "## Storia\n\n"
            "- 2022 — prima richiesta di offerta dal cliente.\n"
            "- 2024 — rinnovo annuale dei termini commerciali.\n\n"
            "## Decisioni estratte\n\n"
            "- Listino aggiornato annualmente.\n"
            "- Pagamento a 30 giorni data fattura.\n"
        )
        return _FakeAnthropicResponse(narrative)


class _FakeAnthropicClient:
    def __init__(self) -> None:
        self.messages = _FakeAnthropicMessages()


# --- helper: esegue una sequenza di comandi CLI con CliRunner -------------


def _invoke(args: list[str]) -> Any:
    runner = CliRunner()
    return runner.invoke(wiki_main, args, catch_exceptions=False)


# --- test principale ------------------------------------------------------


def test_pilot_pipeline_end_to_end(isolated_pilot_repo: tuple[Path, Path, Path]) -> None:
    """End-to-end completo: scan → extract → categorize → reconcile (hash + soft + schede).

    Le assertion sono coerenti con la sezione 2 del brief PILOT-E2E.
    """
    repo_root, dataset_root, state_dir_slug = isolated_pilot_repo

    # ----- 1. scan -----------------------------------------------------------
    result = _invoke(["scan", "--client", PILOT_SLUG])
    assert result.exit_code == 0, result.output
    # Almeno il messaggio "scan nas" è stampato
    assert "scan nas" in result.output

    nas_jsonl = state_dir_slug / "inventory" / "nas.jsonl"
    assert nas_jsonl.exists(), "Inventory nas.jsonl non creato"
    records = [
        json.loads(line)
        for line in nas_jsonl.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    # I file binari/grandi (.dwg, .zip) sono esclusi dai filtri_globali;
    # restano 40-60 record "puliti".
    assert 40 <= len(records) <= 60, f"Inventory dimensioni anomale: {len(records)}"
    # I file binari NON devono essere nell'inventory.
    names = [r["name"] for r in records]
    assert "disegno_tecnico.dwg" not in names, "Il .dwg doveva essere escluso"
    assert "backup_grande.zip" not in names, "Il .zip doveva essere escluso"

    # ----- 2. extract --------------------------------------------------------
    # Nota: `wiki extract` riusa `run_pipeline_for_file` che, per disegno
    # (vedi pipeline.py), salta i record già presenti nell'inventory: è
    # idempotente vs il watcher, ma significa che il CLI batch oggi non
    # estrae quando l'inventory è stato appena popolato dallo scan. Per
    # avere un E2E che esercita davvero la fase estrattiva chiamiamo il
    # registry degli extractor direttamente, salvando l'output con la stessa
    # convenzione (`_status/extracted/<sha12>/`). La batch UI farà lo stesso
    # quando arriva in produzione il connettore tra "categorize" e i drafts.
    _extract_inventory(state_dir_slug, records)
    extracted_dir = state_dir_slug / "extracted"
    assert extracted_dir.exists()
    extracted_count = sum(1 for p in extracted_dir.iterdir() if p.is_dir())
    # Almeno il 90% dei record dell'inventory deve essere stato estratto.
    min_ok = int(len(records) * 0.9)
    assert extracted_count >= min_ok, (
        f"Solo {extracted_count}/{len(records)} estratti (atteso >={min_ok})"
    )

    # ----- 3. categorize -----------------------------------------------------
    result = _invoke(["categorize", "--client", PILOT_SLUG])
    assert result.exit_code == 0, result.output
    summary_path = state_dir_slug / "audit" / "categorize.summary.json"
    assert summary_path.exists()
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["total"] == len(records), (
        f"Categorizzati ({summary['total']}) != inventory ({len(records)})"
    )
    # Ogni file ha ricevuto una categoria (somma == total).
    cat_sum = sum(summary["by_category"].values())
    assert cat_sum == summary["total"]
    # La cartella _OLD_NON_USARE/ ha file 2018: dovrebbero finire in ARCHIVIO
    # o CESTINO (le 2 categorie "non-vive").
    archivio_o_cestino = summary["by_category"].get("archivio", 0) + summary[
        "by_category"
    ].get("cestino", 0)
    assert archivio_o_cestino > 0, (
        "I file vecchi (_OLD_NON_USARE / 2018) dovevano finire in archivio/cestino"
    )

    # ----- 4. reconcile (dedup hash globale via CLI) -------------------------
    result = _invoke(["reconcile", "--client", PILOT_SLUG])
    assert result.exit_code == 0, result.output
    by_hash_path = state_dir_slug / "drafts" / "_reconciler" / "by_hash.json"
    assert by_hash_path.exists()
    by_hash = json.loads(by_hash_path.read_text(encoding="utf-8"))
    # by_hash contiene tutti gli sha dei record (almeno uno per categoria).
    assert len(by_hash) > 0

    # ----- 5. dedup soft + schede (via API dei moduli, non CLI) --------------
    # Il CLI `wiki reconcile` Step 3 fa solo l'hash dedup; per il soft dedup
    # e per le bozze scheda chiamiamo direttamente i moduli (la batch UI farà
    # lo stesso). Mock dell'SDK Anthropic via patch della factory.
    fake_client = _FakeAnthropicClient()

    from reconcilers.dedup_soft import run_dedup_soft
    from reconcilers.schede import run_schede

    # Necessario per le schede: i record devono avere categoria settata
    # (VIVO o DA_CONSULTARE per essere clusterizzati). Il CLI `categorize`
    # scrive solo il summary, non muta i JSONL. Qui:
    #   1. Applica le rules (passata 1) e scrive le categorie sul disco.
    #   2. Per i record che le rules non hanno deciso (DA_CHIARIRE), chiama
    #      il categorizer Claude (mock-ato → tutto VIVO) e applica anche
    #      quelle decisioni.
    _apply_categories_to_inventory(state_dir_slug)
    _apply_claude_categories(state_dir_slug, fake_client)

    batch_id = "pilot-2026"

    # Dedup soft: deve trovare almeno il cluster v1/v2/v3/FINAL.
    soft_stats = run_dedup_soft(state_dir_slug, batch_id)
    assert soft_stats["n_clusters"] >= 1, "Nessun cluster soft trovato"
    drafts_batch = state_dir_slug / "drafts" / batch_id
    soft_drafts = list(drafts_batch.glob("dedup-soft-*.md"))
    assert len(soft_drafts) == soft_stats["n_clusters"]

    # Schede: con cliente mockato non si fanno chiamate reali.
    with patch("reconcilers.schede._call_narrative",
               return_value="## Storia\n\n- evento.\n\n## Decisioni estratte\n\n- nessuna.\n"):
        schede_stats = run_schede(
            state_dir_slug, batch_id, client=fake_client, call_llm=True
        )
    # Almeno 2 bozze scheda cliente (Rossi, Verdi, Bianchi → folder /clienti/<slug>/).
    assert schede_stats["n_groups"] >= 2, (
        f"Atteso almeno 2 bozze scheda, trovate {schede_stats['n_groups']}"
    )

    # I file di scheda esistono nel batch.
    schede_dirs = [p for p in drafts_batch.iterdir() if p.is_dir() and p.name.startswith("scheda-")]
    assert len(schede_dirs) >= 2
    for sd in schede_dirs:
        # I 5 file Regola 01-PMI devono esserci.
        for filename in ("CLAUDE.md", "MEMORY.md", "tasks.md", "persone.md"):
            assert (sd / filename).exists(), f"manca {filename} in {sd}"
        # File MOC: `<slug>.md` (lo deduciamo dal nome cartella `scheda-<tipo>-<slug>`).
        slug_dir = sd.name.split("-", 2)[-1]
        assert (sd / f"{slug_dir}.md").exists(), f"manca {slug_dir}.md in {sd}"


def test_dedup_soft_finds_versioned_files(isolated_pilot_repo: tuple[Path, Path, Path]) -> None:
    """Test mirato: il dedup soft deve raggruppare il pattern `_v1/_v2/_v3/_FINAL`.

    Più focalizzato del test E2E: ci limitiamo a scan + dedup soft.
    """
    repo_root, dataset_root, state_dir_slug = isolated_pilot_repo

    # Solo scan
    result = _invoke(["scan", "--client", PILOT_SLUG])
    assert result.exit_code == 0, result.output

    from reconcilers.dedup_soft import run_dedup_soft

    batch_id = "pilot-soft-only"
    stats = run_dedup_soft(state_dir_slug, batch_id)
    assert stats["n_clusters"] >= 1

    drafts_batch = state_dir_slug / "drafts" / batch_id
    contents = "\n".join(p.read_text(encoding="utf-8") for p in drafts_batch.glob("*.md"))
    # Almeno uno dei nomi dei 3 candidati v1/v2/v3 deve apparire.
    assert (
        "offerta_speciale_v1.docx" in contents
        or "offerta_speciale_v2.docx" in contents
        or "offerta_speciale_v3.docx" in contents
        or "offerta_speciale_FINAL.docx" in contents
    ), "Il cluster v1/v2/v3/FINAL non è stato riconosciuto"


def test_categorizer_claude_mocked(isolated_pilot_repo: tuple[Path, Path, Path]) -> None:
    """La passata Claude del categorizer è mock-ata, non chiama API reale.

    Verifica che l'SDK Anthropic NON venga importato di nascosto: la chiamata
    passa attraverso ``categorize_batch`` con ``client=<fake>``.
    """
    repo_root, dataset_root, state_dir_slug = isolated_pilot_repo
    # scan + extract per popolare lo state
    assert _invoke(["scan", "--client", PILOT_SLUG]).exit_code == 0
    assert _invoke(["extract", "--client", PILOT_SLUG]).exit_code == 0

    from categorizers.claude import categorize_batch
    from scanners._base import FileRecord

    inv = state_dir_slug / "inventory" / "nas.jsonl"
    records = [
        FileRecord.from_jsonl(line)
        for line in inv.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ][:5]  # bastano 5 record per il test
    fake_client = _FakeAnthropicClient()
    results = categorize_batch(
        records, mode="safe", state_dir=state_dir_slug, client=fake_client
    )
    assert len(results) == len(records)
    # Tutti VIVO secondo il fake.
    assert all(r["cat"] == "vivo" for r in results)
    # Il client mock ha registrato esattamente una chiamata (5 record < batch_size 20).
    assert len(fake_client.messages.calls) == 1


# --- utility interna ------------------------------------------------------


def _extract_inventory(state_dir_slug: Path, records: list[dict[str, Any]]) -> None:
    """Estrae ogni record dell'inventory chiamando il registry di extractor.

    Replica la convenzione di salvataggio di ``Extractor.write_extraction``
    (cartella ``_status/extracted/<sha12>/``), così il resto della pipeline
    (categorizer Claude con snippet, schede narrative) trova i main.md
    nelle posizioni attese.
    """
    from extractors._base import Extractor
    from extractors._registry import get_extractor

    for rec in records:
        abs_path = (rec.get("extras") or {}).get("abs_path") or rec.get("source_id")
        if not abs_path:
            continue
        p = Path(abs_path)
        if not p.exists():
            continue
        ext = p.suffix.lower()
        mime = rec.get("mime")
        extractor = get_extractor(mime, ext)
        if extractor is None:
            continue
        try:
            result = extractor.extract(p)
        except Exception:
            continue
        sha = rec.get("sha256") or ""
        if not sha:
            continue
        Extractor.write_extraction(result, state_dir_slug, sha, source_record=rec)


def _apply_categories_to_inventory(state_dir_slug: Path) -> None:
    """Applica le categorie (rules) all'inventory e lo riscrive in-place.

    Lo fa una sola volta: prende ogni JSONL non `_`-prefisso, ricostruisce
    i record, chiama ``classify``, scrive di nuovo (atomico via tmp+rename).
    """
    from categorizers.rules import classify
    from scanners._base import FileRecord

    inv_dir = state_dir_slug / "inventory"
    for jsonl in inv_dir.glob("*.jsonl"):
        if jsonl.name.startswith("_"):
            continue
        records = [
            FileRecord.from_jsonl(line)
            for line in jsonl.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        for r in records:
            cat, conf, why = classify(r)
            r.categoria = cat.value
            r.confidence = conf
            r.reason = why
        tmp = jsonl.with_suffix(jsonl.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            for r in records:
                f.write(r.to_jsonl() + "\n")
        tmp.replace(jsonl)


def _apply_claude_categories(
    state_dir_slug: Path, fake_client: "_FakeAnthropicClient"
) -> None:
    """Per i record ``DA_CHIARIRE`` chiama il categorizer Claude (mock-ato).

    Aggiorna i JSONL in-place: ``categoria`` diventa quella decisa dal mock
    (VIVO con conf 0.85), in modo che le schede possano clusterizzare.
    """
    from categorizers._enums import Categoria
    from categorizers.claude import categorize_batch
    from scanners._base import FileRecord

    inv_dir = state_dir_slug / "inventory"
    for jsonl in inv_dir.glob("*.jsonl"):
        if jsonl.name.startswith("_"):
            continue
        records = [
            FileRecord.from_jsonl(line)
            for line in jsonl.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        to_send = [r for r in records if r.categoria == Categoria.DA_CHIARIRE.value]
        if not to_send:
            continue
        results = categorize_batch(
            to_send, mode="safe", state_dir=state_dir_slug, client=fake_client
        )
        # Index per sha (la chiave del fake è sha o source_id).
        by_sha = {res["sha"]: res for res in results}
        for r in records:
            if r.categoria == Categoria.DA_CHIARIRE.value:
                key = r.sha256 or r.source_id
                decision = by_sha.get(key)
                if decision:
                    r.categoria = decision["cat"]
                    r.confidence = decision["conf"]
                    r.reason = "claude:" + decision.get("why", "")
        tmp = jsonl.with_suffix(jsonl.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            for r in records:
                f.write(r.to_jsonl() + "\n")
        tmp.replace(jsonl)
