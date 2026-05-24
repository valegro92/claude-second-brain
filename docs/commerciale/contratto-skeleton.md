# Contratto di delivery — Custodia

> **DISCLAIMER IMPORTANTE.** Questo documento è una **bozza tecnica** redatta a partire dallo skeleton del brief interno [`_brief/06-cost-and-risk.md`](../../\_brief/06-cost-and-risk.md), sezione B.5. **Va validato da un avvocato GDPR italiano** prima della firma con qualsiasi cliente. In particolare devono essere verificate: clausole di limitazione di responsabilità (art. 1229 c.c.), DPA ex art. 28 GDPR, disciplina del recesso, IP e licenza del toolkit. Costo orientativo di una revisione legale completa: 800 - 1.500 € una tantum. Per il primo cliente, **non firmare senza** revisione legale.

---

## CONTRATTO DI CONSULENZA PER LA COSTRUZIONE DI WIKI AZIENDALE DOCUMENTALE STRUTTURATA

**TRA**

**Valentino Grossi**, in proprio / titolare della ditta individuale "[RAGIONE SOCIALE VALENTINO]", con sede legale in [INDIRIZZO VALENTINO], P. IVA [P.IVA VALENTINO], C.F. [CF VALENTINO], PEC [PEC VALENTINO], di seguito denominato "**il Consulente**";

**E**

**[NOME CLIENTE]**, con sede legale in [INDIRIZZO CLIENTE], P. IVA [P.IVA CLIENTE], C.F. [CF CLIENTE], PEC [PEC CLIENTE], in persona del suo legale rappresentante [NOME LEGALE RAPPRESENTANTE], nato a [LUOGO] il [DATA], C.F. [CF], di seguito denominato "**il Cliente**";

congiuntamente le "**Parti**".

---

## Premesse

a) Il Consulente svolge attività professionale di consulenza in materia di organizzazione documentale aziendale e di assistenza nell'adozione di strumenti basati su modelli linguistici di intelligenza artificiale, operando con il toolkit open source `claude-second-brain` (di seguito "**il Toolkit**") di sua proprietà;

b) Il Cliente è una [SETTORE] con sede operativa a [CITTÀ], composta da [N] dipendenti, e necessita di organizzare il proprio patrimonio documentale oggi distribuito tra diverse sorgenti (Drive, NAS, posta elettronica, sistemi gestionali);

c) Il Cliente ha valutato favorevolmente la proposta del Consulente (rif. offerta n. **OFF-[YYYY]-[NN]** del **[DATA]**, allegata) e intende affidargli la costruzione di una wiki aziendale documentale strutturata (di seguito "**il Vault**"), secondo la metodologia in 3 atti descritta nei materiali tecnici del Consulente;

d) Le Parti hanno verificato la compatibilità del trattamento dati con la normativa GDPR e hanno predisposto un Data Processing Agreement separato (Allegato A), che costituisce parte integrante del presente contratto;

tutto quanto premesso, le Parti convengono e stipulano quanto segue.

---

## Art. 1 — Oggetto della prestazione

1.1 Il Cliente affida al Consulente, che accetta, la prestazione di consulenza finalizzata alla costruzione di una wiki aziendale documentale strutturata (Vault) a partire dalle sorgenti documentali del Cliente, mediante l'utilizzo del Toolkit.

1.2 La prestazione include:
- (a) la configurazione del Vault sui sistemi del Cliente;
- (b) lo scandagliamento supervisionato delle sorgenti dichiarate dal Cliente con produzione di schede strutturate in formato Markdown;
- (c) la formazione di una persona designata dal Cliente al ruolo di "Custode" del Vault;
- (d) la consegna del manuale operativo del Custode;
- (e) 3 sessioni di follow-up post-handover, di durata oraria, a cadenza mensile.

1.3 La prestazione è **di mezzi e non di risultato** per quanto attiene all'adozione del Vault da parte del personale del Cliente successivamente all'handover (vedi Art. 9).

---

## Art. 2 — Modalità di esecuzione: i 3 Atti

La prestazione si articola in 3 atti consecutivi, secondo la metodologia descritta nei documenti tecnici [`docs/02-kickoff-checklist.md`](../02-kickoff-checklist.md), [`docs/03-scandagliamento.md`](../03-scandagliamento.md), [`docs/04-handover-checklist.md`](../04-handover-checklist.md), che formano parte integrante (per riferimento) del presente contratto:

**Atto 1 — Kick-off**: ½ giornata on-site presso la sede del Cliente, in data **[DATA]**, durata 4 ore. Output: Vault scheletro, perimetro privacy firmato, configurazione connettori, inventario sorgenti.

**Atto 2 — Scandagliamento supervisionato**: 10-12 giorni lavorativi, prevalentemente remoto, con call settimanale fissa di 30 minuti con il Custode. Periodo: dal **[DATA]** al **[DATA]**. Output: 100-200 documenti strutturati nel Vault per il reparto pilota.

**Atto 3 — Handover**: ½ giornata on-site presso la sede del Cliente, in data **[DATA]**, durata 4 ore. Output: Custode formato sui 3 rituali, manuale custode consegnato e firmato, mail di decommissioning inviata.

2.2 Eventuali slittamenti delle date sopra indicate, dovuti a cause di forza maggiore (malattia, indisponibilità sale, indisponibilità accessi tecnici), sono ammessi entro 7 giorni di calendario senza penali. Slittamenti superiori richiedono riprogrammazione formale concordata via PEC.

---

## Art. 3 — Output e criteri di accettazione

3.1 Al termine dell'Atto 3 il Cliente riceve i seguenti output, oggetto di collaudo formale:

- (a) Il Vault popolato con almeno 100 schede strutturate per il reparto pilota concordato;
- (b) Il file `vault/references/persone.md` completo, con almeno tutte le persone del reparto pilota e i ruoli wiki assegnati;
- (c) Il file `vault/MEMORY.md` con almeno 3 ADR (Architectural Decision Records) datati;
- (d) Le schede dei top 10 clienti / fornitori del reparto pilota, ciascuna conforme alla Regola 01-PMI (5 file: MOC, CLAUDE.md, MEMORY.md, tasks.md, persone.md);
- (e) Il manuale del Custode ([`docs/05-manuale-custode.md`](../05-manuale-custode.md)) consegnato in 2 copie cartacee firmate dalle Parti;
- (f) La dimostrazione pratica, in presenza, dell'esecuzione autonoma dei 3 rituali (giornaliero, settimanale, mensile) da parte del Custode designato;
- (g) La mail di decommissioning inviata ai colleghi del reparto pilota.

3.2 **Procedura di collaudo**: al termine dell'Atto 3, le Parti compilano congiuntamente un **verbale di accettazione** (modello fornito dal Consulente), che ciascuna Parte sottoscrive. La sottoscrizione del verbale costituisce **accettazione tacita** degli output sopra elencati.

3.3 Eventuali rilievi del Cliente sugli output devono essere comunicati per iscritto entro **7 giorni** dalla data di firma del verbale di accettazione. Decorso tale termine senza rilievi, l'accettazione si intende definitiva.

3.4 In caso di rilievi tempestivi, il Consulente si impegna a porre rimedio entro **15 giorni lavorativi**, senza costi aggiuntivi per il Cliente, limitatamente a non conformità documentate rispetto agli output di cui al punto 3.1.

---

## Art. 4 — Obblighi del Cliente

4.1 Il Cliente si obbliga a:

- (a) **Designare un Custode** con nome e cognome, in persona di **[CUSTODE — nome, ruolo]**, garantendone la disponibilità di **3-5 ore settimanali** per i 3 mesi successivi all'handover. La sostituzione del Custode nel corso della delivery comporta diritto del Consulente a un'integrazione di **800 €** + IVA per onboarding del sostituto;
- (b) **Garantire la presenza dell'Owner** (legale rappresentante o suo delegato con poteri di firma) nelle sessioni on-site di Atto 1 e Atto 3, per il tempo richiesto dalle checklist allegate;
- (c) **Mettere a disposizione gli accessi** alle sorgenti dichiarate (Google Workspace, Microsoft 365, NAS, email) con permessi di sola lettura, almeno **7 giorni** prima della data di Atto 1;
- (d) **Approvare per iscritto il perimetro privacy** in Atto 1, sottoscritto dall'Owner. Modifiche successive al perimetro richiedono nuovo accordo scritto;
- (e) **Fornire al Consulente** organigramma, lista persone con ruoli, breve descrizione dei reparti e del reparto pilota concordato, almeno **5 giorni** prima dell'Atto 1;
- (f) **Garantire una connessione internet stabile** (banda minima 20 Mbps simmetrici) e una sala riunioni con proiettore/TV per le sessioni on-site;
- (g) **Rispondere entro 48h lavorative** alle richieste di chiarimento del Consulente durante l'Atto 2;
- (h) **Mantenere la riservatezza** sui materiali, prompt, skill e codice del Toolkit consegnati dal Consulente, ai sensi dell'Art. 7.

4.2 Il mancato rispetto degli obblighi di cui al punto 4.1 lett. (a), (b), (d) costituisce **causa di sospensione della prestazione** da parte del Consulente, con diritto alla riprogrammazione e al rimborso delle eventuali spese vive sostenute.

---

## Art. 5 — Trattamento dei dati personali

5.1 Le Parti riconoscono che la prestazione comporta il trattamento di dati personali da parte del Consulente per conto del Cliente.

5.2 Ai sensi e per gli effetti dell'art. 28 del Regolamento UE 2016/679 (GDPR), le Parti sottoscrivono congiuntamente un **Data Processing Agreement (DPA)**, allegato sub **A** al presente contratto, che ne forma parte integrante.

5.3 Le Parti dichiarano:
- il **Cliente** assume la qualifica di **Titolare del trattamento**;
- il **Consulente** assume la qualifica di **Responsabile del trattamento** ex art. 28 GDPR;
- **Anthropic PBC** (fornitore dell'API Claude utilizzata dal Toolkit) è autorizzata quale **sub-responsabile**, secondo la lista mantenuta nell'Allegato B.

5.4 Il Cliente garantisce di avere **informato i propri interessati** (dipendenti, clienti, fornitori) circa il trattamento dei loro dati personali da parte di fornitori esterni per finalità di organizzazione documentale, e di avere **aggiornato il proprio Registro dei trattamenti**.

5.5 Il Consulente si impegna a fornire al Cliente, su richiesta, evidenza delle misure di sicurezza adottate (cifratura del portatile, gestione accessi, log) e a notificare per iscritto al Cliente, entro **24 ore lavorative**, qualsiasi data breach di cui venga a conoscenza riguardante i dati del Cliente.

5.6 Al termine della prestazione, e comunque non oltre **30 giorni** dall'accettazione finale, il Consulente procede alla **cancellazione documentata** di tutti i dati del Cliente dai propri sistemi (worktree locali, eventuale storage temporaneo cloud, richiesta di flush della cache Anthropic), inviando al Cliente attestazione scritta dell'avvenuta cancellazione.

---

## Art. 6 — Riservatezza e NDA reciproco

6.1 Le Parti si impegnano reciprocamente a **mantenere strettamente riservate** tutte le informazioni di carattere tecnico, commerciale, organizzativo e personale di cui vengano a conoscenza in occasione del presente contratto.

6.2 L'obbligo di riservatezza vincola le Parti per **5 anni** successivi alla cessazione del rapporto contrattuale.

6.3 **Eccezioni standard**: l'obbligo non si applica a informazioni (a) di pubblico dominio, (b) ottenute lecitamente da terzi senza vincolo di riservatezza, (c) sviluppate autonomamente da una Parte senza utilizzo di informazioni riservate dell'altra, (d) la cui divulgazione sia imposta da provvedimento giudiziario o autorità amministrativa competente.

6.4 La violazione dell'obbligo di riservatezza comporta il diritto della Parte non inadempiente al risarcimento del danno, salvo prova di danno maggiore.

---

## Art. 7 — Corrispettivi e fatturazione

7.1 Il corrispettivo complessivo per la prestazione è pari a **€ [IMPORTO SETUP]** ([IMPORTO IN LETTERE]), oltre IVA di legge.

7.2 Le **modalità di pagamento** sono le seguenti:

| Tranche | Importo | Quando |
|---|---|---|
| Acconto 50% | € [50%] + IVA | Alla firma del contratto |
| Saldo 50% | € [50%] + IVA | Entro 7 giorni dalla firma del verbale di accettazione (Art. 3.2) |

7.3 Per importi superiori a 10.000 € il Cliente può richiedere un piano a 3 tranche: 30% firma / 40% inizio Atto 2 / 30% accettazione handover.

7.4 **Modalità di pagamento**: bonifico bancario su IBAN **[IBAN VALENTINO]**, termini 30 giorni data fattura. Fatturazione elettronica via SdI su codice destinatario **[CODICE SDI CLIENTE]** o PEC **[PEC CLIENTE]**.

7.5 **Spese vive** (trasferte, vitto, materiale stampato per il manuale custode): comprese nel corrispettivo per le 2 trasferte previste (Atto 1 e Atto 3) entro un raggio di 200 km dalla sede del Consulente. Trasferte oltre tale raggio o aggiuntive sono fatturate a parte secondo il listino allegato (Allegato E).

7.6 In caso di ritardo nel pagamento oltre i 30 giorni dalla scadenza, si applicano gli interessi di mora ex D.Lgs. 231/2002.

---

## Art. 8 — Manutenzione opzionale post-handover

8.1 Il Cliente, al termine della delivery, può sottoscrivere un **contratto separato di manutenzione**, alle condizioni economiche e operative descritte nell'Allegato E (Listino servizi opzionali).

8.2 La manutenzione **non è obbligatoria**. Il rifiuto della manutenzione non costituisce inadempimento contrattuale.

8.3 I 3 check-up mensili gratuiti di cui all'Art. 1.2 lett. (e) sono **inclusi nel corrispettivo della delivery** e prescindono dalla sottoscrizione della manutenzione.

---

## Art. 9 — Limitazioni di responsabilità

9.1 Il Consulente garantisce l'idoneità degli output al momento della consegna (Art. 3). Il Consulente **non garantisce**:
- (a) il livello di adozione del Vault da parte del personale del Cliente successivamente all'handover (responsabilità del Cliente attraverso il Custode designato);
- (b) il ROI economico della prestazione, misurato in qualunque modo;
- (c) la continuità a tempo indeterminato dei servizi di Anthropic PBC (o di altri sub-fornitori), né il mantenimento delle condizioni economiche del medesimo.

9.2 **Cap di responsabilità**: la responsabilità complessiva del Consulente, a qualsiasi titolo, è limitata a un importo pari al **corrispettivo effettivamente pagato dal Cliente** per la prestazione (Art. 7.1).

9.3 **Esclusioni**: il Consulente non risponde in alcun caso di (a) danni indiretti, (b) perdita di chance, (c) perdita di reputazione, (d) danni cagionati a terzi del Cliente, (e) perdita di dati derivante dall'uso del Vault da parte di terzi successivamente all'handover.

9.4 Le limitazioni di cui ai commi precedenti **non si applicano** in caso di **dolo o colpa grave** del Consulente, conformemente all'art. 1229 c.c.

9.5 Il Consulente dichiara di essere coperto da **polizza di Responsabilità Civile professionale** con massimale di almeno € [MASSIMALE] (copia disponibile su richiesta).

---

## Art. 10 — Proprietà intellettuale

10.1 **Il Vault generato** in esecuzione del presente contratto è di esclusiva proprietà del **Cliente**, che ne acquisisce tutti i diritti di utilizzo, modifica e disposizione a tempo indeterminato.

10.2 **Il Toolkit** (componente software composto da skill, prompt, codice MCP, framework, manualistica) rimane di esclusiva proprietà del **Consulente** ed è concesso al Cliente in **licenza d'uso non esclusiva, perpetua, gratuita, non trasferibile** per il solo scopo di utilizzo e manutenzione del Vault generato.

10.3 Il Cliente non potrà **rivendere, sub-licenziare o distribuire a terzi** il Toolkit, in tutto o in parte. La pubblicazione open source del Toolkit, qualora intervenisse, sarà disciplinata dalla licenza scelta dal Consulente.

10.4 Le **bozze, i template e i pattern di scrittura** generati durante la delivery sono parte del Toolkit. Il Cliente può utilizzarli liberamente all'interno del Vault, ma non costituiscono lavoro su misura di sua esclusiva proprietà.

10.5 Il Consulente potrà utilizzare il rapporto con il Cliente come **referenza commerciale** (logo, nome, breve descrizione del progetto) previa autorizzazione scritta del Cliente, da rilasciarsi successivamente alla chiusura positiva dell'handover.

---

## Art. 11 — Garanzie e SLA

11.1 Il Consulente garantisce la **conformità degli output** ai criteri di accettazione di cui all'Art. 3.1 al momento della consegna.

11.2 Per i **30 giorni successivi all'handover**, il Consulente garantisce la correzione gratuita di non conformità tempestivamente segnalate, secondo i tempi di risposta dell'SLA (Allegato D), che si riassumono qui:

| Evento | Tempo di risposta |
|---|---|
| Blocco totale (Vault inaccessibile, errore critico) | 8 ore lavorative |
| Bug bloccante in una funzionalità del Toolkit | 24 ore lavorative |
| Domanda non urgente del Custode | 48 ore lavorative |

11.3 Lavorativi = lunedì-venerdì, 9-18, escluso agosto (1-31) e festivi nazionali.

11.4 Dopo i 30 giorni, l'SLA si applica solo se sottoscritto il contratto di manutenzione (Art. 8).

---

## Art. 12 — Subappalto e collaboratori

12.1 Il Consulente potrà avvalersi di **collaboratori esterni** per l'esecuzione della prestazione, garantendo che gli stessi siano vincolati da accordi di riservatezza equivalenti a quelli del presente contratto.

12.2 L'utilizzo di collaboratori sarà **comunicato al Cliente** con preavviso scritto di almeno 7 giorni, con indicazione del nominativo e del ruolo del collaboratore.

12.3 Resta in ogni caso ferma la responsabilità diretta del Consulente per l'operato dei propri collaboratori.

---

## Art. 13 — Risoluzione e recesso

13.1 **Recesso del Cliente**: il Cliente può recedere dal contratto in qualsiasi momento, con comunicazione scritta via PEC, riconoscendo al Consulente:
- l'importo dell'acconto già versato (non rimborsabile);
- il **corrispettivo delle ore effettivamente svolte** fino al momento del recesso, calcolate a 80 €/ora sulla base del log lavori del Consulente.

13.2 **Recesso del Consulente**: il Consulente può recedere solo per giusta causa (es. impossibilità sopravvenuta, gravi inadempimenti del Cliente non sanati nei termini), rimborsando in tal caso al Cliente l'acconto già versato al netto delle ore effettivamente svolte.

13.3 **Risoluzione per inadempimento** ex art. 1456 c.c.: il contratto si risolve di diritto, mediante semplice dichiarazione scritta della Parte non inadempiente, in caso di:
- mancato pagamento di una tranche oltre 60 giorni dalla scadenza;
- violazione grave dell'obbligo di riservatezza (Art. 6);
- mancata designazione del Custode (Art. 4.1 lett. a) entro 14 giorni dalla firma.

---

## Art. 14 — Comunicazioni

14.1 Tutte le comunicazioni ufficiali tra le Parti avvengono via **PEC** agli indirizzi indicati in epigrafe.

14.2 Comunicazioni operative non vincolanti (richieste tecniche, calendar invite, allegati di lavoro) possono avvenire via email, all'indirizzo `valentino@cassettadegliaitrezzi.it` *(placeholder)* per il Consulente e a `[EMAIL OPERATIVA CLIENTE]` per il Cliente.

---

## Art. 15 — Foro competente, legge applicabile, miscellanea

15.1 Il presente contratto è regolato dalla **legge italiana**.

15.2 Per ogni controversia relativa all'interpretazione, esecuzione o risoluzione del presente contratto è competente in via esclusiva il **Foro di [CITTÀ VALENTINO]**, salva la facoltà del consumatore qualora il Cliente rientri in tale categoria (non applicabile ai rapporti B2B oggetto di questo modello).

15.3 Eventuali **modifiche o integrazioni** al presente contratto devono essere concordate per iscritto tra le Parti, a pena di nullità.

15.4 La eventuale **invalidità di una singola clausola** non comporta invalidità dell'intero contratto, salvo che la clausola invalida risulti essenziale per la conclusione del contratto.

15.5 Il presente contratto è composto da **15 articoli** e da **5 allegati** che ne formano parte integrante.

---

## Allegati

- **Allegato A** — Data Processing Agreement (DPA) ex art. 28 GDPR
- **Allegato B** — Lista sub-responsabili (Anthropic PBC e altri provider MCP)
- **Allegato C** — Perimetro privacy (compilato congiuntamente in Atto 1)
- **Allegato D** — SLA di dettaglio (tempi di risposta, esclusioni, definizioni)
- **Allegato E** — Listino servizi opzionali (manutenzione, aggiunte, integrazioni custom)

> Gli Allegati A, B, D, E sono predisposti in template separati dal Consulente. L'Allegato C è compilato congiuntamente in Atto 1 e allegato successivamente al contratto firmato.

---

## Sottoscrizione

Letto, approvato e sottoscritto.

**Luogo e data**: ___________________________, ___________________________

**Il Consulente**
Valentino Grossi

____________________________________________

**Il Cliente**
[NOME CLIENTE], in persona di [NOME LEGALE RAPPRESENTANTE]

____________________________________________

---

### Approvazione specifica delle clausole onerose ex artt. 1341 e 1342 c.c.

Il Cliente, dopo averle attentamente lette e valutate, **approva specificamente** le seguenti clausole del presente contratto, in quanto comportano limitazioni di responsabilità o deroghe alla normativa generale:

- Art. 2.2 (slittamento date)
- Art. 4.1 lett. (a) (integrazione per sostituzione Custode)
- Art. 4.2 (sospensione della prestazione)
- Art. 9 (limitazioni di responsabilità, cap, esclusioni)
- Art. 10 (proprietà intellettuale del Toolkit)
- Art. 11 (perimetro garanzie)
- Art. 13 (recesso e risoluzione)
- Art. 15.2 (foro competente esclusivo)

**Luogo e data**: ___________________________, ___________________________

**Il Cliente**
____________________________________________

---

*Bozza tecnica versione 0.1 — da revisionare obbligatoriamente con avvocato GDPR italiano prima della prima firma. Riferimento interno: [`_brief/06-cost-and-risk.md`](../../\_brief/06-cost-and-risk.md) sezioni B.1, B.4, B.5.*
