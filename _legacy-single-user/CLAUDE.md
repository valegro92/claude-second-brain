# CLAUDE.md — Istruzioni di sessione

> Questo file dice a Claude come lavorare nel vault. Per la spiegazione completa del framework leggi `../docs/framework.md`.

---

## [CONFIGURA QUI] — Compila questi 4 campi, poi non toccare altro

```
NOME:     Mario Rossi
RUOLO:    consulente marketing freelance
PROGETTI: ClienteA, ClienteB, Corso-Excel
REGOLE:   tono diretto, no elenchi puntati nelle email, bozza prima di produrre
```

*Il setup-wizard compila questo blocco automaticamente la prima volta. Dopo, modificalo a mano quando cambia qualcosa.*

---

## Architettura della memoria — i 4 layer

| Layer | Dove | Cosa | Quando si carica |
|---|---|---|---|
| **L0 — Identità** | `references/` | Chi sei, voce, ICP, valori, strategia. Stabile. | On-demand quando il task lo richiede |
| **L1 — Sistema** | `MEMORY.md` (radice di questo vault) | Decisioni e lezioni trasversali a tutti i progetti | Ogni mattina al "Buongiorno Claude" |
| **L2 — Progetto** | `progetti/X/MEMORY.md` | Decisioni specifiche del singolo progetto | Quando apro quel progetto |
| **L3 — Operativo** | `Daily/` | Log della giornata, task, idee grezze | Sempre, è il flusso live |

**Mai caricare tutto all'apertura.** Carica L0 solo quando serve, L2 solo quando lavoriamo su quel progetto.

---

## Session Lifecycle — Buongiorno / Buonanotte

- Quando scrivo **"Buongiorno Claude"** → leggi `MEMORY.md` (L1) e il daily di oggi (L3). Rispondi: *"Sessione N aperta. Cosa facciamo?"*
- Quando scrivo **"Buonanotte Claude"** → scrivi un riassunto della giornata nel daily, proponi 0-3 cose da sedimentare in `MEMORY.md`, aspetta il mio ok prima di scrivere.
- Durante il lavoro: caricamento on-demand. Non leggere file "per sicurezza".

---

## Le 3 regole non-negoziabili

### Regola della Bozza
Scrivi sempre prima la bozza nel vault come `.md`. **Aspetta il mio "ok produci"** prima di creare Word, PDF, slide, o file binari di qualsiasi tipo.

Eccezioni: richiesta diretta di binario ("fammi il pptx"), input da un cliente, modifica puntuale a un deliverable esistente.

### Regola 01 — invariante di progetto
Ogni progetto in `progetti/[nome]/` ha **sempre** questi 4 file:

- `[nome].md` — il MOC, hub che linka a tutto
- `CLAUDE.md` — istruzioni specifiche del progetto
- `MEMORY.md` — decisioni datate del progetto
- `tasks.md` — task locali

Più l'opzionale `knowledge/` per documenti di riferimento e trascrizioni call.

Quando apro un progetto, carica quei 4 file — non altro di default.

### Verify-or-redo
Dopo ogni modifica, **verifica davvero** il risultato dal punto di vista di chi lo userà. Apri il file, leggi il contenuto, prova il flusso. Mai dire "fatto" se non hai verificato.

Se la verifica fallisce: diagnosi → fix → verifica di nuovo. Solo allora conferma.

---

## Dove stanno le cose (Filing Rule)

| Cosa devo salvare | Dove va |
|---|---|
| Identità stabile (chi sei, voce, ICP) | `references/` (L0) |
| Decisione trasversale a più progetti | `MEMORY.md` radice (L1) |
| Decisione di un singolo progetto | `progetti/X/MEMORY.md` (L2) |
| Idea grezza | `Daily/Appunti/sparks.md` (L3) |
| Task del progetto X | `progetti/X/tasks.md` |
| Task senza progetto | `Daily/Task/hub.md` |
| Riassunto della sessione | `Daily/Journal/YYYY-MM-DD.md` |
| Trascrizione call | `progetti/X/knowledge/calls/YYYY-MM-DD-titolo.md` |

**Strict first match.** Usa il primo posto che combacia, non cercare il "migliore".

---

## Regole operative

1. **Mai cancellare file.** Se qualcosa è obsoleto, sposta in `_archivio/` o rinomina con `_v1`, `_v2`. Versioni, non cancellazioni.
2. **Brief non chiaro? Chiedi.** Non riempire con contenuto generico.
3. **MEMORY.md leggero.** Max 15-20 entry per sezione. Quando cresce, condensa le più vecchie in un'unica entry di sintesi.
4. **Naming deliverable**: `[progetto]_[tipo]_v[n].[ext]` (es. `acme_proposta_v2.docx`).

---

*Personalizza questo file quanto vuoi. Più è specifico per come lavori tu, più Claude lavora bene. Per la spiegazione completa del framework: `docs/framework.md`.*
