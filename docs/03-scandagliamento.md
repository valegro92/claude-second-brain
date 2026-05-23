# 03 — Scandagliamento supervisionato (Atto 2)

1-2 settimane, prevalentemente remoto, con call settimanale fissa con il Custode.

Obiettivo dell'Atto 2: i contenuti vivi del reparto pilota sono migrati nel vault come `.md` strutturati + link ai binari originali. Le decisioni storiche sono codificate. Il Custode ha visto lavorare l'agente abbastanza da poterlo prendere in mano dall'Atto 3.

---

> **Nota importante — sezioni in costruzione.** Lo Step 2 del prodotto (scanner + extractor + skill di batch-approval + dashboard `_status/`) **non è ancora costruito** alla data di questo documento. Le sezioni marcate `[IN COSTRUZIONE]` descrivono come funzionerà a regime. Per i primi clienti, l'Atto 2 si esegue in modalità manuale supervisionata — sezioni `[MANUALE OGGI]` spiegano come.

---

## Come funziona, a 10.000 piedi

L'Atto 2 non è "Claude scandaglia il Drive e produce magia". È un loop strutturato a 5 step, ripetuto in batch da 50 documenti, fino a che il reparto pilota è coperto.

```
                              Loop settimanale
                              ────────────────

   1. SCAN              2. EXTRACT          3. PROPOSE
   [IN COSTRUZIONE]     [IN COSTRUZIONE]    [IN COSTRUZIONE]
   Scanner gira sulle    Extractor legge i    Skill batch-approval
   sorgenti del          file selezionati,    presenta a Valentino
   reparto pilota,       produce bozze .md    50 bozze per volta
   produce inventario    classificate         con motivazioni
        │                     │                     │
        ▼                     ▼                     ▼
   ┌─────────────────────────────────────────────────────────────────┐
   │              4. APPROVE — Valentino, batch da 50                │
   │  Per ogni bozza: approva / rifiuta / modifica / "chiedi Custode"│
   └─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
            5. CUSTODE REVIEW (call settimanale, 30 min)
            Custode rivede ciò che è andato in vault,
            risolve i "chiedi Custode" accumulati,
            firma il batch.
```

A regime, **un cliente medio è 2-4 batch da 50 = 100-200 documenti nel vault** alla fine dell'Atto 2. Il resto resta dov'è (categoria ARCHIVIO o DA CONSULTARE — vedi [`05-manuale-custode.md`](05-manuale-custode.md), Fase 2).

---

## Workflow settimanale

### Lunedì mattina — lanci lo scanner del batch della settimana

`[IN COSTRUZIONE]`

A regime, da CLI o da Cowork:

```bash
claude-second-brain scan --source "drive:commerciale" --batch 50 --output _status/batch-YYYY-WW.json
```

Lo scanner:
1. Legge una cartella o un set di cartelle dichiarate in `_audit/sources.md`
2. Filtra per freschezza (default: file toccati negli ultimi 12 mesi)
3. Estrae metadati: nome, dimensione, ultima modifica, autore, tipo MIME
4. Cluster preliminare per pattern di naming (es. tutti i file `Offerta_*_2024_*.pdf` finiscono nello stesso cluster)
5. Propone le prime 50 candidate per estrazione

`[MANUALE OGGI]`

Tu apri Claude (Cowork o Code) sul vault. Carichi le statistiche di inventario raccolte in [`02-kickoff-checklist.md`](02-kickoff-checklist.md), Blocco 5. Chiedi a Claude:

> *"Ho un Drive 'Commerciale' di 47 GB, 12.400 file totali, 3.100 toccati negli ultimi 12 mesi. Il reparto pilota è Commerciale. Proponi una lista di 50 file/cartelle da cui partire per costruire le schede dei top 10 clienti. Criterio: contratti firmati, offerte 2024-2025, ultime call transcript se ci sono."*

Claude (con MCP Drive attivo) propone 50 path. Tu rivedi, tagli i fuori scope, confermi.

### Lunedì pomeriggio — extractor sui 50

`[IN COSTRUZIONE]`

```bash
claude-second-brain extract --batch _status/batch-YYYY-WW.json --target vault/clienti/
```

L'extractor processa ogni file:
- PDF testuale → estrazione testo, sintesi strutturata in `.md`
- PDF immagine → OCR via API, poi estrazione
- DOCX → conversione, estrazione strutturata
- XLSX (limitato): solo prime righe + dichiarazione di tipo, NON conversione integrale
- Email .eml: estrazione decisioni + allegati referenziati

Output per ogni file: una bozza `.md` con:
- Frontmatter (tipo, owner proposto, visibilità proposta, stato `bozza`)
- Path originale del file binario (link)
- Sintesi 5-10 righe
- Estrazione campi rilevanti per il tipo (es. per un contratto: parti, oggetto, durata, scadenza, importo)

`[MANUALE OGGI]`

Tu, batch più piccoli (10-20 file), trascini i file in chat con Claude e gli chiedi di estrarre. Ti rispondi con bozze `.md` che incolli nel vault al path giusto. Più lento, ma funziona.

### Martedì — Approvi il batch

`[IN COSTRUZIONE]`

```bash
claude-second-brain approve --batch _status/batch-YYYY-WW.json
```

Apre una UI testuale (TUI) o un report HTML in browser. Per ogni bozza:

| Stato | Tasti |
|---|---|
| **Approva** così com'è | `a` |
| **Approva con modifiche** (apri in editor) | `m` |
| **Rifiuta** (non entra nel vault) | `r` |
| **Chiedi al Custode** in call settimanale | `c` |
| **Salta** (decidi dopo) | `s` |

Le approvate vanno in `vault/clienti/<X>/` (o `fornitori/`, `commesse/`, a seconda della categoria proposta).

Le "chiedi Custode" finiscono in `vault/_pending/da-chiarire.md` con la motivazione del dubbio.

`[MANUALE OGGI]`

Stesso loop, fatto a mano. Tu apri ogni bozza, decidi, sposti nel vault. Tieni un foglio Google con stato di ogni file. Le "chiedi Custode" vanno in un'unica nota condivisa che porti in call settimanale.

### Martedì sera-mercoledì — Custode rivede ciò che è entrato

Il Custode apre Obsidian sul vault. Guarda i file `.md` nuovi della settimana. Per ogni file:

1. **Va bene**: lascia stare, niente da fare
2. **Frontmatter da correggere** (es. owner sbagliato, visibilità troppo aperta): corregge a mano
3. **Contenuto da integrare**: aggiunge informazioni che lui sa e che l'estrazione non ha catturato
4. **Promozione candidata**: nota in `vault/reparti/commerciale/_proposte-promozione.md` ("la decisione di non lavorare con clienti < 5k€/anno è ricorrente — promuovere a L1?")

Tempo Custode: 30-60 minuti tra martedì sera e mercoledì.

### Venerdì — Call settimanale

30 minuti. Custode + tu. Owner solo se serve sbloccare qualcosa.

Agenda fissa:

1. **Sintesi della settimana** (5 min) — quanto migrato, quanto rifiutato, quanto pending
2. **Risoluzione dei "chiedi Custode"** (15 min) — passa per le note in `_pending/da-chiarire.md`, decidete insieme. Le decisioni le scrivi tu in `vault/decisioni/`
3. **Promozioni proposte** (5 min) — il Custode mostra le note in `_proposte-promozione.md`. Decidete cosa promuovere a L2 (procedura) o candidare a L1 (azienda)
4. **Piano della settimana successiva** (5 min) — quale batch, quale criterio di selezione, quali sorgenti

### Dashboard `_status/` `[IN COSTRUZIONE]`

A regime, dentro `vault/_status/` vivono:

- `batch-YYYY-WW.json` — un file per batch, con tutte le decisioni prese
- `pipeline.md` — vista sintetica leggibile: x file scansionati, y estratti, z approvati, w pending
- `costi.md` — costo API Claude accumulato per cliente, aggiornato a ogni batch

Il Custode apre `pipeline.md` ogni mattina per vedere a che punto siamo.

---

## Cosa fare quando l'agente sbaglia

L'agente sbaglia. È normale. La supervisione serve a quello.

### Errore: categoria sbagliata

Sintomo: l'extractor ha messo `Offerta_RossiSrl_2024.pdf` in `vault/fornitori/rossi-srl/` invece che in `vault/clienti/rossi-srl/`.

Causa: il naming è ambiguo o l'extractor ha letto l'intestazione fiscale (Rossi Srl è venditore in quel documento, in altri è cliente).

Cosa fai: in Approve, premi `m`, sposti la bozza nel path giusto, **e aggiungi una riga in `vault/references/glossario.md`**: *"Rossi Srl = cliente storico, NON fornitore. Diffidare dei documenti dove appare come venditore (sono note di credito o rimborsi)."* Così il prossimo batch non rifa lo stesso errore.

### Errore: propone duplicati sbagliati

Sintomo: l'extractor crea `vault/clienti/rossi-srl/contratto-2024.md` e `vault/clienti/rossi/contratto-2024.md` (due slug diversi per lo stesso cliente).

Causa: nei file originali è scritto a volte "Rossi Srl", a volte "Rossi", a volte "ROSSI S.r.l.".

Cosa fai: stop al batch, apri `vault/references/persone.md` e `vault/references/glossario.md`, definisci la regola di slug ("Rossi Srl → `rossi-srl`, ROSSI S.r.l. → `rossi-srl`, evitare 'rossi' nudo"), riprocessi.

### Errore: non capisce un PDF

Sintomo: PDF di un contratto scannerizzato 15 anni fa, OCR fallisce, output dell'extractor è caratteri spazzatura.

Cosa fai: non perdere tempo a forzarlo. Marcalo come **DA CHIARIRE**, chiedi al Custode in call se il contratto serve davvero (spesso no, è già archiviato altrove). Se serve, il Custode lo OCR-a a mano con uno strumento dedicato (Adobe Acrobat, ABBYY) e ritrasmette il PDF testuale. Il tempo Custode su questo va contato.

### Errore: estrae troppo (rumore)

Sintomo: dall'extractor escono `.md` di 800 righe pieni di intestazioni, footer, numerazioni, disclaimer ripetuti.

Cosa fai: in Approve, premi `m`, riduci la bozza a 10-30 righe **essenziali** (chi, cosa, quando, decisione, link al binario). Poi nota in `vault/_audit/extraction-feedback.md` che il template di estrazione per quel tipo (es. "contratti") va stretto. Quando ne accumuli 3-5 esempi, scrivi una skill specifica o aggiorni i prompt dell'extractor.

### Errore: non capisce la lingua tecnica del settore

Sintomo: per un'officina meccanica, "DWG", "ISO 2768", "rugosità Ra 3.2" sono trattati come metadati spazzatura.

Cosa fai: aggiungi terminologia tecnica al `vault/references/glossario.md` PRIMA di lanciare il batch successivo. Il glossario va in contesto a ogni estrazione.

### Errore: il file è dentro un'email che è dentro una zip che è dentro un PDF

Sintomo: scappa, ma succede. Allegato in `.eml` salvato in `.zip` allegato a un altro `.pdf`. L'extractor sbaglia ad ogni livello.

Cosa fai: marcalo come **DA CHIARIRE**, non sprecare il batch. In call settimanale chiedi al Custode se serve. Se sì, lo estrae lui manualmente e ti consegna il file pulito.

---

## Quanto tempo realistico

### Ore tue (Valentino)

Per cliente medio (1 reparto pilota, ~200 file da migrare):

| Attività | Ore stimate |
|---|---|
| Setup degli scanner Lunedì (selezione sorgenti, criteri) | 1-2 h/sett × 2 sett = 2-4 h |
| Approvazione batch (50 bozze × 5 min/bozza media) | 4-5 h/sett × 2-4 batch = 8-20 h |
| Call settimanale con Custode | 0.5 h/sett × 2 sett = 1 h |
| Risoluzione errori, scrittura skill ad-hoc, follow-up | 2-3 h/sett × 2 sett = 4-6 h |
| **Totale Atto 2** | **15-30 ore** |

Più o meno coincide con la stima di 30-50 ore totali sui 3 atti del preventivo in [`01-cosa-vendi.md`](01-cosa-vendi.md).

### Ore Custode

| Attività | Ore stimate |
|---|---|
| Review settimanale dei file entrati | 1 h/sett × 2 sett = 2 h |
| Call settimanale | 0.5 h/sett × 2 sett = 1 h |
| Risposta a domande operative tue | 1 h/sett × 2 sett = 2 h |
| OCR/recupero file particolari (se serve) | variabile, fino a 2-3 h |
| **Totale Atto 2 Custode** | **5-8 ore** |

Conferma le 2-4 ore/settimana dichiarate nel pre-requisito di [`02-kickoff-checklist.md`](02-kickoff-checklist.md).

### Costo Claude API stimato

A regime, con Claude come motore di estrazione:

- 200 file medi × 50 KB testo equivalente input = 10 MB ≈ 2,5 M token input
- 200 bozze × 1.5 KB output ≈ 300 KB ≈ 75 K token output
- Più overhead di prompt strutturato, esempi few-shot, retry: × 2-3 di sicurezza

Stima totale per cliente: **20-60 € di API Claude**. Lo paghi tu, è incluso nel preventivo. Per casi grandi (1.000+ file, 4 reparti dal day 1) si può salire a 100-200 €. Sopra, rinegoziare.

---

## Privacy — cosa Claude vede, cosa no

Dichiarazione operativa che deve essere coerente con il `perimetro-privacy.md` firmato in Atto 1.

### Cosa Claude vede durante l'Atto 2

- **Sì**: i contenuti dei file delle sorgenti dichiarate nel perimetro (Drive `X`, NAS `Y`, casella email `Z`), letti tramite MCP attivati sul laptop del Custode
- **Sì**: gli output dell'estrazione (le bozze `.md`) passano via API Anthropic per essere generate
- **No**: cartelle escluse esplicitamente nel perimetro (HR, retribuzioni, dossier sensibili)
- **No**: i binari originali non vengono caricati interi su Anthropic. Solo il testo estratto e l'eventuale OCR. Per file con allegati binari riservati (es. immagini di documenti d'identità), si tratta come ARCHIVIO e non si estrae

### Dove vivono i dati

- I file originali restano sui sistemi del cliente. Mai copia
- Le bozze `.md` vivono nel vault del cliente. Il vault è sul laptop del Custode (e su backup interno aziendale, se ne fanno)
- Le richieste API a Claude seguono la retention policy di Anthropic (riferimento alla policy ufficiale)
- Lo `_status/` con i metadati dei batch resta nel vault, non condiviso

### Cosa fai tu con i dati del cliente

- Niente. Non li copi sul tuo laptop. Lavori in screen-share o via accesso remoto al laptop Custode
- Eccezione: i log di `_status/batch-YYYY-WW.json` (metadati, non contenuto dei file) li puoi tenere per debug; vanno cancellati a fine Atto 3
- Non riusi prompt o estrazioni del cliente A per il cliente B

---

## Definition of done dell'Atto 2

Per dichiarare chiuso l'Atto 2 (e quindi fissabile l'Atto 3) servono **tutti** questi punti:

- [ ] Reparto pilota ha **almeno 1 file MOC per ognuno dei top 10 oggetti vivi** (clienti / fornitori / commesse a seconda del reparto)
- [ ] Ogni MOC ha i **5 file della Regola 01-PMI** (`<slug>.md`, `CLAUDE.md`, `MEMORY.md`, `tasks.md`, `persone.md`)
- [ ] **Almeno 10 decisioni storiche** sono state codificate in `MEMORY.md` di reparto o di oggetto (raccolte in call settimanale dal Custode)
- [ ] La lista **DA CHIARIRE** è < 20 voci (le restanti verranno chiuse all'Atto 3)
- [ ] Il **costo API totale** è entro il budget (max 100 € per cliente medio, max 200 € per cliente grande)
- [ ] Il **Custode ha visto** almeno 2 cicli completi di approvazione (per essere autonomo dall'Atto 3)

---

## Anti-pattern dell'Atto 2

### Approvare in massa per finire prima

Sintomo: tu, sotto pressione, premi `a` (approva) a raffica senza leggere davvero. Risultato: nel vault entrano bozze sbagliate, il Custode all'Atto 3 trova il caos, l'handover salta.

Antidoto: se sei sotto pressione, riduci la dimensione del batch (25 invece di 50) e fai 4 batch invece di 2. Mai approvare senza leggere.

### Saltare le call settimanali

Sintomo: "questa settimana siamo entrambi presi, ci vediamo la prossima". Risultato: la lista DA CHIARIRE esplode, il Custode si demotiva.

Antidoto: la call settimanale è sacra. Se uno dei due non può, la fa l'altro da solo (15 min) e manda voicemail riepilogativa.

### Allargare il perimetro durante l'Atto 2

Sintomo: l'Owner, vedendo che funziona sul pilota, chiede di partire con altri 2 reparti subito.

Antidoto: scrivi e dici: *"Sì, ma in un Atto 2 separato dopo l'handover di questo. Adesso finiamo questo pulito."* Riusi i 3 atti come template per ogni reparto nuovo.

### Promesse al Custode che non si manterranno

Sintomo: in call dici al Custode "tranquillo, lo facciamo io e l'agente", poi non lo coinvolgi, lui arriva all'Atto 3 sentendosi spettatore.

Antidoto: il Custode deve **fare** il workflow almeno 2 volte sotto la tua guida prima della fine dell'Atto 2. Se non fa, non è formato.

---

## Documenti collegati

- [`02-kickoff-checklist.md`](02-kickoff-checklist.md) — i pre-requisiti dell'Atto 2 si decidono nell'Atto 1
- [`04-handover-checklist.md`](04-handover-checklist.md) — cosa fai per chiudere
- [`05-manuale-custode.md`](05-manuale-custode.md) — Fase 4 e 5 del manuale custode coprono lo stesso workflow dal lato cliente
- [`06-framework-pmi.md`](06-framework-pmi.md) — la struttura dei 6 layer di memoria spiega *dove* va ogni cosa estratta
