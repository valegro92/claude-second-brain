# Preventivo — Custodia

> Template di preventivo personalizzabile per ogni cliente.
> I campi tra `[ ]` sono placeholder da sostituire prima dell'invio.
> Esportabile in PDF via `pandoc preventivo-template.md -o preventivo.pdf` o copia/incolla in Word.

---

## Intestazione

**Da:**
Valentino Grossi
La Cassetta degli AI-trezzi
Via [INDIRIZZO]
[CAP] [CITTÀ] ([PROVINCIA])
P. IVA: [P.IVA VALENTINO]
C.F.: [CF VALENTINO]
PEC: [PEC]
email: valentino@cassettadegliaitrezzi.it *(placeholder)*
tel: +39 [TELEFONO]

**A:**
[NOME CLIENTE / RAGIONE SOCIALE]
[INDIRIZZO]
[CAP] [CITTÀ] ([PROVINCIA])
P. IVA: [P.IVA CLIENTE]
C.F.: [CF CLIENTE]
PEC: [PEC CLIENTE]
Cortese attenzione: [REFERENTE — nome, ruolo]

---

**Riferimento offerta:** OFF-[YYYY]-[NN]
**Data:** [GG / MMMM / AAAA]
**Validità offerta:** 30 giorni dalla data di emissione

---

## Oggetto

**Custodia — installazione wiki aziendale chiavi-in-mano per [NOME CLIENTE]**

Offerta per la costruzione di una wiki aziendale strutturata (vault Markdown) partendo dalle sorgenti documentali esistenti di [NOME CLIENTE], con formazione del Custode interno designato e consegna del manuale operativo.

> Nota commerciale: "Custodia" è il nome di lavoro del servizio. La denominazione contrattuale puntuale è "consulenza per la costruzione di wiki aziendale documentale strutturata mediante toolkit `claude-second-brain`".

---

## 1. Contesto

[NOME CLIENTE] è una [SETTORE — es. officina manifatturiera / studio tecnico / agenzia B2B] con sede a [CITTÀ], composta da [N] dipendenti distribuiti su [N SEDI] sede/i. Il patrimonio documentale è oggi distribuito tra:

- [es. Google Drive condiviso "Commerciale" — ~47 GB, ~12.400 file]
- [es. NAS Synology aziendale — ~240 GB, ~45.000 file]
- [es. casella Outlook `info@cliente.it` — ~14.000 mail]
- [es. cartelle locali su PC singoli — non perimetrate]

Il referente di progetto è **[REFERENTE — nome, ruolo]**. Il Custode designato è **[CUSTODE — nome, ruolo, ore/settimana dichiarate]**.

Reparto pilota concordato per la delivery: **[REPARTO PILOTA — es. Commerciale]**.

---

## 2. Servizi inclusi

La delivery è strutturata in **3 atti** distinti, per un periodo complessivo di 3-4 settimane dal kick-off all'handover.

### Atto 1 — Kick-off on-site (½ giornata, [DATA TENTATIVA])

**Presso:** sede di [NOME CLIENTE], [INDIRIZZO]
**Durata:** 4 ore consecutive
**Presenze obbligatorie:** Owner ([REFERENTE]) + Custode ([CUSTODE])
**Presenze consigliate:** 1-2 Editor del reparto pilota

**Attività:**
- Test di idoneità (4 sì obbligatori)
- Firma del perimetro privacy in presenza dell'Owner
- Wizard azienda: configurazione `references/` del vault (chi-siamo, organigramma, persone, brand voice, glossario)
- Connessione dei connettori MCP alle sorgenti dichiarate
- Inventario rapido delle sorgenti con priorità
- Definizione call settimanale dell'Atto 2 e calendar dell'Atto 3

**Deliverable:**
- Vault scheletro funzionante (file `references/` completi, scheletro `reparti/`)
- File `vault/references/perimetro-privacy.md` firmato e archiviato
- File `vault/_audit/sources.md` con priorità
- ADR-001 in `vault/MEMORY.md` (reparto pilota concordato)
- Mail riepilogativa a Owner + Custode

Dettaglio operativo: [`docs/02-kickoff-checklist.md`](../02-kickoff-checklist.md).

### Atto 2 — Scandagliamento supervisionato (10-12 giorni lavorativi, remoto)

**Modalità:** remoto, con call settimanale fissa di 30 minuti con il Custode
**Canale operativo:** [email / Slack / Teams condiviso — da concordare]

**Attività:**
- Scanner sulle sorgenti del reparto pilota, in batch da 50 documenti
- Extractor: produzione di bozze Markdown classificate (VIVO / DA CONSULTARE / ARCHIVIO / CESTINO / FUORI PERIMETRO)
- Approvazione batch giornaliera (Valentino) + review settimanale (Custode)
- Costruzione delle prime 100-200 schede strutturate (clienti, fornitori, commesse, SOP del reparto pilota)
- Codifica delle decisioni storiche in formato ADR

**Deliverable:**
- 100-200 documenti `.md` strutturati nel vault del reparto pilota
- Schede dei top 10 clienti / fornitori del reparto pilota complete (5 file Regola 01-PMI ciascuna)
- 3-8 SOP estratte e codificate
- Lista `_pending/da-chiarire.md` con voci aperte da risolvere in Atto 3
- 2 verbali call settimanale archiviati nel vault

Dettaglio operativo: [`docs/03-scandagliamento.md`](../03-scandagliamento.md).

### Atto 3 — Handover on-site (½ giornata, [DATA TENTATIVA])

**Presso:** sede di [NOME CLIENTE]
**Durata:** 4 ore consecutive
**Presenze obbligatorie:** Owner + Custode
**Presenze consigliate:** Custodi di reparto aggiuntivi se più di uno

**Attività:**
- Risoluzione delle voci accumulate in `_pending/da-chiarire.md`
- Training del Custode sui 3 rituali (giornaliero, settimanale, mensile) con esercizio pratico
- Primo rituale settimanale fatto insieme
- Mail di decommissioning ai colleghi del reparto pilota (Drive vecchio passa in sola lettura)
- Consegna del manuale custode stampato (2 copie) e firmato

**Deliverable:**
- Custode autonomo verificato sui 3 rituali (test pratico in presenza)
- Manuale custode ([`docs/05-manuale-custode.md`](../05-manuale-custode.md)) stampato e firmato in 2 copie
- Lettera di decommissioning inviata ai colleghi del reparto pilota
- ADR datato in `vault/MEMORY.md` del primo rituale settimanale ufficiale
- Calendar dei 3 check-up mensili gratuiti post-handover

Dettaglio operativo: [`docs/04-handover-checklist.md`](../04-handover-checklist.md).

### Post-handover — 3 check-up mensili gratuiti

3 sessioni remote di 1 ora ciascuna, a cadenza mensile per i 3 mesi successivi all'handover. Verifica adozione, risoluzione micro-blocchi, segnalazione scritta di eventuali derive di adozione.

---

## 3. Servizi esclusi

I seguenti elementi **non sono inclusi** in questo preventivo. Disponibili a quotazione separata:

| Esclusione | Note |
|---|---|
| **Licenze Claude** (Anthropic) | Il cliente sottoscrive autonomamente piani Free / Pro / Cowork in base al numero utenti |
| **Licenze Obsidian** | Gratuito per uso personale. Plug-in Sync opzionale (~50€ una tantum) se serve sincronizzazione tra dispositivi |
| **Connettori MCP custom** per sistemi proprietari non coperti dagli MCP standard (es. gestionali italiani TeamSystem/Zucchetti/Danea/Mexal) | Quotazione separata caso per caso |
| **Modalità on-premise** (modello AI locale, no cloud) | Disponibile in roadmap Step 3, non in v1 |
| **Migrazione di file binari nel vault** | Architettura: il vault contiene `.md` + link, mai copie di PDF/CAD/Excel. I binari restano sulle sorgenti originali |
| **Cambio dei processi aziendali** | Documentazione, non re-engineering. Per change management, possiamo segnalare consulenti specializzati |
| **Estensione ad altri reparti dopo l'handover** | Quotazione 2.000-4.000 € per reparto aggiuntivo |
| **Formazione individuale di Editor o Contributor** | Il manuale persone ([`docs/07-manuale-persone.md`](../07-manuale-persone.md)) è autoesplicativo. Sessioni dedicate disponibili a 600 €/sessione |

---

## 4. Tempi (calendario indicativo)

| Tappa | Quando | Durata |
|---|---|---|
| Firma contratto + acconto 50% | Entro [DATA] | — |
| Pre-kickoff (raccolta accessi, perimetro abbozzato) | [DATA] - [DATA] | 5-7 giorni |
| **Atto 1 — Kick-off on-site** | [DATA] | ½ giornata |
| **Atto 2 — Scandagliamento** | [DATA] - [DATA] | 10-12 giorni lavorativi |
| **Atto 3 — Handover on-site** | [DATA] | ½ giornata |
| Saldo 50% all'accettazione | Entro 7 gg dall'Atto 3 | — |
| Check-up mensile #1 | [DATA + 30 gg] | 1h remoto |
| Check-up mensile #2 | [DATA + 60 gg] | 1h remoto |
| Check-up mensile #3 | [DATA + 90 gg] | 1h remoto |

Date soggette a conferma dopo la firma. Lo slittamento di una settimana è tollerato per cause di forza maggiore (malattia, indisponibilità sale aziendali). Slittamenti maggiori comportano riprogrammazione formale.

---

## 5. Investimento

### Setup chiavi-in-mano (una tantum)

| Voce | Importo |
|---|---|
| **Delivery 3 atti** + 3 check-up mensili gratuiti | **€ [IMPORTO SETUP]** |

**Range applicabile**: da 8.500 € (entry) a 14.000 € (premium, cliente complesso). Importo proposto per [NOME CLIENTE]: **€ [IMPORTO]**, giustificato da:

- Dimensione: [N persone, N sedi]
- Sorgenti coinvolte: [N sorgenti]
- Volume stimato: [GB totali]
- Reparti dal day 1: [N reparti]
- Complessità Custode: [es. Custode già esperto / Custode da formare / più Custodi coinvolti]

### Manutenzione opzionale (post-handover, contratto annuale)

| Piano | Importo | Cosa include |
|---|---|---|
| **Light** | € 700 / mese | 1.5h/mese di presidio: 1 call mensile con Custode, micro-fix, aggiornamenti del toolkit |
| **Premium** | € 1.500 / mese | 4h/mese: tutto il Light + evolutive sulle skill + onboarding nuovi colleghi + aggiunta nuovi tipi di oggetto |

Fatturazione trimestrale anticipata. Disdetta possibile con preavviso di 30 giorni. **Non vincolante alla firma** — decisione del cliente a chiusura dell'handover.

### Voci aggiuntive (eventuali, da concordare a parte)

| Voce | Range |
|---|---|
| Aggiunta nuovo reparto post-handover | 2.000 - 4.000 € a reparto |
| Connettore MCP custom (per gestionale o sistema proprietario) | da 1.500 € a 5.000 € a integrazione |
| Formazione dedicata di Editor / Contributor | 600 € a sessione (½ giornata) |
| Trasferta aggiuntiva oltre i 2 on-site previsti | 600 € a trasferta (a/r + giornata) |

**Tutti gli importi sono IVA esclusa.** IVA 22% sarà applicata in fattura se applicabile.

---

## 6. Modalità di pagamento

| Tranche | Importo | Quando |
|---|---|---|
| Acconto 50% | € [50% SETUP] + IVA | Alla firma del contratto |
| Saldo 50% | € [50% SETUP] + IVA | All'accettazione positiva dell'handover (Atto 3), entro 7 giorni |

Per importi superiori a 10.000 € il cliente può richiedere un piano a 3 tranche: 30% firma / 40% inizio Atto 2 / 30% accettazione handover.

**Modalità di pagamento accettate:**
- Bonifico bancario su IBAN [IBAN VALENTINO]
- Termini di pagamento: 30 giorni data fattura

**Fatturazione elettronica**: PA / FE su [CODICE DESTINATARIO] o PEC [PEC CLIENTE].

---

## 7. Validità offerta

La presente offerta è valida **30 giorni dalla data di emissione** ([DATA]).

Oltre tale termine, gli importi e le tempistiche devono essere riconfermati. La validità può essere prorogata su richiesta scritta del Cliente.

---

## 8. Condizioni accessorie

- **Accettazione**: per accettazione, restituire copia firmata di questo preventivo + del contratto allegato + del DPA allegato, via PEC o email a `valentino@cassettadegliaitrezzi.it`.
- **Trattamento dati personali**: regolato dal DPA in allegato (ex art. 28 GDPR).
- **Limitazione di responsabilità**: cap a 1x il corrispettivo pagato per la delivery (art. 9 del contratto allegato).
- **Foro competente**: foro di [CITTÀ VALENTINO]. Legge applicabile: italiana.
- **Eventuali agevolazioni fiscali** (es. credito d'imposta Industria 4.0/5.0, voucher digitalizzazione): da verificare a cura del commercialista del Cliente. Non costituiscono oggetto della consulenza Valentino.

---

## 9. Allegati

1. **Contratto di delivery** ([`contratto-skeleton.md`](contratto-skeleton.md)) — bozza tecnica, da validare con avvocato di parte
2. **DPA — Data Processing Agreement** ([allegato A al contratto]) — ex art. 28 GDPR
3. **Lista sub-responsabili** ([allegato B al contratto]) — Anthropic + provider MCP eventuali
4. **Perimetro privacy** ([allegato C al contratto]) — da compilare insieme in Atto 1
5. **SLA dettagliato** ([allegato D al contratto])
6. **Listino servizi opzionali** ([allegato E al contratto]) — manutenzione, aggiunta reparti, integrazioni custom

---

## 10. Per accettare

Per procedere:

1. **Firma per accettazione** sotto questa pagina e restituisci copia via PEC entro [DATA + 30 gg]
2. Riceverai entro 24h lavorative la conferma di ricezione + calendar invite per l'Atto 1
3. Bonifico dell'acconto su [IBAN] entro 7 giorni dalla firma
4. Avvio formale dei lavori coincidente con accredito acconto

Per chiarimenti prima della firma: chiamata o videochiamata di 30 minuti senza impegno, scrivimi a `valentino@cassettadegliaitrezzi.it` per fissare uno slot.

---

**Firma per accettazione**

Luogo: ____________________________ Data: ____________________________

[NOME CLIENTE]
Per accettazione integrale dei termini, comprese le clausole di limitazione della responsabilità.

____________________________________________
([REFERENTE], in qualità di [RUOLO])

Timbro azienda:

---

*Documento generato a partire dal template `docs/commerciale/preventivo-template.md` del toolkit Custodia. Versione 1.0 — [DATA EMISSIONE].*
