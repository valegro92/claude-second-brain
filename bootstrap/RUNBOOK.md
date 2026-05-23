# wiki-toolkit — Runbook operativo

Per Valentino in delivery, o per qualunque consulente che porta il toolkit a
un cliente. Tre atti, niente filosofia, solo i comandi.

Prerequisiti: hai seguito `bootstrap/INSTALL.md`. `wiki --version` risponde.
Sei nel virtualenv (`source .venv/bin/activate`).

---

## Atto 1 — Kick-off (5 minuti, on-site)

Sei a casa del cliente, hai chiuso la chiamata di scoping, hai il consenso del
Custode e dell'Owner. Apri il terminale:

```bash
wiki init
```

Rispondi alle 6 domande. Convenzioni rapide:
- **slug**: kebab-case, breve, persistente — sarà il nome di tutte le cartelle
  cliente per sempre (es. `officina-bianchi`)
- **iniziali**: 2 caratteri, sempre maiuscole (es. `GB` per Giulia Bianchi)
- **sorgenti**: separate da virgola, niente spazi (es. `nas,gdrive,email`).
  Scrivi `all` per tutte
- **privacy**: `safe` di default. Se è uno studio legale/medico, conferma con
  il cliente prima di scegliere `full`

Output atteso:
```
Config scritto: bootstrap/clients/officina-bianchi/config.yml
Check ambiente:
  [ok] Python 3.11.x
  [ok] dep 'click' disponibile
  ...
Pronto. Prossimi passi:
  wiki scan --client officina-bianchi
```

A questo punto modifica il config a mano per inserire path NAS reali, mount
M365, ecc. Tutto è documentato con commenti dentro il file.

---

## Atto 2 — Scandagliamento (notte, remoto)

Due modalità: **streaming** (drop file → bozza pronta immediatamente, ideale
per piccoli volumi o per dimostrare al cliente) e **batch** (scan delle
sorgenti in serata, approvazione di mattina).

### Modalità batch (90% dei casi)

```bash
wiki scan       --client officina-bianchi
wiki extract    --client officina-bianchi
wiki categorize --client officina-bianchi
wiki reconcile  --client officina-bianchi
wiki approve    --client officina-bianchi
```

Tempo wall-clock per cliente medio (vedi `_brief/04-step-2-tech-plan.md` §9):
- scan: 1-2 h
- extract: 4-8 h
- categorize + reconcile: 1-2 h
- approve (umano, 30s/bozza × 100 batch da 50): ~40 h sparse sulla settimana

Lancia tutto la sera, torna il giorno dopo, comincia a approvare.

### Modalità streaming (watcher)

```bash
wiki watch --client officina-bianchi
```

Il watcher osserva `_inbox/officina-bianchi/`. Trascina lì qualsiasi file e
parte il pipeline completo per quello solo. Output: bozze in
`_status/officina-bianchi/drafts/<oggi>/`.

Tieni il terminale aperto. Ctrl-C per fermarlo (graceful, scrive `watcher.pid`
fino allo shutdown).

### Check progresso

```bash
wiki status --client officina-bianchi
```

Riporta: file per sorgente, estratti, categorizzati, bozze pending/approved/
rejected, costo Claude cumulativo.

---

## Atto 3 — Handover (½ giornata, on-site)

1. **Setup Custode**: copia il repo sul Mac/PC del Custode, segui `INSTALL.md`
2. **Trasferisci il config**: copia `bootstrap/clients/<slug>/config.yml`
   (NON committarlo in git: contiene credenziali). Comunica la chiave Anthropic
   separatamente
3. **Trasferisci `_status/<slug>/`**: contiene inventory, audit, decisioni.
   Serve al Custode per i rituali settimanali
4. **NON trasferire `_inbox/`**: drop zone temporanea
5. **Training**: dimostra `wiki watch` con un file di esempio. Punto chiave:
   il Custode userà soprattutto questo in steady state — ogni nuovo documento
   passa per `_inbox/` e diventa bozza
6. **Lascia gli skill**: ricordagli `docs/05-manuale-custode.md` per i rituali

---

## Troubleshooting

### `wiki scan` si ferma con "rate limit"
Hai esaurito il quota Anthropic Haiku batch. Aspetta 1 min e ri-lancia
`wiki categorize`: è idempotente, riparte dalla prima riga non processata.

In alternativa: temporanea disattivazione passata 2 settando
`privacy.log_dati_a_anthropic: false` nel config. Riprendi quando hai quota.

### File aperti che danno lock (Windows/SharePoint)
Lo scanner ritenta 3 volte automaticamente. Se dopo 3 tentativi resta locked,
viene loggato `unreadable_locked` nel JSONL e saltato. Ri-lancia `wiki scan`
quando il file è chiuso: cursore-based resume riprende.

### OOM su NAS grossi (>500 GB, >100k file)
Sintomo: il processo Python viene killato a metà scan NAS.
Mitigazione: riduci `filtri_globali.max_file_mb` (es. 25 → meno file passano
il filtro → meno hash → meno memoria). Oppure scinde il NAS in due mount e
fai due `wiki scan --source nas` separati con config diversi.

Soluzione a regime (Step 3): SQLite invece di JSONL come storage di inventory.

### Watcher non parte: "pidfile esiste già"
Se il processo precedente è morto male, il file `_status/<slug>/watcher.pid`
resta orfano. Cancellalo e ri-lancia: il watcher non fa file-lock veri, il
pidfile è solo per health check.

### `wiki approve` dice "modulo batch_ui non disponibile"
Il cantiere BATCH-UI non è ancora fuso. Lavora in batch + edita le bozze a
mano in `_status/<slug>/drafts/<batch>/`. Quando BATCH-UI sarà disponibile,
basterà ri-pullare main.

---

## Convenzioni di file

| Cartella                          | Cosa contiene                          | Versionato?   |
|---|---|---|
| `bootstrap/clients/<slug>/`       | config cliente + credenziali           | **NO**        |
| `_inbox/<slug>/`                  | drop zone per il watcher               | **NO**        |
| `_status/<slug>/inventory/`       | JSONL per sorgente                     | **NO**        |
| `_status/<slug>/extracted/<sha12>`| markdown + meta estratti               | **NO**        |
| `_status/<slug>/drafts/<batch>/`  | bozze in attesa di approvazione        | **NO**        |
| `_status/<slug>/audit/`           | decisions.jsonl, redact-map, ecc.      | **NO**        |
| `_status/<slug>/cost.jsonl`       | log spesa Claude per call              | **NO**        |
| `_status/<slug>/watcher.pid`      | health check del watcher in esecuzione | **NO**        |

Tutto in `_status/` è output di runtime: contiene dati cliente e **non va mai
committato**. Il `.gitignore` è già configurato di conseguenza.
