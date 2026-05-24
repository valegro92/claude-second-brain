# Custodia Web — GUI Streamlit del CLI

Webapp single-user, locale, che sostituisce l'uso da terminale del CLI
`custodia`. Permette al consulente di gestire più progetti cliente (un vault
per cliente), eseguire scan/build/review/write con interfaccia grafica, e
generare lo snippet di config MCP da incollare in Claude Code.

## Quickstart

```bash
cd product/web

# 1. venv dedicato
python3 -m venv .venv
source .venv/bin/activate

# 2. installa il CLI (path-local) + la webapp
pip install -e ../cli
pip install -e .

# 3. lancia
./run.sh
```

La webapp si apre su `http://localhost:8501`.

## Workflow del consulente

1. **Sidebar → Nuovo progetto**: indica nome cliente + path vault. La cartella
   viene creata se non esiste.
2. **Scan**: scegli il connettore (Filesystem / Drive / Outlook / FIC), lancia
   la scansione. La prima volta su un vault, lo state store SQLite viene
   inizializzato automaticamente.
3. **Build**: estrai entità (`cliente`/`fornitore`/`commessa`/`comunicazione`)
   dai documenti con LLM. Usa `anthropic` se hai la key, `fake` + fixture per
   test offline.
4. **Review**: tabella delle pending + form di editing del frontmatter, con
   diff visivo vs eventuale scheda già nel vault. Buttons espliciti
   `Accetta`/`Salva edit`/`Skip`/`Merge col vault`.
5. **Vault**: browser dei file `.md` prodotti, search full-text, bottone
   "Write pending" per materializzare gli approved.
6. **Settings**: stato env vars, snippet MCP pronto-da-copiare per Claude Code.

## Pagine

| Pagina | Cosa fa |
|---|---|
| Dashboard | Metriche aggregate del progetto attivo + ultimi run |
| Scan | Tab per ogni connettore + progress live |
| Build | Estrazione entità con scelta provider LLM |
| Review | Validazione human-in-the-loop con diff e form |
| Vault | Tree dei `.md` + viewer + search + write |
| Settings | Env vars, MCP snippet, versioni |

## Note importanti

- **Single-user**: niente auth, gira solo in locale. NON esponi mai
  Streamlit su una porta pubblica.
- **Connettori cloud (Drive/Outlook/FIC)**: la webapp riusa il token cache
  generato dal CLI in `<vault_parent>/.custodia-state/{google,microsoft,fic}_token.json`.
  Il primo login OAuth deve passare per il CLI (o per Streamlit se hai
  configurato un browser-redirect su `localhost`).
- **L'agente non vive qui**: la webapp produce solo il vault. L'agente lavora
  in Claude Code (o qualsiasi MCP client) leggendo il vault via il server
  `custodia_mcp`.

## Workspace metadata

L'elenco dei progetti registrati vive in `~/.custodia/projects.json`. Non
modificarlo a mano se la webapp è aperta (race condition possibile sul
salvataggio). Cancellare un progetto dalla UI rimuove solo i metadati: il
vault sul disco non viene toccato.

## Screenshot (descrizioni indicative)

> Gli screenshot reali andranno aggiunti in `docs/web/screenshots/`. Cosa
> ci dovrà andare:

- `01-dashboard.png`: pagina Dashboard con 4 `st.metric` in alto, lista runs
  a destra, lista entity per tipo a sinistra. Sidebar con progetto attivo
  evidenziato dal colore.
- `02-scan-filesystem.png`: form con root path, exclude, max size; `st.status`
  espanso con messaggio live "doc indicizzati: 47 nuovi · 0 duplicati".
- `03-review-diff.png`: tab "Diff vs vault" aperto, tabella HTML con righe
  colorate (verde = NEW, giallo = CHANGED, rosso = ONLY-VAULT).
- `04-vault-viewer.png`: selectbox per scegliere file, JSON espanso del
  frontmatter, body markdown renderizzato sotto.
- `05-settings-mcp.png`: blocco code JSON con `mcpServers.custodia` pronto da
  copiare.

## Test

```bash
cd product/web
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

I test toccano solo il service layer (proxy verso il CLI). L'UI Streamlit
non è coperta da unit test (troppo costoso); il smoke test funzionale verifica
che `streamlit run app.py` parta senza crash.

## Out of scope

- Embedded agent chat
- Auth, multi-user, deploy cloud
- Editing del body markdown (il body si edita in Obsidian)
- OAuth flow in-browser (per Drive/Outlook/FIC serve almeno un primo login dal CLI)
