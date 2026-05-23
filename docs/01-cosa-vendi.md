# 01 — Cosa vendi

Playbook commerciale per Valentino. Documento interno, non si consegna al cliente.

Risponde alla domanda: *"Quando arriva la prima call, cosa offri davvero, a chi, a quanto, e quando dici di no?"*

---

## A chi vendi

**ICP — PMI italiana, 30-50 dipendenti, manifatturiera o servizi B2B, prevalentemente nord Italia.**

Profilo che funziona:

- **Dimensione**: 30-50 persone. Sotto i 30 il dolore non è abbastanza forte, sopra i 50 servono ruoli e governance che la v1 non copre.
- **Settori che girano meglio**: manifatturiero (officine meccaniche strutturate, lavorazioni conto-terzi), servizi B2B (studi tecnici, agenzie, consulenze), commercio specializzato (distribuzione tecnica, ricambi). Settori dove c'è patrimonio documentale storico (offerte, contratti, schede, disegni) e processi ripetitivi.
- **IT/Office manager presente**: c'è una persona — interna o consulente fisso da anni — che gestisce account, accessi, NAS, backup. È il candidato naturale a diventare **Custode**. Se non c'è, il prodotto non funziona.
- **Direzione coinvolta**: titolare o COO disponibile a metterci la firma sul perimetro privacy e sull'investimento. Senza sponsor di livello, l'adozione muore.
- **Caos digitale percepito**: il cliente sa di averlo. Lo dice in prima call: "abbiamo tre Drive che nessuno sa più dove sta cosa", "il commerciale risponde a clienti citando offerte vecchie", "ogni volta che entra un nuovo deve girare per due settimane a chiedere".

**Persone tipo**: Anna Ferrari (titolare, Direzione), Giulia Bianchi (IT/Office manager, Custode designato), Mario Rossi e Luca Verdi (commerciale, Editor/Contributor), tutti gli altri (Contributor).

---

## Cosa vendi

**Una wiki aziendale costruita con te al fianco del cliente.** Non un software, non un abbonamento, non un corso. Una struttura di file che vive sui sistemi del cliente, popolata in 3-4 settimane di lavoro congiunto, manutenuta dal Custode interno con i rituali del manuale.

Il bundle è composto da:

1. **Il toolkit** — repo `claude-second-brain` con framework PMI, vault scheletro, le skill di setup/lifecycle/lint, il manuale custode in [`05-manuale-custode.md`](05-manuale-custode.md)
2. **Tu nel ciclo** — 3 atti di delivery presidiati, ½ giornata + 1-2 settimane + ½ giornata
3. **Opzionale: manutenzione mensile** — check-up del Custode, ottimizzazione skill, aggiunta nuovi reparti

### I 3 atti della delivery

| Atto | Quando | Dove | Cosa succede | Doc operativo |
|---|---|---|---|---|
| **1. Kick-off** | Giorno 1 | On-site | Test idoneità, wizard azienda, connessione MCP, perimetro privacy, vault scheletro | [`02-kickoff-checklist.md`](02-kickoff-checklist.md) |
| **2. Scandagliamento** | Settimana 1-2 | Remoto + call settimanale | Scanner sulle sorgenti, batch di 50 bozze, tu approvi, Custode rivede | [`03-scandagliamento.md`](03-scandagliamento.md) |
| **3. Handover** | Giorno finale | On-site | Training Custode sui 3 rituali, primo rituale fatto insieme, mail decommissioning, consegna manuale | [`04-handover-checklist.md`](04-handover-checklist.md) |

Lo Step 2 (scanner + extractor + batch-approval) **non è ancora costruito** in Step 1 del prodotto. Quando vendi oggi, vendi: il framework, le skill base, il manuale custode, i 3 atti con tu nel ciclo. Lo Step 2 lo aggiungi in roadmap quando esce.

---

## Pricing suggerito

**Tutti i valori sono indicativi e da validare in trattativa. Sono punti di partenza, non listino.**

| Voce | Range | Quando |
|---|---|---|
| **Setup una tantum** (3 atti) | 8.000 - 15.000 € | A inizio Atto 1, 50% acconto, 50% a fine Atto 3 |
| **Manutenzione opzionale** | 800 - 1.500 €/mese | Contratto annuale, fatturazione trimestrale |
| **Aggiunta nuovo reparto post-handover** | 2.000 - 4.000 € | Una tantum per ogni nuovo reparto aggiunto al vault dopo il go-live |

### Cosa giustifica l'8 vs il 15

| Fattore | Verso il basso (8k) | Verso l'alto (15k) |
|---|---|---|
| Dimensione | 30 persone, 1 sede | 50 persone, 2-3 sedi |
| Sorgenti da scandagliare | 1-2 (es. solo Drive) | 4+ (Drive + M365 + NAS + email) |
| Volume | < 200 GB | 500 GB - 2 TB |
| Reparti coinvolti | 1 reparto pilota (es. commerciale) | 3-4 reparti dal day 1 |
| Custode disponibile | Sì, 1 persona dedicata 2-4h/sett | Da formare, più persone coinvolte |
| Lingua/complessità | Italiano, processi lineari | Multilingua o processi complessi |

### Cosa include il setup

- 2 incontri on-site (Atto 1 + Atto 3, mezza giornata l'uno)
- Tutte le sessioni remote dell'Atto 2 (call settimanale + approvazione batch giornaliera)
- Stima 30-50 ore di lavoro tuo totali
- Costo Claude API per lo scandagliamento (lo paghi tu, è incluso)
- Repo pronto, manuale custode consegnato, prima settimana di rituali presidiati

### Cosa NON include il setup

- Licenze Claude (il cliente sottoscrive le sue: Cowork o Claude Code, anche piano free per Custode + Editor; uno o due piani Pro per Owner se vuole usarlo intensivamente)
- Licenze Obsidian (gratuito per uso personale, Pay Once per Sync se vogliono sincronizzare tra dispositivi)
- Connettori a sistemi proprietari non coperti dagli MCP standard
- Modifiche organizzative (ridefinizione ruoli, processi interni — quello è change management, non è il tuo perimetro)
- Migrazione di file binari nel vault (il vault contiene `.md` e link, non copie — vedi manuale custode)

---

## Quando NON vendere — 4 casi di fallimento

Sono dal manuale custode, Fase 0. Se senti uno di questi segnali in prima call, **non firmare**.

### 1. Nessun custode designato

Sintomo: "lo facciamo tutti insieme", "decidiamo dopo chi se ne occupa", "ci pensiamo come team".

Perché fallisce: senza una persona con nome, cognome, e 2-4 ore a settimana **scritte sul piano**, il vault muore in 6 settimane. Le 3 trappole più frequenti (Comitato, Consenso implicito, Big Bang) hanno tutte la stessa radice — manca chi decide.

Cosa dire al cliente: *"Posso ripartire con voi appena identificate il Custode. Senza, l'investimento si perde. Vi richiamo io fra 3 settimane se non avete novità."*

### 2. Cultura "ognuno il suo file"

Sintomo: il commerciale ha il suo Drive personale con i clienti, l'amministrazione ha il suo, il titolare il suo. Nessuna sovrapposizione, nessuna SSOT condivisa. Tentativi precedenti di centralizzazione falliti.

Perché fallisce: il vault chiede un cambio culturale (la conoscenza è dell'azienda, non della persona). Cambiare questa cultura è change management, non documentazione. Tu vendi documentazione.

Cosa dire: *"Quello che servirebbe da voi prima del wiki è un lavoro sui ruoli e sulla titolarità delle informazioni. Vi posso suggerire 2-3 consulenti di change management se volete affrontarlo. Quando lo avete fatto, riprendiamo io e voi."*

### 3. Turnover sopra il 30% annuo

Sintomo: la direzione lamenta che "la gente cambia", che "ogni 6 mesi c'è qualcuno nuovo", che certi reparti sono "una porta girevole".

Perché fallisce: la conoscenza evapora con le persone. Il Custode di oggi non è il Custode tra 4 mesi. La promozione settimanale non avviene. Il vault diventa l'ennesimo archivio dimenticato.

Cosa dire: *"Prima di costruire il wiki bisogna stabilizzare il team. Possiamo riparlarne tra 6-12 mesi se la situazione si assesta."*

### 4. Troppe persone con potere di veto

Sintomo: ogni decisione passa per direzione + 2-3 soci + comitato di gestione. Le decisioni piccole richiedono settimane.

Perché fallisce: il vault si costruisce decidendo velocemente — perimetro privacy, struttura reparti, naming, convenzioni di link. Se ogni decisione finisce in CdA, l'Atto 1 dura mesi anziché mezza giornata.

Cosa dire: *"Ho bisogno di un decisore singolo per il perimetro del wiki — di solito è il titolare o un COO. Se non riesco ad averlo, l'esecuzione si blocca. Possiamo individuare insieme chi può prendersi la responsabilità di firma?"*

---

## Come si presenta in 10 minuti

Struttura della demo per la prima call (Zoom o Teams), incollata letterale per essere ripetibile.

### Minuto 1-2 — Riconoscimento del dolore

> *"Mi raccontate in 2 minuti dove sta la vostra conoscenza oggi: chi ha cosa, dove si cerca quando entra una persona nuova, quanto tempo perdete a settimana a chiedere 'dove sta...'?"*

Ascolti. Annoti 2-3 frasi loro che riusi più avanti.

### Minuto 3-4 — Il problema, riformulato

> *"Quello che mi avete descritto è il problema classico delle PMI con 5-10 anni di storia digitale: il patrimonio c'è, ma è sparso tra Drive, NAS, caselle email, portatili. Non manca il contenuto, manca il posto canonico. E ogni tentativo di centralizzazione finisce nello stesso modo — un altro Drive 'definitivo' che diventa 'definitivo_v2' in sei mesi."*

### Minuto 5-7 — Cosa propongo

Apri uno screen share. Mostri **tre cose, in ordine**:

1. **Il vault scheletro** (cartella `vault/` aperta in Obsidian, grafo a vista). 30 secondi. *"Questa è la struttura. Non è un'app, è una cartella sui vostri sistemi. Ogni reparto ha la sua, ogni cliente ha la sua. Una sola persona — il Custode — ne è responsabile."*

2. **La sessione tipo**. Apri Claude (Cowork o Code) sul vault demo. Scrivi *"Buongiorno Claude, sono MR"*. Claude legge memoria aziendale + daily di MR e risponde con un orientamento sintetico. 1 minuto. *"Questo è quello che fa ogni mattina ognuno dei vostri. Apre Claude, dichiara chi è, parte. Niente briefing."*

3. **Il manuale custode**. Apri [`05-manuale-custode.md`](05-manuale-custode.md). Mostri l'indice. *"Questo è quello che vi consegno alla fine. È il manuale operativo del vostro Custode interno. Indipendente da me dopo l'handover."*

### Minuto 8-9 — I 3 atti

Mostri la tabella dei 3 atti (sopra, sezione "Cosa vendi"). *"Tre tappe: io vi monto la struttura on-site in mezza giornata, poi due settimane in cui scandagliamo le vostre sorgenti insieme — voi approvate cosa entra, cosa resta fuori — poi torno per il passaggio di consegne. Quattro settimane in tutto. Investimento 8-15 mila a seconda della dimensione."*

### Minuto 10 — Cosa serve da loro per andare avanti

> *"Per capire se ha senso parto da una domanda secca: chi è il vostro Custode? Una persona, con nome e cognome, che ha 2-4 ore a settimana per i prossimi 3 mesi. Se ce l'avete, vi mando una scheda tecnica e fissiamo l'Atto 1. Se non ce l'avete, vi richiamo io fra 3 settimane."*

Stop. Non parlare oltre. Lascia che rispondano.

---

## Cose escluse esplicitamente dalla v1

Da dichiarare in prima call, **prima** di firmare. Evitano contestazioni in Atto 2.

| Esclusione | Perché | Quando lo affronteremo |
|---|---|---|
| **Gestionali italiani senza API stabili** (TeamSystem, Zucchetti, Danea, Mexal) | Nessun MCP standard, integrazioni custom > budget setup | v1.5 o custom su quotazione separata |
| **Modalità on-premise** (Claude in locale, no cloud) | Richiede setup infrastrutturale dedicato, non è il modello SaaS della v1 | Step 3 o v1.5 (per studi medici, legali, settori regolamentati) |
| **Migrazione di file binari nel vault** | Il vault contiene `.md` + link. I PDF/CAD/Excel restano dove sono | Non è un problema da risolvere, è una scelta architetturale (vedi manuale custode Fase 3) |
| **Garanzia di "trovare tutto subito"** | Il vault entra a regime in 2-3 mesi di uso. Il primo mese è in costruzione | Spiegato esplicitamente in Atto 1, Atto 3 |
| **Cambio dei processi aziendali** | Documentazione, non re-engineering | Se serve, il cliente lo affronta separatamente |

---

## Manutenzione mensile — quando proporla

Non a tutti. Da proporre solo se:

- Il cliente ha **3+ reparti attivi** sul vault dopo il go-live
- Vuole aggiungere reparti / espandere a nuovi tipi di oggetto (commesse, fornitori che non c'erano)
- Il Custode è in difficoltà sui rituali (segnale: dopo 6 settimane il `_proposte-promozione.md` di reparto è ancora vuoto)
- L'azienda usa Claude intensivamente (Owner + 4-5 Editor) e vuole ottimizzare le skill

**Cosa include la manutenzione** (800-1.500 €/mese):

- 1 call mensile con il Custode (1h) — review delle promozioni, dei DA CHIARIRE accumulati, dei rituali
- Aggiustamenti alle skill (vault-lint, setup-wizard-persona, eventuali skill custom)
- Risposta entro 48h a richieste via email su questioni di struttura/governance del vault
- Aggiornamento del repo locale quando esce una nuova versione del toolkit

**Cosa NON include**:

- Scrittura di contenuto al posto del Custode (è un suo lavoro)
- Helpdesk per Contributor singoli (passa dal Custode)
- Sviluppo connettori MCP custom (quotazione separata)

---

## Checklist trattativa

Da spuntare prima di mandare il preventivo.

- [ ] Conosco la persona del Custode (nome, ruolo, ore disponibili)
- [ ] So chi firma (titolare, COO, direttore generale)
- [ ] Ho mappato le sorgenti principali (Drive? M365? NAS? email?) e ho una stima di GB
- [ ] Ho identificato 1 reparto pilota su cui partire
- [ ] Ho dichiarato esplicitamente le esclusioni (gestionali, on-premise)
- [ ] Ho proposto la mezza giornata on-site dell'Atto 1 con date possibili
- [ ] Il cliente ha capito che vendo "tu nel ciclo + toolkit", non un'app
- [ ] Ho almeno 1 caso di fallimento dei 4 escluso (ho verificato che non siamo lì)

Se 8/8 spuntati, mandi il preventivo. Se anche uno solo manca, fai un'altra call prima.

---

## Documenti collegati

- [`02-kickoff-checklist.md`](02-kickoff-checklist.md) — cosa fai l'Atto 1
- [`03-scandagliamento.md`](03-scandagliamento.md) — cosa fai l'Atto 2
- [`04-handover-checklist.md`](04-handover-checklist.md) — cosa fai l'Atto 3
- [`05-manuale-custode.md`](05-manuale-custode.md) — quello che consegni al cliente
- [`06-framework-pmi.md`](06-framework-pmi.md) — la teoria che sta sotto al prodotto
