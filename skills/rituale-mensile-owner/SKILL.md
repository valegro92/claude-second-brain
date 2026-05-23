---
name: rituale-mensile-owner
description: Rituale mensile dell'Owner con i Custodi (1h, una volta al mese). Rivede le candidate a L1 raccolte dai rituali settimanali di tutti i reparti e decide quali entrano nella memoria aziendale, quali diventano ADR (decisioni archiviate), quali si rifiutano. Trigger - "rituale mensile", "review mensile aziendale", "promozioni del mese", "rituale owner".
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# rituale-mensile-owner — Review mensile aziendale

L'Owner, insieme ai Custodi di tutti i reparti, una volta al mese (idealmente primo lunedì del mese, 1 ora) rivede le candidate a L1 che i rituali settimanali hanno raccolto. Decide cosa entra nella memoria aziendale (`MEMORY.md`), cosa diventa una decisione archiviata permanente (ADR in `decisioni/`), cosa si scarta.

È il Livello 3 del protocollo a 3 livelli. Vedi `docs/06-framework-pmi.md` per il protocollo completo e i 6 layer.

---

## Quando si attiva

- Una volta al mese, lanciato dall'Owner (idealmente con i Custodi presenti, anche da remoto).
- Trigger tipici: "rituale mensile", "review mensile aziendale", "promozioni del mese", "vediamo le candidate L1".

---

## Pre-flight

1. **Identifica l'utente attivo**. Se non c'è, chiedi.
2. **Verifica ruolo**: l'utente deve essere Owner (preferibile) o Custode. Se è Contributor/Editor: "Il rituale mensile è normalmente fatto dall'Owner con i Custodi. Vuoi procedere lo stesso o aspettiamo l'Owner?".
3. **Censisci le candidate**: cerca tutti i file `vault/reparti/*/_candidate-L1.md` non vuoti. Se nessuno ha candidate: "Nessuna candidata accumulata questo mese. Niente da fare".
4. **Carica contesto**:
   - `vault/MEMORY.md` — memoria aziendale attuale (L1)
   - Lista file in `vault/decisioni/` — ADR esistenti (per non duplicare e per la prossima numerazione progressiva)
   - `vault/references/persone.md` — per riconoscere proponenti e Custodi

Riepiloga:
> Rituale mensile aziendale. <N> candidate da <K> reparti. ADR esistenti: <X>. Ultima decisione L1: <data ultima entry MEMORY.md>. Iniziamo.

---

## Comportamento

### 1. Per ogni candidata — una alla volta, raggruppate per reparto

Presenta:
> Candidata <i>/<N> — reparto <reparto> — del <data>:
> "<testo>"
> Proponente: <XX>. Custode di reparto: <YY>. Motivazione: <riga dal _candidate-L1.md>.
>
> Cosa ne facciamo?
> (a) entra in **L1** — aggiungo entry datata in `vault/MEMORY.md` (decisione viva, può essere rivista in futuro)
> (b) diventa **ADR** — creo `vault/decisioni/<YYYY-MM-DD>_<slug>.md` numerato progressivo (decisione architetturale, vincolante, raramente rivista)
> (c) **rifiutata** — non sale a L1, resta nei MEMORY di reparto

Aspetta decisione. Se l'utente vuole approfondire o ascoltare il Custode di quel reparto, sospendi e riprendi quando ha deciso.

### 2. Applica la decisione

**(a) Entra in L1**:
- Apri `vault/MEMORY.md`.
- Aggiungi entry: `## <YYYY-MM-DD> — <titolo breve>\n\n<testo riformulato come decisione aziendale>. (origine: reparto <reparto>, proposta <XX>, valutata nel rituale del <YYYY-MM-DD>)`
- Aggiorna `ultima-revisione:` nel frontmatter.

**(b) ADR**:
- Determina numerazione progressiva: cerca in `vault/decisioni/` il file con numero più alto (formato atteso: `NNN_titolo.md` o nei contenuti `numero: NNN`). Prossimo = max+1, zeropad a 3 cifre.
- Chiedi titolo (max 6 parole).
- Crea `vault/decisioni/<YYYY-MM-DD>_<slug>.md` con struttura:
  ```markdown
  ---
  tipo: adr
  numero: <NNN>
  data: <YYYY-MM-DD>
  owner: <iniziali-owner>
  editor: [<iniziali-owner>]
  visibilita: azienda
  stato: vivo
  origine-reparto: <reparto>
  proponente: <XX>
  ---

  # ADR <NNN> — <titolo>

  ## Contesto
  <perché si è arrivati a questa decisione>

  ## Decisione
  <cosa è stato deciso, in modo chiaro e vincolante>

  ## Conseguenze
  <cosa cambia in pratica, chi è impattato>

  ## Alternative considerate
  <opzioni scartate e perché>
  ```
- Aggiorna anche `vault/MEMORY.md` con una entry breve che linka all'ADR: `## <YYYY-MM-DD> — ADR <NNN>: <titolo>. Vedi vault/decisioni/<file>.md`.

**(c) Rifiutata**: nessuna scrittura aziendale, solo nota per il riepilogo.

### 3. Svuota le candidate processate

Dopo aver elaborato tutte le candidate di un reparto:
- Sovrascrivi `vault/reparti/<reparto>/_candidate-L1.md` lasciandolo vuoto (mantieni frontmatter, intestazione, template).
- Aggiungi entry nel `vault/reparti/<reparto>/MEMORY.md` (L3): `## <YYYY-MM-DD> — Esito rituale mensile aziendale: <NL1> a L1, <NADR> ADR, <NR> rifiutate.`

### 4. Log del rituale aziendale

Aggiungi entry in coda a `vault/MEMORY.md`:

```markdown
## <YYYY-MM-DD> — Rituale mensile (owner <XX>)
Reparti rivisti: <lista>. Candidate totali: <N>. Esito: <NL1> a L1, <NADR> nuovi ADR (<lista numeri>), <NR> rifiutate.
```

### 5. Riepilogo finale

> Rituale mensile completato.
> - <N> entrate in L1 (memoria aziendale)
> - <N> nuovi ADR creati: <lista numeri>
> - <N> rifiutate
>
> Reparti con candidate svuotate: <lista>. Prossimo rituale mensile: primo lunedì del mese prossimo.

---

## Regole di comportamento

- Una candidata alla volta. Niente batch.
- ADR è vincolante e raramente rivisto: usalo solo quando la decisione è architetturale (es. "non lavoriamo più con clienti sotto 50k", "stack tecnico standard"). Tutto il resto va in L1, che è vivo.
- Numerazione ADR sempre progressiva, zeropad 3 cifre, mai riusare un numero.
- Mai modificare ADR esistenti dall'esterno di questo rituale: per cambiare un ADR si crea un nuovo ADR che "supersede: NNN" il vecchio.
- Le candidate rifiutate restano nei MEMORY di reparto come traccia.
- Lingua: italiano.
- Tono: da CdA. Conciso, decisivo.
