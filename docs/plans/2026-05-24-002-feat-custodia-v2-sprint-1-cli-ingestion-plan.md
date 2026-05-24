---
title: "feat: Custodia v2 Sprint 1 — CLI ingestion v0.1"
type: feat
status: active
date: 2026-05-24
origin: docs/brainstorms/custodia-v2-agent-ready-requirements.md
related:
  - docs/plans/2026-05-24-001-feat-custodia-v2-sprint-0-validazione-plan.md
  - docs/plans/2026-05-24-003-design-llm-provider-and-drive-connector.md
---

# feat: Custodia v2 Sprint 1 — CLI ingestion v0.1

## Summary

Sprint 1 costruisce la **ingestion side** di Custodia v2: il CLI a stadi che il consulente avvia in casa cliente per *costruire* il vault Obsidian dalle sorgenti reali (Google Drive, filesystem locale + NAS). Non è un eseguibile autonomo: è un workflow consulente-in-loop, con review umana fra uno stadio e il successivo. L'output è coerente con lo schema YAML frontmatter già validato dalle 3 schede demo in `product/vault-demo/clienti/` ed è consumabile dall'MCP server già esistente in `product/mcp-server/custodia_mcp.py`.

Sprint 1 chiude con: `custodia init → scan <drive|fs> → build clients → build communications → review → write` eseguibile end-to-end su un fixture sintetico e su uno spike reale (Drive personale di Valentino) con risultato review-able.

---

## Problem Frame

La consumption side è funzionante (MCP server + vault demo con 3 schede a mano). Il prodotto vero richiede di sostituire "Valentino scrive markdown a mano" con "il CLI estrae da Drive/NAS in 2-3 giorni di consulenza on-site". Senza ingestion non c'è prodotto vendibile in Sprint 4-5. Senza astrazione `LLMProvider` sin da subito, Sprint 2 (Sovrano on-demand) richiede refactor traumatico.

---

## Requirements (mappa Sprint 1)

- **R1.** Comando CLI a stadi con stato persistente fra invocazioni: `init`, `scan`, `build`, `review`, `write`. Re-runnabile, idempotente sui passi puri.
- **R2.** Astrazione `LLMProvider` (Protocol/ABC) con un solo adapter v0.1 (`AnthropicProvider`). Adapter Sovrano = porta aperta, non costruita.
- **R3.** Connettore Google Drive con OAuth desktop per il consulente, traversal folder root, parsing PDF/DOCX/XLSX/GDoc → stream di `SourceDocument`.
- **R4.** Connettore filesystem locale (NAS via mount POSIX) con stesso contratto + parser PDF (pypdf), DOCX (python-docx), XLSX (openpyxl).
- **R5.** Entity extractor LLM-driven che prende `SourceDocument` e produce schede `cliente|fornitore|commessa|comunicazione` con frontmatter YAML conforme allo schema delle 3 schede demo esistenti (campi obbligatori validati).
- **R6.** Stage `review` interattivo: mostra diff con il vault esistente per ogni entità candidata, permette accept/edit/skip, poi `write` scrive i file `.md` finali.
- **R7.** Verificabilità: fixture sintetico in `product/cli/tests/fixtures/finto-drive/` permette CI deterministico (LLM stubbed); spike reale dimostra E2E con Claude API vera.

---

## Scope Boundaries

### Dentro Sprint 1
- Linguaggio: Python 3.10+. Stile: simile a `product/mcp-server/custodia_mcp.py` (dataclass leggero, parser frontmatter manuale, type hints).
- CLI con `typer` (Decisione tecnica D1 sotto).
- 2 connettori (Drive, filesystem locale). NON 5 come da roadmap origin: prioritizziamo profondità su breadth.
- 1 provider LLM (Anthropic). Interfaccia generalizzata.
- Entity types v0.1: `cliente`, `fornitore`, `commessa`, `comunicazione`. Schema YAML preso verbatim dalle 3 schede demo.
- Test pytest, fixture deterministico, 1 spike reale dogfooded sul Drive di Valentino.

### Deferred (esplicitamente fuori Sprint 1)
- Connettore Outlook 365 / Exchange → Sprint 1.5
- Connettore Fatture in Cloud → Sprint 1.5
- Quinto connettore (TeamSystem / Zucchetti) → Sprint 1.5+ post-discovery
- Adapter Sovrano vero (Xference o equivalente) → Sprint 2 o on-demand
- Auto-sync da sorgenti (watcher continuo) → post v2.0
- Trasporto HTTP del MCP server → fuori scope (è consumption side)
- OCR su PDF immagine → opzionale, gated dietro flag `--ocr`, non blocking
- Multi-tenant / multi-cliente parallelo → fuori scope (1 vault per istanza CLI)

---

## Context & Research

### Codice esistente da rispettare
- `product/mcp-server/custodia_mcp.py` — convenzioni: `from __future__ import annotations`, `parse_frontmatter` manuale (NON usare `python-frontmatter`), dataclass/dict semplici, error handling esplicito con `{"error": ...}` invece di eccezioni propagate ai tool. Adottare lo stesso stile nel CLI.
- `product/vault-demo/clienti/*.md` — schema YAML autoritativo. Campi obbligatori per `tipo: cliente`: `nome`, `piva`, `settore`, `sede`, `referente_principale`, `email_referente`, `stato_relazione`, `ultimo_contatto`, `prossima_azione`. Campi strutturati nidificati: `condizioni_commerciali`, `eccezioni_concordate[]`, `prodotti_ricorrenti[]`, `red_flag[]`. Campo `note_relazionali` è prose multi-linea YAML (`|`).
- `product/vault-demo/inbox/2026-05-21-bianchi-richiesta-sconto.md` — schema entity `comunicazione`: `data`, `da`, `oggetto`, `cliente_collegato`, `stato`, body.
- `pyproject.toml` root — dipendenze utili già presenti: `anthropic`, `pypdf`, `python-docx`, `openpyxl`, `google-api-python-client`, `google-auth-oauthlib`. Riusare versioni già fissate.

### Design doc parallelo
- `docs/plans/2026-05-24-003-design-llm-provider-and-drive-connector.md` — contratti `LLMProvider` e `SourceDocument` adottati da questo piano.

---

## Key Technical Decisions

- **D1. CLI framework: `typer`** (non `click` raw). Motivazione: type hints nativi, sotto-comandi annidati naturali (`custodia scan drive`, `custodia scan fs`), help auto-generato leggibile per il consulente non-tech. Il root `pyproject.toml` già ha `click>=8.1`; `typer` lo wrappa, compatibile.
- **D2. Stato persistente: SQLite locale in `product/.custodia-state/state.db`** (non JSON flat). Motivazione: lo scan può produrre 1k-10k `SourceDocument`, JSON diventa unwieldy. SQLite permette query (`WHERE status='extracted' AND entity_type='cliente'`) e transazionalità sulle scritture vault. Schema semplice: tabelle `documents`, `entities`, `review_decisions`. Uno schema separato per progetto/vault permette anche `--vault` switching futuro.
- **D3. `LLMProvider` come `typing.Protocol`** (non ABC). Più Pythonic, zero ereditarietà, duck-typing testabile con MagicMock. Metodi: `complete(messages, *, system, max_tokens, temperature) -> str` e `extract_structured(messages, *, schema: dict, system) -> dict`. Il secondo è il workhorse dell'extractor.
- **D4. Estrazione strutturata via JSON mode/tool-use Anthropic**, non parsing testuale fragile. `extract_structured` impone uno schema JSON e ritorna dict validato.
- **D5. Chunking documenti lunghi: split su pagine PDF / sheet XLSX**, no semantic chunking v0.1. Limite hard 50k token per chunk; merge ragionato dei risultati nell'extractor (per cliente: union eccezioni, max(ultimo_contatto), prose append). Strategia documentata; sofisticazioni rinviate.
- **D6. Review CLI: rendering basato su `rich`** (tables, syntax-highlighted YAML diff). Già nell'ecosistema typer.
- **D7. Schema-as-source-of-truth: estratto da una scheda demo via codice**, non scritto a mano. Funzione `load_canonical_schema()` legge `product/vault-demo/clienti/rossetto-laminazioni.md`, estrae i campi e i tipi → schema usato per (a) prompting LLM, (b) validazione output, (c) prompt di review. Single source of truth = vault demo, evita drift.

---

## Open Questions

### Resolved during planning
- "Quale source format per documenti Drive nativi (Google Docs)?" → export su API in `text/plain` per Doc, `text/csv` per Sheet, `application/pdf` come fallback. Decisione operativa nel connettore Drive.
- "Come decidere quando un `SourceDocument` parla di un cliente esistente vs uno nuovo?" → l'extractor produce candidati nuovi; in `review` il consulente ha azione "merge with existing" che richiama `load_existing_client(id)` e propone diff.

### Deferred to implementation
- Limite token mensile per cliente per il primo spike → si misura, non si pre-vincola.
- Lingua del prompting (IT vs EN) → IT per output frontmatter (deve combaciare con campi italiani), EN per system prompt strutturale. Misurare qualità.
- Handling allegati email (post Outlook): non in Sprint 1.

---

## Implementation Units

### U1. CLI scaffolding + stato persistente

**Goal:** comandi `custodia init|scan|build|review|write` registrati, parser argomenti coerente, stato condiviso via SQLite locale.

**Requirements:** R1

**Dependencies:** Nessuna (foundational)

**Files:**
- Create: `product/cli/__init__.py`
- Create: `product/cli/main.py` — entry point typer, registra sub-app
- Create: `product/cli/commands/init.py` — `custodia init --vault <path>` crea `.custodia-state/` con DB schema
- Create: `product/cli/commands/scan.py` — wrapper, registra `custodia scan drive|fs`
- Create: `product/cli/commands/build.py` — `custodia build clients|communications|fornitori|commesse`
- Create: `product/cli/commands/review.py` — placeholder, popolato in U6
- Create: `product/cli/commands/write.py` — finalizza review → vault `.md`
- Create: `product/cli/state/__init__.py`
- Create: `product/cli/state/store.py` — `StateStore` class: `add_document`, `list_documents(filter)`, `upsert_entity`, `record_review_decision`, `list_pending_writes`
- Create: `product/cli/state/schema.sql` — DDL tabelle `documents`, `entities`, `review_decisions`, `runs`
- Create: `product/cli/pyproject.toml` — package separato (analogo a `product/mcp-server/`), dipendenze: `typer`, `rich`, `pyyaml`, `anthropic`, `pypdf`, `python-docx`, `openpyxl`, `google-api-python-client`, `google-auth-oauthlib`
- Create: `product/cli/README.md` — quickstart consulente

**Approach:**
- `custodia init` è idempotente: se `.custodia-state/state.db` esiste, controlla schema version e migra (banale in v0.1: una versione).
- Stato persistente vive in `<vault-parent>/.custodia-state/` per stare *fuori* dal vault (il vault è del cliente, lo stato è del consulente).
- Ogni run di `scan`/`build` registra un `run_id` per tracciabilità (utile in review).

**Test scenarios:**
- Happy: `custodia init --vault /tmp/v` → crea DB; `custodia init` di nuovo → no-op silenzioso.
- Edge: `custodia scan drive` senza `init` → errore chiaro "esegui prima `custodia init`".
- Edge: schema SQL retro-compatibile con `PRAGMA user_version`.
- CLI help: `custodia --help` mostra tutti i sub-comandi con descrizione breve italiana.

**Verification:**
- pytest su `StateStore` con SQLite in-memory.
- Snapshot test del help output (regression sui nomi comandi).

---

### U2. LLMProvider abstraction + Anthropic adapter

**Goal:** astrazione provider e un adapter funzionante.

**Requirements:** R2

**Dependencies:** Nessuna (può procedere in parallelo a U1)

**Files:**
- Create: `product/cli/llm/__init__.py` — esporta `LLMProvider`, `get_provider`
- Create: `product/cli/llm/base.py` — `Protocol LLMProvider`, dataclass `Message`, dataclass `LLMUsage` (in/out tokens, cost stimato)
- Create: `product/cli/llm/anthropic_provider.py` — `AnthropicProvider` con metodi `complete` e `extract_structured`. Usa Anthropic SDK; modello default `claude-haiku-4-5` per categorizzazione, `claude-sonnet-4-5` per estrazione strutturata. Configurabile via env `CUSTODIA_LLM_MODEL`.
- Create: `product/cli/llm/registry.py` — `get_provider(name: str) -> LLMProvider` (oggi solo `"anthropic"`; aggancio futuro `"sovrano"`)
- Create: `product/cli/llm/fakes.py` — `FakeLLMProvider` deterministico per test (legge da YAML fixture)
- Create: `product/cli/tests/test_llm.py`

**Approach:**
- `extract_structured` usa Anthropic tool-use: definisce un tool fittizio con `input_schema=schema`, forza il modello a chiamarlo, ritorna l'argomento parsato.
- Logging usage in `StateStore.runs` per misurare il costo per cliente (rischio Sprint 1 origin).
- Retry esplicito su `429`/`529` con backoff esponenziale (max 3 tentativi).

**Test scenarios:**
- Happy: `AnthropicProvider.extract_structured` con schema cliente su una fattura sintetica → ritorna dict con campi obbligatori popolati.
- Edge: schema con campo non-popolabile dal documento → output ha campo a `None`/missing, non hallucination.
- Error: rate-limit simulato → retry, successo al 3°.
- Determinism (con `FakeLLMProvider`): test end-to-end dell'extractor non chiamano la rete.

**Verification:**
- Coverage > 80% su `anthropic_provider.py`.
- Spike manuale: una fattura `.pdf` di esempio → output frontmatter valido per schema cliente.

---

### U3. Connettore Google Drive

**Goal:** OAuth desktop, traversal folder root, stream `SourceDocument`.

**Requirements:** R3

**Dependencies:** U1 (StateStore per persistere documenti)

**Files:**
- Create: `product/cli/connectors/__init__.py` — esporta `SourceDocument` dataclass, `Connector` Protocol
- Create: `product/cli/connectors/base.py` — dataclass `SourceDocument(source_id, source_path, mime_type, text, metadata: dict, raw_bytes_ref: Optional[Path])`; Protocol `Connector` con metodo `iter_documents() -> Iterator[SourceDocument]`
- Create: `product/cli/connectors/google_drive.py` — `GoogleDriveConnector(root_folder_id, credentials_path)`
- Create: `product/cli/connectors/parsers/__init__.py`
- Create: `product/cli/connectors/parsers/pdf.py` — `parse_pdf(bytes_or_path) -> str` con pypdf, fallback `pdfplumber` per layout complessi (già in dep root)
- Create: `product/cli/connectors/parsers/docx.py` — `parse_docx` via python-docx
- Create: `product/cli/connectors/parsers/xlsx.py` — `parse_xlsx` via openpyxl, output testuale tabellare deterministico
- Create: `product/cli/connectors/parsers/gdoc.py` — converte export API Drive in testo
- Create: `product/cli/auth/google_oauth.py` — flow `InstalledAppFlow`, token cache in `.custodia-state/google_token.json`, scope `drive.readonly`
- Modify: `product/cli/commands/scan.py` — registra sub `scan drive --root-folder-id <id>`

**Approach:**
- Read-only scope. Token utente (consulente), non service account: il consulente accede col proprio account Google che ha visibilità sul Drive del cliente (workspace-shared o delega esplicita).
- Traversal BFS limitato a folder root e discendenti. `pageSize=100`.
- Per ogni file: `files.get(supportsAllDrives=True)`, `files.export` per GDoc/Sheet/Slide, `files.get_media` per binari nativi.
- Persiste `raw_bytes_ref` come file in `.custodia-state/cache/<source_id>` per re-parse senza ri-scaricare.
- Filtra fuori: cestino, file > 50MB (warning), formati video/immagini (skip silenzioso v0.1).

**Test scenarios:**
- Happy: fixture mock di `googleapiclient` ritorna 3 file (1 PDF, 1 GDoc, 1 XLSX) → connettore produce 3 `SourceDocument` con `text` non vuoto.
- Edge: file con permission denied → log warning, prosegue, non crasha.
- Edge: token scaduto → flow di refresh, no re-prompt se refresh token valido.
- Edge: GDoc vuoto → `SourceDocument` con `text=""`, downstream extractor lo ignora.
- Manuale: spike su una folder di Drive di Valentino con 5-10 documenti aziendali reali.

**Verification:**
- Test unit con `unittest.mock` su `build("drive", ...)`.
- Spike report: tempo per 100 documenti, costo zero (Drive API è gratis), volume token testuale prodotto.

---

### U4. Connettore filesystem locale + parser file

**Goal:** lettura ricorsiva da cartella locale o mount NAS, stesso contratto di U3.

**Requirements:** R4

**Dependencies:** U1, U3 (riusa `parsers/` e `SourceDocument`)

**Files:**
- Create: `product/cli/connectors/filesystem.py` — `FilesystemConnector(root_path, exclude_patterns)`
- Modify: `product/cli/commands/scan.py` — registra sub `scan fs --root <path> [--exclude <glob>]`
- Create: `product/cli/connectors/tests/fixtures/finto-drive/` — corpus sintetico per CI: 1 fattura PDF, 1 contratto DOCX, 1 listino XLSX, 1 email .txt — contenuti finti ma realistici (3 clienti corrispondenti alle 3 schede demo, così l'extractor può ricostruirle)

**Approach:**
- `pathlib.Path.rglob("*")`, filtro MIME via `mimetypes` + estensione.
- `exclude_patterns` default: `[".git", ".obsidian", "__pycache__", "*.tmp"]`.
- Riusa i parser di U3 (single source of truth).
- Per file > 50MB → skip con warning, non OOM.

**Test scenarios:**
- Happy: fixture `finto-drive/` → 4 `SourceDocument`, contenuti parsati correttamente.
- Edge: cartella vuota → iterator vuoto, no errori.
- Edge: file PDF protetto da password → catch, warning, skip.
- Edge: symlink loop → `rglob` lo gestisce nativamente, ma test la robustezza.
- Edge: encoding non-UTF8 su `.txt` → fallback `chardet` o `errors="replace"`.

**Verification:**
- pytest con fixture sintetico → reproducible CI.

---

### U5. Entity extractor

**Goal:** trasforma stream di `SourceDocument` in schede entità con frontmatter YAML conforme.

**Requirements:** R5

**Dependencies:** U1 (StateStore), U2 (LLMProvider), U3+U4 (input `SourceDocument`)

**Files:**
- Create: `product/cli/extractor/__init__.py`
- Create: `product/cli/extractor/schema.py` — `load_canonical_schema(entity_type) -> dict` (legge da scheda demo, estrae JSON schema)
- Create: `product/cli/extractor/prompts.py` — system + user prompt templates per ogni `entity_type`. Template IT, esempi few-shot estratti dalle 3 schede demo
- Create: `product/cli/extractor/extractor.py` — `Extractor(provider, store).extract(documents, entity_type) -> list[EntityCandidate]`
- Create: `product/cli/extractor/chunking.py` — `chunk_document(doc, max_tokens=50000) -> list[Chunk]`, strategy per-page (PDF) / per-sheet (XLSX) / paragraph (DOCX)
- Create: `product/cli/extractor/merger.py` — quando più chunk parlano della stessa entità, merge ragionato: union su `eccezioni_concordate[]`, max() su date, append su prose con separatore
- Create: `product/cli/extractor/validator.py` — valida output LLM vs schema canonical, ritorna `(valid: bool, errors: list[str])`
- Create: `product/cli/extractor/tests/test_extractor.py` con `FakeLLMProvider`
- Modify: `product/cli/commands/build.py` — `custodia build clients` legge documenti da StateStore non ancora processati, chiama Extractor, salva `EntityCandidate` in StateStore

**Approach:**
- Two-stage prompting:
  1. **Categorization** (Haiku): "questo documento parla di clienti/fornitori/commesse/comunicazioni? quali nomi compaiono?" → output: lista `(entity_type, entity_hint_name)`
  2. **Extraction** (Sonnet): per ogni `(entity_type, hint)`, prompt strutturato con schema canonical e tool-use → entity candidate
- Few-shot: includere nel prompt 1 esempio completo (es. Rossetto Laminazioni) come golden reference. Hardcoded estratto da `product/vault-demo/clienti/rossetto-laminazioni.md` a init-time.
- Output `EntityCandidate(entity_type, entity_id_proposed, frontmatter: dict, body_md: str, source_doc_ids: list, confidence: float)`.
- Confidenza euristica: 1.0 se tutti i campi obbligatori popolati, decremento per ogni campo `None`.
- Doppio-output gestito: lo stesso documento può generare `cliente` + `comunicazione` (es. una mail dal cliente).

**Test scenarios:**
- Happy con `FakeLLMProvider`: fixture `finto-drive/` → 3 candidati cliente che combaciano con i 3 esistenti in vault demo (verifica E2E del pipeline su input/output noti).
- Happy reale: 1 fattura PDF di un cliente nuovo → genera `EntityCandidate` con `piva`, `nome`, `fatturato_2024` corretti.
- Edge: documento generico (es. un manuale tecnico) → categorizer ritorna lista vuota, no candidates spurious.
- Edge: campo obbligatorio mancante (es. `piva` non in nessun documento) → candidato con `piva: null`, confidence < 1.0, segnalato in review.
- Edge: documento da 80 pagine → chunking, merge, output coerente.
- Schema drift: se domani si aggiunge un campo alla scheda demo, il prompt si aggiorna automatic (via `load_canonical_schema`). Test esplicito.

**Verification:**
- Test deterministico con `FakeLLMProvider` (response YAML pre-registrate).
- Spike reale: input Drive di Valentino → almeno 1 entità estratta correttamente, validata da Valentino visivamente.

---

### U6. Stage review CLI + write

**Goal:** consulente vede ogni candidato, lo confronta con il vault corrente, decide accept/edit/skip/merge. Poi `write` materializza i `.md`.

**Requirements:** R6

**Dependencies:** U1 (StateStore con candidati), U5 (candidati prodotti)

**Files:**
- Create: `product/cli/review/__init__.py`
- Create: `product/cli/review/diff.py` — `diff_entity(candidate, existing_md_path) -> RichRenderable` con highlight per campo (verde = nuovo, giallo = modifica, rosso = conflitto/perso)
- Create: `product/cli/review/interactive.py` — REPL stage-based: itera candidati, mostra diff, accetta input `a/e/s/m/q` (accept / edit / skip / merge / quit)
- Create: `product/cli/review/editor.py` — apre `$EDITOR` su YAML temp file per editing veloce; al return parse + valida
- Create: `product/cli/review/writer.py` — `write_entities(decisions, vault_root)` scrive `<vault>/<entity_type_plural>/<entity_id>.md` con frontmatter serializzato in YAML deterministico (chiavi ordinate come nello schema canonical) + body
- Modify: `product/cli/commands/review.py` — entry point, legge candidati da StateStore, lancia REPL
- Modify: `product/cli/commands/write.py` — finalizza solo `decisions` con status `accept|edit|merge`

**Approach:**
- REPL Rich-based:
  - Pannello sinistro: candidato YAML.
  - Pannello destro: esistente nel vault (se merge candidate).
  - Footer: hint comandi.
- `edit`: apre YAML in editor; al salvataggio rivalida schema; se invalido → mostra errori e ri-edita.
- `merge`: produce un YAML mergiato (eccezioni union, prose append marcato per data, condizioni → consulente sceglie campo-per-campo se conflitto).
- Decisioni persistite in StateStore → `write` separato è idempotente (può girare/ripartire).
- Output `.md`: serializzazione YAML con `sort_keys=False` (rispetta ordine schema), block style per prose lunghi (`default_style='|'` su `note_relazionali`), wrap a 80 char per leggibilità Obsidian.

**Test scenarios:**
- Happy: 3 candidati → accept tutti → 3 file `.md` scritti, ognuno parsabile dall'MCP server esistente (`Vault.get_client` ritorna senza errori).
- Edge: candidato vs esistente identico → diff vuoto, propone "skip silently".
- Edge: edit con YAML invalido → re-edit, no perdita lavoro.
- Edge: merge con conflitto su `condizioni_commerciali.termini_pagamento` (vault dice "60gg", candidato dice "30gg") → prompt esplicito "quale tieni?".
- Edge: ctrl-c durante review → stato salvato, ripresa con `custodia review --resume`.
- Integration E2E: fixture `finto-drive/` → scan fs → build clients → review (accept all, auto-mode `--yes` per test) → write → MCP server `list_clients` ritorna i 3 clienti.

**Verification:**
- pytest end-to-end con `--yes` auto-accept.
- Demo manuale: video screen recording di Valentino che fa scan → review interattivo → write su un Drive reale.

---

## Dependency graph

```
U1 (CLI scaffolding + state) ─┬─> U3 (Drive)  ─┐
                              │                ├─> U5 (Extractor) ──> U6 (Review + Write)
U2 (LLMProvider) ─────────────┘                │
                              ├─> U4 (FS) ─────┘
                              │
                              └─> U6 (commands wiring)
```

- U1 e U2 sono **foundational, parallelizzabili** da subito.
- U3 e U4 sono parallelizzabili dopo U1; U4 dipende da U3 per i parser (shared module).
- U5 parte appena U2 + (U3 o U4) + U1 sono pronti.
- U6 chiude la sequenza ma può iniziare in dry-run su candidati finti appena U1 esiste.

**Sequenziamento raccomandato (2 settimane / 2 dev paralleli):**
- Giorni 1-3: U1 e U2 in parallelo.
- Giorni 3-6: U4 (semplice, sblocca extractor su fixture sintetico) + U3 in parallelo.
- Giorni 5-9: U5 (cuore intelligente, richiede iterazione su prompt).
- Giorni 8-12: U6 (REPL ergonomico, polish).
- Giorni 12-14: integrazione, spike reale Drive Valentino, bugfix, doc.

---

## Sprint-end success criteria

1. ✅ `custodia init && custodia scan fs --root product/cli/tests/fixtures/finto-drive && custodia build clients && custodia review --yes && custodia write` gira end-to-end senza errori e produce 3 file `.md` consumabili dall'MCP server esistente.
2. ✅ Spike Drive reale: Valentino lancia `custodia scan drive --root-folder-id <suo>` su una folder di prova, vede emergere ≥ 1 entità riconoscibile, valida visivamente la scheda generata.
3. ✅ Coverage pytest ≥ 70% sui moduli `product/cli/` (escluso `commands/` wiring).
4. ✅ `LLMProvider` ha 1 adapter funzionante (Anthropic) + 1 fake deterministico. Aggiungere un secondo adapter è documentato e stimato ≤ 1 giorno.
5. ✅ Schema YAML output combacia campo-per-campo con `product/vault-demo/clienti/rossetto-laminazioni.md` (validato da test snapshot).
6. ✅ Costo Claude misurato su spike reale e annotato (rischio "costo per cliente esplode" — punto 5 dei rischi origin).
7. ✅ `product/cli/README.md` permette a un secondo consulente di eseguire il flow senza coaching diretto.

---

## Sprint-1-specific risks

| Rischio | Probabilità | Impatto | Mitigazione |
|---|---|---|---|
| Estrazione LLM produce output schema-incoerente | Alta | Alto | Validator + retry con feedback errore in prompt (1 retry); fallback a `null` su campo unparseable; review umano comunque obbligatorio |
| OAuth Drive flow rotto in casa cliente (firewall, no-browser) | Media | Alto | Documentare in U3 un flow alternativo `--credentials-file` con JSON pre-generato dal consulente sul proprio Mac |
| Costo token per cliente esplode (50K documenti × Sonnet) | Media | Medio | Categorizer Haiku come prefiltro (sconto ~5×); flag `--max-cost-eur` che blocca il run se stima eccede |
| PDF scansionati senza OCR → estrazione zero | Alta su clienti vecchi | Medio | OCR fuori scope v0.1; warning chiaro in scan + suggerimento manuale; `--ocr` flag come escape hatch opzionale |
| Stato SQLite corrotto in mezzo a un run lungo | Bassa | Alto | Transazioni esplicite per ogni documento; `--resume` da run_id |
| Schema canonical drifta dalle schede demo nel tempo | Media | Medio | `load_canonical_schema` riparte ogni run dalla scheda Rossetto → la scheda demo è canone vivo |
| MCP server non legge output del CLI (incompatibilità sottile YAML) | Bassa | Alto | Test E2E in U6: dopo write, instanziare `Vault.get_client(id)` da `product/mcp-server/custodia_mcp.py` e validare |
| Spike Drive reale rivela case non gestiti (es. Shared Drive, Drive di terzi) | Media | Medio | Spike pianificato a fine sprint, non in coda — buffer 2 giorni per risposta |

---

## Documentation / Operational Notes

- Tutto il codice CLI in `product/cli/` (package separato, proprio `pyproject.toml` analogo a `product/mcp-server/`). Convivono nello stesso repo ma non si dependono cross-package: il CLI scrive `.md`, l'MCP server li legge — interfaccia = filesystem.
- Convenzioni di stile: adottare quelle di `product/mcp-server/custodia_mcp.py` come standard de-facto (commenti/docstring in IT, codice EN, `from __future__ import annotations`, no eccezioni propagate ai tool MCP — nel CLI invece eccezioni OK ma con messaggi utente IT).
- Token Drive e API key Anthropic: **mai committati**. `.custodia-state/` è in `.gitignore` (da verificare/aggiungere).
- Dati di clienti reali: lo spike di fine sprint usa Drive di Valentino. Niente dati di clienti veri Custodia in repo o test fixtures.

---

## Out of scope — esplicitamente Sprint 1.5+

- Connettore Outlook 365 / Microsoft Graph (Sprint 1.5)
- Connettore Fatture in Cloud (Sprint 1.5)
- Adapter `SovranoProvider` vero (Sprint 2 o on-demand)
- Auto-discovery sorgenti / watcher continuo (post v2.0)
- HTTP transport del MCP server (consumption side, fuori scope ingestion)
- Multi-vault parallel / multi-tenant (post v2.0)
- OCR di default per PDF immagine (opt-in via flag in Sprint 1.5)

---

## Sources & References

- **Origin:** `docs/brainstorms/custodia-v2-agent-ready-requirements.md` (rev 2, 2026-05-24) — sezioni "Architettura concettuale", "Connettori prioritari per v0.1", "Note di handoff per /ce-plan".
- **Predecessor sprint:** `docs/plans/2026-05-24-001-feat-custodia-v2-sprint-0-validazione-plan.md`.
- **Parallel design:** `docs/plans/2026-05-24-003-design-llm-provider-and-drive-connector.md`.
- **Consumption side esistente:** `product/mcp-server/custodia_mcp.py`, `product/vault-demo/`.
- **Convenzioni:** stile di `product/mcp-server/custodia_mcp.py` + dipendenze già fissate in root `pyproject.toml`.
