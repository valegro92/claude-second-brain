# Guida completa — Dal nulla al secondo cervello funzionante

Questa guida copre tutto: cosa stai costruendo, come lo installi, come funziona, e come lo usi ogni giorno.

È pensata per essere seguita sia in aula che in autonomia. Hai un computer davanti? Puoi completarla mentre la leggi.

**Tempo totale**: 45–60 minuti la prima volta.

---

## Prima di iniziare — Cosa ti serve

| Cosa | Dove si prende | Costo |
|---|---|---|
| Un computer (Mac o Windows) | Ce l'hai già | — |
| Un account Claude | [claude.ai](https://claude.ai) | Gratuito (piano free basta) |
| Obsidian | [obsidian.md](https://obsidian.md) | Gratuito |
| Cowork **oppure** Claude Code | Vedi Step 2 | Gratuito |
| Il template del secondo cervello | [github.com/valegro92/claude-second-brain](https://github.com/valegro92/claude-second-brain) | Gratuito |

Non ti serve sapere cos'è Git. Non ti servono competenze tecniche. Serve solo seguire i passi nell'ordine.

---

## Il concetto in 3 minuti — Prima di installare qualsiasi cosa

### Il problema che risolviamo

Claude non ricorda nulla tra una sessione e l'altra. Ogni conversazione riparte da zero.

Per chi lo usa ogni tanto per una domanda veloce, non è un problema. Per chi ci lavora — consulenti, formatori, freelancer, content creator — è un limite enorme: non puoi costruire contesto su un cliente, non puoi andare in profondità su un progetto, perché ogni volta devi risbriefingare tutto.

La soluzione "memoria automatica" di Claude o altri strumenti delega il problema all'AI: speri che ricordi le cose giuste. Questo sistema fa il contrario.

### La soluzione: file che controlli tu

**La tua conoscenza vive in file di testo sul tuo computer. Claude li legge quando servono.**

È semplice come sembra. Scrivi "chi sei, su cosa stai lavorando, che decisioni hai preso" in file `.md` dentro una cartella. Claude legge quella cartella. Ogni mattina riparte già al corrente di tutto.

Niente magia. Niente server. Niente abbonamenti aggiuntivi. Solo file di testo che tu possiedi e controlli.

### L'analogia con un sistema operativo

Pensa al sistema come a un computer con il suo OS:

| Concetto informatico | Nel tuo secondo cervello |
|---|---|
| **Kernel** (il cervello del sistema) | `vault/CLAUDE.md` — dice a Claude come comportarsi |
| **Firmware** (identità stabile) | `vault/references/` — chi sei, come scrivi, con chi lavori |
| **RAM persistente** | `vault/MEMORY.md` — decisioni e lezioni che valgono sempre |
| **App** (singoli contesti) | `vault/progetti/nome-cliente/` — dati specifici di un progetto |
| **Log** (flusso quotidiano) | `vault/Daily/` — task, appunti, diario della giornata |

Quando dici *"Buongiorno Claude"*, il kernel si attiva, legge la RAM, apre il log del giorno, e ti risponde già al corrente di tutto. Niente briefing. Solo lavoro.

### I 4 layer di memoria

Il sistema organizza la memoria in 4 livelli. Ogni livello ha una frequenza diversa di lettura e scrittura:

```
L0 — Chi sei         (references/)          → si legge quando il task lo richiede
L1 — Le tue regole   (MEMORY.md radice)     → si legge OGNI MATTINA
L2 — Il progetto     (progetti/X/MEMORY.md) → si legge quando apri quel progetto
L3 — Oggi            (Daily/)               → è sempre aperto, è il flusso live
```

Una decisione nasce in L3 (un appunto di oggi). Se ritorna, sale a L2 (regola del progetto). Se vale per tutto, sale a L1. Se diventa parte di chi sei, sale a L0.

Questo è il cuore del sistema. Il resto è setup.

---

## Step 1 — Installa Obsidian

Obsidian è l'app che ti fa vedere i tuoi file `.md` come un sistema connesso, con un grafo visivo dei collegamenti. Non è obbligatoria per il sistema, ma è quella che rende tutto comprensibile a colpo d'occhio.

**È gratuita. Mac, Windows, Linux, mobile.**

1. Vai su **[obsidian.md](https://obsidian.md)**
2. Clicca **Download** → scegli la versione per il tuo sistema
3. Installala come una qualsiasi app (trascina in Applications su Mac, installa con il wizard su Windows)
4. Aprila — ti chiede di aprire o creare un vault. **Non fare nulla per ora.** La collegheremo al template tra poco.

✅ Obsidian è installato.

---

## Step 2 — Installa lo strumento per parlare con Claude sui tuoi file

Hai due opzioni. **Scegli solo una.**

### Opzione A — Cowork (consigliata, più semplice)

Cowork è l'app desktop di Claude pensata per lavorare con file sul tuo computer. È quella che usi se sei in aula con Valentino.

1. Vai su [claude.ai/download](https://claude.ai/download) oppure cerca "Claude desktop download"
2. Scarica la versione per il tuo sistema
3. Installala e accedi con il tuo account Claude
4. L'app si apre con una chat. **Non fare nulla per ora** — la collegheremo alla cartella tra poco.

### Opzione B — Claude Code (per chi è a suo agio col Terminal)

1. Apri il Terminal (Mac: `Cmd+Spazio` → scrivi "Terminal" → invio. Windows: cerca "PowerShell")
2. Assicurati di avere Node.js. Se non lo hai: [nodejs.org](https://nodejs.org) → scarica la versione LTS → installala
3. Installa Claude Code:
   ```bash
   npm install -g @anthropic-ai/claude-code
   ```
4. Verifica:
   ```bash
   claude --version
   ```
   Se vedi un numero di versione, funziona.

✅ Lo strumento è installato.

---

## Step 3 — Scarica il template

Il template è la struttura di partenza del tuo secondo cervello. Non è un software — è semplicemente una cartella con file `.md` pre-organizzati.

### Metodo A — ZIP (più semplice, niente Git)

1. Apri il browser e vai su **[github.com/valegro92/claude-second-brain](https://github.com/valegro92/claude-second-brain)**
2. Clicca il pulsante verde **`Code`** in alto a destra
3. Clicca **`Download ZIP`** nel menu che si apre
4. Il file `claude-second-brain-main.zip` si scarica nella tua cartella Download
5. Decomprimi lo ZIP:
   - **Mac**: doppio click → si crea `claude-second-brain-main/`
   - **Windows**: tasto destro → "Estrai tutto..."
6. **Sposta la cartella** dove preferisci (consiglio: dentro i tuoi Documenti)
7. **Rinominala** togliendo il `-main`: da `claude-second-brain-main` a `claude-second-brain`

### Metodo B — Git (se hai usato l'Opzione B sopra)

Dal Terminal:
```bash
cd ~/Documents
git clone https://github.com/valegro92/claude-second-brain.git
cd claude-second-brain
```

✅ Il template è sul tuo computer.

---

## Step 4 — Apri il vault in Obsidian

Il vault è la sottocartella `vault/` dentro `claude-second-brain`. **Non aprire la cartella radice — apri proprio `vault/`.**

1. Apri Obsidian
2. Nella schermata iniziale, clicca **"Open folder as vault"** (o "Apri cartella come vault")
3. Naviga fino alla cartella `claude-second-brain` → entra dentro → seleziona la cartella **`vault`** → conferma
4. Obsidian apre il vault. Nel pannello sinistro vedi la struttura dei file.

> **Se ti chiede di "trust" la cartella** → clicca "Trust author and enable plugins". Serve per i plugin già configurati.

### Cosa vedi dentro

```
vault/
├── CLAUDE.md          ← il "kernel" del sistema (non modificare a mano)
├── MEMORY.md          ← la tua RAM persistente (riempirai questo)
├── references/        ← chi sei, come scrivi, con chi lavori
├── progetti/          ← i tuoi clienti, corsi, idee
│   └── _esempio/      ← template per ogni nuovo progetto
├── Daily/             ← log, task, appunti del giorno
└── Scheduled/         ← task automatici (avanzato)
```

### Installa i plugin consigliati

In Obsidian: **Settings** (icona ingranaggio in basso a sinistra) → **Community plugins** → sposta "Safe mode" su OFF → **Browse**

Cerca e installa:
- **Tasks** — gestisce la board dei task attivi (obbligatorio)
- **Templates** — crea file daily automaticamente (consigliato)

Dopo aver installato Tasks, cerca "Templates" nelle impostazioni e imposta:
- Template folder location: `Daily/templates`

✅ Obsidian è configurato.

---

## Step 5 — Collega la cartella a Cowork (o lancia Claude Code)

### Se hai scelto Cowork

1. Apri Cowork
2. Vai nelle impostazioni (icona in alto a destra o nel menu laterale)
3. Cerca **"Aggiungi cartella"** o **"Add folder"**
4. Naviga fino alla cartella `claude-second-brain` (la cartella radice, non `vault/`) e selezionala
5. Cowork ora vede tutti i file dentro

### Se hai scelto Claude Code

Dal Terminal, entra nella cartella:
```bash
cd ~/Documents/claude-second-brain
claude
```

Claude Code si apre in modalità conversazionale direttamente nella cartella giusta.

✅ Claude vede i tuoi file.

---

## Step 6 — Lancia il setup wizard

Questo step personalizza il sistema per te. Claude ti farà alcune domande e compilerà automaticamente i file base con le tue risposte reali.

**In Cowork o Claude Code**, apri una nuova chat e incolla **esattamente** questo prompt:

```
Leggi il file skills/setup-wizard/SKILL.md e segui le istruzioni
per configurare il mio secondo cervello. Ho appena clonato
il template e voglio adattarlo al mio caso.
```

Premi invio.

### Le domande del wizard

Il wizard ti farà **5 domande base**, una alla volta. Rispondi in modo naturale — anche disordinato va bene, Claude struttura lui:

**Domanda 1 — Chi sei professionalmente?**
Esempio: *"Faccio la consulente HR per piccole aziende del Veneto, mi occupo di selezione e formazione."*

**Domanda 2 — Su cosa stai lavorando in questo periodo?**
Esempio: *"Ho tre clienti attivi: Rossi Srl (selezione figure tecniche), Bianchi (corso onboarding), e un corso per un'associazione di categoria."*

**Domanda 3 — Come vuoi che Claude lavori con te?**
Esempio: *"Tono diretto, risposte concise, niente preamboli. Se non sai una cosa, dimmelo."*

**Domanda 4 — Cosa ti stanchi di rispiegare ogni volta?**
Esempio: *"Con Rossi Srl evitiamo i test psico-attitudinali. Con Bianchi il budget è limitato, materiali snelli."*

**Domanda 5 — Come scrivi e comunichi?**
Esempio: *"Nelle email ai clienti uso un tono formale-amichevole, niente elenchi puntati. Nei report sì."*

Dopo le 5 domande, il wizard fa un riepilogo. **Leggi, correggi se serve, conferma.**

### Cosa viene scritto

Claude compila automaticamente 3 file:
- `vault/CLAUDE.md` — con le tue preferenze di lavoro
- `vault/MEMORY.md` — con le prime decisioni che vuole che ricordi
- `vault/references/chi-sono.md` — con la tua identità professionale

**Poi chiede se vuoi continuare con il setup avanzato** (3 step opzionali: un progetto reale, intelligence, automazioni). Puoi dire sì o no — il sistema funziona già con il setup base.

✅ Il sistema è personalizzato.

---

## Step 7 — Test: funziona?

Apri una **nuova chat** in Cowork (importante: nuova, non quella del wizard). Scrivi:

```
Buongiorno Claude
```

**Se funziona**, Claude risponde con qualcosa di tipo:
```
Sessione 1 aperta. Cosa facciamo?

Ho letto il tuo profilo: sei [il tuo nome], lavori su [i tuoi temi].
Come prima sessione, vuoi che ti aiuti ad aprire un progetto reale
oppure preferisci esplorare come funziona il sistema?
```

**Se risponde in modo generico** ("Ciao! Come posso aiutarti?") senza menzionare nulla che ti riguarda, c'è un problema → vai alla sezione [Troubleshooting](#troubleshooting) in fondo.

✅ Il secondo cervello è attivo.

---

## Come si usa ogni giorno

Il sistema non richiede disciplina complicata. Richiede due frasi al giorno.

### La mattina — "Buongiorno Claude"

Scrivi `Buongiorno Claude` all'inizio di ogni sessione di lavoro.

Claude legge `MEMORY.md` e il daily di oggi, poi ti risponde con un orientamento: che progetti hai attivi, cosa avevi annotato come "da fare oggi", se c'è qualcosa che aspetta risposta.

**Da lì si parte. Niente briefing.**

### Durante la giornata — lavoro normale

Lavori normalmente con Claude. La differenza è che lui ha il contesto:
- Sa chi è il cliente su cui stai lavorando
- Sa che preferisci un certo approccio
- Sa le decisioni che avete preso insieme

Se apri un progetto specifico, aggiungi solo:
```
Stiamo lavorando su [nome-cliente]. Leggi projects/[nome-cliente]/MEMORY.md.
```

Claude carica il contesto specifico di quel progetto. Da quel momento è al corrente di tutto.

### La sera — "Buonanotte Claude"

Scrivi `Buonanotte Claude` a fine sessione.

Claude scrive un riassunto nel diario di oggi e ti propone 0–3 cose che hanno valore di essere ricordate. Esempio:

```
Oggi abbiamo lavorato su Rossi Srl e definito l'approccio per i colloqui.
Vuoi che salvi queste due cose in memoria?

1. Marco (HR Rossi Srl) preferisce WhatsApp per le urgenze, mai email → memoria del progetto?
2. La traccia colloquio parte sempre con un caso pratico, mai domande generali → regola generale?

Dimmi sì/no per ognuna o correggimi.
```

Tu rispondi `1 sì, 2 sì`. Lui aggiorna i file giusti. **Costo: 60 secondi.**

Il giorno dopo, quella roba è già lì.

---

## Come si aggiunge un nuovo progetto

Ogni volta che inizi qualcosa di nuovo — un cliente, un corso, un'idea — crei una cartella progetto con sempre la stessa struttura.

**Il modo più semplice** — chiedi a Claude in Cowork:
```
Aggiungi un nuovo progetto chiamato rossi-srl. Usa il template in vault/progetti/_esempio/.
```

Claude crea la struttura, ti chiede 2-3 informazioni base, e in 5 minuti hai la cartella pronta.

**La struttura che viene creata:**
```
vault/progetti/rossi-srl/
├── rossi-srl.md      ← MOC: l'hub che linka a tutto
├── CLAUDE.md         ← istruzioni specifiche per questo progetto
├── MEMORY.md         ← decisioni e contesto del cliente
├── tasks.md          ← i task aperti
└── knowledge/        ← documenti, transcript call
```

Ogni progetto ha la stessa struttura. Sempre. Questo significa che non devi mai ricordare "dove avevo messo le note di...": stai sempre nel posto giusto.

---

## Cosa sono i file `.md` — spiegazione rapida

I file `.md` (Markdown) sono file di testo normale. Puoi aprirli con qualsiasi editor di testo. La differenza rispetto a un `.txt` è che usano simboli semplici per la formattazione:

| Simbolo | Effetto |
|---|---|
| `# Titolo` | Titolo grande |
| `## Sottotitolo` | Titolo più piccolo |
| `**grassetto**` | **grassetto** |
| `*corsivo*` | *corsivo* |
| `- voce` | Punto elenco |
| `[[nome-file]]` | Link a un altro file del vault |
| `---` | Linea separatrice |

Il simbolo più importante per il sistema è `[[nome-file]]`. Ogni volta che scrivi questo in un file, stai creando un collegamento tra quel file e un altro. Questi collegamenti costruiscono il grafo.

**Non devi imparare la sintassi a memoria.** Claude la conosce. Quando gli chiedi di creare o modificare un file, lo fa nel formato corretto. Il tuo lavoro è sapere *cosa vuoi*, non *come scriverlo*.

Per una guida completa sulla sintassi: [`guida-markdown-e-grafo.md`](guida-markdown-e-grafo.md)

---

## Il grafo in Obsidian — cosa è e come si usa

Il grafo è la rappresentazione visiva del tuo secondo cervello. Ogni file è un punto (nodo). Ogni `[[collegamento]]` tra file è una linea (arco). Il risultato è una rete.

### Come aprirlo

In Obsidian: **tasto in basso a sinistra** (icona rete) oppure `Cmd+Shift+G` (Mac) / `Ctrl+Shift+G` (Windows).

Si apre una finestra con tutti i nodi. Puoi:
- Zommare dentro e fuori
- Cliccare un nodo per aprire quel file
- Filtrare per tag (pannello a destra)

### Cosa vedi

All'inizio il grafo è poco denso — hai appena iniziato. Man mano che lavori, aggiungi file e `[[link]]`, il grafo cresce.

I nodi più grandi (con più connessioni) sono i tuoi hub: `MEMORY.md`, il MOC di ogni cliente, i file in `references/`. Se un file è isolato (nessun collegamento), è spesso un segnale che è fuori posto o dimenticato.

### Vista locale (la più utile)

Da qualsiasi file aperto: **tasto destro → "Open local graph"**. Vedi solo i file collegati a quello specifico — perfetto quando vuoi capire rapidamente tutto quello che ruota intorno a un cliente o a un progetto.

### Configura i colori (fallo una volta sola)

Settings → Graph view → Groups → aggiungi una regola per ogni area:

| Tag | Colore |
|---|---|
| `tag:#consulenza` | Viola |
| `tag:#formazione` | Verde |
| `tag:#content` | Arancio |
| `tag:#daily` | Grigio |
| `tag:#contesto` | Bianco |

Dopo questa configurazione, il grafo è colorato per area. A colpo d'occhio vedi dove c'è più attività.

Per la guida completa sul grafo: [`guida-markdown-e-grafo.md`](guida-markdown-e-grafo.md)

---

## La prima settimana — cosa fare

Il sistema funziona dal giorno uno. Ma il valore cresce. Ecco cosa fare la prima settimana:

**Giorno 1** — Completa il setup (sei qui). Lancia il wizard. Prova il primo "Buongiorno Claude".

**Giorni 2–3** — Apri il sistema ogni mattina. Non serve lavorarci ore: anche solo 20 minuti di lavoro reale. L'importante è usare "Buongiorno" e "Buonanotte".

**Giorno 4–5** — Aggiungi il tuo primo progetto reale. Uno solo. Compila il `MEMORY.md` di quel progetto con le decisioni che ti stanchi di rispiegare.

**Fine settimana** — Riapri quel progetto. Nota se Claude ha già il contesto senza che tu glielo abbia rispiegato. Quella è la prova che funziona.

**Non aggiungere estensioni, skill custom, o connettori MCP prima del mese 1.** Il sistema funziona solo se la disciplina di base (Buongiorno/Buonanotte + un progetto vero) diventa abitudine prima.

---

## Troubleshooting

### "Buongiorno Claude" risponde in modo generico

**Causa 1 — Chat sbagliata.** Hai aperto la chat del wizard invece di una nuova. Apri una nuova chat in Cowork.

**Causa 2 — Cowork non vede la cartella.** Vai nelle impostazioni → Cartelle → verifica che `claude-second-brain` sia ancora presente.

**Causa 3 — Il wizard non ha scritto i file.** Apri `vault/CLAUDE.md` con Obsidian e controlla che ci sia il tuo nome e le tue preferenze, non `[CONFIGURA QUI]` o dati di default.

### Il wizard si è bloccato a metà

Apri una nuova chat e scrivi:
```
Riprendi il setup-wizard. Ci eravamo fermati alla domanda N.
```
Se non ricorda, ricomincia — il wizard è idempotente, sovrascrive i file dopo conferma.

### Non trovo la cartella in Cowork

Su Mac la cartella è probabilmente in `~/Documents/claude-second-brain`. In Cowork, aggiungi la cartella cercandola in Documenti.

### Obsidian non mostra il grafo

Verifica di aver aperto la **sottocartella `vault/`** e non la cartella radice `claude-second-brain`. Il grafo funziona solo dentro `vault/`.

### Voglio ricominciare da zero

Elimina solo i 3 file compilati dal wizard:
- `vault/CLAUDE.md`
- `vault/MEMORY.md`
- `vault/references/chi-sono.md`

Poi rilancia il wizard. La struttura del vault resta intatta.

---

## FAQ

**Devo pagare qualcosa?** No. Il template è MIT (gratuito). Obsidian è gratuito. Cowork e Claude Code sono gratuiti con un account Claude. Il piano free di Claude basta per iniziare.

**Funziona con ChatGPT o Gemini?** La struttura dei file funziona con qualsiasi LLM. Il setup-wizard automatico è ottimizzato per Claude. Con altri strumenti devi compilare i file a mano.

**I miei dati sono al sicuro?** I file vivono sul tuo computer. Claude li legge solo durante la sessione attiva. Non vengono caricati su server esterni.

**Devo usarlo ogni giorno?** No. Il valore è proporzionale alla frequenza, ma anche 3 sessioni a settimana fanno la differenza in un mese.

**Posso avere più top-level (Lavoro/, Contenuti/, Formazione/)?** Sì, è l'evoluzione naturale. Il template parte con una singola cartella `progetti/` — puoi espandere quando hai 10+ progetti e senti il bisogno di organizzarli per area. Fallo al mese 1-2, non al giorno 1.

**Posso condividere il vault con un collega?** Sì, metti la cartella su un servizio di sync (iCloud, Dropbox, OneDrive). Ma attenzione ai dati sensibili — clienti, password, contratti. In dubbio, tieni i file riservati fuori dal vault.

---

## Riepilogo in 7 step

| Step | Cosa fai | Tempo |
|---|---|---|
| 1 | Installa Obsidian | 5 min |
| 2 | Installa Cowork o Claude Code | 5 min |
| 3 | Scarica il template (ZIP o git clone) | 3 min |
| 4 | Apri `vault/` in Obsidian | 2 min |
| 5 | Collega la cartella a Cowork | 2 min |
| 6 | Lancia il setup wizard + rispondi alle 5 domande | 15 min |
| 7 | Scrivi "Buongiorno Claude" in una nuova chat | 1 min |

**Totale: ~30–35 minuti.** Il resto viene da solo.

---

## Dove andare dopo

| Documento | Quando leggerlo |
|---|---|
| [`README.md`](../README.md) | Per il quadro completo del sistema e i 4 componenti |
| [`guida-markdown-e-grafo.md`](guida-markdown-e-grafo.md) | Per capire la sintassi `.md` e usare il grafo in profondità |
| [`docs/framework.md`](framework.md) | Per la spiegazione tecnica completa (layer, regole, protocollo) |
| [`docs/aggiungere-un-progetto.md`](aggiungere-un-progetto.md) | Quando apri il tuo primo progetto reale |

---

*Sistema creato da [Valentino Grossi](https://lacassettadegliaitrezzi.substack.com) — La Cassetta degli AI-trezzi*
*Repository: [github.com/valegro92/claude-second-brain](https://github.com/valegro92/claude-second-brain)*
