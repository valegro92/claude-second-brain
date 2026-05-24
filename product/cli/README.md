# Custodia CLI

CLI di ingestion e build del vault Obsidian Custodia v2.

> Stato Sprint 1: pipeline `init → scan → build → review → write` completa e
> testata end-to-end (250 test verdi, incluso loop offline su finto-drive con
> `FakeLLMProvider`).

Per la panoramica end-to-end (ingestion + consumption MCP) vedi
[`../README.md`](../README.md).

## Setup

```bash
cd product/cli
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

L'entry point `custodia` viene installato nel venv. `pip install -e` rende
le modifiche al sorgente immediate.

## Quickstart

```bash
custodia init --vault /tmp/demo/vault
custodia scan fs --vault /tmp/demo/vault --root tests/fixtures/finto-drive
custodia build clients --vault /tmp/demo/vault \
    --llm-provider fake --fixture tests/fixtures/llm/extractor_responses.yaml
custodia review --vault /tmp/demo/vault --yes
custodia write  --vault /tmp/demo/vault
ls /tmp/demo/vault/clienti/   # → rossetto-laminazioni.md, bianchi-impianti.md
```

Per la guida full end-to-end (con OAuth Google Drive, provider Anthropic
reale, aggancio MCP) vedi [`../README.md`](../README.md).

## Comandi (riferimento)

Ogni comando supporta `--help` per il dettaglio delle opzioni.

| Comando | Cosa fa |
| --- | --- |
| `custodia init` | Crea lo state store SQLite per un vault (idempotente). |
| `custodia scan fs` | Scansiona ricorsivamente una cartella locale o NAS. Estrae testo da PDF/DOCX/XLSX/TXT/MD. Default: skip symlink, skip file > 50MB, skip cartelle `.git`/`node_modules`/`.venv`. |
| `custodia scan drive` | Scansiona una folder Google Drive via OAuth (richiede `CUSTODIA_GOOGLE_CREDENTIALS_JSON`). |
| `custodia build clients` | Pipeline LLM (categorize → extract) per `cliente`. |
| `custodia build fornitori` | Idem per `fornitore`. |
| `custodia build commesse` | Idem per `commessa`. |
| `custodia build communications` | Idem per `comunicazione` (email/messaggi inbox). |
| `custodia build all` | Esegue tutti i build sopra in sequenza. |
| `custodia review` | REPL human-in-the-loop sui candidati pending: `a`ccept, `e`dit, `s`kip, `m`erge, `q`uit. `--yes` per accept-all (CI/test). |
| `custodia write` | Materializza le entity approvate come `.md` nel vault Obsidian. Backup automatico dei file pre-esistenti (disattivabile con `--no-backup`). |

## Architettura moduli

```
custodia_cli/
├── main.py                # entry point typer
├── commands/              # un sub-comando per file
│   ├── init.py
│   ├── scan.py            # subcommand: fs, drive
│   ├── build.py           # subcommand: clients, fornitori, commesse, communications, all
│   ├── review.py
│   └── write.py
├── connectors/            # adattatori per sorgenti
│   ├── base.py            # interfaccia SourceConnector + SourceDocument
│   ├── filesystem.py      # scan ricorsivo + parsing PDF/DOCX/XLSX/TXT/MD
│   ├── google_drive.py    # OAuth + scan folder Drive
│   └── parsers/           # parser dedicati per estensione
├── extractor/             # pipeline LLM
│   ├── prompts.py         # template categorize + extract (italiano)
│   ├── schema.py          # carica schema canonical dal vault-demo
│   ├── chunking.py        # split documenti per budget token
│   ├── extractor.py       # orchestratore categorize → extract
│   ├── merger.py          # merge candidati multi-chunk per stessa entity
│   └── validator.py       # validazione jsonschema con error reporting
├── review/                # REPL human-in-the-loop
│   ├── interactive.py
│   ├── editor.py          # apre $EDITOR per edit interattivo
│   ├── diff.py            # diff side-by-side per merge
│   ├── merger.py          # merge candidato vs scheda esistente
│   ├── yaml_io.py         # serializzazione ordinata frontmatter
│   └── writer.py          # write .md nel vault con backup
├── state/                 # StateStore SQLite
│   ├── store.py           # API: add_document, list_documents, upsert_entity, …
│   └── schema.sql         # schema versionato (oggi v3)
├── llm/                   # provider LLM
│   ├── base.py            # interfaccia LLMProvider, ModelTier, Message
│   ├── anthropic_provider.py
│   ├── fakes.py           # FakeLLMProvider YAML-driven (offline)
│   ├── registry.py        # get_provider("anthropic"|"fake")
│   └── exceptions.py
└── auth/
    └── google_oauth.py    # OAuth desktop flow per Drive
```

## Configurazione (env vars)

| Variabile | Cosa controlla |
| --- | --- |
| `CUSTODIA_ANTHROPIC_API_KEY` | API key per il provider Anthropic. Obbligatoria se `--llm-provider=anthropic`. |
| `CUSTODIA_GOOGLE_CREDENTIALS_JSON` | Path al `credentials.json` OAuth desktop di Google. Obbligatoria per `scan drive`. |
| `CUSTODIA_LLM_PROVIDER` | Default provider quando `--llm-provider` non è passato (`anthropic` o `fake`). |
| `CUSTODIA_USD_TO_EUR` | Tasso di cambio per la stima costo nel log usage (default: 0.92). |

## Schema canonical

Le schede vault sono **YAML frontmatter + body Markdown**. Lo schema JSON
usato per validazione e tool-use è inferito a runtime dai file canonical in
`product/vault-demo/`:

| Entity type | File canonical | Path nel vault prodotto |
| --- | --- | --- |
| `cliente` | `vault-demo/clienti/rossetto-laminazioni.md` | `<vault>/clienti/<slug>.md` |
| `fornitore` | `vault-demo/fornitori/template-fornitore.md` | `<vault>/fornitori/<slug>.md` |
| `commessa` | `vault-demo/commesse/template-commessa.md` | `<vault>/commesse/<slug>.md` |
| `comunicazione` | `vault-demo/inbox/2026-05-21-bianchi-richiesta-sconto.md` | `<vault>/inbox/<slug>.md` |

Aggiungere/togliere campi a un file canonical aggiorna automaticamente:
- il prompt few-shot inviato all'LLM;
- la validazione frontmatter dei candidati;
- la review UI (chiavi mostrate in ordine canonical).

## Testing

```bash
pytest tests/ -v                                # 250 test
pytest tests/test_end_to_end.py -v              # regression E2E offline
pytest tests/ -k "not test_anthropic" -v        # salta i test che vogliono API key
```

### Aggiungere fixture per FakeLLMProvider

`tests/fixtures/llm/extractor_responses.yaml` è il file di canned responses
usato dai test E2E e dallo smoke offline. Schema:

```yaml
responses:
  - match_prefix: |-
      <system prompt completo>
      <prima riga dello user prompt, es. "Documento sorgente: `<path>`">
    operation: extract_structured
    response:
      entities: [...]   # per categorize
      # oppure:
      tipo: cliente     # per extract
      nome: ...
    tokens_in: 80
    tokens_out: 20
```

Matching: il `FakeLLMProvider` concatena `system + "\n" + last_user_content`
e ritorna la prima entry il cui `match_prefix` è prefisso della key. Per
generare le fixture conviene **ancorare i prefix ai prompt reali** importando
`custodia_cli.extractor.prompts.{categorize,extract}_system_prompt` in uno
script Python (vedi il header del file YAML per il pattern).

### Aggiungere documenti al finto-drive

`tests/fixtures/finto-drive/` è il corpus di riferimento. I binari (PDF/DOCX/
XLSX) sono generati al primo run dei test da `conftest.py` (idempotente).
Per aggiungere un nuovo documento di test:
1. Aggiungi il path al generator in `conftest.py::_ensure_finto_drive_binaries`.
2. Aggiungi le entry corrispondenti in `tests/fixtures/llm/extractor_responses.yaml`
   (categorize per ogni entity_type + extract per ogni entità).

## Layout testing

```
tests/
├── conftest.py                          # genera binari finto-drive on-demand
├── fixtures/
│   ├── finto-drive/                     # corpus E2E (PDF/DOCX/XLSX/TXT/MD)
│   └── llm/extractor_responses.yaml     # canned responses FakeLLMProvider
├── test_end_to_end.py                   # regression Sprint 1 (pipeline full)
├── test_extractor_*.py                  # unit per pipeline LLM
├── test_filesystem_connector.py
├── test_google_drive_connector.py
├── test_review_*.py
├── test_state_store.py
└── test_write_command.py
```
