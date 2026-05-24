# Pitch Slides — Custodia v2

---

## Slide 1 — Quanto vale, in tempo, rispondere al cliente Rossi?

**Copy**

Prima di scrivere una riga di risposta al cliente Rossi, il vostro commerciale ha già perso 30-45 minuti: ha cercato nel Drive sbagliato, ha scritto a Carlo in produzione per le condizioni dell'ultima offerta, ha aperto tre versioni di un file Excel senza capire quale fosse l'attuale, ha ricostruito a memoria le eccezioni concordate nel 2023.

Il problema non è l'efficienza del vostro team. È che la conoscenza aziendale vive sparsa in cinque posti diversi, e ogni risposta al cliente costa una piccola spedizione di recupero.

L'effetto a catena è prevedibile: i clienti aspettano, le condizioni vengono dimenticate o replicate in modo errato, e ogni nuovo assunto impiega settimane — a volte mesi — prima di essere autonomo su un portafoglio.

---

**Descrizione visiva per mockup**

Layout verticale o a due colonne. A sinistra, una figura centrale stilizzata (il commerciale) circondata da cinque fonti sconnesse, ciascuna con un'etichetta: "Drive definitivo v3", "NAS reparto", "Inbox di Marco", "Post-it sullo schermo", "Carlo lo sa". Le frecce puntano tutte verso l'esterno, verso la figura — non verso una destinazione condivisa. L'atmosfera è quella di un documento editoriale anni '90: niente clip art Microsoft, preferire forme geometriche pulite e un tono quasi infografico. A destra (opzionale), un orologio o un'indicazione temporale che mostra "30-45 min" prima che il commerciale possa scrivere la prima parola della risposta. Stile cromatico: bianco, un grigio caldo, e un solo colore di accento per i nomi delle fonti.

---

**Speaker notes**

Questa slide non parla di tecnologia: parla di un pomeriggio qualunque in ufficio. In discovery call avete sentito i vostri interlocutori descrivere esattamente questa scena — probabilmente con parole come "ognuno ha il suo Drive", "il commerciale lo sa lui", "quando entra uno nuovo ci vuole un mese". Il punto non è che la vostra azienda funziona male. Il punto è che questo è lo stato normale di ogni PMI con 10 anni di storia digitale, e che esistono costi sommersi che non appaiono su nessun bilancio. Questa slide serve a dare un nome a qualcosa che il lettore già conosce — non a sorprenderlo.

---

## Slide 2 — Un second brain aziendale, leggibile dagli agenti.

**Copy**

Custodia v2 non installa un'intelligenza artificiale nella vostra azienda. Costruisce il layer di conoscenza che serve perché un'intelligenza artificiale — quella che avete già, o che sceglierete voi — possa lavorare davvero.

In quattro settimane, al fianco del vostro team, mettiamo in piedi tre cose: un vault Obsidian strutturato con le schede dei vostri clienti, fornitori e commesse principali; un MCP server configurato che espone quella conoscenza agli agenti off-the-shelf (Claude, ChatGPT, Codex); e una persona interna — il Custode — formata per tenere il sistema vivo.

Il risultato concreto: il vostro commerciale apre Claude Code, scrive "rispondi al cliente Rossi sul preventivo del compressore X", e in 30 secondi ha una bozza che conosce le condizioni concordate, l'offerta del 2024, l'ultima email rilevante. L'agente lo fa perché il vault strutturato lo sa. L'agente lo trovate voi sul mercato — noi costruiamo il posto dove l'agente pesca.

Il vault è uno solo. Lo costruiamo in modalità Cloud (Claude API, server EU, GDPR) oppure in modalità Sovrana (LLM su server dedicato presso un provider di inferenza italiano/UE) — la scelta la facciamo insieme all'Atto 1, in base a dove preferite che girino i dati durante la lavorazione.

---

**Descrizione visiva per mockup**

Tre box orizzontali collegati da frecce, come una pipeline semplice. Box 1 a sinistra: "Sorgenti aziendali" — etichette piccole con Drive, NAS, email. Box 2 al centro, leggermente più grande e in evidenza: "Custodia" — con due righe sotto: "Vault Obsidian" e "MCP server". Box 3 a destra: "Agenti" — etichette Claude, ChatGPT, Codex. Le frecce vanno sinistra-verso-destra: le sorgenti entrano nel vault, il vault è esposto agli agenti. Sotto la pipeline, su tutta la larghezza, uno screenshot o mockup statico di una scheda cliente in Obsidian: frontmatter YAML visibile con campi come `cliente`, `settore`, `ultime-condizioni`, `offerte`, `stato-relazione`, due o tre righe di testo corpo. Non serve che sia compilato con dati reali — basta che sia leggibile e pulito. Font monospazio per il frontmatter, leggero e aerato.

---

**Speaker notes**

La modalità di inferenza (Cloud vs Sovrana) è una decisione che si prende a tavolino all'Atto 1: il vault prodotto è identico, cambia solo dove gira il motore che lo costruisce. Cloud è il default — più veloce da avviare, GDPR-compliant via clausole standard UE. Sovrana è l'opzione per chi vuole che durante la fase di scandagliamento i dati restino sotto giurisdizione italiana, su un server dedicato; comporta un piccolo extra di setup e qualche settimana di lead time. Non è un upsell, è una scelta legittima che ha senso solo per alcuni clienti — di solito quelli con compliance interna che lo richiede esplicitamente. Il punto da sottolineare con chi legge questa slide è la distinzione tra knowledge layer e AI. Molti prodotti sul mercato vendono "AI per la tua azienda" — Copilot, Notion AI, ChatGPT Enterprise — ma si appoggiano sulla vostra conoscenza così com'è, dispersa e non strutturata. Custodia fa il contrario: costruisce prima il layer di conoscenza, poi lascia che ci mettiate l'agente che preferite. Questo è il motivo per cui il valore è difendibile nel tempo: il vault strutturato rimane vostro, non dipende da un vendor, e funziona con qualsiasi agente che uscirà l'anno prossimo. SharePoint Copilot indicizza quello che avete. Noi costruiamo quello che avete in modo che valga la pena indicizzarlo.

---

## Slide 3 — In 4 settimane, davanti ai vostri occhi.

**Copy**

**Atto 1 — Kick-off on-site (settimana 1).** Mezza giornata presso di voi. Mappiamo le sorgenti, definiamo il perimetro privacy, nominiamo il Custode. La struttura del vault viene montata in giornata.

**Atto 2 — Scandagliamento supervisionato (settimane 2-3).** Leggiamo le sorgenti autorizzate e popoliamo il vault con le schede clienti, fornitori e commesse. Il Custode ci affianca e impara facendo. Voi approvate cosa entra.

**Atto 3 — Handover con demo live (settimana 4).** Mezza giornata con il vostro team. Consegna del vault completo, formazione del Custode, e — davanti a tutti — l'agente che risponde a una mail reale del vostro portafoglio clienti usando lo storico del vault.

Investimento: €12.000-18.000 una tantum (IVA esclusa), con un'opzione di manutenzione mensile a €800-1.500/mese per i mesi successivi. Il range dipende da numero di sorgenti, volume dei dati e reparti coinvolti — preventivo personalizzato dopo la chiamata.

**Come si inizia: 30 minuti di scoperta gratuita, senza impegno.** Raccontate la vostra situazione, capiamo insieme se ci sono le condizioni per lavorare. Se non ci sono, lo diciamo subito.

`valentino@cassettadegliaitrezzi.it` — oppure LinkedIn (Valentino Grossi)

---

**Descrizione visiva per mockup**

Parte alta: timeline orizzontale con quattro segmenti — settimane 1, 2, 3, 4 — e i tre atti marcati sopra con etichette brevi (Kick-off, Scandagliamento, Handover). Atto 1 copre settimana 1, Atto 2 copre settimane 2-3, Atto 3 copre settimana 4. Parte centrale: screenshot statico di Obsidian con una scheda cliente aperta, frontmatter YAML visibile, grafo di connessioni sullo sfondo (pannello destra di Obsidian). L'immagine occupa circa metà larghezza della slide, allineata a destra o al centro. Parte bassa: CTA in un rettangolo leggero — email e LinkedIn, niente logo, niente testimonial, niente loghi cliente. Stile pulito, spazio bianco generoso, nessun elemento decorativo.

---

**Speaker notes**

Il momento che vende questa slide — e che vende il prossimo cliente quando il vostro interlocutore lo racconterà ai colleghi — è l'Atto 3. Non la struttura del vault, non il MCP server, non la formazione del Custode. L'agente che risponde a una mail reale, davanti al team, in 30 secondi. È lì che il beneficio smette di essere astratto e diventa visibile a chi non ha partecipato alla discovery call. È anche il momento che distingue Custodia da qualsiasi prodotto che "indicizza i vostri documenti": l'agente non risponde perché ha trovato un file — risponde perché il vault gli ha già detto le condizioni che avete con quel cliente, l'ultima offerta, lo stato della relazione. Questo è quello che rendete concreto nella demo. Preparatela con una mail reale del loro portafoglio, sceglietela insieme al Custode nella settimana 3.
