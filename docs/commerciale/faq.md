# FAQ — Custodia

Domande frequenti, risposte brevi, niente buzzword.

Se la tua domanda non c'è, scrivimi a `valentino@cassettadegliaitrezzi.it` *(placeholder)* — la aggiungo qui.

> Nota: "Custodia" è il nome di lavoro. Validazione finale dominio + marchio EUIPO/UIBM in corso (vedi [`_brief/07-naming-brand.md`](../../\_brief/07-naming-brand.md)).

---

## Cos'è Custodia

### Custodia è un software?

No. È un **servizio di consulenza chiavi-in-mano** che ti lascia in azienda una wiki strutturata (cartella di file `.md` sul tuo Drive/NAS) + il tuo Custode interno formato per mantenerla. Niente abbonamento, niente piattaforma proprietaria.

### Cosa vuol dire "wiki aziendale chiavi-in-mano"?

In 3-4 settimane di lavoro congiunto, costruiamo insieme la struttura della wiki, ci popoliamo le informazioni dei tuoi clienti/fornitori/processi partendo dai file che hai già, e formiamo una persona della tua azienda — il Custode — che la tiene viva nel tempo. A fine lavoro hai un asset documentale completo, non un software da imparare.

### Da cosa parte la wiki?

Dai file che hai già: Drive condivisi, NAS, casella email `info@`, eventuali SharePoint. Niente "ricominciamo da capo". Scandagliamo le sorgenti che tu autorizzi e proponiamo cosa diventa scheda strutturata, cosa resta dov'è come link, cosa va in archivio.

### Chi è il "Custode"?

Una persona della tua azienda — di solito l'IT/Office manager — che diventa responsabile della wiki. Spende 3-5 ore a settimana per i primi 3 mesi e poi 2-3 ore/settimana a regime. Senza Custode designato, non vendiamo: il vault muore in 6 settimane.

### Custodia è basato su Claude / OpenAI / quale AI?

Su **Claude (Anthropic)**. Lo usiamo come strumento di lettura/scrittura assistita. La wiki è in Markdown puro, quindi anche se domani cambiassi modello AI (o lo togliessi del tutto), il vault funziona — lo apri con Obsidian o qualunque editor.

### In cosa è diverso da Notion / SharePoint / Confluence?

Quelli sono **contenitori vuoti** che devi popolare a mano. Custodia è **delivery + contenuto + ruolo**: ti consegniamo la struttura *già popolata* con i tuoi dati, e ti formiamo la persona che la mantiene. Più simile a "ti installiamo un archivista" che a "ti diamo un'app".

---

## Quanto costa, come funziona la fatturazione

### Quanto costa la delivery?

Da **8.500 € a 14.000 €** una tantum (IVA esclusa). Il range dipende da: dimensione azienda, sorgenti coinvolte, volume dati, numero reparti dal day 1. Preventivo personalizzato dopo una chiamata di scoperta di 30 minuti.

### Come si paga?

50% alla firma del contratto (acconto, fattura immediata). 50% al collaudo positivo dell'handover (Atto 3). Bonifico bancario, IVA 22% se sei italiano. Per importi sopra i 10k posso accettare 3 tranche (30% firma / 40% inizio Atto 2 / 30% handover).

### C'è un canone mensile?

**No, è opzionale**. Dopo l'handover ricevi 3 check-up mensili gratuiti, poi sei libero. Se vuoi continuare con il presidio puoi sottoscrivere una manutenzione: 700 €/mese Light (1.5h al mese) o 1.500 €/mese Premium (4h al mese + evolutive). Contratto annuale, fatturazione trimestrale.

### Cosa NON è incluso nei 8.500-14.000 €?

- Licenze Claude (tue: piano Free / Pro / Cowork, scegli tu)
- Licenze Obsidian (gratis per uso personale, ~50€ una tantum per Sync se vuoi sincronizzare)
- Connettori MCP a sistemi proprietari non standard (es. gestionale italiano custom)
- Cambio dei processi aziendali (è change management, non documentazione)
- Migrazione dei file binari nel vault (architettura: il vault contiene `.md` + link, mai copie di PDF/CAD/Excel)

### Posso pagare a "consumo" (per persona, per GB)?

Sconsigliato. €/persona penalizza il manifatturiero (40 operai + 5 ufficio). €/GB è una pessima proxy (100 GB di video sono triviali, 10 GB di Excel articolati richiedono settimane). Il flat è più equo per entrambi.

---

## Privacy, GDPR, dati sensibili

### I miei dati vengono mandati all'estero?

Durante la delivery i contenuti dei tuoi file passano per l'API di **Anthropic**, server in USA. Anthropic ha **clausole contrattuali standard UE** (SCC) firmate e nel proprio DPA si impegna a **non usare i tuoi dati per training**. La cache è temporanea, viene cancellata a fine delivery. Se ti sta stretto, possiamo escludere preventivamente intere cartelle dal perimetro.

### Sono io il titolare del trattamento?

Sì. Tu sei **Titolare**, Valentino è **Responsabile esterno** (DPA art. 28 GDPR firmato con te), Anthropic è **sub-responsabile** dichiarato. Cancellazione di tutto a 30 giorni dall'handover, con lettera di attestazione.

### Cosa succede se ho dati sensibili (HR, medico, sindacale)?

**Strategia di esclusione a monte**: prima del kick-off decidiamo insieme quali cartelle/etichette NON vengono mai scandagliate. Esempi tipici: `/Personale/`, `/HR/Cartelle-dipendenti/`, `/Medicina-del-lavoro/`, cartelle DPO. Il perimetro privacy lo firma l'Owner in Atto 1.

### Sono uno studio medico / clinica / RSA. Mi serve?

In v1 cloud-based **non vendiamo a strutture sanitarie** per il loro core operativo (cartelle cliniche, dati pazienti). Possiamo lavorare solo su amministrazione/contabilità di una struttura sanitaria, con DPO coinvolto e perimetro che esclude rigorosamente cartelle cliniche. Per il core, aspetta la versione **on-premise** (Step 3 di roadmap).

### Avete il DPA pronto?

Sì, abbiamo uno **scheletro DPA + contratto base** revisionato. Per il primo contratto con un cliente, raccomandiamo che lo faccia rileggere un avvocato GDPR di vostra fiducia (1.000-1.500 € indicativi). Per i contratti successivi è già rodato.

---

## Tecnologia, requisiti, integrazioni

### Su che sistemi gira?

La wiki è una **cartella di file Markdown** sui tuoi sistemi: Google Drive condiviso, OneDrive/SharePoint, NAS interno, anche solo cartella locale sincronizzata. Si apre con Obsidian (gratuito), VS Code, qualunque editor di testo. Niente server da gestire.

### Quali integrazioni avete?

Lato lettura (Atto 2 scandagliamento), via MCP:
- **Google Workspace** (Drive, Gmail) — pronto
- **Microsoft 365** (SharePoint, Outlook, OneDrive) — pronto
- **NAS** (SMB/AFP) — montaggio standard
- **Slack / Teams** — letture trascrizioni se servono (caso per caso)

Non integriamo gestionali italiani (TeamSystem, Zucchetti, Danea, Mexal) in v1 — fuori scope, lo dichiariamo in prima call.

### Devo cambiare i miei strumenti?

No. Continui a usare Drive, NAS, Outlook come prima. Il vault è **aggiuntivo**, non sostitutivo. Mette ordine sopra a quello che hai. L'unica abitudine nuova è: prima di scrivere una nota su un cliente, il vault diventa la SSOT — non più "lo metto in fondo a una mail".

### Funziona se siamo su Linux / Mac / Windows?

Tutti e tre. Il vault sono file `.md`, l'editor Obsidian gira ovunque. Claude (Cowork o Claude Code) gira su tutti. Unica accortezza: il portatile del Custode deve essere cifrato (FileVault Mac / BitLocker Win / LUKS Linux) — è dichiarato nel DPA.

### Cosa fa il Custode quando esce Claude 5 / cambia il modello?

Niente di urgente. La wiki è Markdown plain text — non dipende dal modello. Gli aggiornamenti del toolkit (skill, prompt) li distribuiamo via git, il Custode fa `git pull` e prosegue. Test di non-regressione sulle skill principali a ogni rilascio.

---

## E se…

### Esce di azienda il Custode che hai formato?

Capita. Il manuale custode ([`docs/05-manuale-custode.md`](../05-manuale-custode.md)) è pensato per essere passato a un sostituto in 2-3 settimane di affiancamento. Se hai una manutenzione attiva, ti aiutiamo nell'handover interno. Se non ce l'hai, paghi una sessione di formazione del nuovo Custode (1.500-2.500 € a seconda della complessità).

### Stiamo facendo una ristrutturazione aziendale / fusione / cambio di assetto

Aspetta la fine. Custodia richiede **stabilità organizzativa di 6-9 mesi minimo**. Durante una ristrutturazione i ruoli cambiano, le decisioni vengono ribaltate, il vault diventa documentazione di cose che non esistono più. Riparliamone a ristrutturazione conclusa.

### Usiamo TeamSystem / Zucchetti / Danea — integrate?

In v1 **no**. Quei gestionali non hanno MCP standard e le integrazioni custom escono dal budget setup. Possiamo lavorare attorno a loro (es. esportiamo CSV, li indicizziamo nel vault) ma il flusso bidirezionale lo affrontiamo solo come progetto separato a quotazione. Lo dichiariamo esplicitamente in pre-vendita.

### Vogliamo on-premise — niente traffico USA

In v1 non è disponibile. È in roadmap (Step 3) con un modello open source eseguito localmente. Tempi orientativi: 6-12 mesi dalla prima richiesta concreta di un cliente disposto a pagare il setup dedicato (stima 25-40k€ per il primo deploy). Se per voi è bloccante, parliamone — possiamo aspettare insieme.

### Abbiamo già una wiki interna che non viene aggiornata

È il caso più frequente. Non la sostituiamo, la **assorbiamo selettivamente**: leggiamo cosa è ancora valido (10-30% tipico), lo importiamo nel vault con frontmatter, il resto va in `_archivio`. La differenza con i tentativi precedenti è il Custode formato + i rituali settimanali — se quelli reggono, questa volta non muore.

### Siamo 80 persone, ci aiutate uguale?

Sotto i 30 e sopra i 50 il modello v1 va calibrato. Sotto i 30 puoi farlo con un Custode unico e un setup ridotto (5-7k€). Sopra i 50 (fino a ~100) serve un Custode capo + 2-3 Custodi di reparto, e il setup sale a 15-22k€. Sopra le 100 persone aspetta — servono ruoli formali e sponsor esecutivo che la v1 non gestisce bene.

---

## Documenti collegati

- [`deck-vendita.md`](deck-vendita.md) — slide deck completo per la presentazione
- [`preventivo-template.md`](preventivo-template.md) — template del preventivo personalizzabile
- [`contratto-skeleton.md`](contratto-skeleton.md) — bozza del contratto di delivery
- [`landing-page.md`](landing-page.md) — versione web condivisibile
- [`docs/01-cosa-vendi.md`](../01-cosa-vendi.md) — playbook commerciale (interno)
- [`_brief/06-cost-and-risk.md`](../../\_brief/06-cost-and-risk.md) — costi, rischi, audit legale (interno)
