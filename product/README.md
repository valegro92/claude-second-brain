# Custodia v2 — Quickstart end-to-end

Spina dorsale tecnica per consulenti che vogliono dare ai loro clienti
un **agente che conosce davvero l'azienda**. Sprint 1 — pronto da provare in
locale, offline, con un finto-drive incluso.

## Cos'è Custodia v2

Un sistema in due tempi:

1. **Il consulente** scansiona le sorgenti del cliente (Drive, NAS, cartelle locali),
   estrae schede strutturate `cliente / fornitore / commessa / comunicazione`
   e le materializza come file Markdown in un vault Obsidian. Il consulente
   valida ogni scheda in review prima del commit.
2. **L'agente del cliente** (Claude Code, oppure altro client MCP) legge il vault
   via MCP server e risponde a domande operative tenendo conto di condizioni
   commerciali, eccezioni storiche e segnali di relazione.

Obiettivo: portare un agente da "generico" a "uno che conosce davvero il cliente
Rossi" in meno di 10 minuti, partendo da un mucchio di documenti.

## I due lati del prodotto

```
                       Custodia v2
              ┌───────────────────────────┐
              │                           │
   INGESTION  │   Drive / NAS / FS        │   CONSUMPTION
              │           │               │
              │           ▼               │
              │      custodia CLI         │           Claude Code
              │  (scan → build → review   │              │
              │    → write)               │              ▼
              │           │               │       (richieste tipo
              │           ▼               │       "rispondi alla
              │     vault Obsidian        │        mail di Bianchi"
              │   clienti/                │              │
              │   fornitori/  ◄───────────┼──── MCP ─────┘
              │   commesse/   ───────────►│  server stdio
              │   inbox/                  │  (custodia_mcp.py)
              │                           │
              └───────────────────────────┘
        (lato consulente, locale)   (lato cliente, locale o remoto)
```

Il vault è il **contratto** fra i due lati. Tutto ciò che il consulente scrive
nel vault diventa contesto strutturato per l'agente.

## Setup (una volta sola)

Custodia ha due venv separati: uno per il CLI di ingestion, uno per il server MCP.

```bash
# CLI (ingestion)
cd product/cli
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# MCP server (consumption)
cd ../mcp-server
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Quickstart end-to-end

Esempio integrale sul corpus `tests/fixtures/finto-drive/` (3 documenti
commerciali + 1 email). **Tutto funziona offline** grazie al `FakeLLMProvider`.

```bash
cd product/cli && source .venv/bin/activate

# 1. Inizializza lo state store
custodia init --vault /tmp/demo/vault

# 2. Scansiona la sorgente (qui un finto drive; in produzione: cartella NAS
#    del cliente, oppure `custodia scan drive` con OAuth Google)
custodia scan fs --vault /tmp/demo/vault --root tests/fixtures/finto-drive

# 3. Estrai entità con LLM
#    - offline (test/demo):  fake provider + fixture canned
#    - online (produzione):  --llm-provider anthropic (richiede CUSTODIA_ANTHROPIC_API_KEY)
custodia build clients        --vault /tmp/demo/vault \
    --llm-provider fake --fixture tests/fixtures/llm/extractor_responses.yaml
custodia build fornitori      --vault /tmp/demo/vault \
    --llm-provider fake --fixture tests/fixtures/llm/extractor_responses.yaml
custodia build communications --vault /tmp/demo/vault \
    --llm-provider fake --fixture tests/fixtures/llm/extractor_responses.yaml

# 4. Review consulente (interattivo, oppure --yes per accettare tutto in batch)
custodia review --vault /tmp/demo/vault --yes

# 5. Materializza il vault Obsidian
custodia write --vault /tmp/demo/vault

# 6. Verifica il vault prodotto
ls /tmp/demo/vault/clienti/
# bianchi-impianti.md   rossetto-laminazioni.md
ls /tmp/demo/vault/fornitori/
# torrelli-meccanica.md
ls /tmp/demo/vault/inbox/
# conferma-ordine-pompe-idrauliche.md
```

In produzione, sostituisci `--llm-provider fake --fixture …` con
`--llm-provider anthropic` e imposta `CUSTODIA_ANTHROPIC_API_KEY` nell'env.

## Aggancio agente (Claude Code)

Aggiungi a `~/.claude/mcp.json` (oppure config progetto):

```json
{
  "mcpServers": {
    "custodia": {
      "command": "/PATH/ASSOLUTO/product/mcp-server/.venv/bin/python",
      "args": ["/PATH/ASSOLUTO/product/mcp-server/custodia_mcp.py"],
      "env": {
        "CUSTODIA_VAULT": "/tmp/demo/vault"
      }
    }
  }
}
```

Riavvia Claude Code. Diventano disponibili i tool:
- `list_clients` — elenco clienti del vault
- `get_client(id)` — scheda completa di un cliente
- `recent_communications(n)` — ultime N email/comunicazioni
- `search_vault(query)` — full-text search nel vault

## Comandi disponibili

| Comando | Descrizione |
| --- | --- |
| `custodia init --vault PATH` | Crea lo state store SQLite (idempotente). |
| `custodia scan fs --vault PATH --root PATH` | Scansiona ricorsivamente una cartella locale o NAS mount. |
| `custodia scan drive --vault PATH --folder-id ID` | Scansiona una folder Google Drive (richiede OAuth). |
| `custodia build clients --vault PATH` | Estrae candidati `cliente` dai documenti pending. |
| `custodia build fornitori --vault PATH` | Idem per fornitori. |
| `custodia build commesse --vault PATH` | Idem per commesse. |
| `custodia build communications --vault PATH` | Estrae email/comunicazioni inbox. |
| `custodia build all --vault PATH` | Esegue in sequenza tutti i build sopra. |
| `custodia review --vault PATH [--yes]` | REPL human-in-the-loop sui candidati. `--yes` accetta tutto. |
| `custodia write --vault PATH` | Scrive le entity approvate come `.md` nel vault. |

Tutti i `build *` accettano `--llm-provider {anthropic|fake}` e (per `fake`)
`--fixture <yaml>`.

## Cosa NON c'è ancora

- **Connettori Outlook e Fatture in Cloud** — Sprint 2.
- **Sovrana on-demand** (estrazione contestuale all'arrivo di una mail) — Sprint 2.
- **Trasporto HTTP per MCP** (oggi solo stdio, agente locale) — Sprint 2.
- **Autenticazione MCP** — quando serve multi-tenant.
- **Training ML reale** sui candidati per pre-validazione — Sprint 1.5.

## Layout repository

```
product/
├── README.md              # questo file
├── cli/                   # CLI di ingestion (questo lato del prodotto)
│   ├── README.md          # quickstart tecnico CLI + contributing
│   ├── custodia_cli/
│   │   ├── commands/      # init, scan, build, review, write
│   │   ├── connectors/    # filesystem, google_drive, parsers
│   │   ├── extractor/     # pipeline LLM categorize → extract
│   │   ├── review/        # REPL human-in-the-loop + writer
│   │   ├── state/         # StateStore SQLite
│   │   ├── llm/           # provider Anthropic + Fake (offline)
│   │   └── auth/          # OAuth Google
│   └── tests/             # 250 test verdi (incl. E2E offline)
├── mcp-server/            # server MCP stdio
│   ├── custodia_mcp.py    # tool list_clients, get_client, search_vault, …
│   └── pyproject.toml
└── vault-demo/            # vault Obsidian di esempio (canonical examples)
    ├── clienti/           # Rossetto, Bianchi, Torrelli
    ├── fornitori/         # template
    ├── commesse/          # template
    └── inbox/             # email di esempio
```
