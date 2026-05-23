# Brief — Audit Issues (subagente 1)

31 issue distinte trovate nel repo attuale. Molte si auto-risolvono con la sostituzione del vault e la riscrittura della doc. Quello che resta da affrontare attivamente è marcato `[AZIONE]`.

## Categoria 1: Path POSIX inesistenti

| File | Riga | Problema | Risoluzione |
|---|---|---|---|
| docs/come-aggiungere-progetto.md | 20, 60, 82-83, 124, 130-133, 144 | Path `Business/Consulenza/`, `Business/Formazione/`, `Content-Creator/`, `Idee/`, `~/Vault Claude/`, `~/Output Claude/` inesistenti | Auto-risolto: file riscritto in cantiere DOCS |
| skills/vault-lint/SKILL.md | 55-62, 76 | Script bash cerca path inesistenti — skill rotta out-of-the-box | `[AZIONE]` SKILLS: riscrivere vault-lint per nuovo vault PMI |
| applica-e-push.sh | 7 | Commenta path `~/Output Claude/Idee/claude-second-brain/` inesistente | `[AZIONE]` DOCS: decidere se documentare/integrare/cancellare lo script |
| docs/installazione-per-dummies.md | 282 | Link `docs/da-base-a-avanzato.md (in arrivo)` | Auto-risolto: file riscritto |
| docs/framework.md | 313 | Stesso link rotto | Auto-risolto: file riscritto |
| docs/come-aggiungere-progetto.md | 124 | Cita "Whitelist entità canoniche" inesistente in vault/CLAUDE.md | Auto-risolto: file riscritto |

## Categoria 2: Frontmatter incoerente nel vault legacy

| File | Problema | Risoluzione |
|---|---|---|
| vault/Daily/Task/hub.md | Zero frontmatter | Va in `_legacy-single-user/` — non più mantenuto |
| vault/Daily/templates/daily-template.md | Manca `parent:` e footer | Va in legacy |

**Per il NUOVO vault PMI**: imporre frontmatter standard (con i campi permessi: `owner`, `editor`, `visibilita`, `stato`, vedi brief 02-framework-pmi.md).

## Categoria 3: Wiki-link rotti

| File | Riga | Link | Problema |
|---|---|---|---|
| vault/Daily/Task/attivi.md | 9 | `[[hub]]` | Path risolution ambigua. Va in legacy. |

I `[[nome-del-file]]`, `[[progetto]]`, `[[Regola-01]]` nei `.md` di documentazione sono **esempi di sintassi**, non errori — vanno tenuti come esempi nel nuovo doc markdown-grafo.

## Categoria 4: Sovrapposizioni doc (alta priorità)

Le 3 triplicazioni più gravi che il cantiere DOCS deve eliminare:

| Sezione | File coinvolti | Stato target |
|---|---|---|
| Setup 3 opzioni (Cowork / Claude Code / Web) | INIZIA-QUI, installazione-per-dummies, guida-formazione | UNA volta sola, in `02-kickoff-checklist.md` o `installazione.md` (consolidato) |
| Plugin Obsidian (Tasks, Templates) | INIZIA-QUI, installazione-per-dummies, guida-formazione | UNA volta sola |
| Setup wizard + 5 domande | INIZIA-QUI, installazione-per-dummies, guida-formazione | UNA volta sola (vivrà come descrizione della skill `setup-wizard-azienda`) |
| Buongiorno/Buonanotte protocollo | README, vault/CLAUDE.md, framework.md, guida-formazione.md | UNA volta in `06-framework-pmi.md`, riferimenti altrove |
| 4 layer di memoria | vault/CLAUDE.md, framework.md, guida-formazione.md | UNA volta in `06-framework-pmi.md` (e diventano 6 layer PMI) |

## Categoria 5: File orfani (script non documentati)

| File | Decisione |
|---|---|
| applica-e-push.sh | `[AZIONE]` DOCS: leggere lo script, decidere se è utile per il flusso prodotto. Se sì → documentare in 02-kickoff-checklist o spostare in `bootstrap/` (riservato a Step 2). Se no → cancellare. |
| setup_github.sh | Stesso trattamento. |
| vault/Scheduled/_helpers/log-append.sh | Va in legacy (sparisce con `vault/`). |

## Categoria 6: Tag dichiarati ma non istanziati

`#consulenza`, `#formazione`, `#content`, `#daily`, `#contesto` sono dichiarati in `guida-markdown-e-grafo.md` ma nel template solo `#daily` esiste in `Daily/templates/daily-template.md`.

**Per il nuovo vault PMI**: rivedere la tassonomia tag. Probabilmente serve un set diverso (per-reparto, per-tipo-documento). Vedi brief framework-pmi sezione frontmatter.

## Categoria 7: Comandi/CLI con `~/Vault Claude` vs `vault/`

In tutti i comandi bash della doc, il path è incoerente: a volte `~/Vault Claude/`, a volte `vault/`. Per il nuovo prodotto, **path standard**: `vault/` (cartella relativa al repo clonato). Niente `~/Vault Claude/`.

---

## Riassunto azioni residue per i cantieri

- **VAULT**: archivia tutto `vault/` corrente in `_legacy-single-user/`, costruisce nuovo `vault/`
- **SKILLS**: riscrivi `vault-lint` per il nuovo vault. Riscrivi `session-lifecycle` multi-utente. Le altre skill sono nuove
- **DOCS**: elimina triplicazioni, decide cosa fare di `applica-e-push.sh` e `setup_github.sh` (leggi gli script e valuta)
