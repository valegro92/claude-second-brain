# CLAUDE.md — Kernel del vault PMI

> Questo file dice a Claude come lavorare nel vault aziendale.
> Il framework completo è descritto in `../docs/06-framework-pmi.md`.
> Qui c'è solo lo stretto necessario per operare ogni giorno.

---

## [CONFIGURA QUI] — Compila al kick-off, poi tocca solo quando cambia

```
AZIENDA:           Esempio Srl
SETTORE:           manifatturiero (carpenteria leggera, conto terzi)
SEDE:              Brescia (BS)
PERSONE-INIZIALI:  AF, GB, MR, LV, SC, PN, RM     # iniziali dichiarate in references/persone.md
SORGENTI:          Google Drive condiviso (vendite), Outlook, NAS /Volumes/produzione/, gestionale TeamSystem (sola lettura)
CUSTODE-CAPO:      GB (Giulia Bianchi, amministrazione)
OWNER-AZIENDA:     AF (Anna Ferrari, direzione)
```

Il setup-wizard-azienda compila questo blocco la prima volta. Dopo si
modifica a mano quando cambia qualcosa (nuovo reparto, nuova sorgente, nuovo
Custode).

---

## Architettura della memoria — 6 layer

Matrice: *cosa* (statico vs vivo) per *chi* (azienda vs reparto vs oggetto).

| Layer | Nome | Path | Cambia ogni | Quando si carica |
|---|---|---|---|---|
| **L0** | Identita aziendale | `references/` | trimestre | on-demand quando serve tono / posizionamento / glossario |
| **L1** | Memoria aziendale | `MEMORY.md` | mese | ad ogni "Buongiorno" di chiunque |
| **L2** | Procedure & playbook | `reparti/<X>/procedure/` | mese | quando il task tocca quel reparto |
| **L3** | Vita del reparto | `reparti/<X>/MEMORY.md` | settimana | quando apri un task del reparto |
| **L4** | Knowledge di oggetto | `clienti/<X>/`, `fornitori/<X>/`, `commesse/<X>/` | per evento | quando apri quell'oggetto |
| **L5** | Operativo personale | `Daily/<iniziali>/YYYY-MM/YYYY-MM-DD.md` | quotidiano | sempre, per la persona loggata |

**Mai caricare tutto.** Cammina dal layer giusto al layer giusto, in
funzione del task. L'esempio canonico e' nel framework doc.

---

## Identita utente attivo

Ogni sessione inizia con la dichiarazione:

> "Buongiorno Claude, sono MR"

Claude legge `references/persone.md`, recupera nome / reparto / ruolo /
email, e tiene le iniziali in una variabile di sessione. Da quel momento:

- **Filtra permessi** sui file via frontmatter `editor:` (vedi sotto)
- **Scrive il daily** in `Daily/MR/YYYY-MM/YYYY-MM-DD.md`
- **Firma** ogni proposta di promozione con le iniziali
- **Rifiuta** la scrittura in file dove non e' tra gli `editor:` e
  propone una bozza in `_bozze/` con frontmatter `stato: bozza`

Se la dichiarazione non arriva, Claude chiede "chi sei?" prima di
scrivere ovunque. Solo lettura senza identita dichiarata.

### Frontmatter standard

Ogni file vivo del vault porta un frontmatter come questo:

```yaml
---
tipo: scheda-cliente              # scheda-cliente | scheda-fornitore | sop | verbale | adr | post-mortem | onboarding | moc
owner: MR                         # iniziali dell'unico responsabile
editor: [MR, LV, GB]              # chi puo modificare il contenuto
visibilita: reparto               # azienda | reparto | privato
stato: vivo                       # bozza | vivo | archiviato
ultima-revisione: 2026-05-23
revisore: GB
---
```

Campi opzionali per tipo specifico (es. `cliente:`, `fornitore:`,
`commessa:`, `reparto:`, `versione:`, `prossima-revisione:`).

---

## Le 4 regole non-negoziabili

### Regola 1 — Bozza (rafforzata)

1. Leggi le fonti
2. Scrivi una bozza `.md` con `stato: bozza`
3. Se editor multipli, breve review interna
4. **Aspetta OK esplicito** di Owner / Custode
5. Solo allora produci il binario, con naming
   `[oggetto]_[tipo]_v[n]_YYYY-MM-DD.[ext]`
   (es. `rossi-srl_offerta_v2_2026-05-23.pdf`)

Niente Word / PDF / slide prima del passaggio 4.

### Regola 2 — Regola 01-PMI (5 file invece di 4)

Ogni oggetto in `clienti/`, `fornitori/`, `commesse/`, `processi/` ha
**sempre** questi 5 file:

- `<slug>.md` — il MOC, hub che linka a tutto
- `CLAUDE.md` — istruzioni specifiche dell'oggetto
- `MEMORY.md` — decisioni datate dell'oggetto
- `tasks.md` — task locali
- `persone.md` — chi e' chi (referenti da entrambi i lati)

Opzionali: `riunioni/`, `knowledge/`, `post-mortem/`, `_archivio/`.

Apri un oggetto → carica quei 5 file, non altro di default.

### Regola 3 — Verify-or-redo (estesa)

Dopo ogni modifica, **verifica davvero**: apri il file, leggi il
contenuto, prova il flusso. La verifica include il **canale di
pubblicazione**: se il binario doveva andare su Drive con un naming
specifico, controlla che ci sia, con quel nome, nel posto giusto.

Mai dire "fatto" se non hai verificato. Se la verifica fallisce:
diagnosi → fix → verifica di nuovo. Solo allora conferma.

### Regola 4 — SSOT per oggetto (anti-Drive caotico)

Per ogni cliente / fornitore / commessa / persona esiste **un solo**
file di verita nel vault: il MOC. Tutto il resto (allegati Drive,
righe Excel, mail con info datate) o linka a quel file o ci viene
riconciliato. Niente schede doppie. Niente "definitivo_v2_FINAL".

Quando trovi due verita su un oggetto, fermati: scegli quella nel
vault, archivia l'altra, scrivi una entry datata nel MEMORY
dell'oggetto.

---

## Protocollo a 3 livelli

Sostituisce il "Buongiorno / Buonanotte" single-user. Vedi
`docs/06-framework-pmi.md` per dettagli operativi.

**Livello 1 — Personale (giornaliero, ogni persona)**
- "Buongiorno Claude, sono XX" → legge L1 + suo L5
- "Buonanotte Claude" → scrive nel suo daily, propone 0-3 promozioni
  in `reparti/<reparto>/_proposte-promozione.md` (NON in L1)

**Livello 2 — Reparto (settimanale, Custode del reparto)**
- Venerdi 16:00, 30 min. Custode rivede `_proposte-promozione.md`,
  decide: sale a L3 (MEMORY reparto), sale a L2 (nuova SOP),
  candidata a L1 (entry da portare al rituale azienda), scartata.

**Livello 3 — Azienda (mensile, Owner + Custodi)**
- Prima settimana del mese, 1h. Rivedono candidate a L1 e nuovi ADR.
  Aggiornano `MEMORY.md` aziendale. Firmano nuove decisioni
  cross-reparto.

---

## Filing Rule — dove va cosa (decision tree)

Domanda 1: e' contenuto **statico** che descrive l'azienda nel suo
insieme (chi siamo, brand, glossario)?
→ `references/` (L0)

Domanda 2: e' una **decisione che riguarda piu di un reparto**?
→ `MEMORY.md` (L1). Se richiede anche un razionale articolato, anche
  ADR in `decisioni/`.

Domanda 3: e' una **procedura / SOP / template** di un reparto
specifico?
→ `reparti/<X>/procedure/` (L2)

Domanda 4: e' una **decisione interna a un reparto** o uno stand-up
del Custode?
→ `reparti/<X>/MEMORY.md` (L3)

Domanda 5: riguarda un **singolo cliente / fornitore / commessa**?
→ `clienti/<X>/`, `fornitori/<X>/`, `commesse/<X>/` (L4) — apri il
  MOC, scrivi nei 5 file giusti.

Domanda 6: e' la mia **giornata** (sparks, log, task personali)?
→ `Daily/<iniziali>/YYYY-MM/YYYY-MM-DD.md` (L5)

**Strict first match.** Usa il primo posto che combacia, non cercare il
"migliore". Se sei tra L1 e L3, vai L3: e' piu facile promuovere a L1
dopo, che ritirare giu da L1.

---

## Regole operative

1. **Mai cancellare file.** Sposta in `_archivio/` o rinomina con
   `_v1`, `_v2`. Versioni, non cancellazioni.
2. **Brief non chiaro? Chiedi.** Non riempire con contenuto generico.
3. **MEMORY leggero.** Max 15-20 entry per sezione. Quando cresce,
   condensa le piu vecchie in una entry di sintesi.
4. **Naming binari**: `[oggetto]_[tipo]_v[n]_YYYY-MM-DD.[ext]`.
5. **Wiki-link** `[[...]]` solo verso file che esistono. Niente link
   fantasma. Se serve un placeholder, scrivi il nome tra apici e basta.
6. **Niente emoji** in nessun file del vault.

---

*Per la spiegazione completa del framework: `docs/06-framework-pmi.md`.*
*Per il protocollo di migrazione da Drive caotico: `docs/05-manuale-custode.md`.*
