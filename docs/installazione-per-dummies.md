# Installazione per dummies

Una guida passo-passo per chi non ha mai usato Claude Code, Cowork, Git o un Terminal.
Se sei già a tuo agio con questi strumenti, leggi direttamente il [`README.md`](../README.md): basta.

**Tempo totale**: 30-45 minuti la prima volta. Le volte successive 5 minuti.

---

## Cosa ti serve prima di iniziare

1. Un computer (Mac o Windows)
2. Un account Claude (anche piano gratuito) — [claude.ai](https://claude.ai)
3. ~30 minuti
4. Un editor di testo qualsiasi (per dare un'occhiata ai file). Se non sai cosa intendo, va bene anche TextEdit (Mac) o Notepad (Windows).

Non ti serve sapere cos'è Git, non ti serve un account GitHub, non ti serve Obsidian.

---

## Le 3 opzioni: scegli quella giusta per te

| Opzione | Per chi | Difficoltà |
|---|---|---|
| **A. Cowork** | Per chi non ha mai aperto un Terminal in vita sua | ⭐ Facile |
| **B. Claude Code** | Per chi è a suo agio con il Terminal o vuole imparare | ⭐⭐ Medio |
| **C. Solo Web** | Per chi vuole solo provarlo senza installare niente | ⭐ Facile, ma limitato |

**Raccomandazione**: se hai dubbi, scegli **A. Cowork**. È la via più liscia.

---

## OPZIONE A — Installazione con Cowork (raccomandata)

Cowork è l'app desktop di Claude pensata per lavorare con file sul tuo computer. È quella che stai usando ora se mi stai leggendo via Cowork.

### A.1 — Installa Cowork (se non ce l'hai già)

1. Vai su [claude.com/cowork](https://claude.com/cowork) (o cerca "Claude Cowork download" su Google)
2. Scarica la versione per il tuo sistema (Mac o Windows)
3. Installalo come una qualsiasi app
4. Accedi con il tuo account Claude

### A.2 — Scarica il template (senza Git, ZIP)

Questo è il pezzo che spaventa i principianti. Niente Git, niente comandi: scarichi uno ZIP da GitHub.

1. Apri il browser e vai su **[github.com/valegro92/claude-second-brain](https://github.com/valegro92/claude-second-brain)**
2. In alto a destra c'è un pulsante verde **`Code`**. Clicca.
3. Si apre un menù: clicca **`Download ZIP`** (in fondo)
4. Il file `claude-second-brain-main.zip` viene scaricato nella cartella **Download**
5. Vai nella cartella Download:
   - **Mac**: doppio click sul file ZIP → si crea automaticamente una cartella `claude-second-brain-main/`
   - **Windows**: tasto destro sul file ZIP → "Estrai tutto..." → conferma
6. Sposta la cartella `claude-second-brain-main` dove ti pare (consigliato: la tua cartella **Documenti**). Per comodità, rinominala in `claude-second-brain` (togli `-main`).

A questo punto hai una cartella locale con dentro tutto il template.

### A.3 — Aggiungi la cartella a Cowork

1. Apri Cowork
2. Clicca sull'icona delle impostazioni / cartelle (in alto a destra o nel menu laterale, dipende dalla versione)
3. Cerca la voce **"Aggiungi cartella"** o **"Add folder"**
4. Naviga fino alla cartella `claude-second-brain` (in Documenti) e selezionala
5. Cowork ora vede questa cartella

### A.4 — Lancia il setup-wizard

Apri una nuova chat in Cowork. Copia e incolla **esattamente** questo prompt:

```
Leggi il file skills/setup-wizard/SKILL.md e segui le istruzioni
per configurare il mio secondo cervello. Ho appena clonato
il template e voglio adattarlo al mio caso.
```

Premi invio.

Claude leggerà il file e ti dirà:

> Perfetto — sono qui per aiutarti a configurare il tuo secondo cervello con Claude. Funziona in due fasi:
> 1. Setup base (10 minuti, sempre)...
> 2. Setup avanzato (5 minuti, opzionale)...
> Iniziamo dal setup base?

Rispondi `sì` (o equivalente).

### A.5 — Rispondi alle 5 domande

Claude ti farà 5 domande, una alla volta. Rispondi in modo naturale, anche disordinato. Esempi:

> **Q1**: Chi sei e cosa fai professionalmente?
> *Tu*: Sono Anna, faccio la consulente HR per piccole aziende del Veneto. Mi occupo soprattutto di selezione e formazione.

> **Q2**: Su cosa stai lavorando in questo periodo?
> *Tu*: Tre clienti attivi: Rossi Srl (selezione 5 figure tecniche), Bianchi (corso onboarding), Verdi (revisione job description). E un corso che sto preparando per un'associazione di categoria.

> **Q3**: Come preferisci che Claude lavori con te?
> *Tu*: Tono diretto, niente preamboli lunghi. Risposte concise. Se non sai una cosa dimmelo, non inventare.

> **Q4**: Cosa ti stanchi di rispiegare ogni volta?
> *Tu*: Che con Rossi Srl evitiamo i test psico-attitudinali, hanno chiesto solo colloqui strutturati. E che con Bianchi il budget è limitato, quindi materiali snelli.

> **Q5**: Hai uno stile di scrittura riconoscibile?
> *Tu*: Quando scrivo email ai clienti uso un tono formale-amichevole. Mai elenchi puntati nelle email, sembra freddo. Nei report invece sì.

Dopo le 5 domande Claude fa un riepilogo e ti chiede conferma. Conferma o correggi.

### A.6 — Setup base completato

Claude scrive 3 file:
- `vault/CLAUDE.md` — con il blocco di configurazione compilato con i tuoi dati
- `vault/MEMORY.md` — con le prime decisioni che vuoi che ricordi
- `vault/references/chi-sono.md` — con la tua identità professionale

Poi ti chiede se vuoi continuare con il setup avanzato (3 step opzionali). Puoi:
- Dire **"sì"** → fai i 3 step (un primo progetto reale, intelligence, automazioni). +5 minuti.
- Dire **"no, mi fermo qui"** → vai allo step A.7

### A.7 — Testa

Apri una **nuova chat** in Cowork (importante: nuova, non la stessa di prima). Scrivi:

```
Buongiorno Claude
```

Se Claude risponde con qualcosa tipo *"Sessione 1 aperta. Cosa facciamo?"* — funziona. La memoria sta partendo. 🎉

Se invece risponde generico ("Ciao! Come posso aiutarti?") senza menzionare nulla che ti riguarda, qualcosa è andato storto. Vai al [Troubleshooting](#troubleshooting).

---

## OPZIONE B — Installazione con Claude Code (Terminal)

Per chi è a suo agio col Terminal o vuole imparare. Più potente perché può lavorare in modalità agente.

### B.1 — Installa Claude Code

1. Apri il Terminal (Mac: Cmd+Spazio → "Terminal" → invio. Windows: cerca "PowerShell" nel menu Start)
2. Se hai Node.js installato:
   ```bash
   npm install -g @anthropic-ai/claude-code
   ```
3. Se non sai cosa è Node.js, scaricalo prima da [nodejs.org](https://nodejs.org) (versione LTS)
4. Verifica che funzioni:
   ```bash
   claude --version
   ```

### B.2 — Clona il repo

Sempre dal Terminal:

```bash
cd ~/Documents
git clone https://github.com/valegro92/claude-second-brain.git
cd claude-second-brain
```

Se non hai Git installato:
- **Mac**: il primo comando `git` te lo proporrà di installare automaticamente (Xcode Command Line Tools). Conferma.
- **Windows**: scarica e installa [Git for Windows](https://git-scm.com/download/win).

### B.3 — Lancia Claude Code nella cartella

```bash
claude
```

Si apre Claude in modalità conversazionale. Da qui in poi i passi sono come [A.4 in poi](#a4--lancia-il-setup-wizard).

---

## OPZIONE C — Solo via Web (per provare al volo)

Limitata: non hai persistenza dei file tra sessioni. Va bene per **provare** il framework, non per usarlo davvero.

### C.1 — Vai su claude.ai

[claude.ai](https://claude.ai), accedi.

### C.2 — Scarica il template come ZIP

Stessa procedura di [A.2](#a2--scarica-il-template-senza-git-zip).

### C.3 — Carica i file chiave nella chat

Apri una nuova conversazione. Trascina nella chat questi 3-4 file:
- `vault/CLAUDE.md`
- `vault/MEMORY.md`
- `vault/references/chi-sono.md`
- `skills/setup-wizard/SKILL.md`

Scrivi:

> Ho appena caricato i file di un template "secondo cervello" per Claude. Leggi `setup-wizard/SKILL.md` e seguilo per aiutarmi a configurare i miei file con le mie informazioni reali.

### C.4 — Limite

A fine sessione perdi tutto. Devi salvare i file generati e ricaricarli ogni volta. Per uso serio passa a **Cowork** o **Claude Code**.

---

## OPZIONALE — Aggiungi Obsidian

Obsidian è un'app gratuita che ti fa vedere i tuoi file `.md` come un grafo. Non è obbligatoria, ma è bella e utile.

1. Scarica Obsidian da [obsidian.md](https://obsidian.md) (gratuito, Mac/Windows/Linux)
2. Apri Obsidian → **"Open folder as vault"** → seleziona la cartella `vault/` dentro `claude-second-brain` (NON la cartella radice — proprio `vault/`)
3. Obsidian apre il vault. Vedrai i file e il grafo.
4. **Plugin consigliati** (vai in Settings → Community plugins → Browse):
   - **Tasks** — per la board dei task in `Daily/Task/attivi.md`
   - **Templates** — per il daily template (Settings → Templates → Template folder location: `Daily/templates/`)

Puoi tenere Obsidian aperto a fianco di Cowork: lavorano sulla stessa cartella, le modifiche di uno appaiono nell'altro in tempo reale.

---

## Aggiungere un nuovo progetto (cliente, corso, idea)

Una volta installato, ogni volta che inizi qualcosa di nuovo:

**Da Cowork** (più semplice):
> Aggiungi un nuovo progetto chiamato **rossi-srl**. Copia la struttura da `vault/progetti/_esempio/` e adattala.

Claude crea la cartella, ribattezza i file, e ti chiede 2 domande veloci per popolare il MOC.

**Da Terminal**:
```bash
cp -r vault/progetti/_esempio vault/progetti/rossi-srl
```
Poi apri Claude e dici: *"Ho creato `progetti/rossi-srl`, aiutami a compilare il MOC."*

---

## Troubleshooting

### "Buongiorno Claude" non risponde nulla di personalizzato
Cause possibili:
1. **Hai aperto la chat sbagliata.** Apri una **nuova chat** in Cowork dopo aver completato il wizard. La chat in cui hai fatto il wizard non ha caricato il `CLAUDE.md` aggiornato.
2. **Cowork non vede la cartella.** Verifica nelle impostazioni che la cartella `claude-second-brain` sia ancora aggiunta.
3. **Il wizard non ha completato la scrittura.** Apri `vault/CLAUDE.md` con un editor di testo e controlla che il blocco `[CONFIGURA QUI]` contenga davvero i tuoi dati e non `Mario Rossi` di default.

### Il wizard si è inceppato a metà
Apri una nuova chat e scrivi:
> Riprendi il setup-wizard dal punto in cui ci siamo fermati. Avevamo arrivato alla domanda N.

Se non sa rispondere, ricomincia da capo: il wizard è idempotente, sovrascrive i file precedenti dopo conferma esplicita.

### Voglio ricominciare da zero
Cancella la cartella `claude-second-brain` e ripeti dall'inizio. Oppure cancella solo i 3 file `vault/CLAUDE.md`, `vault/MEMORY.md`, `vault/references/chi-sono.md` e rilancia il wizard.

### I miei dati sono al sicuro?
Sì. Il vault sta **sul tuo computer**. Claude lo legge solo durante la sessione. Non viene caricato su server esterni a meno che tu non lo carichi esplicitamente. **Nota**: il contenuto delle conversazioni (cioè quello che digiti nella chat) segue le policy di Claude — leggi quelle se è un punto critico.

### Posso pubblicare il mio vault su GitHub?
Sì, ma **fai prima un fork** del template e usa quello. Non pushare il tuo vault personale sul repo originale `valegro92/claude-second-brain`. E fai attenzione a non committare informazioni sensibili (clienti reali, password, dati personali).

### Come tengo aggiornato il template quando esce una nuova versione?
- Se hai usato l'**Opzione A (ZIP)**: scarica il nuovo ZIP, **non sovrascrivere** la tua cartella. Crea una nuova cartella `claude-second-brain-v2`, ricopia i tuoi `vault/CLAUDE.md`, `vault/MEMORY.md`, `vault/references/` e `vault/progetti/` nella nuova versione, e cambia cartella in Cowork.
- Se hai usato l'**Opzione B (Git)**: dal Terminal, nella cartella del repo:
  ```bash
  git pull origin main
  ```
  Git è abbastanza furbo da mergiare le tue modifiche con quelle nuove.

---

## FAQ

**Devo pagare?** No. Il template è gratuito, MIT. Cowork e Claude Code sono gratuiti se hai un account Claude. Funziona anche con il piano free di Claude.

**Sono su Windows, è uguale?** Sì. I percorsi delle cartelle cambiano leggermente (`C:\Users\nome\Documents\...` invece di `~/Documents/...`), ma la logica è identica.

**Ho ChatGPT/Gemini, posso usarlo lo stesso?** Sì, ma non c'è il setup-wizard automatico — devi compilare i file a mano. La struttura della memoria (4 layer, 3 regole) funziona con qualunque LLM che sappia leggere file.

**Quanto tempo prima di vedere valore vero?** Setup 10 minuti, primo "Buongiorno Claude" funziona subito. Il valore composto cresce nel tempo: dopo 2-3 settimane di uso quotidiano è quando il sistema inizia davvero a ricordare per te decisioni passate.

**E se non lo uso ogni giorno?** Funziona lo stesso. Il valore è proporzionale alla frequenza, ma anche 3 sessioni a settimana fanno la differenza nel giro di un mese.

**Posso modificare la struttura del vault?** Sì. È un punto di partenza, non una gabbia. Quando il sistema base diventa stretto puoi aggiungere top-level (`Lavoro/`, `Contenuti/`, `Formazione/`) o skill specifiche. Vedi `docs/da-base-a-avanzato.md` (in arrivo).

---

## Cosa fare quando sei pronto al passo successivo

Quando i Layer 1-2 (Identità + un paio di progetti) sono diventati abitudine — stiamo parlando di 3-4 settimane di uso quotidiano, non di domani — puoi pensare alle estensioni:

- **Trascrizioni meeting automatiche** (Layer 3): integri Granola, Otter, Fireflies o un altro tool con il vault.
- **Connettori MCP** (Layer 4): colleghi Gmail, Calendar, Asana, Slack, ecc. al tuo Claude per fare workflow autonomi.
- **Skill personalizzate**: pipeline di scrittura, automazioni di vault-lint, agenti specializzati.

Tutto questo **non lo metti subito** — lo aggiungi quando il caso d'uso lo giustifica e non prima. È la differenza tra un sistema che usi e uno che ti pesa.

---

*Tornato qui dopo l'installazione e ti sei perso? Il punto di ingresso è sempre il [`README.md`](../README.md). La spiegazione completa del framework è in [`framework.md`](framework.md).*
