---
title: "feat: Custodia v2 Sprint 2a — Scalabilità backend + scan parlante"
type: feat
status: active
date: 2026-05-24
origin: docs/brainstorms/custodia-v2-agent-ready-requirements.md
related:
  - docs/plans/2026-05-24-002-feat-custodia-v2-sprint-1-cli-ingestion-plan.md
  - docs/plans/2026-05-24-003-design-llm-provider-and-drive-connector.md
---

# feat: Custodia v2 Sprint 2a — Scalabilità backend + scan parlante

## Summary

Sprint 1 ha dimostrato il loop end-to-end su 5 documenti finti. Sprint 1.5 ha aggiunto Outlook e Fatture in Cloud. La webapp Streamlit è arrivata a un look premium. **Il prodotto regge a 5 file, blocca a 5000+.** Sprint 2a rende il backend asincrono, parlante e scalabile su filesystem reali (Drive del cliente: 10K-100K file, NAS: anche milioni), senza ancora riscrivere la UI in React.

Sprint 2a chiude con: scan su `~/Documents` del consulente (50K+ file reali) che gira in background, mostra progress live (file corrente, contatore, ETA), può essere fermato con un click, riprende da interruzione, salta file già visti, e non blocca mai la UI.

**Sprint 2b (React rewrite) parte solo dopo aver validato la consumption side con 1-2 clienti veri.** Quel plan verrà scritto in un'altra sessione.

---

## Problem Frame

Il pain emerso dal test reale di oggi: utente avvia scan su `~/Downloads/15_Personale-Vario`, il browser appare bloccato per 10+ minuti, nessun feedback su cosa sta succedendo, nessun modo di fermare. Cause:

1. **Scan sincrono nel main thread Streamlit**: bloccante per tutta la durata, niente progress
2. **Niente cancel token**: una volta avviato non si ferma
3. **Niente incremental scan**: rerun rifa tutto da capo
4. **Niente filtri smart**: tutti i file passano dal parser anche quelli inutili (`.DS_Store`, eseguibili, video, foto fotocamera)
5. **Parsing PDF single-thread**: 1 PDF alla volta, il resto aspetta
6. **Niente resume**: kill del processo perde tutto il lavoro

Questo va risolto PRIMA di portare un cliente di consulenza reale a fare ingestion sui suoi dati veri, altrimenti l'esperienza brucia la prima impressione.

---

## Requirements

- **R1.** Lo scan filesystem produce progress live (file corrente, contatore N/M, ETA stimato) consumabile sia da CLI sia dalla UI.
- **R2.** Lo scan può essere fermato (cancel button) e ripreso da dove era arrivato (resume) senza perdere lavoro.
- **R3.** Lo scan è incrementale: un rerun salta i file già processati (hash + mtime cached nel state DB).
- **R4.** Il parsing PDF/DOCX/XLSX è parallelizzato con thread pool (CPU-bound) con tetto configurabile (default 4 worker).
- **R5.** Filtri intelligenti aggiuntivi: skip eseguibili, app bundles, librerie sistema, file binari non-document, video > 10s, foto Photos.app.
- **R6.** Streamlit UI mostra: file corrente in elaborazione, contatore, ETA, throughput (doc/sec), bottone Stop visibile. Non si blocca mai (anche durante uno scan da 100K file, le altre pagine restano navigabili).
- **R7.** Stress test documentato su una cartella reale del consulente da ≥50K file: lo scan completa, la UI resta reattiva, il file `state.db` non si corrompe.
- **R8.** Cost-of-error contenuto: un crash mid-scan non corrompe il DB, al riavvio si riprende da dove si era fermati.

---

## Scope Boundaries

### Dentro Sprint 2a
- Async/threading backend per scan e build
- Progress streaming (callback + persistent runs.progress)
- Incremental scan via SQLite manifest (hash sha1[16] + mtime)
- Cancel token nei connector
- Thread pool per parser (configurabile)
- Filtri smart aggiuntivi nel filesystem connector
- Streamlit UI aggiornata con st.empty() + polling (no full React rewrite)
- Resume da scan interrotto
- Stress test ≥50K file documentato

### Deferred a Sprint 2b (React rewrite)
- Frontend React + Vite + Tailwind + shadcn/ui
- Websocket vero (oggi facciamo polling con st.empty)
- Virtualization per liste >10K elementi
- Drag & drop per upload
- Multi-finestra / multi-cliente in tab parallele
- Look ulteriormente premium con micro-animation framer-motion

### Outside this product's identity
- Distributed job queue (Celery, RQ, Arq con Redis) — è single-user locale, AsyncIO in-process basta
- Multi-tenant scaling — single-user
- Real-time multi-utente — un consulente alla volta

---

## Key Technical Decisions

- **D1. Job runner: AsyncIO in-process con thread pool per CPU-bound** — non Celery/Redis. Custodia gira sul Mac del consulente, single-user. Aggiungere Redis = operational overhead inutile. Pattern: `asyncio.create_task(scan_job(...))` con `concurrent.futures.ThreadPoolExecutor` per i parser.
- **D2. Progress channel: tabella SQLite `runs.progress_json`** — non WebSocket. Streamlit non supporta WebSocket nativamente. Tabella aggiornata ogni ~500ms dal job runner, Streamlit polla con `st.empty()` + `time.sleep(0.5)` in un loop. Quando passeremo a React useremo WebSocket vero.
- **D3. Cancel: shared mutable flag `CancelToken`** passato al connector. Il connector check-a `token.cancelled` a ogni file. Il flag vive in memoria (lifecycle = durata del job) ma il *job status* è persistente nella tabella `runs`.
- **D4. Incremental: hash sha1(content) troncato a 16 byte + mtime** memorizzati in nuova tabella `scan_manifest`. Match su (source_id, hash) → skip. Match su (source_id, NOT hash, mtime older) → re-scan. Match su mancante → scan nuovo.
- **D5. Thread pool size: `os.cpu_count() - 1`, capped a 8** — i parser sono I/O+CPU-bound (read + parse), 4-8 worker ottimi su laptop M1/M2/M4. Default configurabile via env `CUSTODIA_PARSER_WORKERS`.
- **D6. Resume: `runs.status='running'` al kill resta 'running' fino a 5 minuti dopo last heartbeat. Allo startup il `register_run` controlla se c'è un run abbandonato (status=running, heartbeat>5min) e lo segna 'interrupted', poi il connector può ripartire da `last_processed_source_id`.
- **D7. UI threading model in Streamlit**: il job gira in un thread di background lanciato col bottone Scan; il main thread Streamlit pollarsi `runs.progress_json` ogni 500ms via `st.empty()` placeholder + `time.sleep`. Stop button mette il `CancelToken.cancelled = True`. Streamlit re-render fluido.

---

## Implementation Units

### U1. Job runner + CancelToken + progress channel

**Goal:** infrastruttura backend per eseguire scan/build in modo asincrono, con progress che fluisce verso UI e cancel-stoppabile dall'esterno.

**Requirements:** R1, R2, R6, R8

**Files:**
- Create: `product/cli/custodia_cli/jobs/__init__.py`
- Create: `product/cli/custodia_cli/jobs/runner.py` — `Job`, `JobRunner`, `JobStatus` enum
- Create: `product/cli/custodia_cli/jobs/cancel.py` — `CancelToken` (thread-safe)
- Create: `product/cli/custodia_cli/jobs/progress.py` — `ProgressReporter` con coalescing (skip update se < 200ms dall'ultimo)
- Modify: `product/cli/custodia_cli/state/store.py` — aggiungi colonna `runs.progress_json TEXT` + metodi `update_run_progress`, `get_run_progress`, `mark_run_heartbeat`
- Modify: `product/cli/custodia_cli/state/schema.sql` — version bump a v4, aggiunta colonna
- Create: `product/cli/tests/test_jobs_runner.py`
- Create: `product/cli/tests/test_cancel_token.py`
- Create: `product/cli/tests/test_progress_reporter.py`

**Approach:**
- `Job` ha campi `id, name, status, started_at, completed_at, summary, progress_payload, cancel_token`
- `JobRunner.submit(fn, *args, cancel_token=...) -> Job` — esegue in thread separato
- `ProgressReporter.update(current=N, total=M, current_file=..., throughput=..., eta_sec=...)` — write su `runs.progress_json` (UPSERT) con coalescing
- `CancelToken` è `threading.Event` wrapper con `set_cancelled()` e `is_cancelled` property

**Test scenarios:**
- Happy: job completa, `runs.status='success'`, `progress_payload` ha update intermedi
- Cancel: chiama `token.set_cancelled()` mid-flight → job ritorna in stato `cancelled`, summary include "Interrotto"
- Heartbeat: job che dorme 10 sec aggiorna heartbeat ogni N — verifica timestamps in DB
- Concurrent: 2 job paralleli — verifica isolamento dei progress_payload (per run_id)
- Crash: kill del thread → `runs.status` resta 'running' ma `heartbeat_at` non si aggiorna più; al rerun viene marcato `interrupted`

---

### U2. Incremental scan + manifest

**Goal:** skip dei file già processati in run precedenti dello stesso progetto, basato su hash content + mtime.

**Requirements:** R3, R7

**Dependencies:** U1 (per progress)

**Files:**
- Modify: `product/cli/custodia_cli/state/store.py` — nuova tabella `scan_manifest`, metodi `seen_before`, `mark_seen`, `count_manifest`, `clear_manifest`
- Modify: `product/cli/custodia_cli/state/schema.sql` — DDL tabella manifest, schema v4 → v5
- Modify: `product/cli/custodia_cli/connectors/filesystem.py` — pre-check manifest prima di hashare/parsare, post-process `mark_seen`
- Create: `product/cli/tests/test_scan_manifest.py`
- Create: `product/cli/tests/test_filesystem_incremental.py`

**Approach:**
- Tabella `scan_manifest`: `(connector_name TEXT, source_id TEXT, content_hash_sha1_16 BLOB, mtime_iso TEXT, file_size INTEGER, last_seen_run_id INTEGER, PRIMARY KEY (connector_name, source_id))`
- Algoritmo pre-file:
  1. Calcola `(source_id, mtime, size)` SENZA aprire/hashare
  2. Lookup manifest by `(connector, source_id)`. Se match e `mtime + size invariati` → skip silenzioso (incrementa `stats['skipped_unchanged']`)
  3. Se mtime/size differiscono OR manifest assente → hash full content → match by `(connector, hash)`
  4. Se hash match (file rinominato o spostato) → riusa source_id esistente
  5. Se hash mismatch o nuovo → processa file, aggiorna manifest
- Hash sha1 troncato a 16 byte (128 bit, collisione astronomica per <100M file)

**Test scenarios:**
- Happy: scan iniziale popola manifest. Rerun stessa cartella → 100% skipped_unchanged.
- File modificato: rerun → file ri-processato (mtime cambiato), manifest aggiornato
- File rinominato (stesso content): rerun → riusa source_id originale, no duplicato
- File cancellato: scan non lo trova, manifest resta (orphan accettato per ora; cleanup è fuori scope Sprint 2a)
- Cancel mid-scan: i file processati fino a quel punto sono in manifest, rerun riprende
- Stress: 10K file scan iniziale + rerun 100% incrementale → secondo rerun deve essere ≥10x più veloce

---

### U3. Filtri smart + thread pool parser

**Goal:** ridurre il numero di file che entrano nel parser pipeline + parallelizzare il parsing.

**Requirements:** R4, R5

**Dependencies:** U1, U2

**Files:**
- Modify: `product/cli/custodia_cli/connectors/filesystem.py` — `_SMART_EXCLUDES` allargato, prefilter MIME via magic bytes (NON solo estensione), thread pool per parser
- Modify: `product/cli/custodia_cli/connectors/parsers/__init__.py` — `ParserPool` wrapper attorno a ThreadPoolExecutor
- Create: `product/cli/tests/test_smart_filters.py`
- Create: `product/cli/tests/test_parser_pool.py`

**Smart excludes (aggiungere a `_DEFAULT_EXCLUDES`):**
- Eseguibili: `*.app`, `*.exe`, `*.dmg`, `*.pkg`, `*.deb`, `*.rpm`, `*.iso`
- Librerie/build: `node_modules`, `.next`, `dist`, `build`, `target`, `.gradle`, `.m2`, `.cargo`
- Cache sistema: `~/Library/Caches`, `~/Library/Application Support` (default exclude se root contiene `Library`)
- Foto Photos.app: `*.photoslibrary` (database, non da scannare)
- Video brevi (preview/screen recording): `.mov`, `.mp4` skippate di default
- Foto fotocamera massive: `.heic`, `.heif`, `.raw`, `.cr2`, `.nef` skippate
- Database/binari: `*.sqlite`, `*.db`, `*.dat`, `*.bin`
- Compresse non-document: `*.zip`, `*.tar.gz`, `*.7z`, `*.rar` (oggi le ignoriamo già implicitamente, esplicitiamo)
- Streamlit cache: `.streamlit`, `__pycache__` (già escluso)

**Magic bytes prefilter:** prima di parsare, leggi primi 16 byte del file e confronta con magic signature attesa per il MIME del'estensione. Se mismatch (es. `.pdf` ma non inizia con `%PDF`) → skip + log warning.

**ParserPool:**
- `ThreadPoolExecutor(max_workers=os.cpu_count()-1 capped 8)` configurabile via env
- `pool.parse(path, mime) -> Future[str]` — submit asincrono, yield risultati con `as_completed`
- Order preservation NON necessario (lo state store accetta documenti in qualsiasi ordine)

**Test scenarios:**
- Smart exclude `node_modules`: cartella di test con `node_modules/` 1k file dentro → 0 file processati
- Magic byte mismatch: file `fake.pdf` che è in realtà text → skip con warning loggato
- Thread pool: 100 PDF in parallelo, verifica throughput > single-thread (benchmark)
- Pool shutdown su cancel: cancel mid-batch chiude pool entro 5sec, in-flight task completano o terminano

---

### U4. Streamlit UI parlante (scan + build)

**Goal:** UI Streamlit che mostra progress live durante scan/build, con cancel button, file corrente, ETA, throughput.

**Requirements:** R1, R2, R6

**Dependencies:** U1, U2, U3

**Files:**
- Modify: `product/web/custodia_web/services/scan.py` — wrap job runner invece di chiamata sincrona
- Modify: `product/web/custodia_web/pages/scan.py` — UI polling con `st.empty()` + `time.sleep(0.5)` loop
- Create: `product/web/custodia_web/components/live_progress.py` — componente riusabile per progress live
- Modify: `product/web/custodia_web/pages/build.py` — stesso pattern

**UX target — pagina Scan durante scan attivo:**
```
┌─────────────────────────────────────────────────────────────┐
│  Scan filesystem in corso · cliente Decathlon                │
│                                                             │
│  ████████████████░░░░░░░░░░░░░░░░░░░  47% · 23,420 / 50,012 │
│                                                             │
│  📄 Sto leggendo:                                            │
│     /Users/.../Documenti/clienti/decathlon/2024/             │
│        offerta-Q3-revisione.docx                             │
│                                                             │
│  Throughput: 142 doc/sec · ETA: 3 min 12 sec                │
│                                                             │
│  Skippati: 1.245 (excluded) · 832 (size) · 410 (tipo)       │
│                                                             │
│  [ ⏸  Sospendi ]  [ ✕  Annulla ]                            │
└─────────────────────────────────────────────────────────────┘
```

**Streamlit threading pattern:**
```python
# nel handler del bottone "Scan"
cancel_token = CancelToken()
job = runner.submit(scan_filesystem, ..., cancel_token=cancel_token)
st.session_state['active_job_id'] = job.id
st.session_state['active_cancel_token'] = cancel_token

# poi un st.empty() loop che polla runs.progress_json
progress_placeholder = st.empty()
while True:
    prog = store.get_run_progress(job.id)
    if prog['status'] in ('success', 'error', 'cancelled'):
        break
    with progress_placeholder.container():
        render_live_progress(prog)
    time.sleep(0.5)
```

**Cancel button** scrive `cancel_token.set_cancelled()` e attende che lo status passi a 'cancelled'.

**Test scenarios:**
- UI rimane reattiva durante scan da 10K file (le altre pagine sono navigabili — bisogna usare `st.session_state` per il job persistente)
- Cancel button effettivamente ferma lo scan entro 5 sec
- Sospendi (opzionale Sprint 2a) — può anche essere DEFERRED a 2b
- ETA si stabilizza dopo i primi 100 file
- Throughput è aggiornato ogni 500ms

---

### U5. Resume da scan interrotto

**Goal:** se uno scan è stato killato (crash, kill del processo, ctrl+c CLI), al rerun parte da dove si era fermato.

**Requirements:** R2, R8

**Dependencies:** U1, U2

**Files:**
- Modify: `product/cli/custodia_cli/state/store.py` — `find_interrupted_runs(threshold_minutes=5)`, `mark_run_interrupted`
- Modify: `product/cli/custodia_cli/jobs/runner.py` — startup hook che marca run abbandonati
- Modify: `product/cli/custodia_cli/commands/scan.py` — sub-comando `scan resume --run-id ID` opzionale
- Modify: `product/web/custodia_web/pages/scan.py` — banner "C'è uno scan interrotto, vuoi riprendere?" se rilevato
- Create: `product/cli/tests/test_scan_resume.py`

**Approach:**
- All'avvio del JobRunner, check tutti i runs con `status='running' AND heartbeat_at < NOW() - 5 min`
- Marcali `status='interrupted'`, summary "Crash o kill del processo"
- Al successivo scan sullo stesso connector+root, banner UI: "C'è uno scan interrotto in corso per questa sorgente. Riprendere o ripartire da zero?"
- "Riprendi" → riparte ma il manifest U2 fa da fatto skip dei file già processati. Il sub-comando CLI è opzionale.

**Test scenarios:**
- Kill processo durante scan, riavvio → run marcato interrupted, manifest contiene i file fatti finora
- Rerun manuale UI → riprende, manifest skippa i fatti, processa solo i rimanenti
- Multiple interrupted runs su connector diversi → ogni connector ha il suo banner separato

---

### U6. Stress test + benchmark documentato

**Goal:** dimostrare che lo Sprint 2a regge una cartella reale del consulente con tens of thousands of files.

**Requirements:** R7

**Dependencies:** U1-U5 tutti

**Files:**
- Create: `product/cli/tests/test_stress_filesystem.py` — test con fixture sintetica grande (5K file generati programmaticamente)
- Create: `product/cli/tests/fixtures/stress/generate.py` — script per generare 5K file finti (TXT + PDF + DOCX + XLSX in proporzioni realistiche)
- Create: `docs/solutions/2026-05-24-sprint-2a-scalability-benchmark.md` — doc operativo con risultati su ~Documents reale del consulente

**Misura:**
- Tempo totale scan iniziale (cold) su 50K file
- Tempo scan incrementale (cached) su stessi 50K file
- Throughput: doc/sec medio + mediana
- Memory peak (resident set size del processo)
- File processed vs skipped breakdown
- Cancel responsiveness (tempo dal click Stop alla terminazione effettiva)

**Bench su laptop M1/M2/M4 medio dovrebbe target:**
- Cold scan 50K file: ≤10 minuti, ≤2GB RAM peak
- Hot (incremental) scan 50K file: ≤30 sec
- Cancel responsiveness: ≤5 sec

**Test scenarios:**
- Fixture sintetica 5K file → completa in <2 min su CI macchina, no OOM, no crash
- Test su `~/Documents` reale del developer: documenta i numeri in `docs/solutions/...`

---

## Dependency graph

```
U1 (job runner + progress) ──┬─► U2 (incremental)  ──┐
                              │                       ├─► U4 (Streamlit UI)
U3 (smart filters + pool) ────┤                       │
                              │                       │
                              └─► U5 (resume) ────────┘
                              
                              U6 (stress test) → finale, depends on tutti
```

**Sequenziamento (1 dev, ~5 giorni)**:
- Giorno 1: U1
- Giorno 2: U2
- Giorno 3: U3
- Giorno 4: U4 + U5 (paralleli, file diversi)
- Giorno 5: U6 + bugfix + doc

---

## Sprint-end success criteria

1. ✅ `custodia scan fs --root ~/Documents --vault /tmp/test` (con ~Documents reale ~50K file) completa entro 10 minuti, mostra progress live, restituisce status `success`
2. ✅ Rerun stessa cartella entro 30 secondi (skip 100% via manifest)
3. ✅ Cancel mid-scan via UI ferma entro 5 sec con state consistente
4. ✅ Kill del processo mid-scan + riavvio webapp → banner "scan interrotto", click resume completa
5. ✅ UI Streamlit reattiva durante scan (le altre pagine navigabili)
6. ✅ Smart filtri eliminano: `node_modules`, `*.dmg`, `*.app`, `.photoslibrary`, video/heic
7. ✅ Throughput su ≥4 worker visibilmente maggiore di single-thread (benchmark documentato)
8. ✅ Test suite passa: 367 esistenti + i nuovi (target +30-40 nuovi)

---

## Sprint-2a-specific risks

| Rischio | Probabilità | Impatto | Mitigazione |
|---|---|---|---|
| Streamlit + threading hanno race condition viziose su `st.session_state` | Alta | Medio | Usa state_store SQLite come "memoria condivisa" fra thread, non `st.session_state` direttamente. Test specifico per la race "click cancel mentre il polling re-renderizza" |
| SQLite write contention fra job thread e UI polling thread | Media | Alto | Solo il job thread scrive; UI solo legge. WAL mode già attivo (verifica) |
| Hash sha1 di 50K PDF è I/O+CPU bound che da solo dura 10+ minuti | Media | Medio | Hash solo i primi 1MB del file (sufficiente per detection di modifiche; collisione astronomicamente bassa) |
| File handle leak nel thread pool su crash di un singolo parser | Bassa | Alto | Context manager rigoroso, test specifico con parser che solleva, verifica `lsof` count stabile |
| `os.cpu_count()` su Mac M4 ritorna 14 → pool da 13 worker pestelli memoria | Bassa | Medio | Cap a 8 (default), configurabile via env. Documentato. |
| Resume con manifest corrotto perde lavoro | Bassa | Alto | Manifest scritto in transaction per ogni file, NON in batch. Crash a metà di un file = manifest non aggiornato → ri-processo, no perdita |

---

## Documentation / Operational Notes

- Tutto il codice resta in Python 3.10+, asyncio + threading. NO nuove dipendenze pesanti (no Celery, no Redis, no Arq).
- Versione schema StateStore passa da v3 a v5 (v4 aggiunge `runs.progress_json`, v5 aggiunge tabella `scan_manifest`). Le migration sono additive, no breaking.
- Convenzioni stile: come sempre (`from __future__ import annotations`, italiano docstring, English identifier).
- Aggiorna `.streamlit/config.toml` se serve (probabilmente no).
- Quando Sprint 2b arriverà (React rewrite), il pattern di progress streaming via state.db tornerà utile: il backend FastAPI esporrà GET `/runs/{id}/progress` invece di Streamlit polling.

---

## Out of scope — esplicitamente Sprint 2b o oltre

- **React + Vite + Tailwind + shadcn/ui frontend** — Sprint 2b (dopo validazione con 1-2 clienti veri)
- **WebSocket vero** — Sprint 2b con FastAPI backend
- **Virtualization per liste >10K candidati** — Sprint 2b (oggi review usa tabella semplice, ok per <500 candidati)
- **Distributed job queue (Celery/Redis)** — fuori product identity (single-user locale)
- **Multi-tenant** — fuori product identity
- **Drag & drop upload** — Sprint 2b
- **Notifiche desktop a scan completato** — Sprint 2b o oltre
- **Pause/Resume granulare** (oltre il resume da crash) — opzionale Sprint 2b

---

## Sources & References

- **Origin product**: `docs/brainstorms/custodia-v2-agent-ready-requirements.md`
- **Sprint 1 plan**: `docs/plans/2026-05-24-002-feat-custodia-v2-sprint-1-cli-ingestion-plan.md`
- **Design LLM/Drive**: `docs/plans/2026-05-24-003-design-llm-provider-and-drive-connector.md`
- **Real-world trigger**: utente ha tentato scan su `~/Downloads/15_Personale-Vario` durante demo session 2026-05-24, blocco UI 10+ minuti senza feedback
- **Streamlit existing code**: `product/web/custodia_web/services/scan.py`, `pages/scan.py`
- **Backend existing code**: `product/cli/custodia_cli/connectors/filesystem.py`, `commands/scan.py`, `state/store.py`
