# Brief — Step 2 Tech Plan (scanner / extractor / batch)

Design tecnico dello Step 2: il pezzo di toolkit che Valentino lancia dopo il kick-off on-site per scandagliare le sorgenti del cliente, produrre bozze nel vault PMI e fargliele approvare a batch da 50.

Il doc è scritto per un implementatore (umano + Claude Code agentico) che il giorno dopo aver chiuso Step 1 deve poter aprire la prima PR. Dove non c'è certezza tecnica, è marcato esplicitamente come `[DA VERIFICARE]` con suggerimento di dove risolvere il dubbio.

---

## Indice

1. Architettura generale
2. Scanner — uno per fonte
3. Extractor — uno per tipo di file
4. Categorizer
5. Reconciler
6. Batch approval workflow
7. Costo Claude per cliente medio
8. Privacy e modalità on-premise (preview Step 3)
9. Tempi e dimensionamento
10. Risks e cose escluse
11. Roadmap implementativa (in che ordine si scrive)

---

## 1. Architettura generale

### 1.1 Flusso end-to-end

```
                    ATTO 1                          ATTO 2 (remoto, batch)                           ATTO 3
                ┌────────────┐
KICK-OFF ──────▶│ bootstrap/ │
on-site         │ wizard +   │
                │ config.yml │
                └─────┬──────┘
                      │
                      ▼
              ┌──────────────────┐
              │   scanners/      │       per ognuna delle 5 fonti
              │  (gdrive, m365,  │  ─────────────────────────────────▶  inventory/<source>/files.jsonl
              │  email, nas,     │       (un JSONL per fonte, append-only)
              │  server)         │
              └─────────┬────────┘
                        │
                        ▼
              ┌──────────────────┐
              │   extractors/    │       legge files.jsonl, scarica il file fisico
              │  (pdf, docx,     │  ─────────────────────────────────▶  extracted/<sha>/main.md
              │  xlsx, eml, ocr) │                                       extracted/<sha>/meta.json
              └─────────┬────────┘
                        │
                        ▼
              ┌──────────────────┐
              │  categorizer/    │       regole + Claude solo sui dubbi
              │  (5 categorie    │  ─────────────────────────────────▶  aggiorna files.jsonl
              │  VIVO/DA-CONS/   │                                       con categoria + confidence
              │  ARCHIVIO/etc.)  │
              └─────────┬────────┘
                        │
                        ▼
              ┌──────────────────┐
              │  reconciler/     │       dedup, dedup-soft, raggruppa
              │  (hash, regex,   │  ─────────────────────────────────▶  drafts/<batch-id>/*.md
              │  scheda-cliente, │                                       (bozze di vault/clienti/X.md,
              │  persone)        │                                        persone.md, ecc.)
              └─────────┬────────┘
                        │
                        ▼
              ┌──────────────────┐
              │  batch-ui/       │       mini web UI locale (Flask/FastAPI)
VALENTINO ───▶│  approve N=50    │  ─── approvati ────▶ flush in vault/
              │                  │  ─── rejected ─────▶ restano in _audit/
              └─────────┬────────┘  ─── edited ──────▶ riapplicati e re-validati
                        │
                        ▼
                  vault/ + _audit/decisions.jsonl
                                                                                     ┌────────────┐
                                                                                     │ HANDOVER   │
                                                                                     │ ½ giornata │
                                                                                     │ training   │
                                                                                     │ Custode    │
                                                                                     └────────────┘
```

Ogni stage è **idempotente** e **resumable**: ri-eseguirlo non duplica, e se cade a metà riparte dall'ultimo file processato.

### 1.2 Linguaggio e runtime

**Python 3.11+** come linguaggio principale.

Motivazioni:
- Ecosistema librerie per parsing documentale (`pypdf`, `pdfplumber`, `python-docx`, `openpyxl`, `mailbox`, `tesseract` bindings) molto più maturo di Node
- Anthropic SDK Python è first-class
- Valentino è già su Mac (Apple Silicon) → `uv` + venv standard, nessuna sorpresa
- Per on-premise futuro (Step 3): Docker image Python è banale, niente toolchain Node + native modules

Eccezioni:
- **Bash** per gli entry point lato Valentino: `./scan.sh gdrive`, `./extract.sh`, `./approve.sh`. Wrapper sottili sopra moduli Python (~10 righe ognuno)
- **Mini web UI** per batch approval: Flask + HTMX (no React, no build step). Server locale `127.0.0.1:7423` lanciato dal CLI. HTMX permette diff viewer + checkbox senza JS handwritten

Package manager: **`uv`** (Astral). Più veloce di pip, lockfile deterministico, supporta sia venv che ambienti effimeri (`uv run`). Banale da spiegare al Custode in Atto 3.

Dipendenze pesanti (Tesseract, Pandoc) installate via Homebrew sul Mac di Valentino + documentate in `bootstrap/INSTALL.md`. Per on-premise: incluse nell'immagine Docker.

### 1.3 Layout cartelle prodotto

Cartelle nuove da creare a Step 2 (sorelle di `vault/`, `skills/`, `docs/`):

```
.
├── bootstrap/                # script + config kick-off Atto 1
│   ├── wizard.py             # CLI interattiva: domande al Custode
│   ├── config.template.yml   # template di config cliente
│   ├── INSTALL.md            # prerequisiti Mac (brew install tesseract, ...)
│   └── auth/                 # gestione token OAuth, service account
│       ├── gdrive.py
│       ├── m365.py
│       └── gmail.py
│
├── scanners/                 # uno per fonte
│   ├── _base.py              # classe base Scanner + JSONL writer
│   ├── gdrive.py
│   ├── m365.py
│   ├── email.py
│   ├── nas.py
│   └── server.py
│
├── extractors/               # uno per tipo file
│   ├── _base.py              # classe base Extractor
│   ├── _registry.py          # mapping mime/estensione → extractor
│   ├── pdf.py                # pdf testuali (pypdf/pdfplumber)
│   ├── pdf_ocr.py            # pdf scansionati (tesseract + opzionale Claude vision)
│   ├── docx.py               # pandoc o mammoth
│   ├── xlsx.py               # openpyxl + strategy per gestionali "artigianali"
│   ├── eml.py                # mailbox stdlib
│   └── plain.py              # txt, md, csv (passthrough)
│
├── categorizers/
│   ├── rules.py              # euristiche (data, dimensione, path, naming)
│   ├── claude.py             # chiamate Claude per casi DA-CHIARIRE
│   └── pipeline.py           # orchestra rules → claude → output
│
├── reconcilers/
│   ├── dedup_hash.py         # file identici binari
│   ├── dedup_soft.py         # naming pattern _v\d+, _FINAL, copia di
│   ├── schede.py             # genera bozza scheda cliente/fornitore/commessa
│   └── persone.py            # estrae persone da email/firme
│
├── _status/                  # output runtime, non versionato
│   ├── inventory/            # JSONL per fonte (scanners)
│   ├── extracted/<sha>/      # markdown estratti
│   ├── drafts/<batch-id>/    # bozze pronte per approvazione
│   ├── audit/                # decisions.jsonl + log di tutto
│   └── cost.jsonl            # tracking spesa Claude per call
│
├── batch_ui/                 # web UI locale
│   ├── server.py             # Flask
│   ├── templates/            # Jinja
│   └── static/               # htmx, pico.css
│
└── pyproject.toml            # dipendenze (uv)
```

Note:
- `_status/` è in `.gitignore`. È output di runtime, vive solo sulla macchina di Valentino o on-premise dal cliente. **Mai** committato (può contenere dati cliente)
- Lo Step 3 aggiungerà la dashboard come `_status/dashboard.html` o `_status/INDEX.md` rigenerato a ogni stage
- Le 5 categorie del Custode (VIVO/DA-CONSULTARE/ARCHIVIO/CESTINO/DA-CHIARIRE) sono enum unico in `categorizers/_enums.py`, importato sia da rules che da claude

### 1.4 Config cliente

Generato dal wizard (Atto 1), vive in `bootstrap/clients/<cliente-slug>/config.yml`. Esempio:

```yaml
cliente:
  slug: officina-bianchi
  nome: "Officina Bianchi Srl"
  custode: GB
  owner: AF

sorgenti:
  gdrive:
    enabled: true
    workspace: bianchi.it
    auth: service-account
    perimetro:
      include: ["Drive condivisi/Commerciale", "Drive condivisi/Produzione"]
      exclude: ["Drive condivisi/HR", "Cestino"]
  m365:
    enabled: false
  email:
    enabled: true
    provider: gmail
    accounts: ["info@bianchi.it"]
    folders: ["Clienti", "Fornitori", "Allegati"]
  nas:
    enabled: true
    mount: "/Volumes/NAS-bianchi/condiviso"
    perimetro:
      include: ["Commerciale", "Amministrazione"]
      exclude: ["CAD-vivi", "Foto-cantieri"]
  server: { enabled: false }

filtri_globali:
  max_file_mb: 50
  exclude_extensions: [".dwg", ".step", ".iges", ".mp4", ".mov", ".zip", ".dmg"]
  exclude_paths_glob: ["**/.git/**", "**/node_modules/**", "**/_ARCHIVIO/**"]

privacy:
  modalita: safe
  log_dati_a_anthropic: true

batch:
  size: 50
  cost_alert_eur: 50
  cost_hard_stop_eur: 200
```

---

## 2. Scanner — uno per fonte

Tutti gli scanner ereditano da `scanners/_base.py`:

```python
class Scanner:
    def __init__(self, config, state_dir): ...

    def scan(self) -> Iterator[FileRecord]:
        """Yields FileRecord, idempotent, resumable."""
        raise NotImplementedError

    def _checkpoint(self, cursor): ...
    def _resume(self): ...

@dataclass
class FileRecord:
    source: str
    source_id: str
    path: str
    name: str
    size: int
    mtime: datetime
    mime: str
    author: str | None
    last_modified_by: str | None
    permissions: dict | None
    sha256: str | None
    extras: dict
```

Output uniforme: **JSONL** in `_status/inventory/<source>.jsonl`, una riga per file. Append-only.

Motivazione JSONL su CSV/SQLite:
- streamable, banale da debuggare con `jq`
- nessun lock, nessuna concorrenza
- SQLite si potrebbe valutare in v1.5 se la dashboard diventa pesante (Step 3)

### 2.1 Google Drive / Workspace

| Campo | Valore |
|---|---|
| MCP esistente? | `[DA VERIFICARE in 05-mcp-audit.md]` |
| Libreria | `google-api-python-client` + `google-auth` |
| Auth | Service account con domain-wide delegation per Workspace, OAuth desktop per Drive personali |
| Estrae per file | id, name, parents, mimeType, size, modifiedTime, owners, lastModifyingUser, permissions, md5Checksum, webViewLink |
| Output | `_status/inventory/gdrive.jsonl` |
| Filtri perimetro | include/exclude path, max_file_mb, exclude_extensions |
| Resume | Cursor = ultimo modifiedTime, salvato in `_status/inventory/gdrive.cursor` |
| Incremental | `changes.list` con pageToken per re-scan post-handover |

**Trabocchetti**: Shared Drives richiedono `corpora=allDrives`. Google Docs nativi non hanno md5, vanno esportati. Rate limit 1000/100s/utente.

### 2.2 Microsoft 365 / OneDrive / SharePoint

| Campo | Valore |
|---|---|
| MCP esistente? | `[DA VERIFICARE in 05-mcp-audit.md]` |
| Libreria fallback | `msgraph-sdk` |
| Auth | App registration Azure AD, client credentials flow per scan bulk |
| Estrae | driveItem.id, name, parentReference.path, file.mimeType, size, lastModifiedDateTime, createdBy, lastModifiedBy, permissions, file.hashes.quickXorHash |
| Output | `_status/inventory/m365.jsonl` |
| Resume | Delta queries (`/drives/{id}/root/delta`) |

**Trabocchetti**: SharePoint multi-site richiede list sites in config. Hash diverso da SHA256: dedup intra-fonte usa hash nativo, cross-fonte fa lazy SHA256.

### 2.3 Email (Gmail / Outlook)

| Campo | Valore |
|---|---|
| Libreria | Gmail: `google-api-python-client`. Outlook: `msgraph-sdk` |
| Auth | OAuth o service account con delegation |
| Estrae per messaggio | message-id, threadId, subject, from, to, cc, date, snippet (200 char), body_size, attachments |
| Output | `_status/inventory/email.jsonl` — una riga per messaggio. Allegati come record FILE separati con `source: "email-attachment"` |
| Filtri | Label/folder dal config. Skip trash/spam. Default skip senza allegati con body < 500 char |
| Resume | Gmail historyId, Outlook delta token |

**Trabocchetti**: caselle `info@` con 7000+ mail. Strategia filtro hard `has:attachment` o `from:` cliente noto. Privacy: modalità `safe` invia solo `subject + from + first_500_chars`.

### 2.4 NAS / cartelle di rete

| Campo | Valore |
|---|---|
| MCP esistente? | Non serve, solo filesystem. Python stdlib + `pathlib` |
| Libreria | `pathlib`, `os.scandir`, `hashlib`, `python-magic` |
| Auth | Nessuna applicativa. Mount SMB/NFS già autenticato a livello OS |
| Estrae | path, name, size, mtime, mime, owner uid/gid (best-effort), permessi POSIX, sha256 |
| Output | `_status/inventory/nas.jsonl` |
| Filtri | glob pattern include/exclude, exclude_paths_glob globale |
| Resume | Bloom filter di path già processati su disco |

**Trabocchetti**: NAS 320GB con 45k file = 30-60 min hash. Mitigazione: hash solo file che passano i filtri. POSIX su SMB su Mac spesso `nobody:nobody`. Skip symlink di default.

### 2.5 Server interno

**Scenario A** (Linux/Windows server con cartelle condivise): identico a NAS, riusa `scanners/nas.py` con mount diverso.
**Scenario B** (app web custom / DB casereccio): **escluso v1**. Workaround: Custode esporta CSV/Excel manualmente.

`scanners/server.py` a v1 = thin wrapper su NAS con etichetta diversa.

### 2.6 Dedup hash globale

Post-step `scanners/dedup_index.py` legge tutti i `*.jsonl`, costruisce `_status/inventory/_by_hash.json` mappa `sha256 → [file_records]`. Usato dal reconciler.

---

## 3. Extractor — uno per tipo di file

Tutti ereditano da `extractors/_base.py`:

```python
class Extractor:
    name: str
    mimes: list[str]
    extensions: list[str]

    def extract(self, file_path: Path, record: FileRecord) -> ExtractionResult:
        raise NotImplementedError

@dataclass
class ExtractionResult:
    markdown: str
    metadata: dict
    warnings: list[str]
    quality: float
```

Output uniforme:

```
_status/extracted/<sha256-first-12>/
├── main.md
├── meta.json
├── source.json
└── _warnings.log
```

Il registry mappa mime → extractor. Estensione fallback. Mime/estensioni non gestite → fallback a `plain.py` se UTF-8-decodable, altrimenti skip.

### 3.1 PDF testuale → markdown

| Opzione | Pro | Contro | Scelta |
|---|---|---|---|
| `pypdf` | leggero | layout-naive | fallback |
| `pdfplumber` | gestisce tabelle | più lento | **primario** |
| `marker` (Datalab) | qualità eccellente | dipendenze pesanti | opzionale post-MVP |
| `pymupdf` | velocissimo | AGPL → no commerciale | escluso |

**Decisione**: `pdfplumber` primario. Se `quality < 0.5` → passato a `pdf_ocr.py`.

### 3.2 PDF scansionato → OCR

| Opzione | Pro | Contro |
|---|---|---|
| Tesseract | gratuito, on-premise, multilingua | qualità mediocre su scansioni vecchie |
| Claude vision (Sonnet) | qualità altissima | ~$0.003/pagina |
| Apple Vision (macOS) | ottimo italiano, gratuito | non portabile Linux |

**Strategia ibrida**:
1. Tesseract primario su tutto
2. Se `quality < 0.6` retry con Claude vision pagina per pagina solo su quelle problematiche
3. Budget cap: max N pagine Claude vision per cliente (default 200 = ~$0.60)

`pdf_ocr.py` logga ogni chiamata Claude in `_status/cost.jsonl`.

`[DA VERIFICARE]`: in Atto 1 Valentino campiona 20 PDF con `extractors/_pdf_quality_check.py` per stimare quanti finiranno in OCR-Claude → preventivo.

### 3.3 DOCX → markdown

**Scelta**: `pandoc -f docx -t gfm --extract-media=...`. Fallback: `mammoth` con warning.

Immagini incorporate: estratte in `_status/extracted/<sha>/media/` e linkate.

### 3.4 XLSX → markdown table

**Il caso difficile della v1.** Excel-gestionali PMI sono spesso: 47 fogli con uno solo usato, tabelle alla riga 8 dopo header con celle merged, colonne nascoste, celle libere posizionate visivamente.

Libreria: `openpyxl`.

Strategia:
```python
for sheet in workbook:
    if sheet.is_empty(): continue
    if sheet.cell_count < 10: skip_with_warning("foglio quasi vuoto")
    # Heuristic: trova "tabella vera"
    # 1. prima riga con >= 3 celle non-vuote contigue → assumi header
    # 2. legge fino a prima riga interamente vuota
    # Output: H2 per foglio, tabella markdown, annotazioni libere come bullet
```

Per > 5 fogli: multi-sezione H2. Per > 1000 righe: tronca + warning.

**Escluso v1**: Excel con macro VBA, pivot dinamiche, link a fonti esterne → `quality: 0.3` + `DA-CHIARIRE`.

### 3.5 EML → markdown

Libreria: `mailbox` + `email` stdlib.

Output:
```markdown
---
from: m.rossi@bianchi.it
to: a.ferrari@bianchi.it
date: 2024-03-12T10:23:00
subject: Re: offerta Verdi Costruzioni
message-id: <abc@bianchi.it>
attachments: 2
---

## Allegati
- `[2024-03-12_offerta-verdi.pdf](../<sha-allegato-1>/main.md)` (PDF, 184 KB)

## Corpo
<testo markdown via markdownify>
```

Quoted reply **non rimossi**: spesso contengono decisioni. Body > 50KB: tronca + salva `body-full.txt`.

### 3.6 Tipi non supportati

| Tipo | Trattamento |
|---|---|
| `.txt`, `.csv`, `.md` | `plain.py` passthrough |
| `.png`, `.jpg` | skip default. Opzionale "include_images" → Claude vision (costoso) |
| `.dwg`, `.step` (CAD) | skip, log "binary excluded" |
| `.mp4`, `.mp3` | skip. Whisper = caso d'uso futuro |
| `.zip`, `.tar.gz` | skip v1 (no ricorsione su archivi) |

---

## 4. Categorizer

5 categorie (vedi brief 03):
```python
class Categoria(Enum):
    VIVO = "vivo"
    DA_CONSULTARE = "da-consultare"
    ARCHIVIO = "archivio"
    CESTINO = "cestino"
    DA_CHIARIRE = "da-chiarire"
```

**Strategia due passate**: regole prima, Claude solo sui residui. Risparmia token + deterministico.

### 4.1 Passata 1 — rules.py

Score per categoria basato su regole leggibili:
```python
def score(record: FileRecord) -> dict[Categoria, float]:
    s = {c: 0.0 for c in Categoria}
    age_days = (now() - record.mtime).days

    # Età
    if age_days < 90: s[VIVO] += 0.6
    elif age_days < 365: s[VIVO] += 0.3; s[DA_CONSULTARE] += 0.3
    elif age_days < 1095: s[DA_CONSULTARE] += 0.4; s[ARCHIVIO] += 0.3
    else: s[ARCHIVIO] += 0.6

    # Naming red-flag → CESTINO
    if any(p in record.name.lower() for p in ["copia di", "copy of", "untitled", "_old"]):
        s[CESTINO] += 0.5

    # Path
    if any(p in record.path.lower() for p in ["_archivio", "vecchio", "backup"]):
        s[ARCHIVIO] += 0.7

    return s
```

`confidence >= 0.7` → regola-decisi, non vanno a Claude.
`confidence < 0.5` → passata 2.

### 4.2 Passata 2 — claude.py

Solo sui dubbi. Batch da 20 file/prompt, modello **Haiku** (task semplice basta).

```python
prompt = """Sei un consulente che categorizza file aziendali di una PMI.
5 categorie: VIVO / DA-CONSULTARE / ARCHIVIO / CESTINO / DA-CHIARIRE
Per OGNI file, JSON: [{"sha": "abc", "cat": "VIVO", "conf": 0.8, "why": "..."}]
Files: ..."""
```

Modalità `safe`: solo metadati. Modalità `full`: + primi 500 char di main.md.

### 4.3 Audit della classificazione

`_status/audit/categorize.jsonl` (append-only):
```json
{"sha": "abc", "stage": "rules", "scores": {...}, "chosen": "VIVO", "conf": 0.8, "reason": "path=clienti/attivi"}
{"sha": "def", "stage": "claude", "model": "haiku", "tokens_in": 124, "tokens_out": 38, "chosen": "DA-CHIARIRE", "conf": 0.4}
```

---

## 5. Reconciler

Il pezzo più "magico" del prodotto.

### 5.1 Dedup per hash (dedup_hash.py)

```python
for sha, records in by_hash.items():
    if len(records) <= 1: continue
    canonical = max(records, key=lambda r: (source_priority(r.source), r.mtime))
    for r in records:
        r.dedup = {"role": "canonical" if r is canonical else "duplicate-of",
                   "canonical": canonical.id if r is not canonical else None}
```

### 5.2 Dedup per nome simile (dedup_soft.py)

Pattern regex:
```python
SOFT_DUP_PATTERNS = [
    re.compile(r"^(?P<base>.+?)[\s_]*(copia|copy)(\s*\(?(?P<n>\d+)\)?)?\.\w+$", re.I),
    re.compile(r"^(?P<base>.+?)[\s_-]*_?v(?P<n>\d+)\.\w+$", re.I),
    re.compile(r"^(?P<base>.+?)[\s_-]*_?(final|definitivo|def)\.\w+$", re.I),
    re.compile(r"^(?P<base>.+?)[\s_-]*\(\d+\)\.\w+$"),
]
```

**Non auto-applica**: produce decisione in `_status/drafts/<batch-id>/dedup-soft-<n>.md` per approvazione manuale.

### 5.3 Riconciliazione schede oggetto (schede.py)

Il pezzo ambizioso:
1. Raggruppa file per probabile oggetto (cartella, nome file, dominio email)
2. Per ogni gruppo, genera bozza scheda con i 5 file Regola 01-PMI parzialmente compilati
3. Marker TODO espliciti per Custode/Valentino
4. Chiama Claude Sonnet per sezioni "Storia" e "Decisioni estratte"

### 5.4 Estrazione persone (persone.py)

1. Per ogni .eml: estrai From/To/Cc/Reply-To
2. Parsing firme email
3. Cluster per dominio: `@rossi-srl.it` → scheda `rossi-srl`; `@bianchi.it` (interno) → `references/persone.md`
4. Bozza riga per persona con marker "estratto da dati esistenti, da validare"

**Privacy/GDPR**: punto più sensibile di tutta la pipeline. Modalità `safe`: Claude vede solo conteggi aggregati, mai liste con email.

---

## 6. Batch approval workflow

### 6.1 Esperienza Valentino

```bash
./approve.sh --batch=3
```

Browser su `http://127.0.0.1:7423/batch/3`:

```
Batch 3 — 50 bozze pronte
Filtra: [tutte] [solo schede] [solo dedup] [solo persone]
Stato:  [pending: 50] [approved: 0] [rejected: 0]

[1] scheda-rossi-srl.md      | conf 0.65 | [view diff] [approve] [reject] [park]
[2] dedup-soft-007.md        | conf 0.90 | [view diff] [approve] [reject] [park]
...

[Approve all conf > 0.85] [Apply approved → flush to vault]
```

View diff con highlighting verde/giallo/rosso (estratto / TODO / warnings). Edit inline via HTMX. Stati: pending/approved/rejected/edited/parked.

### 6.2 Flush al vault

Approved → flush in `vault/`. Rejected → `_status/audit/rejected/` (mai cancellati: audit + giustifica fatturazione).

Conflitti su file esistente: chiede overwrite/merge/skip/rename.

### 6.3 Logging decisioni

`_status/audit/decisions.jsonl`:
```json
{"ts": "2026-05-23T14:23", "batch": 3, "draft": "scheda-rossi-srl.md", "action": "approved", "user": "valentino", "edits": 2, "applied_to": "vault/clienti/rossi-srl/rossi-srl.md"}
```

Usi: audit verso cliente, migliorare categorizer, dashboard Step 3.

### 6.4 Tecnologia UI

Flask + HTMX + Pico.css + difflib stdlib. ~500 righe Python. Single-user, locale.

Alternative scartate: file markdown con checkbox (no diff visivo), Notion/Linear (vendor lock-in + dati cliente fuori), TUI (curva apprendimento).

---

## 7. Costo Claude per cliente medio

### 7.1 Ipotesi cliente

- 50 persone, 500 GB, 5000 file rilevanti
- Mix: 40% PDF (20% scansionati), 20% DOCX, 15% XLSX, 20% EML, 5% altro

### 7.2 Token per operazione

| Operazione | Modello | In/out per call | Chiamate |
|---|---|---|---|
| Categorizer (passata 2) | Haiku 4.5 | 4000/1000 (batch 20) | ~75 batch |
| OCR vision pagine difficili | Sonnet | 1500/800 | ~500 |
| Scheda oggetto | Sonnet | 3000/800 | ~80 |
| Persone | Haiku | 500/200 | ~80 |

### 7.3 Stima costi

Pricing assunto Haiku 4.5: $1 in / $5 out. Sonnet 4.5: $3 in / $15 out. **Da rivalidare con pricing attuale**.

| Operazione | Costo |
|---|---|
| Categorizer | $0.68 |
| OCR vision | $8.25 |
| Schede | $1.68 |
| Persone | $0.12 |
| **Totale** | **~$11** (~€10) |

### 7.4 Range

| Scenario | Costo |
|---|---|
| Minimo | €3-5 |
| Atteso | €10-15 |
| Peggior caso (1000 PDF scansionati anni '90) | €50-80 |

**Costo Claude non è il driver economico.** Il driver è il tempo di Valentino.

### 7.5 Early-exit e budget guard

`bootstrap/config.yml` definisce `cost_alert_eur` e `cost_hard_stop_eur`. Ogni chiamata logga in `_status/cost.jsonl`. Modulo `cost_monitor.py` letto a ogni stage. Hard stop = pipeline ferma, richiede `./resume.sh --confirm-overage`.

---

## 8. Privacy e modalità on-premise (preview Step 3)

### 8.1 Cosa Claude vede di default

| Stage | SAFE | FULL |
|---|---|---|
| Scanner | no Claude | no Claude |
| Extractor OCR | Tesseract only | + Claude vision |
| Categorizer | metadati + name + path + size + mtime | + primi 500 char |
| Reconciler schede | metadati + nomi + path | + snippet 500 char per file |
| Reconciler persone | conteggi aggregati | liste nome+email |

`safe` riduce accuratezza ~15% (`[DA VALIDARE]`), protegge contenuto.

Default raccomandato:
- Studio legale/medico/fiscale: **safe** obbligatorio
- PMI generica: **full** ok, comunicato in Atto 1
- Settore difensivo/PA: **on-premise** (Step 3)

### 8.2 Switch nel config

```yaml
privacy:
  modalita: safe
  log_dati_a_anthropic: true
  redact_pii: false
```

`redact_pii: true`: pass pre-Claude maschera email/CF/IBAN/telefono. Mappa redact ↔ valore salvata in `_status/audit/redact-map.json` (mai inviata).

### 8.3 Modalità on-premise (Step 3, preview)

Opzioni in valutazione:
- Claude on AWS Bedrock con account cliente
- Modello locale (Llama 3.1 70B via vLLM) per categorizer + persone, Claude solo per scheda finale via VPN
- Modello locale full (qualità peggiore)

Docker image: Python + Tesseract + Pandoc + modello. Pipeline identica, backend LLM diverso.

---

## 9. Tempi realistici e dimensionamento

### 9.1 Cliente medio

**Wall-clock scandagliamento** (parallelo sulle 5 fonti):

| Stage | Tempo |
|---|---|
| Scanner gdrive (12K file) | 15-30 min |
| Scanner m365 (8K file) | 20-40 min |
| Scanner email (10K msg) | 30-60 min |
| Scanner NAS (45K file con hash) | 60-120 min |
| **Scanner parallel** | **~2 h** |
| Extractor | 4-8 h |
| Categorizer | 30-60 min |
| Reconciler | 1-2 h |
| **Totale wall-clock** | **8-12 h** |

Si gira di notte sul Mac di Valentino. Venerdì sera → lunedì mattina batch pronti.

**Tempo umano Valentino**:

| Attività | Tempo |
|---|---|
| Lancio + setup config Atto 1 | ½ gg on-site |
| Babysitter scan (verifiche, rate limit) | 1-2 h sparse |
| Approvazione batch (100 batch × 50 = ~5000 bozze, 30 sec/bozza) | **~40 h** |
| Call settimanali Custode | 2 × 1 h |
| Handover Atto 3 | ½ gg on-site |
| **Totale** | **~5 giorni-uomo** + 2 on-site |

Coerente con ~€3-5k per cliente.

### 9.2 Bottleneck

1. API rate limit Anthropic (categorizer Haiku batch)
2. Hash NAS (I/O bound)
3. **Tempo Valentino** (vero collo). 30 sec/bozza ottimistico → UI fluida fondamentale

### 9.3 Parallelismo

- Scanner: parallel sulle 5 fonti
- Extractor: pool worker su sha
- Categorizer rules: file-level parallel
- Categorizer Claude: batch sequenziale (rate limit)
- Reconciler: sequenziale (visione globale)
- Approval: single-user single-thread

---

## 10. Risks e cose escluse

### 10.1 Gestionali italiani senza API

**Escluso v1.** TeamSystem, Zucchetti, Danea, Mago, Profis. Pattern Custode: esporta CSV/Excel in `_export-gestionale/` su NAS, scanner NAS li pesca.

### 10.2 Drive con > 1M file

Fuori target (PMI sta 10k-100k). Soluzione v1.5 se serve: switch a SQLite con indice sha.

### 10.3 File con contenuto sensibilissimo

Studi medici/legali/notarili:
- Default `safe` + `redact_pii: true`
- Disabilita `reconciler.persone` (rischio GDPR: estrazione = "trattamento")
- Documenta in kick-off: toolkit cliente ha visione, Anthropic vede solo metadati
- v1.5/Step 3: on-premise

### 10.4 Drive condivisi cross-azienda

PMI condividono cartelle con clienti/fornitori. Wizard chiede esplicitamente in Atto 1, default include + warning.

### 10.5 File aperti / lock

Su Windows/SharePoint, file Word aperti danno lock. Scanner ritenta 3 volte, poi `unreadable_locked`.

### 10.6 Cliente che lavora durante scan

Scan dura 8-12h, ci sono modifiche. Cursor-based resume + avviso Custode "evitate ristrutturazioni massive durante la settimana".

### 10.7 Cose non automatizzate volutamente

- Decisioni business (cliente vivo o morto) → Valentino + Custode
- Promozione L1/L2 → rituale Custode (manuale)
- Naming canonico clienti (slug) → Valentino approva

---

## 11. Roadmap implementativa

Ordine consigliato (implementatore + Claude Code, ~6-8 settimane part-time):

### Sprint 0 — Scaffolding (1 settimana)
- `pyproject.toml` con uv
- `bootstrap/INSTALL.md` + wizard CLI minimo
- Layout cartelle, `_base.py`, `_status/` gitignored
- CI base: lint + test smoke

### Sprint 1 — Scanner NAS + Extractor PDF/DOCX/EML (2 settimane)
**Path di minor frizione**: solo filesystem, no auth cloud. Test E2E su dataset sintetico.
- `scanners/nas.py` + dedup hash
- `extractors/pdf.py` (pdfplumber), `docx.py` (pandoc), `eml.py`, `plain.py`
- `categorizers/rules.py` (no Claude ancora)
- `reconcilers/dedup_hash.py` + `dedup_soft.py`

### Sprint 2 — Batch UI + Claude categorizer (1 settimana)
- `batch_ui/server.py` Flask + HTMX
- `categorizers/claude.py` con Haiku batch
- `_status/audit/decisions.jsonl`
- Pilota interno su vault di Valentino

### Sprint 3 — Scanner cloud (Drive + Reconciler schede) (2 settimane)
- `scanners/gdrive.py` con OAuth + service account
- `reconcilers/schede.py` + `persone.py` con Sonnet
- Pilota su cliente 0 (noto, basso rischio)

### Sprint 4 — M365 + Email + OCR (1-2 settimane)
- `scanners/m365.py`
- `scanners/email.py` (Gmail prima)
- `extractors/pdf_ocr.py` con Tesseract + Claude vision opzionale
- `extractors/xlsx.py`

### Sprint 5 — Hardening (1 settimana)
- Resume robusto
- Cost monitor + early exit
- Modalità safe vs full
- `bootstrap/RUNBOOK.md` per Valentino

**Cliente 1 vero**: fine Sprint 4. Cliente 2-3 in parallelo a Sprint 5.

### NON entra in Step 2 (rimandato Step 3)

- Dashboard `_status/INDEX.html` per Custode
- Modalità on-premise completa
- Re-scan incrementale schedulato post-handover
- Playbook commerciale finale + pricing pubblico
- Demo video

---

## 12. Decisioni aperte da risolvere prima di Sprint 0

1. `[DA VERIFICARE]` MCP audit — esiste MCP M365/Graph production-grade? → `_brief/05-mcp-audit.md`
2. Pricing modelli Claude maggio 2026 → numeri sezione 7 da rivalidare
3. Slug naming convention — `rossi-srl` o `rossi_srl`? Raccomandato kebab-case
4. Cliente 0 per pilota — chi è il primo cliente noto/tollerante?
5. Mac Valentino vs server dedicato — per 500 GB Mac regge. Per 2 TB serve macchina dedicata. Decisione differita

---

## 13. Riepilogo per chi implementa

5 cose da non dimenticare:

1. **Idempotenza ovunque** — ri-esecuzione safe
2. **JSONL come formato di scambio** — streamable, debuggabile, append-only
3. **`_status/` mai committato** — dati cliente, gitignored
4. **Audit di tutto** — ogni decisione in `decisions.jsonl`
5. **Claude è assistente, non oracolo** — regole prima, Claude sui dubbi, umano nel ciclo

Tempo stimato a delivery v1 (cliente pilota incluso): **8-10 settimane part-time**.
