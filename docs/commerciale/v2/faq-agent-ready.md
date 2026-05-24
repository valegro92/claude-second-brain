# FAQ — Custodia v2 Agent-Ready

Domande prevedibili da imprenditori e responsabili che stanno valutando il servizio.

---

## 1. I miei dati dove vanno a finire?

Dipende dalla modalità che scegliamo insieme all'Atto 1. Sono due, intercambiabili, e producono lo stesso vault.

**Cloud (default).** Durante lo scandagliamento i contenuti dei vostri file passano attraverso le API di Anthropic (Claude) per essere letti e strutturati. Anthropic gestisce l'elaborazione su infrastruttura EU, ha firmato le clausole contrattuali standard UE (SCC) e nel suo DPA si impegna a non usare i vostri contenuti per addestrare modelli. I dati transitano, non si fermano: dopo la delivery vengono cancellati dalle code di elaborazione.

**Sovrana.** Se preferite che durante lo scandagliamento tutto resti sotto giurisdizione italiana, usiamo un LLM ospitato su server dedicato presso un provider di inferenza sovrana italiano/UE. Niente passaggi fuori dall'UE, server dedicato al vostro progetto. Comporta +€2-4K di setup e 2-3 settimane di lead time aggiuntive.

In entrambi i casi il vault finale resta sui vostri sistemi — Drive, NAS o server interno — e noi non teniamo copie. Le cartelle sensibili (HR, legale, dati dipendenti) le escludiamo prima di partire: lo formalizziamo nel kick-off.

---

## 2. GDPR — è a posto? Cosa devo firmare?

Sì, la struttura legale è in ordine. Voi siete **Titolari del trattamento**, io sono **Responsabile esterno** ai sensi dell'art. 28 GDPR. Firmiamo un DPA (accordo sul trattamento dei dati) prima di iniziare il lavoro. Nel DPA sono dichiarati: perimetro dei dati trattati, sub-responsabili (Anthropic), tempi di cancellazione, misure di sicurezza. Alla fine della delivery invio una lettera di attestazione di cancellazione. Ho uno schema di contratto e DPA già pronti — per il primo contratto vi consiglio di farlo rileggere a un vostro consulente legale (costo orientativo: 1.000-1.500 €), per i successivi il testo è già rodato.

---

## 3. E se cambio fornitore? Resto incastrato con voi?

No. Il vault è una cartella di file `.md` in testo puro sul vostro Drive o NAS. Obsidian, che usate per visualizzarlo, è gratuito e gira su Windows, Mac e Linux. Se domani decidete di non lavorare più con me, avete tutto in mano: il vault, il manuale del Custode, i prompt. Potete continuare da soli, affidare la manutenzione a qualcun altro, o smettere del tutto — i file restano leggibili da qualunque editor di testo. Non c'è nessuna piattaforma proprietaria da cui dipendere.

---

## 4. Quanto serve il Custode interno davvero? Non ho una persona libera 4 ore/settimana

È la condizione che guardiamo per prima nelle nostre call. Se non c'è una persona disponibile, non accettiamo il lavoro — non per rigidità, ma perché l'esperienza ci dice che senza Custode il vault si ferma in sei settimane. Il Custode non deve essere un tecnico: di solito è l'IT/Office manager, la segreteria di direzione, o un commerciale senior con voglia di ordine. Il carico è 3-4 ore/settimana per i primi tre mesi, poi scende a 2-3 ore/settimana a regime. È una persona che smette di fare altro? No. È una persona che inizia a farlo in modo strutturato anziché sparso. Se la risorsa c'è ma è al 90% del carico, parliamone: a volte basta ridefinire il perimetro iniziale del vault.

---

## 5. Cosa succede se l'agente sbaglia e manda una risposta sbagliata al cliente?

L'agente non invia mai direttamente. Prepara una bozza che il commerciale legge, modifica se serve, e poi invia con il suo account. Il flusso è sempre: agente prepara → commerciale rilegge → commerciale invia. È lo stesso che fareste con uno stagista bravo: non gli date le credenziali per rispondere da soli. Detto questo, l'agente commette errori, soprattutto nelle prime settimane — può confondere date, citare condizioni superate, fraintendere richieste ambigue. Per questo nel vault esistono campi di "stato scheda" e "ultima verifica": il Custode tiene aggiornate le schede dei clienti più attivi, e più il dato è preciso, più la bozza è affidabile. L'obiettivo non è sostituire il giudizio del commerciale, è togliergli il lavoro di ricerca.

---

## 6. Funziona col mio gestionale (TeamSystem / Fatture in Cloud / Zucchetti / Passepartout)?

Dipende da cosa intendete per "funziona". Il vault non si integra direttamente con i gestionali italiani in questa versione: quei sistemi non espongono connettori standard e le integrazioni custom uscirebbero dal budget del setup. Quello che facciamo è lavorare attorno a loro: se esportate CSV con l'estratto ordini o lo storico fatturazione, possiamo importarlo nel vault e strutturarlo. Il flusso bidirezionale — vault che scrive nel gestionale o gestionale che aggiorna automaticamente il vault — lo affronteremo come progetto separato solo se più clienti lo chiedono contemporaneamente. Lo dichiariamo esplicitamente prima di firmare, senza sorprese.

---

## 7. Quanto costa l'AI mensilmente dopo? Tipo i token di Claude o ChatGPT?

Il costo dei token è vostro, non mio, e dipende dall'uso che fate dell'agente. Per dare un'idea concreta: un commerciale che usa l'agente per preparare 10-15 risposte al giorno spende circa 5-15 € al mese su Claude Pro (piano da 20 €/mese tutto incluso) o meno di 5 € in token API diretti se l'utilizzo è moderato. Non è un costo rilevante rispetto al setup. Se invece volete una stima precisa basata sui vostri volumi, ve la preparo durante la call di scoperta una volta capito il numero di clienti attivi e la frequenza delle interazioni.

---

## 8. Quanto ci mettete davvero — 4 settimane è realistico?

Dipende da quante sorgenti ci sono e da quanto è disponibile il Custode. Nelle aziende dove il Custode è presente e reattivo, e le sorgenti sono Google Drive + un NAS ben organizzato, 4 settimane sono realistiche. Se avete tre NAS storici mai bonificati, 15 anni di email in PST e nessuno disponibile per la revisione, ci vogliono 6-7 settimane. Nel preventivo dichiariamo sempre la stima con il range e le assunzioni su cui si basa. Se durante il lavoro emerge un volume molto superiore a quello dichiarato, ne parliamo prima di procedere — non aggiungiamo settimane in silenzio.

---

## 9. Cosa fa Custodia che non fa già Microsoft Copilot / ChatGPT Enterprise / SharePoint AI?

Quelli funzionano bene quando i vostri dati sono già strutturati e aggiornati. Se avete Microsoft 365 con SharePoint usato correttamente, Teams con trascrizioni attive, e un CRM che tutti alimentano ogni giorno — Copilot funziona. Il problema è che la maggior parte delle PMI che incontriamo ha Drive pieni di cartelle senza logica, NAS con file dal 2011 mai classificati, e la vera storia col cliente che sta nelle mail personali di tre commerciali diversi. Nessun agente nativo funziona sopra il caos. Custodia fa la cosa che quegli strumenti non fanno: viene da voi, legge tutto quello che avete, decide cosa tenere, lo struttura in un formato che gli agenti capiscono, e vi forma la persona interna che lo mantiene. Dopo, potete usare Copilot sopra il vault se volete.

---

## 10. Posso provarlo prima di pagare tutto?

Il pagamento è strutturato in due tranche: 50% alla firma del contratto, 50% all'handover con collaudo positivo. Non pagate tutto prima. Per importi sopra i 10.000 € possiamo ragionare su tre rate (30% firma / 40% inizio Atto 2 / 30% handover). Non offriamo un pilota gratuito a tutti i potenziali clienti perché il lavoro di scandagliamento richiede tempo reale — ma nella call di scoperta facciamo spesso un esercizio pratico: vi mostro come appare una scheda cliente strutturata partendo da un esempio anonimizzato del vostro settore, così capite concretamente cosa consegniamo prima di decidere. Se volete una prova più estesa su una sorgente reale limitata (es. solo i 10 clienti principali), possiamo discuterne come scope ridotto a prezzo ridotto — valutiamo caso per caso.
