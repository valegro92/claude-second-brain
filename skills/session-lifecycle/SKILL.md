---
name: session-lifecycle
description: Gestisce apertura e chiusura sessione personale nel vault aziendale multi-utente. Identifica l'utente attivo, carica L1+L5, filtra permessi durante la sessione, raccoglie promozioni a chiusura. Trigger - "Buongiorno Claude", "Buongiorno Claude sono <XX>", "Buonanotte Claude", "Iniziamo", "Chiudiamo".
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# session-lifecycle — Apertura e chiusura sessione (multi-utente)

Gestisce il ciclo giornaliero di una persona nel vault aziendale: apertura, lavoro con filtro permessi, chiusura con proposta promozioni.

Vedi `docs/06-framework-pmi.md` per la teoria del protocollo a 3 livelli (giornaliero, settimanale, mensile) e dei 6 layer di memoria.

---

## Apertura sessione

### Trigger

- "Buongiorno Claude, sono <XX>" (esplicito)
- "Buongiorno Claude" (implicito: legge utente attivo da `vault/CLAUDE.md` blocco `[UTENTE LOCALE]`)
- "Hello Claude", "Iniziamo", "Good morning Claude"

### Comportamento

1. **Identifica l'utente**:
   - Se l'utente si dichiara (`sono <XX>`), prendi quelle iniziali.
   - Altrimenti leggi `vault/CLAUDE.md` cercando `utente attivo: <XX>` nel blocco `[UTENTE LOCALE]`.
   - Se nessuna delle due → chiedi: "Chi sei? Dimmi le iniziali. Se sei nuovo, lancia prima `setup-wizard-persona`".
2. **Valida l'utente**: leggi `vault/references/persone.md`. Se `<XX>` non c'è → "Non ti trovo in `persone.md`. Lancia prima `setup-wizard-persona`".
3. **Memorizza in variabile sessione** le info dell'utente: iniziali, nome, reparto, ruolo. Da qui in poi sono il contesto di tutte le scritture.
4. **Carica L1 + L5**:
   - L1: `vault/MEMORY.md` (memoria aziendale).
   - L5: `vault/Daily/<XX>/<YYYY-MM>/<YYYY-MM-DD>.md` (daily di oggi dell'utente attivo).
   - Crea il daily di oggi se non esiste (usa il template `vault/Daily/_template-daily.md` se presente, altrimenti crea con frontmatter standard).
   - Crea la cartella mese `<YYYY-MM>/` se non esiste.
5. **Aggiungi riga al daily**: `### Sessione <N> aperta — HH:MM` (N = numero progressivo delle sessioni di oggi, default 1).
6. **Rispondi** in una sola riga:
   > Sessione <N> aperta per <XX>. <orientation in una riga: cosa c'è di rilevante in L1 per oggi, o "niente di nuovo">. Cosa facciamo?

### Non fare

- Non caricare L0 (`references/`) di default — solo on-demand quando il task richiede tono / glossario / brand voice.
- Non caricare L2/L3 dei reparti — solo quando l'utente apre un task di un reparto.
- Non caricare L4 (clienti/fornitori/commesse) — solo quando l'utente apre quell'oggetto.
- Non chiedere conferma — apri e basta.

---

## Durante la sessione

### Filtro permessi su scritture

Ogni volta che stai per scrivere o modificare un file del vault:

1. **Leggi il frontmatter** del file di destinazione (campi `owner:`, `editor:`, `visibilita:`).
2. **Se non hai frontmatter**: trattalo come pubblico-reparto (chiunque può scrivere). Aggiungi mentalmente alla lista di file "da bonificare" che segnalerai a chiusura.
3. **Applica la regola**:
   - Se `<XX>` è in `editor:` (o è `owner:`) → procedi.
   - Se non lo è → **rifiuta** la scrittura diretta e proponi alternativa:
     > Non posso scrivere su `<file>` — gli editor abilitati sono <lista>. Ti preparo una bozza in `vault/_bozze/<XX>/<file-originale>.md` che potrai sottoporre via rituale settimanale al Custode del reparto. Confermi?
4. **Bozza in `_bozze/<XX>/`**: stesso path relativo del file target, ma sotto la propria cartella bozze. Frontmatter: `stato: bozza`, `proponente: <XX>`, `file-target: <path originale>`.

### Log della sessione

- Ogni azione rilevante (file scritto, cliente aperto, decisione presa) → aggiungi una riga nel log del daily: `- HH:MM <azione breve>`.
- Idee grezze, sparks → in fondo al daily, sezione `## Sparks` (crea se non esiste).
- Task nuovi → `vault/clienti/<X>/tasks.md` se contesto cliente, altrimenti sezione `## Task del giorno` nel daily.
- Bozze di contenuto → scrivi sempre nel vault prima (in `_bozze/<XX>/` se non hai permessi), aspetta "ok produci" prima di toccare binari.

---

## Chiusura sessione

### Trigger

- "Buonanotte Claude", "Good night Claude", "Chiudiamo", "Fine sessione"

### Comportamento

1. **Scrivi un riassunto** nel daily dell'utente attivo (`vault/Daily/<XX>/<YYYY-MM>/<YYYY-MM-DD>.md`), sezione `## Riassunto sessione <N>`:
   - 3-6 bullet con cosa è stato fatto, decisioni prese, file toccati.
2. **Identifica 0-3 promozioni candidate**. Una promozione è una cosa che vale la pena far uscire dal Daily personale e portare verso il reparto o l'azienda. Criteri:
   - Decisione che cambia come si lavora (candidata a L3 reparto o L1 azienda)
   - Nuova procedura emersa o template (candidata a L2 reparto)
   - Lezione generalizzabile ad altri progetti/clienti
   - Non includere mai: appunti operativi, micro-task, gossip di giornata.
3. **Per ogni promozione, proponi la formulazione e chiedi conferma**:
   > Promozione 1/<N>: "<formulazione 1-2 righe>". Va al reparto <reparto-utente> nelle proposte settimanali. Confermo? (sì / no / riscrivi)
4. **Scrivi solo le approvate** in `vault/reparti/<reparto-utente>/_proposte-promozione.md`, formato:
   ```markdown
   ## <YYYY-MM-DD> — <titolo breve>
   Proponente: <XX>
   <testo della proposta in 2-4 righe>
   Contesto: <link al daily o al file toccato>
   ```
   Le promozioni NON vanno mai direttamente in `vault/MEMORY.md` (L1) né in `vault/reparti/<X>/MEMORY.md` (L3). Per quello esistono i rituali (vedi `rituale-settimanale-custode` e `rituale-mensile-owner`).
5. **Aggiungi log chiusura nel daily**: `### Sessione <N> chiusa — HH:MM`.
6. **Rispondi**:
   > Sessione <N> chiusa per <XX>. <N> promozioni proposte al reparto <reparto>. A domani.

---

## Regole di comportamento

- Mai inventare file o utenti: se `<XX>` non è in `persone.md`, blocca.
- Una sessione = un utente attivo. Se cambia (es. "ora sono <YY>"), chiudi la corrente e apri una nuova.
- Filtro permessi sempre attivo durante la sessione. Mai bypassare "perché tanto siamo tutti colleghi".
- Le promozioni NON vanno mai dirette in L1/L3. Sempre via `_proposte-promozione.md` del reparto.
- Tono: diretto, mai prolisso. Una riga di orientation in apertura, max 6 bullet in chiusura.
- Lingua: italiano.
