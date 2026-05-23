# 04 — Handover checklist (Atto 3)

Mezza giornata on-site. Chiude la delivery prodotto.

Obiettivo: alla fine della mezza giornata il Custode è **autonomo sui 3 rituali**, la lista **DA CHIARIRE è chiusa**, l'azienda riceve il **manuale custode firmato e stampato**, e tu hai **decommissionato il tuo accesso** ai sistemi del cliente.

---

## Pre-requisiti

Verificati nella settimana prima:

- Definition of done dell'Atto 2 è ✓ (vedi [`03-scandagliamento.md`](03-scandagliamento.md), sezione finale)
- Slot di **4 ore consecutive** confermato con Owner + Custode
- Manuale custode ([`05-manuale-custode.md`](05-manuale-custode.md)) **stampato o convertito in PDF**, una copia per Owner e una per Custode
- Slot calendar mensili (3 a 6 mesi) tentativamente proposti per check-up post-handover
- Bozza del **contratto di manutenzione** pronta, se previsto (vedi [`01-cosa-vendi.md`](01-cosa-vendi.md), sezione "Manutenzione mensile")

---

## Runtime — checklist ordinata della mezza giornata

### Blocco 1 — Risoluzione DA CHIARIRE (60 min)

Custode + tu, in screen-share sul vault.

Apri `vault/_pending/da-chiarire.md`. Per ogni voce accumulata in Atto 2:

| Stato | Cosa fate |
|---|---|
| Decisione presa in call settimanale, da formalizzare | Scrivi in `vault/decisioni/YYYY-MM-DD_titolo.md` come ADR numerato, link dal MOC dell'oggetto |
| Manca un'informazione che il Custode deve recuperare offline | Lascia voce in `_pending/`, schedula nei task del Custode |
| Bozza tagliata in Atto 2, ora va riintegrata | Riapri la bozza, integri, sposti dal `_pending/` al path finale |
| Non serve, era un falso positivo | Cancelli la voce |

Obiettivo: `_pending/da-chiarire.md` deve scendere sotto 5 voci. Le 5 restanti vanno nelle prime due settimane post-handover del Custode (task in `vault/reparti/<X>/tasks.md`).

### Blocco 2 — Training del Custode sui 3 rituali (90 min)

Custode + tu. Si fa in sala riunioni, schermo proiettato.

Il framework PMI definisce 3 rituali a 3 livelli (vedi [`06-framework-pmi.md`](06-framework-pmi.md), sezione "Protocollo a 3 livelli"). Li si addestra in ordine.

#### 2.1 — Rituale personale giornaliero (15 min)

> Chi: ogni persona dell'azienda che usa Claude. Frequenza: ogni giorno, 2 minuti al mattino + 2 minuti alla sera.

Mostri al Custode (e fai provare al Custode):

1. *"Buongiorno Claude, sono GB."* — Claude legge `MEMORY.md` aziendale + daily personale del Custode, risponde con orientamento sintetico
2. Si lavora normalmente (es. il Custode chiede *"prepara una bozza di mail per ricordare a Anna Ferrari la revisione mensile di MEMORY"*)
3. *"Buonanotte Claude"* — Claude scrive un riassunto della sessione nel daily del Custode, propone 0-3 cose da sedimentare

Riferimento operativo: skill `session-lifecycle` (vedi `skills/session-lifecycle/SKILL.md` nel repo).

Esercizio: il Custode lo fa, davanti a te, una volta. Poi lo rifa 2 ore dopo, senza tua guida, e tu osservi solo.

#### 2.2 — Rituale settimanale del Custode (45 min)

> Chi: il Custode (più Custode di reparto se ne avete designato più di uno). Frequenza: 30 min ogni venerdì, ora fissa.

Riferimento operativo: skill `rituale-settimanale-custode` (vedi `skills/rituale-settimanale-custode/SKILL.md` nel repo).

Mostri al Custode il flusso completo, **simulando un rituale reale**:

1. Apre `vault/reparti/<pilota>/_proposte-promozione.md` — vede le proposte accumulate durante la settimana (dalle conversazioni di tutti i colleghi)
2. Per ogni proposta decide:
   - **Sale a L3** (vita del reparto, `reparti/<X>/MEMORY.md`) — è una decisione che vale per il reparto ma non ancora per l'azienda
   - **Sale a L2** (procedura, `reparti/<X>/procedure/`) — è una pratica che si ripete, va scritta come SOP
   - **Candidata a L1** (memoria aziendale) — porta al rituale mensile con l'Owner
   - **Scartata** — era un'idea estemporanea, non vale
3. Aggiorna `reparti/<X>/MEMORY.md` con le decisioni promosse a L3
4. Lancia la skill `vault-lint` per verificare integrità (frontmatter, link rotti, file orfani) — vedi `skills/vault-lint/SKILL.md`
5. Risolve gli errori riportati da `vault-lint` (es. correggere frontmatter, sistemare link)

Esercizio: il Custode **fa davvero** un primo rituale settimanale, con i contenuti accumulati nelle settimane di Atto 2. Tu osservi e correggi solo se sbaglia.

#### 2.3 — Rituale mensile Owner + Custode (30 min)

> Chi: Owner + tutti i Custodi (se più di uno). Frequenza: 1h una volta al mese, data fissa (es. primo venerdì del mese).

Riferimento operativo: skill `rituale-mensile-owner` (vedi `skills/rituale-mensile-owner/SKILL.md` nel repo).

Mostri sul vault:

1. Apre la lista delle **candidate a L1** accumulate dai Custodi nei 4 rituali settimanali del mese
2. Per ogni candidata, Owner decide: **promuovi a `vault/MEMORY.md` aziendale** (è una decisione che vale per tutta l'azienda) o **non promuovere** (resta a livello reparto)
3. Owner rivede eventuali **ADR cross-reparto** in `vault/decisioni/` e le firma (campo `approvato-da:` nel frontmatter)
4. Owner + Custodi guardano la salute del vault (numero file vivi, MOC mancanti, reparti con poco contenuto) e decidono se serve espansione a nuovo reparto

Esercizio: si simula il primo rituale mensile con l'Owner presente. Owner deve **fare** una promozione vera. Anche solo una.

### Blocco 3 — Primo rituale settimanale fatto insieme (30 min)

Custode + tu. Già fatto in 2.2 come simulazione — qui si rifa **per davvero** con la settimana corrente.

Differenza: nel 2.2 era esercizio. Qui è il primo rituale ufficiale, va scritto come tale, va datato in `MEMORY.md` aziendale: *"YYYY-MM-DD — primo rituale settimanale Custode (GB), affiancato da Valentino."*

Il rituale successivo (venerdì prossimo) il Custode lo farà da solo.

### Blocco 4 — Mail di decommissioning (15 min)

Custode redige, tu rivedi, Owner approva.

La mail va a tutto il personale dei reparti coinvolti. Modello (adattato dal manuale custode, Fase 5):

```
A: tutto il personale del reparto Commerciale
Da: Anna Ferrari (Direzione) + Giulia Bianchi (Custode)
Oggetto: Da [data, +14 giorni] cambia dove si scrive: ecco come

Ciao a tutti,

Da [data, +14 giorni] cambia il modo in cui salviamo e ritroviamo
la conoscenza del reparto Commerciale.

- LAVORO CORRENTE (offerte nuove, contratti, schede cliente, decisioni):
  va nel nostro nuovo wiki, accessibile via [Cowork / link al vault].
  Chiedete a GB se vi serve l'accesso o un breve walkthrough.

- DRIVE "Commerciale" attuale:
  resta accessibile in SOLA LETTURA. Ci si può ancora cercare cose vecchie.
  Non scriveteci più.

- DOMANDE E DUBBI:
  GB è il punto di riferimento. Le scrivete via Teams.

- PERCHE':
  il wiki risolve quello che ci dicevamo da anni — "non si trova più nulla
  quando entra qualcuno nuovo". Da oggi entra ogni cosa nuova nel posto giusto.

Per chi vuole capire come funziona: [`manuale-persone.pdf`] (allegato),
1 pagina, 5 minuti.

Grazie a tutti per la pazienza,
Anna + Giulia
```

Lì in sala: la mail si scrive, l'Owner la firma, parte oggi. **Non rimandare.** Il decommissioning sui sistemi (Drive in sola lettura) lo fa il Custode nei 14 giorni successivi.

### Blocco 5 — Consegna materiali (15 min)

Owner + Custode + tu. Cerimonia, conta.

Si consegna formalmente:

1. **Manuale custode** ([`05-manuale-custode.md`](05-manuale-custode.md)) — copia stampata o PDF, una per Owner e una per Custode
2. **Manuale persone** ([`07-manuale-persone.md`](07-manuale-persone.md)) — PDF, da allegare alla mail di decommissioning (Blocco 4)
3. **Repo claude-second-brain** — sui sistemi del cliente, ramo `main`, README adattato al cliente
4. **File `references/perimetro-privacy.md`** firmato all'Atto 1 — ne tieni copia anche tu (PDF scan), una resta in azienda
5. **Backup vault** — il Custode mostra dove sta il backup automatico del vault (su un secondo disco, su un servizio cloud aziendale, ecc.)

### Blocco 6 — Calendar mensili e contratto manutenzione (30 min)

Owner + Custode + tu.

1. **Crea in sala** gli invite calendar per i **check-up mensili**: 3 occorrenze (mese 1, mese 3, mese 6 post-handover), 30 min ciascuna, in Teams o Zoom. Anche se non hai vendutoo la manutenzione, questi 3 check-up sono inclusi nel setup come buona pratica.

2. Se **contratto di manutenzione è in trattativa**: lo firmate qui, in sala. Decorrenza dal giorno dopo l'handover. Fatturazione trimestrale anticipata.

3. Se la manutenzione **non è stata venduta**: si concorda che il Custode può scriverti via email per emergenze (entro 30 giorni) senza costi aggiuntivi. Dopo i 30 giorni, eventuali interventi vanno a quotazione separata.

### Blocco 7 — Decommissioning tuo (15 min)

Custode + tu.

Smonti il tuo accesso ai sistemi del cliente:

1. **Revoca degli accessi MCP**: il Custode rimuove i tuoi token / le tue delegated permissions su Drive, M365, NAS
2. **Cancellazione locale**: cancelli dal tuo laptop i `_status/*.json` di lavoro (i metadati dei batch) — il resto del vault non era mai stato sul tuo laptop, lavoravi in screen-share
3. **Pulizia chat Claude tue**: cancelli le conversazioni di lavoro relative al cliente dalle tue history (la policy interna che dichiari in `01-cosa-vendi.md`)
4. **Conferma scritta**: scrivi una mail al Custode + Owner che dichiara "ho decommissionato il mio accesso ai vostri sistemi alla data [oggi]. Per future richieste opero solo via call o via email." — una copia resta a entrambi

---

## Output atteso a fine giornata

Sul vault del cliente:

- `_pending/da-chiarire.md` < 5 voci, le restanti sono task del Custode
- `MEMORY.md` aziendale ha una entry con la data dell'handover
- `vault/decisioni/` contiene gli ADR firmati durante l'Atto 2 + quelli risolti nel Blocco 1
- Almeno 1 rituale settimanale ufficialmente fatto (Blocco 3)

In mano al cliente:

- Manuale custode stampato o PDF, consegnato a Owner e Custode
- Manuale persone PDF, già inviato a tutto il personale del reparto pilota
- Repo `claude-second-brain` adattato (README parla del cliente) sul Git aziendale o su un repo Git interno
- 3 invite calendar per i check-up mensili (mese 1, 3, 6)
- Eventuale contratto di manutenzione firmato

Sul tuo lato:

- Accessi ai sistemi del cliente revocati
- Scan firmato del perimetro privacy
- Bozza fattura saldo (50% rimanente del setup, fatturazione entro 30 giorni)
- Nota nel tuo CRM personale: data handover, prossimi check-up, eventuali ganci per espansione futura (altri reparti)

---

## Anti-pattern dell'Atto 3

### Saltare il primo rituale per "fretta"

Sintomo: il Custode è stanco, sono le 18:00, voi dite *"il rituale lo fai venerdì da solo"*.

Antidoto: no. Il Blocco 3 (primo rituale insieme) è il momento di verifica più importante dell'Atto 3. Se non lo fai, il Custode al primo intoppo si ferma. Anche se vi tirate dietro mezz'ora extra, fatelo.

### Consegnare il manuale "dopo, te lo mando"

Sintomo: hai dimenticato di stampare. Dici *"te lo mando via email entro stasera"*.

Antidoto: il manuale custode è il **deliverable centrale dell'Atto 3**. Stamparlo, rilegarlo (anche solo a spirale), e consegnarlo fisicamente con cerimonia. Conta nella percezione del cliente di "cosa ho comprato". Se proprio non hai potuto stampare, prepara almeno la PDF impaginata su un USB che lasci sul tavolo.

### Lasciare aperti accessi tuoi "per comodità"

Sintomo: *"lascio attivi gli MCP così se il Custode ha problemi posso intervenire al volo"*.

Antidoto: no. Decommissioning fatto, scritto, mandato per mail. Se dopo serve, il Custode ti riapre l'accesso in 5 minuti. Lasciare aperto = rischio privacy + cliente che ti chiama per cose che potrebbe risolvere da solo.

### Non fissare i check-up mensili

Sintomo: *"ci sentiamo per il primo check-up tra un mese"* — detto in sala, senza calendar invite.

Antidoto: invite in sala, sul calendar di Owner e Custode, con link Teams/Zoom precompilato. Senza calendar invite, il primo check-up non avviene.

### Promettere manutenzione gratuita "a vita"

Sintomo: per chiudere bene la sala dici *"per qualsiasi cosa scrivimi pure, sempre"*.

Antidoto: chiarisci subito il perimetro post-handover: 30 giorni di garanzia per bug/correzioni → gratis. Oltre, va a contratto o a quotazione. Scrivilo nella mail di decommissioning tua (Blocco 7).

---

## Definition of done dell'Atto 3 (e della delivery)

- [ ] DA CHIARIRE chiusa o ridotta a < 5 voci con assegnatario
- [ ] Custode ha eseguito **da solo** almeno 1 rituale settimanale completo
- [ ] Owner ha partecipato alla simulazione del rituale mensile
- [ ] Mail di decommissioning partita, perimetro letto da tutti
- [ ] Manuale custode + manuale persone consegnati
- [ ] Calendar check-up mensili creati (3 occorrenze)
- [ ] Accessi tuoi ai sistemi del cliente revocati e dichiarati per scritto
- [ ] Eventuale contratto manutenzione firmato
- [ ] Fattura saldo emessa

---

## Documenti collegati

- [`01-cosa-vendi.md`](01-cosa-vendi.md) — manutenzione mensile, quando proporla
- [`03-scandagliamento.md`](03-scandagliamento.md) — definition of done dell'Atto 2 (pre-requisito dell'Atto 3)
- [`05-manuale-custode.md`](05-manuale-custode.md) — il manuale che consegni
- [`07-manuale-persone.md`](07-manuale-persone.md) — allegato della mail di decommissioning
