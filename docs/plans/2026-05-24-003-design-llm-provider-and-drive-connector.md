# Design — LLMProvider abstraction & Google Drive connector

**Stato:** design document (no implementazione)
**Data:** 2026-05-24
**Autore:** software-architect (delega da Valentino)
**Scope:** Custodia v2 — Sprint 1 (ingestion CLI)
**Predecessori:** `docs/brainstorms/custodia-v2-agent-ready-requirements.md` (rev 2)
**Successore:** Sprint 1 plan (pianificato in parallelo, non in questo doc)

---

## TL;DR

Sprint 1 di Custodia v2 introduce il primo pezzo dell'**ingestion side**: un CLI che legge dalle sorgenti del cliente, estrae info tramite LLM, e popola schede `.md` con frontmatter YAML strutturato nel vault Obsidian.

Questo design fissa **due fondazioni** che condizioneranno tutto il resto del CLI:

1. **`LLMProvider`** — astrazione sopra il modello, con adapter Anthropic (oggi) e porta aperta per un provider OpenAI-compatible "sovrano" (domani). Interfaccia minima ma con primitiva `structured_complete` perché l'estrazione strutturata è il caso d'uso dominante.
2. **Google Drive connector** — primo connettore prioritario. OAuth desktop flow (consulente con account di accesso al Drive cliente), traversal ricorsivo limitato a una cartella root scelta dal consulente, parsing locale per PDF/DOCX/XLSX/Google-native, output streaming di `SourceDocument` consumati dagli extractor.

Entrambi sono progettati per essere **boring**: API stabili, dipendenze mainstream, error-paths espliciti. Il rischio è di sovra-ingegnerizzare prima di avere il primo cliente reale; le decisioni qui sotto sono volutamente al minimo livello di complessità che soddisfa Sprint 1-3.

---

## Componente 1 — `LLMProvider` abstraction

### Decisioni e trade-off

#### D1.1 — Protocol vs ABC: **Protocol (`typing.Protocol`)**

**Scelta:** `typing.Protocol` con `@runtime_checkable` opzionale.

**Trade-off:**
- **Pro Protocol:** structural typing → un adapter qualsiasi (anche di terze parti, anche futuro Xference SDK) è automaticamente conforme se ha i metodi giusti. Niente eredità forzata, niente import circolari su moduli di test. Allineato allo stile "funzionale > OOP" del CLAUDE.md root.
- **Contro Protocol:** nessuna ereditarietà di default → ogni adapter ridichiara le firme. Mitigato dal fatto che gli adapter sono 2-3 in totale, non 20.
- **Pro ABC:** forza la firma in compile-time, default methods condivisibili (es. `count_tokens` di default).
- **Contro ABC:** richiede `isinstance` checks rigidi, accoppia gli adapter al modulo base.

In una codebase di 2-3 adapter Protocol vince per leggerezza. Se in futuro emergono molti default methods condivisi (retry, logging, cost tracking) si può aggiungere una `BaseProvider` mixin senza rompere il Protocol.

#### D1.2 — Una o più operazioni: **tre primitive, una sola obbligatoria**

**Scelta:**
- `complete(prompt, system, options) -> CompletionResult` — obbligatoria, primitiva base
- `structured_complete(prompt, system, schema, options) -> StructuredResult[T]` — obbligatoria perché è il caso d'uso dominante in Custodia (output deve essere frontmatter YAML coerente, non testo libero)
- `count_tokens(text) -> int` — obbligatoria, ma può avere un fallback approssimato (`len(text) // 4`) per provider che non espongono tokenizer

**Cosa NON entra come primitiva di provider:**
- `extract_entity(template)`, `extract_table()`, etc. — queste sono **operazioni di dominio**, vivono nel layer `extractors/` sopra il provider. Mettere "extract entità cliente" dentro il provider lo accoppia al dominio Custodia, e rende l'adapter Anthropic non riusabile per altri progetti del team. Il provider è dumb e generico, gli extractor sono smart e specifici.

**Trade-off:**
- **Pro split:** provider resta una libreria sottile e testabile, gli extractor incapsulano la logica prompt-engineering specifica.
- **Contro split:** se in futuro un provider esponesse un'API nativa per "extract structured entity from doc" (es. Anthropic tool-use, OpenAI function calling) bisognerà scegliere se piegarla dentro `structured_complete` con `schema` o aggiungere una primitiva nuova. La firma di `structured_complete` è il punto di compromesso: accetta sia il "JSON-mode" sia il "tool-use" come implementazioni interne.

#### D1.3 — Tier di modello provider-agnostic: **enum `ModelTier` + mapping per-adapter**

**Scelta:** il caller chiede un tier semantico (`FAST`, `SMART`, `REASONING`), l'adapter mappa internamente.

```
ModelTier.FAST       → anthropic: claude-haiku-*       sovrano: qwen3-7b-instruct
ModelTier.SMART      → anthropic: claude-sonnet-*      sovrano: qwen3-32b-instruct
ModelTier.REASONING  → anthropic: claude-opus-*        sovrano: qwen3-max
```

**Trade-off:**
- **Pro tier semantici:** il codice di Custodia non contiene mai stringhe modello (`"claude-3-5-sonnet-20241022"`) → cambiare modello = aggiornare una sola tabella nell'adapter.
- **Pro tier semantici:** mappa direttamente alle decisioni di prodotto già in `custodia-v2-agent-ready-requirements.md` (Haiku per categorizzazione, Sonnet per generazione strutturata, Opus quando serve ragionamento).
- **Contro tier semantici:** perdi accesso a feature specifiche di un modello (es. context window 1M di Opus 4.7) se non sono uniformi tra provider. Mitigato con un `extra: dict[str, Any]` in `options` che passa pass-through al provider — anti-pattern accettato in cambio della portabilità.
- **Override esplicito:** `options.model_override` permette di forzare un modello specifico per caller che sanno cosa stanno facendo (es. test, benchmarking).

#### D1.4 — Configurazione: **gerarchia esplicita CLI > env > config file > default**

**Scelta:** tre livelli, in quest'ordine di precedenza:

1. **CLI flag** (`--llm-provider=anthropic --llm-tier-default=smart`) — per override puntuali
2. **Env var** (`CUSTODIA_LLM_PROVIDER`, `ANTHROPIC_API_KEY`, `SOVRANO_API_BASE`, `SOVRANO_API_KEY`) — per credenziali e ambienti
3. **Config file** (`custodia.toml` nella root del progetto cliente) — per defaults per-cliente persistenti
4. **Default hard-coded** — `provider=anthropic`, `tier=smart`

**Trade-off:**
- **Pro gerarchia esplicita:** stessa convenzione di `gh`, `docker`, `kubectl`. Predicibile. Permette dotfiles per consulente + override per-cliente.
- **Pro TOML su YAML:** TOML ha tipi nativi (numeri, bool) senza ambiguità tipo `yes/no/on/off`. Stdlib `tomllib` in Python 3.11+ → zero dipendenze.
- **Contro:** tre livelli sono più di quelli che servono in Sprint 1 (basterebbe env var). Ma definire la gerarchia adesso costa un'ora e poi è già pronta quando il consulente avrà 5 clienti diversi.
- **Cosa NON va in config file:** API keys. Solo env var o secret manager OS. Allineato a OBBLIGATORIO sicurezza in CLAUDE.md root.

#### D1.5 — Streaming vs blocking: **blocking-only in Sprint 1**

**Scelta:** solo blocking. Niente streaming.

**Trade-off:**
- **Pro blocking-only:** CLI è batch, non interattivo. L'extractor processa N documenti in pipeline, ogni doc impiega ~5-20s; non c'è UX a beneficiare di streaming token-by-token. Aggiungere streaming raddoppia la superficie API.
- **Contro:** se in futuro un comando `custodia review` interattivo mostrasse la generazione live di una scheda all'utente, servirà streaming. Aggiungerlo retroattivamente è ~mezza giornata per adapter (Anthropic ha `messages.stream`, OpenAI-compatible ha `stream=True`).
- **Decisione:** Sprint 1 NO. Riesamina in Sprint 3 quando il CLI cresce e si vede se serve.

#### D1.6 — Error handling e retry: **nel provider, esposto in modo uniforme**

**Scelta:** retry e classificazione errori vivono **dentro l'adapter del provider**, non nell'extractor. L'extractor riceve solo eccezioni di una gerarchia comune.

```
LLMProviderError (base)
├── LLMTransientError        # rate limit, 5xx, timeout → retried internally
├── LLMAuthError             # 401/403 → no retry, fail fast
├── LLMInvalidRequestError   # 400, schema invalido → no retry, surface al caller
├── LLMContextOverflowError  # input + max_tokens > context window → no retry, callable può decidere chunking
└── LLMSafetyError           # contenuto rifiutato dal modello → no retry, log e skip
```

**Retry strategy interna:** `tenacity` con exponential backoff (`min=2s, max=30s, attempts=3`) sui soli `LLMTransientError`. Documentato in CLAUDE.md root come pattern già in uso (GeminiService nel progetto WEEKO).

**Trade-off:**
- **Pro retry nel provider:** ogni extractor non riscrive `try/except + retry` per ogni chiamata. Configurazione centralizzata.
- **Contro:** se un extractor vuole retry policy diversa (es. "fail subito dopo 1 tentativo per non bruciare token"), passa `options.retry_attempts=1`.
- **Pro gerarchia eccezioni:** l'extractor decide cosa fare per ogni classe (es. `LLMContextOverflowError` → splitta input in chunk; `LLMSafetyError` → skip documento con warning).

#### D1.7 — Token counting / cost tracking: **delegato al provider, aggregato a livello CLI run**

**Scelta:**
- Ogni `CompletionResult` espone `tokens_in`, `tokens_out`, `estimated_cost_eur` (basato su una tabella prezzi statica per-adapter, aggiornabile manualmente).
- Un singleton `CostTracker` (o context manager `with track_costs() as costs:`) aggrega per CLI run e stampa il summary alla fine (`custodia scan drive → 47 file, 1.2M token, ~€0.43`).
- **NO database, NO persistenza** in Sprint 1. Solo print a fine run.

**Trade-off:**
- **Pro:** sales-relevant numbers per dire al cliente "il vault è costato 80€ di token". Sprint 1 ha già un'utilità.
- **Contro precisione:** tariffe Sovrano non sono pubbliche, useremo una stima placeholder e la flagghiamo come tale nell'output.
- **Quando spostarlo in DB:** quando il consulente fattura tre clienti contemporaneamente e serve attribuire i costi → non in Sprint 1.

---

### Interfaccia (pseudo-Python)

```python
# src/custodia/llm/types.py
from enum import Enum
from dataclasses import dataclass
from typing import Protocol, Any, TypeVar, Generic

T = TypeVar("T")  # tipo dello schema strutturato

class ModelTier(str, Enum):
    FAST = "fast"            # categorizzazione, dedup, classificazione binaria
    SMART = "smart"          # estrazione strutturata, generazione frontmatter
    REASONING = "reasoning"  # solo quando l'extractor richiede ragionamento esteso

@dataclass(frozen=True)
class CompletionOptions:
    tier: ModelTier = ModelTier.SMART
    max_tokens: int = 4096
    temperature: float = 0.0          # default deterministico per estrazione
    timeout_s: float = 60.0
    retry_attempts: int = 3
    model_override: str | None = None # bypass del tier mapping
    extra: dict[str, Any] | None = None  # pass-through provider-specific

@dataclass(frozen=True)
class CompletionResult:
    text: str
    tokens_in: int
    tokens_out: int
    estimated_cost_eur: float
    model_used: str
    finish_reason: str  # "stop" | "length" | "safety" | "tool_use"

@dataclass(frozen=True)
class StructuredResult(Generic[T]):
    data: T
    raw: CompletionResult


# src/custodia/llm/provider.py
class LLMProvider(Protocol):
    name: str  # "anthropic" | "sovrano" | "mock"

    def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        options: CompletionOptions | None = None,
    ) -> CompletionResult: ...

    def structured_complete(
        self,
        prompt: str,
        *,
        schema: type[T] | dict,   # pydantic model OR JSON schema dict
        system: str | None = None,
        options: CompletionOptions | None = None,
    ) -> StructuredResult[T]: ...

    def count_tokens(self, text: str) -> int: ...


# src/custodia/llm/errors.py
class LLMProviderError(Exception): ...
class LLMTransientError(LLMProviderError): ...
class LLMAuthError(LLMProviderError): ...
class LLMInvalidRequestError(LLMProviderError): ...
class LLMContextOverflowError(LLMProviderError): ...
class LLMSafetyError(LLMProviderError): ...


# src/custodia/llm/factory.py
def get_provider(name: str | None = None) -> LLMProvider:
    """Factory: legge config gerarchica e ritorna l'adapter giusto.
    name override forza un provider specifico (utile per test)."""
    ...
```

### Uso lato caller (extractor)

```python
# src/custodia/extractors/cliente_extractor.py
from custodia.llm import get_provider, ModelTier, CompletionOptions
from custodia.llm.errors import LLMContextOverflowError
from custodia.schemas import ClienteFrontmatter  # pydantic model

def extract_cliente_from_email_thread(thread_text: str, llm=None) -> ClienteFrontmatter:
    llm = llm or get_provider()
    system = "Sei un estrattore dati per CRM PMI italiane. Output JSON conforme allo schema."
    prompt = f"Estrai i campi del cliente da questo thread email:\n\n{thread_text}"
    try:
        result = llm.structured_complete(
            prompt,
            schema=ClienteFrontmatter,
            system=system,
            options=CompletionOptions(tier=ModelTier.SMART, temperature=0.0),
        )
        return result.data
    except LLMContextOverflowError:
        # delega al chunker
        return extract_from_chunks(thread_text, llm)
```

**Test con mock:**

```python
# tests/extractors/test_cliente_extractor.py
from custodia.llm.mock import MockProvider

def test_extract_cliente_happy_path():
    mock = MockProvider(canned_responses={
        "structured_complete": ClienteFrontmatter(nome="Rossetto Laminazioni SRL", ...)
    })
    result = extract_cliente_from_email_thread("...", llm=mock)
    assert result.nome == "Rossetto Laminazioni SRL"
    assert mock.call_count("structured_complete") == 1
```

---

## Componente 2 — Google Drive connector

### Decisioni e trade-off

#### D2.1 — Auth: **OAuth desktop flow (Installed App)**

**Scelta:** OAuth 2.0 "Installed Application" flow. Il consulente esegue `custodia auth drive` la prima volta, si apre il browser, login Google con l'account che ha accesso al Drive del cliente, callback locale su `http://localhost:<random_port>`, token salvato in `~/.custodia/credentials/drive-<cliente>.json`.

**Scenario reale assunto:** il consulente, all'Atto 1, riceve dal cliente un account Google creato ad hoc (es. `consulente.custodia@cliente.com`) con permessi di lettura sul sottoalbero rilevante. Loggarsi con questo account è onesto e tracciabile lato cliente (audit log Workspace mostra chi ha letto cosa).

**Trade-off vs Service Account:**
- **Pro Service Account:** non scade, ideale per scheduling. Nessun browser flow.
- **Contro Service Account:** richiede che il Workspace admin del cliente crei un service account e gli condivida cartelle. Friction enorme: l'admin del cliente PMI è spesso un esterno (consulente IT) o il titolare stesso, che dirà "spiegamelo bene". Service Account + domain-wide delegation è ancora peggio (richiede approvazione admin a livello dominio).
- **Verdetto:** OAuth desktop flow è l'unica opzione realistica per il setup "Atto 1 in azienda davanti al cliente". Service Account si valuta se in futuro Custodia diventa SaaS managed.

**Trade-off vs API Key:**
- API Key non è supportata da Drive API per accesso a contenuti utente. Off the table.

**Conseguenze operative:**
- Token OAuth scade (refresh token in genere lungo, ma può essere revocato). Il CLI deve gestire `RefreshError` e mostrare un messaggio chiaro: "credenziali Drive scadute, esegui `custodia auth drive --reauth`".
- Per il primo cliente, il consulente userà credenziali OAuth proprie (per dogfood interno sul Drive di Valentino) — stessa code path, account diverso.

#### D2.2 — Scope: **lettura limitata a una cartella root indicata**

**Scelta:** scope OAuth = `https://www.googleapis.com/auth/drive.readonly` (read-only su tutto il Drive a cui l'account ha accesso) + il consulente specifica esplicitamente un **folder ID root** quando inizializza la sorgente.

```
custodia source add drive --name="commerciale-2020-2025" \
   --folder-id="1AbCdEf..." \
   --client="rossetto"
```

**Trade-off:**
- **Scope `drive.file` (più ristretto, accesso solo a file aperti tramite app):** sembrerebbe la scelta più "least privilege", ma non funziona per il caso d'uso. `drive.file` richiede che l'utente apra ogni singolo file con il picker, non c'è traversal di cartella. Inutilizzabile.
- **Scope `drive.readonly` (l'intero Drive in read-only):** dà accesso teorico a tutto, ma il CLI legge SOLO il sottoalbero della folder-id indicata. La promessa di scope minimo è enforced lato applicazione, non lato API. **Accettabile** perché l'account è già dedicato al progetto consulenziale e ha solo le cartelle condivise dal cliente.
- **Scope `drive.metadata.readonly`:** servirebbe per fare dry-run senza scaricare contenuti. Lo richiediamo come scope aggiuntivo per il comando `custodia scan drive --dry-run` che mostra "cosa verrebbe processato" senza scaricare nulla.

**Cosa NON facciamo:**
- Niente accesso al `My Drive` completo. Niente accesso ai Shared Drives interi del cliente. Solo il folder-id esplicito + ricorsivo da lì in giù.
- Refuse esplicito: se il consulente passa l'ID di un Shared Drive (top-level), il CLI mostra un warning "stai per indicizzare uno Shared Drive completo, conferma?" → richiede `--yes-i-know`.

#### D2.3 — Traversal: **ricorsivo completo + dry-run obbligatorio prima del primo run**

**Scelta:**
- `custodia scan drive --dry-run` (default al primo run) lista i file che verrebbero processati con counts per tipo e size, **senza scaricare nulla** (solo metadata API call).
- `custodia scan drive` (run vero) richiede conferma esplicita se >500 file o >1GB totale.
- Limiti hard configurabili (`--max-files=10000`, `--max-size-mb=5000`) con default sani.

**Trade-off:**
- **Pro ricorsivo full-depth:** semplice, completo, niente sorprese di "ah quel sottofolder non l'avevo visto".
- **Pro dry-run obbligatorio:** evita il caso "ho lanciato sul Drive sbagliato, ho bruciato 50€ di Claude". Allineato al pattern "CLI a stadi con review umana" del brainstorm.
- **Contro stage-by-stage con conferma per ogni sottofolder:** troppo verboso, il consulente vuole "vai" non "conferma 30 volte".

#### D2.4 — Parsing per tipo file: **librerie locali, no LLM-OCR in Sprint 1**

| Tipo MIME | Parser scelto | Motivo |
|---|---|---|
| `application/pdf` | **pypdf** | Stdlib-quality, no dipendenze native (vs pdfplumber che pulls in tantissimo). Per PDF non-OCR funziona bene. PDF scansionati senza testo → skip con warning in Sprint 1. |
| `application/vnd.openxmlformats-officedocument.wordprocessingml.document` (DOCX) | **python-docx** | Standard de facto. Output: testo concatenato + tabelle linearizzate. |
| `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` (XLSX) | **openpyxl** | Stdlib-quality. Output: ogni sheet → CSV-like text (header + righe), separatore tab. LLM legge molto meglio una tabella TSV che JSON. |
| `application/vnd.google-apps.document` (Google Docs nativo) | **export DOCX via Drive API** poi python-docx | Drive API supporta export nativo, niente parsing diretto del formato Google. |
| `application/vnd.google-apps.spreadsheet` (Google Sheets nativo) | **export XLSX via Drive API** poi openpyxl | Stessa logica. |
| `text/plain`, `text/markdown`, `text/csv` | lettura diretta | Trivial. |
| `image/*` | **skip in Sprint 1** | OCR (Tesseract o Gemini Vision) rimandato a v0.1.1 quando un cliente reale ce l'avrà come blocker. |
| Tutto il resto | skip con warning | Logger registra il file ignorato. |

**Trade-off su LLM-OCR vs parser locali:**
- **Pro LLM-OCR (Claude Vision o Gemini Vision):** legge anche PDF scansionati, ricevute fotografate, manoscritti. Qualità superiore su layout complessi (tabelle annidate).
- **Contro LLM-OCR:** costo per documento ~10-50x rispetto a parser locale. Per un Drive con 5K file, esplodono i costi. E i provider Sovrano potrebbero non supportare vision affidabilmente.
- **Decisione:** parser locali in Sprint 1. LLM-OCR è una feature opt-in (`--ocr-fallback`) in v0.1.1 quando un cliente reale lo richiede.

#### D2.5 — Incremental scan: **hash MD5 da Drive metadata + state file locale**

**Scelta:**
- Drive API espone `md5Checksum` per file binari (non per Google-native, vedi sotto).
- State file: `~/.custodia/state/<cliente>/drive-scan.json` con `{file_id: {md5, modified_time, processed_at, extractor_version}}`.
- A ogni rerun: per ogni file, se `md5` invariato AND `extractor_version` invariato → skip. Altrimenti → riprocessa.

**Caso speciale Google-native (Docs/Sheets):** `md5Checksum` è null. Si usa `modifiedTime` come fallback.

**Caso speciale "extractor migliorato":** quando l'extractor cambia (es. abbiamo migliorato il prompt per estrarre clienti), serve invalidare la cache. Soluzione: ogni extractor ha una `version: int`, incrementata manualmente quando cambia in modo significativo. Lo state file tiene la versione usata per ogni file → mismatch = riprocessa.

**Trade-off:**
- **Pro MD5:** robusto, non sensibile a tocchi di file accidentali (toccare un file su Drive che non è cambiato → MD5 stesso).
- **Contro state file locale:** se il consulente cambia macchina, perde lo stato e rifa tutto. Mitigato dal fatto che il vault `.md` finale è già il "vero" stato persistente; lo state-file è solo cache.
- **Quando spostarlo in DB:** mai per Sprint 1-3. Forse v0.1.1 se il consulente lavora su 10+ clienti.

#### D2.6 — Rate limits e file grandi

**Drive API rate limits:** Google espone ~1000 query/100s/user di default, alzabile a richiesta. In pratica con traversal sequenziale non si arriva mai. Mitigazione:
- Backoff esponenziale su `429`/`403 quotaExceeded` (libreria `tenacity`, già citata sopra).
- **No parallelizzazione aggressiva** in Sprint 1: traversal sequenziale, max 5 file in parallelo per download. Semplice e sufficiente.

**File grandi:**
- Drive supporta download fino a 5TB. Custodia mette un limite a `--max-file-size-mb=50` di default (skip + warning oltre).
- File >10MB vengono streamati su disco temporaneo (`tempfile.NamedTemporaryFile`) prima di parsing, non tenuti in RAM.
- PDF >100 pagine: parser locali gestiscono bene, ma l'LLM downstream esploderà sul context. Soluzione: il connettore Drive ritorna il testo intero; è responsabilità del prossimo layer (chunker, prima dell'LLM) splittare. Separation of concerns mantenuta.

---

### Interfaccia (pseudo-Python)

```python
# src/custodia/connectors/types.py
from dataclasses import dataclass, field
from typing import Iterator, Protocol
from datetime import datetime

@dataclass(frozen=True)
class SourceDocument:
    """Documento estratto da una sorgente, pronto per gli extractor."""
    source_id: str                    # "drive:1AbCdEf..." stable across reruns
    source_type: str                  # "drive" | "outlook" | "filesystem" | ...
    path: str                         # "Commerciale 2020-2025/Offerte/Rossetto/2024-q3.pdf"
    mime_type: str                    # "application/pdf"
    text: str                         # contenuto testuale parsato
    metadata: dict[str, Any] = field(default_factory=dict)
    # metadata canonici comuni a tutte le sorgenti:
    #   "modified_time": datetime
    #   "created_time": datetime
    #   "size_bytes": int
    #   "checksum": str | None
    # + metadata source-specific (es. drive: owner, last_modifying_user, web_view_link)

class SourceConnector(Protocol):
    """Interfaccia comune a tutti i connettori (Drive, Outlook, FS, ...)."""
    source_type: str
    name: str  # nome dato dal consulente: "commerciale-2020-2025"

    def authenticate(self) -> None:
        """Setup credenziali (idempotente, no-op se già autenticato)."""
        ...

    def scan(self, *, dry_run: bool = False) -> Iterator[SourceDocument]:
        """Stream di documenti. Se dry_run=True, yield doc con text=''."""
        ...

    def stats(self) -> dict[str, Any]:
        """Counts per tipo, size totale, file skippati, errori. Sicuro chiamare durante/dopo scan."""
        ...


# src/custodia/connectors/drive.py
@dataclass(frozen=True)
class DriveSourceConfig:
    name: str                          # "commerciale-2020-2025"
    folder_id: str                     # root del traversal
    client_id: str                     # "rossetto"
    max_files: int = 10_000
    max_file_size_mb: int = 50
    skip_mime_prefixes: tuple[str, ...] = ("image/", "video/", "audio/")
    extractor_version: int = 1

class DriveConnector:
    """Implementa SourceConnector."""
    source_type = "drive"

    def __init__(self, config: DriveSourceConfig, *, credentials_path: Path | None = None): ...
    def authenticate(self) -> None: ...  # OAuth desktop flow, refresh handling
    def scan(self, *, dry_run: bool = False) -> Iterator[SourceDocument]: ...
    def stats(self) -> dict[str, Any]: ...
```

### Flusso end-to-end

Dal punto di vista del consulente in azienda:

```
# 1. Setup (una tantum per cliente)
$ custodia init --client=rossetto
  → crea ./vault-rossetto/, ~/.custodia/clients/rossetto/

$ custodia auth drive --client=rossetto
  → apre browser, login con consulente.custodia@rossetto.com
  → salva token in ~/.custodia/credentials/drive-rossetto.json

$ custodia source add drive \
    --client=rossetto \
    --name=commerciale-2020-2025 \
    --folder-id=1AbCdEf...
  → scrive ~/.custodia/clients/rossetto/sources.toml

# 2. Dry-run (sempre prima)
$ custodia scan drive --client=rossetto --source=commerciale-2020-2025 --dry-run
  → 847 file trovati: 412 PDF, 203 DOCX, 156 XLSX, 76 GDoc/GSheet
  → ~2.1 GB totali, ~80 file >50MB (verranno skippati)
  → stima costo LLM: ~€28 (Claude Sonnet a tier SMART)
  → procedi? (richiede --confirm)

# 3. Scan vero (popola staging area, NON il vault ancora)
$ custodia scan drive --client=rossetto --source=commerciale-2020-2025 --confirm
  → 847 file → stream di SourceDocument
  → ogni doc viene salvato in ~/.custodia/clients/rossetto/staging/drive/<file_id>.json
  → state file aggiornato file-by-file (resumable se crashato)
  → output: 832 processati, 15 skippati (8 too-big, 7 unsupported mime)

# 4. Build (il prossimo agente fa questo step — non in scope qui)
$ custodia build clienti --client=rossetto
  → legge staging area, chiama LLMProvider.structured_complete per ogni doc/gruppo
  → produce ./vault-rossetto/clienti/*.md con frontmatter YAML
  → review umana via custodia review
```

**Flusso dato (data flow):**

```
Google Drive API
    │
    │ (OAuth credentials, drive.readonly scope)
    ▼
DriveConnector.scan()
    │
    │ — lista ricorsiva file dal folder_id
    │ — per ogni file: filtra (size, mime, skip-list)
    │ — incremental: check vs state file → skip se invariato
    │ — download → parser locale (pypdf/python-docx/openpyxl)
    │ — yield SourceDocument
    ▼
Iterator[SourceDocument]
    │
    ▼
Staging area locale (~/.custodia/clients/<c>/staging/drive/)
    │
    │ (separato dallo scan, chiamato da `custodia build`)
    ▼
Extractors (cliente, fornitore, commessa, ...)
    │
    │ — usano LLMProvider.structured_complete
    │ — output: pydantic model validato vs schema frontmatter
    ▼
Vault Obsidian (./vault-<cliente>/clienti/*.md, ecc.)
    │
    ▼
Review umana del consulente (`custodia review`)
    │
    ▼
Vault finale consegnato al cliente
```

**Punti di contatto LLMProvider × Drive connector:**

Il Drive connector **NON usa l'LLMProvider direttamente** in Sprint 1. È un componente puro I/O+parsing. L'LLM entra al layer successivo (extractors). Questa separazione:
- Permette di testare il connettore senza chiavi API LLM
- Permette di riusare il connettore per export "raw" del Drive (utility non-AI per il consulente)
- Mantiene il connettore generico e riusabile

L'unica eccezione futura sarà OCR LLM-based (D2.4), ma è opt-in e rimandato.

---

## Open questions per Sprint 1

Queste vanno chiuse prima dell'implementazione, non in questo design doc:

### LLMProvider
1. **Schema validation library:** pydantic v2 ovunque, oppure permettiamo anche raw JSON schema dict? → Pydantic-first, ma `structured_complete` accetta entrambi. Da decidere se il fallback JSON schema vale la complessità.
2. **Anthropic SDK version pinning:** quale versione minima? Anthropic ha cambiato API più volte. → Verificare ultima stabile e fissare in `pyproject.toml`.
3. **Tabella prezzi modello → cost tracking:** la manteniamo hard-coded in codice o in `models-pricing.toml`? Quanto spesso cambia? → Probabile hard-coded ok per ora.
4. **Mock provider canned responses:** formato? File YAML per fixture, oppure costruzione programmatica nei test? → Pattern WEEKO usa programmatic, preferenza per coerenza.
5. **Quale modello Sovrano usare per stub adapter:** anche se non costruiamo l'adapter Sovrano in Sprint 1, vale la pena scrivere uno stub con interfaccia OpenAI-compatible (`openai` SDK punta a un base_url custom) per validare che l'astrazione regge? Costo: ~mezza giornata. **Raccomandato sì.**

### Drive connector
6. **OAuth client_id distribution:** il consulente deve registrare la sua app su Google Cloud Console, oppure Custodia ne ha una "ufficiale" condivisa? → Una condivisa è UX migliore ma centralizza il rischio. Per Sprint 1 probabilmente OK l'una; per più consulenti serve formalizzare.
7. **Shared Drives support:** il primo cliente potrebbe avere file in Shared Drive invece che in My Drive. La Drive API richiede `supportsAllDrives=True` esplicito. Da verificare con cliente Sprint 4 reale. Costo aggiunto: piccolo, da mettere ora come default.
8. **PDF scannerizzati:** quanti sono realisticamente nel Drive di una PMI? Se >5%, OCR-skip lascia buchi importanti nel vault. → Validare empiricamente sul Drive di Valentino in dogfood.
9. **Versioning file Drive:** Drive tiene tutte le revisioni. Indicizziamo solo l'ultima versione (Sprint 1) o anche storico? → Sprint 1 solo ultima. Discusso in retrospettiva.
10. **Permessi missing:** se il consulente non ha accesso a un file dentro la cartella root (raro ma possibile con Drive shares granulari), API ritorna 403. Skip silenzioso con log, oppure fail fast? → **Skip + warning aggregato a fine run.**
11. **Naming files con caratteri speciali:** path Drive può contenere `/`, `:`, emoji, ecc. Sanitizzare per uso come parte di `SourceDocument.source_id`? → Sì, ma mantenere `path` originale per riferimento umano nel vault.

### Cross-cutting
12. **Logging convention:** il CLAUDE.md root suggerisce emoji (📸 🔍 ✅ ❌). Applichiamo anche qui? → Sì per UX CLI, coerente con tono "consulenziale" di Custodia.
13. **Test fixtures Drive:** mockare Drive API a livello HTTP (vcr.py / responses) o a livello SDK (mock dell'oggetto `googleapiclient.discovery`)? → Da decidere col qa-engineer.
14. **Where does staging live nel filesystem:** `~/.custodia/clients/<c>/staging/` o dentro la cartella del progetto consulenza? Trade-off privacy/portabilità.

---

## Riferimenti

- Brainstorm v2 rev 2: `docs/brainstorms/custodia-v2-agent-ready-requirements.md`
- MVP consumption-side: `product/mcp-server/custodia_mcp.py`, `product/vault-demo/`
- Schema target frontmatter: `product/vault-demo/clienti/rossetto-laminazioni.md`
- Convenzioni codice: `CLAUDE.md` (root + globale)
- Plan parallelo (in corso): Sprint 1 plan da altro agente

---

**Nota su scope:** questo doc copre design architetturale e contratti. NON include: pianificazione lavoro/stime, scelta esatta versioni librerie, codice eseguibile, test plan dettagliato. Quelli sono job di Sprint 1 plan e qa-engineer in fase successiva.
