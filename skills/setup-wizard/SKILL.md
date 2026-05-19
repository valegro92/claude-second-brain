# SKILL: Setup Wizard — Configura il tuo secondo cervello

Questo skill guida l'utente attraverso la configurazione iniziale del vault.
Obiettivo: capire chi è, come lavora, e scrivere i file chiave del framework con le sue parole.

Il wizard copre **4 layer di memoria**:
- **L0/L1 — Identità + Sistema** (sempre, 5 domande): chi sei, su cosa lavori, come vuoi che Claude ti parli, cosa non vuoi rispiegare, come comunichi
- **L2 — Progetto** (opzionale): predispone la cartella di un primo progetto reale
- **L3 — Intelligence** (opzionale): predispone `knowledge/calls/` per le trascrizioni meeting
- **L4 — Skill/Automazioni** (opzionale): annota in `MEMORY.md` i tool che vorrai automatizzare in futuro

I tre layer opzionali sono saltabili: se l'utente vuole solo il setup base, in 10 minuti è online.

---

## Quando si attiva

L'utente ha appena clonato il repo e vuole configurarlo per sé.
Trigger tipici: "configura il vault", "setup", "iniziamo", "sono nuovo", oppure l'utente ha aperto la cartella e scritto qualcosa di simile.

---

## Comportamento

### Step 1 — Presentati e spiega cosa succederà

Rispondi con qualcosa del tipo:

> Perfetto — sono qui per aiutarti a configurare il tuo secondo cervello con Claude. Funziona in due fasi:
>
> 1. **Setup base (10 minuti, sempre)** — ti faccio 5 domande per capire chi sei e come lavori. Compilo `CLAUDE.md`, `MEMORY.md`, `references/chi-sono.md`.
> 2. **Setup avanzato (5 minuti, opzionale)** — 3 mini-step per predisporre un progetto reale, le trascrizioni delle call, e gli automation futuri. Puoi saltarli e farli dopo.
>
> Iniziamo dal setup base?

Non partire con le domande subito — aspetta conferma.

---

### Step 2 — Le 5 domande del setup base (Layer 0/1)

Fai UNA domanda alla volta. Aspetta la risposta prima di passare alla successiva.
Non fare elenchi. Tono conversazionale, non da form.

**Domanda 1 — Chi sei**
> Chi sei e cosa fai professionalmente? Anche in modo informale — non serve la bio LinkedIn.

*(Ascolta: ruolo, settore, tipo di lavoro, eventuale identità professionale)*

**Domanda 2 — Con chi e su cosa lavori**
> Su cosa stai lavorando in questo periodo? Clienti, progetti, corsi, idee — anche in modo disordinato.

*(Ascolta: nomi dei progetti attivi, clienti, aree di lavoro correnti)*

**Domanda 3 — Come vuoi che Claude ti parli**
> Come preferisci che Claude lavori con te? C'è qualcosa che ti dà fastidio o che vuoi che faccia sempre / non faccia mai?

*(Ascolta: tono preferito, lunghezza delle risposte, cose da evitare, stile)*

**Domanda 4 — Cosa non vuoi dover rispiegare ogni volta**
> C'è qualcosa che ti stanchi di rispiegare ogni volta — una preferenza, una decisione già presa, un vincolo su un cliente o progetto?

*(Ascolta: 2-5 cose da mettere subito in MEMORY.md)*

**Domanda 5 — Come comunichi**
> Quando scrivi per lavoro — email, post, report — hai un tono o uno stile riconoscibile? Anche "non lo so ancora" va bene.

*(Ascolta: tono di scrittura, canali preferiti, esempi se li dà)*

---

### Step 3 — Riepilogo e conferma

Prima di scrivere i file, fai un riepilogo breve:

> Ok, ho capito. Prima di scrivere i file, ti confermo quello che ho capito: [riepilogo in 4-5 righe]. Va bene così, o vuoi correggere qualcosa?

Aspetta conferma o correzioni.

---

### Step 4 — Scrivi i file del setup base

Dopo la conferma, scrivi o sovrascrivi questi tre file nella cartella vault/:

#### `vault/CLAUDE.md`

Mantieni la struttura del template (sezione [CONFIGURA QUI], architettura 4 layer, regole non-negoziabili) ma compila il blocco di configurazione con i dati reali dell'utente:

```
NOME:     [nome e ruolo reale]
RUOLO:    [ruolo professionale in una riga]
PROGETTI: [nomi dei progetti attivi separati da virgola]
REGOLE:   [2-4 regole di lavoro emerse dalla conversazione]
```

**Non toccare il resto della struttura del file** — solo il blocco `[CONFIGURA QUI]`. Le sezioni "Architettura della memoria", "Session Lifecycle", "Le 3 regole non-negoziabili", "Filing Rule" sono parte del framework e devono restare invariate.

#### `vault/MEMORY.md`

Scrivi le prime entry reali con le informazioni date nella domanda 4.
Formato: `## YYYY-MM-DD — titolo breve` + 2-3 righe di contesto.
Usa la data di oggi. Max 5 entry per iniziare — non inventare, usa solo quello che l'utente ha detto.

#### `vault/references/chi-sono.md`

Compila il template con le risposte reali dell'utente (domande 1, 2, 5).
Tono in prima persona, come se l'utente lo avesse scritto lui/lei.
Non inventare dettagli non dati — usa "da definire" per le sezioni vuote.

---

### Step 5 — Conferma base e proposta avanzato

Dopo aver scritto i file:

> Fatto. Ho compilato i tuoi tre file con le tue informazioni.
>
> Vuoi continuare con il setup avanzato (3 mini-step da ~5 minuti totali) o fermarti qui? Se ti fermi qui puoi già iniziare a lavorare con `Buongiorno Claude`.

Se l'utente vuole fermarsi → salta allo Step 9 (chiusura).
Se vuole continuare → Step 6.

---

### Step 6 — Setup avanzato L2 (un primo progetto reale)

> Bene. Hai già un cliente / corso / idea a cui vorresti applicare il sistema subito? Anche solo per testare. Se sì, dimmi il nome (può essere qualsiasi cosa: un cliente reale anonimizzato, un corso, una tua idea in sviluppo).

Se l'utente dice un nome:
1. Crea la cartella `vault/progetti/[nome-kebab-case]/` copiando da `vault/progetti/_esempio/`
2. Rinomina `_esempio.md` in `[nome].md` e aggiorna i riferimenti interni
3. Chiedi 2 domande veloci:
   - "In una riga: di cosa si tratta?"
   - "C'è una decisione che hai già preso e che vuoi che Claude ricordi su questo progetto?"
4. Compila il MOC (`[nome].md`) con la descrizione e `progetti/[nome]/MEMORY.md` con la prima entry datata

Se l'utente dice "non ancora" → salta a Step 7.

---

### Step 7 — Setup avanzato L3 (Intelligence — trascrizioni call)

> Registri o trascrivi le call di lavoro? (Otter, Granola, Fireflies, Zoom auto-transcript, registratore vocale...)

Se sì:
1. Crea la cartella `vault/progetti/[nome-progetto-corrente]/knowledge/calls/` (se progetto esiste dallo Step 6)
2. Aggiungi una nota in `MEMORY.md` radice:
   ```
   ## YYYY-MM-DD — Intelligence
   - Trascrizioni meeting: [tool indicato dall'utente]
   - Convenzione: salvo i transcript in `progetti/X/knowledge/calls/YYYY-MM-DD-titolo.md`
   ```
3. Spiega all'utente:
   > Quando vorrai che una call entri nel sistema, incollami il transcript e dimmi il progetto. Lo salvo nella cartella giusta e lo riassumo nel MEMORY del progetto.

Se l'utente dice "no" o "non ancora" → salta a Step 8.

---

### Step 8 — Setup avanzato L4 (Skill/Automazioni — annota i tool)

> Quali sono i tool che usi di più nel quotidiano (Gmail, Calendar, Slack, Asana, Notion, gestionali, fogli...)? Non ti collego niente adesso — annoto solo in `MEMORY.md` quali sono, così quando vorrai automatizzare partiamo da una lista già pronta.

Aggiungi una entry in `MEMORY.md` radice:
```
## YYYY-MM-DD — Stack di lavoro
Tool che uso ogni giorno: [lista dall'utente]
Da automatizzare in futuro (ordine di priorità): [lista o "da definire"]
```

---

### Step 9 — Conferma finale

> Setup completato. Da questo momento puoi iniziare a lavorare — scrivi **`Buongiorno Claude`** per aprire la prima sessione ufficiale.
>
> Se vuoi vedere come appare la tua `CLAUDE.md` compilata, posso mostrartela. Altrimenti hai 4 layer di memoria pronti, e domani mattina il sistema saprà già chi sei.

Se l'utente conferma di vedere il file → mostra `vault/CLAUDE.md` come riferimento.
Se l'utente è già a posto → chiusura.

---

## Note importanti

- **Non inventare mai informazioni che l'utente non ha dato.** Preferisci "da definire" a qualsiasi placeholder generico.
- **Se l'utente risponde in modo vago**, fai una domanda di chiarimento prima di procedere. Mai inventare per riempire.
- **Tono caldo ma diretto**, niente lunghe introduzioni a ogni domanda.
- **Se l'utente ha già compilato uno dei file** (non è la versione template), non sovrascrivere — chiedi prima.
- **I 3 step opzionali (6, 7, 8) sono indipendenti**: l'utente può saltarne uno e fare gli altri. Chiedi sempre prima.
- **Tempo totale realistico**:
  - Solo setup base (Step 1-5 + 9): ~10 minuti
  - Setup completo (Step 1-9): ~15 minuti
