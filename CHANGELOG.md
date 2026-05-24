# CHANGELOG

Tutte le modifiche notevoli al toolkit `wiki-toolkit` (nome di lavoro: **Custodia**).

Formato basato su [Keep a Changelog](https://keepachangelog.com), versioning [SemVer](https://semver.org).

---

## [0.2.0] — 2026-05-24 — Polish v1 (Step 4 partial)

### Aggiunto

- **`wiki doctor`** — health check completo (Python, tool di sistema, env vars, config cliente, cartelle runtime, spazio disco). Exit code 0/1/2 secondo severità. `--strict` per failure su warning.
- **`wiki demo`** — demo end-to-end self-contained: genera dataset finto (48 file misti, 3 clienti + 2 fornitori), esegue pipeline completa, apre dashboard. Utile per training, screen-recording, valutazione.
- **`wiki/errors.py`** — gerarchia eccezioni custom (`WikiError`, `ConfigError`, `ScanError`, `ExtractError`, `LLMError`, `PipelineError`, `SubprocessError`, `ValidationError`).
- **`wiki/_atomic.py`** — scrittura atomica file (tmp + fsync + rename). Helper: `atomic_write_text`, `atomic_write_bytes`, `atomic_write_json`, `append_jsonl`.
- **`wiki/_retry.py`** — decoratore `@retry_on(exceptions, attempts, backoff)` con backoff esponenziale e cap su delay.
- **`wiki/_subprocess.py`** — wrapper sicuro per `subprocess.run` con timeout obbligatorio, error handling strutturato via `SubprocessError`.
- **`Makefile`** — shortcuts `install/test/lint/format/typecheck/coverage/security/smoke/watch/all/clean`.
- **`tests/test_no_secrets.py`** — scan repo per credenziali hardcoded (Anthropic key, AWS access key, private PEM, password literal). Skip file di test/legacy/fixture.
- **`tests/test_helpers.py`** — 22 test per i nuovi moduli helper.
- **`tests/test_doctor.py`** — 21 test per il health check.
- **`CHANGELOG.md`** — questo file.

### Modificato

- **`pyproject.toml`** — config ruff strict (select `E,W,F,I,B,C4,UP,ARG,SIM,PTH,RUF` + ignore mirati), mypy gradual (strict_optional, exclude legacy/brief/vault), coverage config (branch=true, exclude righe non testabili), pytest marker per skip condizionali (`requires_pandoc`, `requires_tesseract`, `requires_reportlab`, `slow`). Dev deps estese: `mypy`, `pre-commit`, `types-PyYAML`.
- **`wiki/__init__.py`** — definito `__version__ = "0.2.0"`, `__author__`, `__license__`.
- **`wiki/cli.py`** — rimossi `type: ignore` non necessari, integrati comandi `doctor` e `demo`.
- **`scanners/m365.py`, `wiki/llm/anthropic_api.py`, `wiki/llm/bedrock.py`** — rimossi `type: ignore` non necessari.

### Quality gates

- **Ruff**: 130 issue auto-fixate, 53 file riformattati, 14 issue residue minori (`os.replace` → `Path.replace`, etc.).
- **Mypy**: gradual mode attivo, 19 errori residui in 9 file (principalmente type narrowing `LLMClient | Any`, cast Observer in watcher.py — non bloccanti).
- **Coverage**: 77.1% overall (sopra target 70%). 100%: helpers, errors, server scanner. >85%: dashboard, safe_mode, bedrock, retry, base scanner. Deboli: pipeline.py (21%, manca test diretto), gdrive.py reale (59%, no creds in test).
- **Test totale**: **237 passed, 1 skipped** (era 190 → +47).
- **Smoke E2E**: `wiki demo` completa scan + extract + categorize + reconcile + dashboard senza errori. Pipeline funzionante.

---

## [0.1.0] — 2026-05-23 — MVP v1 (Step 1+2+3)

### Step 1 — Vault PMI + skills + docs

- Vault PMI multi-utente: 6 layer di memoria, 4 ruoli (Owner/Custode/Editor/Contributor), 4 regole non-negoziabili, protocollo a 3 livelli (personale/reparto/azienda).
- 6 skill agentiche: `setup-wizard-azienda`, `setup-wizard-persona`, `session-lifecycle` multi-utente, `rituale-settimanale-custode`, `rituale-mensile-owner`, `vault-lint` (riparato).
- 7 doc per i 3 attori: `01-cosa-vendi`, `02-kickoff-checklist`, `03-scandagliamento`, `04-handover-checklist`, `05-manuale-custode`, `06-framework-pmi`, `07-manuale-persone`.
- Vault istanziato come "Esempio Srl" (officina manifatturiera 38 persone).
- Template solista archiviato in `_legacy-single-user/`.

### Step 2 — Toolkit Python eseguibile

- **CLI `wiki`** con 8 subcommand: `init`, `scan`, `extract`, `categorize`, `reconcile`, `approve`, `watch`, `status`.
- **5 scanner**: `nas` (reale), `gdrive`, `m365`, `email`, `server` (mock-able via fixture JSON).
- **6 extractor**: PDF (`pdfplumber`), PDF OCR (`pytesseract`), DOCX (`pandoc` + fallback `python-docx`), XLSX (`openpyxl`), EML (stdlib), plain.
- **Categorizer**: rules + Claude Haiku batch con cost tracking.
- **Reconciler**: dedup hash + dedup soft + generatore schede cliente/fornitore (Regola 01-PMI) + estrazione persone.
- **Batch UI**: Flask + HTMX su `127.0.0.1:7423`, diff viewer, approve/reject/edit/park, flush al vault con conflict policy.
- **Watcher daemon**: `wiki watch` sempre-in-ascolto su `_inbox/<slug>/` con debounce 2s, pidfile health-check.

### Step 3 — Dashboard, on-premise, materiali commerciali

- **Dashboard HTML auto-contenuto** + INDEX.md (`wiki dashboard --client <slug>`). Metriche: sorgenti, 5 categorie, bozze per stato, salute vault, costi Claude. SVG inline per grafici.
- **Astrazione LLM provider** (`wiki/llm/`): `AnthropicApiClient` (default) + `BedrockClient` (Claude su AWS Bedrock account cliente) + `SafeModeWrapper` (redact PII per email/CF/IBAN/telefono italiani).
- **Docker** (`Dockerfile` + `docker-compose.yml`): Python 3.11 slim + Pandoc + Tesseract italiano + Poppler.
- **`docs/08-on-premise.md`** — guida per DPO cliente, matrice trigger, 3 opzioni (Bedrock / safe-mode / Docker).
- **Materiali commerciali** (`docs/commerciale/`): deck 20 slide, 25 FAQ, preventivo template, contratto skeleton (con disclaimer avvocato GDPR), landing page, demo script, cheatsheet Custode.
- **Pilot E2E**: `tests/fixtures/build_pilot_dataset.py` + `tests/e2e/test_pilot_pipeline.py` (3 test E2E con Anthropic mockato).
- **Hardening watcher**: retry con backoff (default 3 tentativi × 5s), dead-letter queue, logging JSON.
- **CI GitHub Actions** (`.github/workflows/test.yml`): matrix Python 3.11 + 3.12.
- **Fix bug `wiki extract`**: il batch CLI bypassa ora il dedup-skip del pipeline watcher.

### Brief di planning conservati in `_brief/`

- `04-step-2-tech-plan.md` — architettura completa scanner/extractor/batch
- `05-mcp-audit.md` — verdict MCP per le 5 fonti
- `06-cost-and-risk.md` — cost model + GDPR + contratto skeleton
- `07-naming-brand.md` — proposta "Custodia" con shortlist e razionale

---

## Tipologie di entry

- **Aggiunto**: nuove feature
- **Modificato**: cambi a feature esistenti
- **Deprecato**: feature in via di rimozione
- **Rimosso**: feature rimosse
- **Fix**: bug fix
- **Sicurezza**: vulnerabilità corrette
- **Quality gates**: code quality, test, lint, type checking
