# Script demo — Catasto

Script per registrare una demo video di **5-7 minuti** che Valentino userà come asset commerciale (LinkedIn, landing page, primo contatto). La registrazione è manuale (OBS / QuickTime / Loom) — questo file dà setup, scaletta, copione e fallback.

Obiettivo della demo: in 5-7 minuti, un decisore PMI deve capire **cos'è**, **come si usa quotidianamente**, **cosa resta in azienda**.

> Nota: "Catasto" è nome di lavoro. Riferimenti al naming finale da aggiornare quando definito (vedi [`_brief/07-naming-brand.md`](../../\_brief/07-naming-brand.md)).

---

## Setup — cosa preparare prima

### Cliente demo

Usa **"Esempio Srl"**, l'officina manifatturiera di Brescia da 38 persone introdotta nel deck. Persone tipo:

- **AF** — Anna Ferrari, titolare, Owner
- **GB** — Giulia Bianchi, Office manager, Custode capo
- **MR** — Mario Rossi, commerciale senior, Editor
- **LV** — Luca Verdi, commerciale junior, Contributor
- **Cliente nel vault**: **Rossi Srl** (officina meccanica di precisione, cliente da 4 anni)

### Stato del vault prima della registrazione

Il vault demo (`/home/user/claude-second-brain/vault/` o un fork dedicato) deve avere:

- `vault/CLAUDE.md` — kernel multi-utente (già nel template)
- `vault/MEMORY.md` — 3-4 ADR datati realistici (es. *"ADR-001: scelta CRM 2023 / ADR-002: cambio fornitore acciaio inox / ADR-003: passaggio a fatturazione elettronica forzata"*)
- `vault/references/persone.md` — AF, GB, MR, LV + altri 3-4 fittizi popolati
- `vault/references/chi-siamo.md`, `organigramma.md`, `brand-voice.md`, `glossario.md` — compilati
- `vault/reparti/commerciale/MEMORY.md` — 2-3 lezioni recenti del reparto
- `vault/reparti/commerciale/procedure/sop-offerte.md` — un esempio
- `vault/clienti/rossi-srl/` con i 5 file Regola 01-PMI completi (`rossi-srl.md` MOC, `CLAUDE.md`, `MEMORY.md`, `tasks.md`, `persone.md`)
- `vault/clienti/rossi-srl/riunioni/2025-04-12_kickoff-progetto-x.md` — un verbale
- `vault/reparti/commerciale/_proposte-promozione.md` — 4-5 proposte realistiche per la scena del rituale

### Tool aperti prima di partire

1. **Obsidian** aperto sul vault demo, view "graph" pronta + file `clienti/rossi-srl/rossi-srl.md` aperto in tab
2. **Claude Code** (o Cowork) aperto in terminale/pannello, working directory = vault
3. **Browser** in finestra a parte, pronto a mostrare il repo GitHub (placeholder) e la pagina del deck
4. **Editor di testo** semplice (VS Code) aperto su una cartella `.md` qualunque del vault, per la scena "anche offline funziona"

### Setup tecnico

- **Registrazione**: OBS Studio o QuickTime, output 1080p, formato MP4
- **Audio**: microfono USB esterno (no microfono del laptop), test di livello prima
- **Webcam in PiP**: opzionale, posizionata in basso a destra, 240x135 px, attiva solo nelle scene 1 e 7
- **Cursore**: ingrandito (System Preferences → Accessibility → Cursor Size)
- **Notifiche**: tutte silenziate (Mac: "Do Not Disturb", Win: "Focus Assist")
- **Finestre**: solo l'app di scena in primo piano, sfondo pulito (desktop senza icone, wallpaper neutro)

### Timing target

| Scena | Durata | Cumulato |
|---|---|---|
| 1. Apertura e contesto | 0:30 | 0:30 |
| 2. Il vault come cartella di file | 0:45 | 1:15 |
| 3. Il grafo e la struttura | 0:45 | 2:00 |
| 4. "Buongiorno Claude, sono MR" | 1:30 | 3:30 |
| 5. Scheda cliente Rossi Srl | 1:00 | 4:30 |
| 6. Il rituale settimanale del Custode | 1:00 | 5:30 |
| 7. Chiusura: "funziona anche offline" + CTA | 0:30 | 6:00 |

Target totale: **6 minuti**. Margine ±1 minuto.

---

## Scaletta scena per scena

### Scena 1 — Apertura e contesto (0:30)

**Cosa mostrare**: webcam in primo piano, sfondo neutro, eventuale slide titolo "Catasto" dal deck.

**Cosa dire** (copione letterale):

> *"Ciao, sono Valentino. In 6 minuti ti faccio vedere come funziona Catasto, il sistema che installiamo nelle PMI italiane per organizzare il loro patrimonio documentale.*
>
> *Lo vedrai dalla parte di un'azienda inventata che chiameremo Esempio Srl: officina meccanica di Brescia, 38 persone, 8 anni di Drive condivisi sedimentati e una casella `info@` da 14.000 mail. Il classico caso.*
>
> *Cosa vedrai: una cartella di file, la routine quotidiana di un commerciale, e il rituale settimanale di chi tiene viva la wiki. Partiamo."*

**Fallback**: se la webcam non parte → solo audio + slide titolo del deck.

---

### Scena 2 — Il vault come cartella di file (0:45)

**Cosa mostrare**: Finder/Esplora risorse aperto sulla cartella `vault/` del vault demo. Espandere la struttura.

**Cosa dire**:

> *"Prima cosa importante: questa è una **cartella di file**. Non un'app, non un SaaS. Sta sul vostro Drive o sul vostro NAS, accanto a tutto il resto.*
>
> *Vedete la struttura: `references/` per l'identità aziendale, `reparti/` con dentro Commerciale, Amministrazione, Produzione, `clienti/` con la cartella di ogni cliente, `fornitori/`, `Daily/` con il diario di ogni persona.*
>
> *I file sono Markdown — testo. Si aprono con qualunque editor. Anche tra 10 anni, anche se chiudo io, anche se Anthropic non esiste più."*

**Azione**: aprire un file Markdown qualunque (es. `chi-siamo.md`) con TextEdit / Notepad per mostrare che è solo testo.

**Fallback**: se l'apertura con editor sbaglia → mostrare lo stesso file dentro Obsidian in modalità "source".

---

### Scena 3 — Il grafo e la struttura (0:45)

**Cosa mostrare**: switch a Obsidian, vista "Graph view" del vault demo. Far girare il grafo. Poi click su un nodo (es. `rossi-srl`) per evidenziare le connessioni.

**Cosa dire**:

> *"Questo è il grafo del vault di Esempio Srl come si presenta in Obsidian, che è uno dei modi per leggerlo — gratuito.*
>
> *Ogni nodo è un file: una persona, un cliente, una decisione, una procedura. Le linee sono i link tra di loro. Quando clicco su `rossi-srl`, vedo immediatamente: i 5 file del cliente, i verbali di riunione, le procedure del reparto Commerciale che lo riguardano, le persone coinvolte.*
>
> *Questa è la prima cosa che cambia rispetto a un Drive: **niente più "dov'è il file di Rossi"**. C'è un posto, è linkato a tutto il contesto, ci arrivi in 2 click."*

**Fallback**: se il grafo è troppo denso o illeggibile → passare direttamente a `clienti/rossi-srl/rossi-srl.md` aperto come MOC e mostrare i link interni.

---

### Scena 4 — "Buongiorno Claude, sono MR" (1:30)

**Cosa mostrare**: switch a Claude Code (o Cowork) aperto in terminale, working directory `vault/`. Scrivere e mostrare la risposta in tempo reale.

**Cosa dire** (mentre digiti):

> *"Adesso ti faccio vedere come Mario Rossi, commerciale di Esempio Srl, inizia la sua giornata. Apre Claude, e scrive una cosa sola:"*

**Azione**: digita lentamente nella CLI:

```
Buongiorno Claude, sono MR
```

Invia. Aspetta la risposta. Claude (sul vault correttamente configurato) leggerà `references/persone.md` → MR=Editor Commerciale, `MEMORY.md` aziendale, `reparti/commerciale/MEMORY.md`, `Daily/MR/YYYY-MM/oggi.md`.

**Cosa dire mentre Claude risponde**:

> *"In questi 5 secondi sta leggendo: chi è Mario — Editor del Commerciale — la memoria aziendale, la memoria del suo reparto, e il suo diario di ieri. Niente di più. Niente caricamento massivo. Solo quello che serve a orientare la sua giornata.*
>
> *Ecco la risposta. Mario adesso sa: dove era rimasto ieri, quali decisioni cross-reparto sono uscite, quali clienti ha in agenda, quale offerta gli aspetta sul tavolo. 30 secondi al mattino, e non deve più chiedere a nessuno."*

**Azione bonus** (se c'è tempo): scrivere un secondo prompt operativo:

```
Apri la scheda di Rossi Srl e dimmi a che punto siamo con la trattativa
```

Mostrare Claude che carica `clienti/rossi-srl/rossi-srl.md` e riassume.

**Fallback**: se Claude risponde in modo lento o sbagliato → fermarsi alla prima risposta e dire *"in produzione la risposta arriva in 5-8 secondi, qui sto registrando in tempo reale per onestà"*.

---

### Scena 5 — Scheda cliente Rossi Srl (1:00)

**Cosa mostrare**: torna su Obsidian, apri `vault/clienti/rossi-srl/rossi-srl.md` (il MOC). Mostra la struttura. Click su un link a `MEMORY.md` per mostrare le decisioni datate. Click su `persone.md` per mostrare le persone.

**Cosa dire**:

> *"Questa è la scheda di Rossi Srl. La struttura segue una regola fissa — la chiamiamo Regola 01-PMI — che vale per ogni oggetto di business: 5 file, sempre gli stessi, sempre nello stesso posto.*
>
> *Il MOC è la pagina di apertura, fa da indice. `MEMORY.md` tiene le decisioni storiche datate — vedete, qui c'è scritto che a marzo 2024 abbiamo cambiato il referente commerciale di loro, qui ad agosto 2024 abbiamo rinegoziato i tempi di pagamento. `persone.md` ha tutte le persone coinvolte — i nostri commerciali da una parte, i loro buyer dall'altra, con i contatti.*
>
> *Quando entra un nuovo commerciale che eredita il cliente Rossi, in **30 secondi** ha 4 anni di contesto. Non gli serve più di Mario per il giorno 1."*

**Fallback**: se i link interni di Obsidian non si aprono → fare lo screenshare a livello di sistema operativo aprendo direttamente i file dalla cartella.

---

### Scena 6 — Il rituale settimanale del Custode (1:00)

**Cosa mostrare**: aprire `vault/reparti/commerciale/_proposte-promozione.md` in Obsidian (file preparato in setup con 4-5 proposte realistiche, es. *"MR ha proposto che la SOP offerte includa sempre la clausola di rivalutazione prezzi materia prima"*, *"GB ha notato che 3 clienti chiedono fattura elettronica con codice destinatario invece di PEC, aggiornare procedura"*, ecc.).

**Cosa dire**:

> *"Ultima cosa, quella che molti non capiscono e che fa la differenza: la wiki resta viva solo se qualcuno la cura. Quel qualcuno è il Custode.*
>
> *Ogni venerdì pomeriggio, 30 minuti, il Custode apre questo file — `_proposte-promozione.md`. È pieno di idee che i colleghi hanno accumulato durante la settimana: dialogando con Claude, ognuno suggerisce piccole sedimentazioni. Il Custode decide cosa promuovere a memoria di reparto, cosa diventa nuova procedura, cosa va al rituale mensile con il titolare, cosa si scarta.*
>
> *In 30 minuti la wiki ha digerito la settimana. Senza questo rituale, la wiki muore in 6 mesi. Con questo rituale, dopo un anno è la cosa più letta dell'azienda."*

**Azione**: lanciare `vault-lint` da terminale (o mostrare il file della skill in `skills/vault-lint/SKILL.md`) per mostrare il check di igiene.

**Fallback**: se `vault-lint` non gira pulito → mostrare il file della skill come testo e raccontare cosa fa a parole.

---

### Scena 7 — Chiusura: "funziona anche offline" + CTA (0:30)

**Cosa mostrare**: chiudere Claude (Cmd+Q / Alt+F4). Disconnettere il Wi-Fi (Mac: alt+click su simbolo Wi-Fi → disattiva; Win: pannello connessioni). Aprire Obsidian. Aprire la stessa scheda `rossi-srl/rossi-srl.md`. Mostrare che funziona uguale.

**Cosa dire**:

> *"Ultima dimostrazione, importante. Chiudo Claude. Stacco il Wi-Fi. Apro Obsidian. La scheda di Rossi è esattamente lì com'era. Funziona uguale.*
>
> *Quello che lasciamo in azienda non dipende da Claude, non dipende da Anthropic, non dipende da Internet. È una cartella di file di testo. Vostra, per sempre.*
>
> *Se quello che ho fatto vedere ha senso per la tua azienda, prenota una chiamata di 30 minuti — il link te lo lascio in descrizione. Capiamo insieme se sei un caso servibile, senza vendere nulla per forza. Grazie."*

**Azione finale**: webcam in primo piano, sorriso, fade out con logo Catasto + tagline corta + URL.

---

## Riprese alternative se qualcosa non funziona

| Cosa va male | Cosa fare al posto |
|---|---|
| **Wi-Fi cade** | Tethering dal telefono. Se cade anche quello: registrare le sezioni offline (1, 2, 3, 5, 6, 7) in sequenza, lasciare la scena 4 per ultima quando torna la rete |
| **Claude risponde in modo strano o errato** | Riprovare 2 volte. Se persiste: fare voice-over di una risposta tipica preregistrata, in trasparenza dire "ho preregistrato questa parte perché la live è impredicibile" |
| **Obsidian si pianta o si blocca** | Avere VS Code come backup, aprire i file `.md` direttamente lì — l'esperienza visiva è meno bella ma il messaggio passa |
| **`vault-lint` segnala 50 errori del vault demo** | Saltare il `vault-lint` live, parlarne a parole guardando il file `SKILL.md` |
| **Audio scratchato** | Riregistrare solo l'audio in voice-over su video muto, sincronizzazione manuale in post |
| **Tempo si dilata oltre i 7 minuti** | Tagliare in post la scena 5 (cliente) o accorciare l'azione bonus della scena 4 |
| **Demo dura meno di 4:30** | Aggiungere nella scena 6 un secondo esempio di rituale (es. mostrare il flusso completo della skill `rituale-settimanale-custode`) |

---

## Checklist pre-registrazione (5 minuti prima di premere REC)

- [ ] Vault demo aggiornato, tutti i file della sezione "Setup" presenti e popolati
- [ ] Claude Code / Cowork aperto sulla working dir corretta, sessione vergine
- [ ] Obsidian aperto sul vault demo, graph view già renderizzata, MOC di Rossi Srl in tab
- [ ] Notifiche silenziate (Do Not Disturb / Focus Assist)
- [ ] Microfono testato (registrare 10 secondi, riascoltare)
- [ ] Cursore ingrandito
- [ ] Browser con tab pronte (repo GitHub, landing page) ma non in primo piano
- [ ] Bottiglietta d'acqua in tavolo (per riprese di più di un take)
- [ ] Cellulare in silenzioso e capovolto
- [ ] Sfondo desktop pulito (nessun documento aperto sul desktop)
- [ ] Slide titolo pronta in Keynote/PowerPoint per le scene 1 e 7

---

## Checklist post-registrazione

- [ ] Salvare il file MP4 originale con naming `demo-catasto-vYYYY-MM-DD.mp4`
- [ ] Editing in iMovie / DaVinci Resolve: tagliare pause, inserire titoli scena (opzionale), aggiungere logo iniziale e finale
- [ ] Sottotitoli automatici + revisione manuale (italiano + opzionale inglese)
- [ ] Export in 2 formati: 1080p per LinkedIn/landing, 720p per email
- [ ] Pubblicare su: landing page (incorporato), LinkedIn (post nativo), YouTube unlisted (per linkare in email)
- [ ] Aggiornare [`docs/commerciale/landing-page.md`](landing-page.md) con embed del nuovo video
- [ ] Backup file sorgente su drive cifrato

---

## Documenti collegati

- [`deck-vendita.md`](deck-vendita.md) — slide deck completo, slide 6 ("Demo flow visuale") è il riferimento di questa demo
- [`docs/06-framework-pmi.md`](../06-framework-pmi.md) — i concetti che la demo mostra (layer, ruoli, regole)
- [`docs/02-kickoff-checklist.md`](../02-kickoff-checklist.md) — la fase di costruzione del vault che la demo mostra "finita"
- [`onboarding-custode.md`](onboarding-custode.md) — cheatsheet del Custode, utile per la scena 6
