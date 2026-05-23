---
name: rituale-settimanale-custode
description: Rituale settimanale del Custode di reparto (30 min, tipicamente venerdi). Rivede le proposte di promozione raccolte dai Contributor durante la settimana e le smista verso L3 reparto, L2 procedure, o candidata a L1 aziendale. Trigger - "rituale settimanale", "promozione settimanale", "facciamo la review del reparto <X>", "rituale custode".
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# rituale-settimanale-custode — Review settimanale di reparto

Il Custode di reparto, una volta a settimana (idealmente venerdì 16:00, 30 minuti), rivede le proposte di promozione che i Contributor del reparto hanno accumulato. Le smista: alcune salgono a L3 (memoria reparto), alcune diventano nuove SOP a L2, alcune sono candidate per il rituale mensile aziendale, alcune si scartano.

È il Livello 2 del protocollo a 3 livelli. Vedi `docs/06-framework-pmi.md` per il protocollo completo e i 6 layer.

---

## Quando si attiva

- Una volta a settimana, lanciato dal Custode di un reparto.
- Trigger tipici: "rituale settimanale", "promozione settimanale", "facciamo la review del reparto commerciale", "vediamo le proposte della settimana".

---

## Pre-flight

1. **Identifica l'utente attivo** (deve essere già loggato via `session-lifecycle`). Se non c'è utente attivo, chiedi: "Chi sei? Dimmi le iniziali".
2. **Verifica ruolo**: leggi `vault/references/persone.md`. Se l'utente non è Custode (né Owner), avvisa: "Il rituale settimanale è normalmente fatto dal Custode di reparto. Risulti come <ruolo>. Vuoi procedere lo stesso?".
3. **Identifica il reparto**:
   - Se l'utente è Custode, default: il suo reparto.
   - Se l'utente specifica un reparto diverso (es. "facciamo la review del commerciale" e l'utente è Custode dell'amministrazione), chiedi conferma.
   - Se l'utente è Owner e non specifica, chiedi quale reparto.
4. **Verifica file proposte**: leggi `vault/reparti/<reparto>/_proposte-promozione.md`. Se è vuoto: "Nessuna proposta accumulata questa settimana. Niente da fare. Buon weekend".

---

## Comportamento

### 1. Carica il contesto

Leggi in apertura:
- `vault/reparti/<reparto>/_proposte-promozione.md` — la lista delle proposte
- `vault/reparti/<reparto>/MEMORY.md` — la memoria di reparto attuale (L3)
- `vault/reparti/<reparto>/procedure/` — lista delle SOP esistenti (L2)
- `vault/MEMORY.md` — per evitare di promuovere a L1 cose già lì

Riepiloga in 2 righe:
> Reparto <reparto>. <N> proposte da rivedere. Memoria attuale: <M> decisioni. SOP esistenti: <K>. Iniziamo.

### 2. Per ogni proposta — una alla volta

Presenta la proposta con contesto:
> Proposta <i>/<N> del <data>:
> "<testo della proposta>"
> Proponente: <XX>. Contesto: <link/path>.
>
> Cosa ne facciamo? Opzioni:
> (a) sale a **L3** — entra in `reparti/<reparto>/MEMORY.md` (decisione/lezione di reparto, datata)
> (b) sale a **L2** — diventa una nuova SOP (`procedure/sop-<slug>.md`) o aggiorna una esistente
> (c) **candidata a L1** — sposto in `_candidate-L1.md`, il rituale mensile deciderà
> (d) **scarta** — non vale la pena, resta solo nel daily del proponente

Aspetta decisione. Se l'utente esita o vuole pensarci, marca la proposta come "rimandata" e passa alla successiva (resterà in `_proposte-promozione.md` per la prossima settimana).

### 3. Applica la decisione

**(a) Promozione a L3**:
- Apri `vault/reparti/<reparto>/MEMORY.md`.
- Aggiungi entry: `## <YYYY-MM-DD> — <titolo breve>\n\n<testo riformulato in forma di decisione di reparto>. (da proposta di <XX>)`
- Aggiorna `ultima-revisione:` nel frontmatter.

**(b) Promozione a L2**:
- Chiedi: "Nuova SOP o aggiorno esistente?". Se esistente, chiedi quale.
- Per nuova SOP: chiedi titolo, genera `vault/reparti/<reparto>/procedure/sop-<slug>.md` con frontmatter (`owner: <custode>`, `editor: [<custode>, <editor-reparto>]`, `visibilita: reparto`, `versione: 1`, `revisore: <custode>`, `prossima-revisione: <oggi+6 mesi>`) e struttura base (Obiettivo, Quando si applica, Passi, Output atteso).
- Per aggiornamento: apri SOP esistente, aggiungi sezione `## Revisione <YYYY-MM-DD>` con il testo della proposta, bump `versione:` e `ultima-revisione:`.

**(c) Candidata a L1**:
- Apri (o crea) `vault/reparti/<reparto>/_candidate-L1.md`.
- Aggiungi entry: `## <YYYY-MM-DD> — <titolo breve>\n\nProponente: <XX>. Custode: <iniziali-custode>.\n<testo della proposta>.\nMotivazione candidatura: <chiedi al Custode una riga>`.

**(d) Scartata**: nessuna scrittura, solo nota mentale per il riepilogo.

### 4. Svuota le proposte processate

Dopo aver elaborato tutte le proposte (escluse le "rimandate"):
- Sovrascrivi `vault/reparti/<reparto>/_proposte-promozione.md` mantenendo solo le proposte rimandate (se ci sono).
- Se nessuna rimandata, lascia il file con solo il template vuoto e frontmatter aggiornato.

### 5. Aggiorna il log del rituale

Aggiungi entry in `vault/reparti/<reparto>/MEMORY.md` in coda:

```markdown
## <YYYY-MM-DD> — Rituale settimanale (custode <XX>)
Proposte riviste: <totale>. Esito: <NL3> a L3, <NL2> a L2, <NL1c> candidate L1, <NS> scartate, <NR> rimandate.
```

### 6. Riepilogo finale

> Rituale completato per reparto <reparto>.
> - <N> promosse a L3 (memoria reparto)
> - <N> a L2 (nuova SOP / aggiornata)
> - <N> candidate a L1 (le valuterà il rituale mensile)
> - <N> scartate
> - <N> rimandate alla prossima settimana
>
> Tempo: <stimato>. Prossimo rituale: venerdì prossimo.

---

## Regole di comportamento

- Una proposta alla volta. Niente batch.
- Mai promuovere a L1 direttamente — è competenza del rituale mensile (vedi `rituale-mensile-owner`).
- Mai cancellare proposte "scartate" senza menzione: restano traccia nel log del MEMORY di reparto via riepilogo.
- Frontmatter sempre aggiornato (`ultima-revisione:`, `versione:` su SOP).
- Lingua: italiano.
- Tono: pragmatico, da capo reparto. Niente cerimonia.
