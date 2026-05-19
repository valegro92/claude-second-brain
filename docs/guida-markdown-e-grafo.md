# File `.md` e grafo — cosa sono e come usarli

Questa guida spiega due cose che il README dà per scontate e che invece non lo sono affatto:

1. **Cos'è un file `.md`** — e come si scrive
2. **Cos'è il grafo in Obsidian** — e come si costruisce e si usa

Non serve essere programmatori. Serve solo capire la logica, che è semplice.

---

## Parte 1 — I file `.md` (Markdown)

### Cos'è un file `.md`

Un file `.md` è un file di testo normale. Puoi aprirlo con qualsiasi editor di testo — Blocco Note, TextEdit, Notepad++, VS Code, Obsidian. Non è un Word, non è un PDF: è testo puro.

La differenza rispetto a un `.txt` è che il `.md` usa un sistema di formattazione leggero chiamato **Markdown**: un insieme di simboli semplici che rendono il testo più leggibile e strutturato, senza bisogno di bottoni, menu, o toolbar.

Markdown è nato tra i programmatori ma si è diffuso ovunque perché funziona: scrivi testo normale con qualche simbolo, e il risultato è leggibile sia come testo grezzo sia quando viene renderizzato (ad esempio in Obsidian, GitHub, o Notion).

### La sintassi in 5 minuti

Tutto quello che ti serve per scrivere i file del vault:

---

**Titoli** — con il cancelletto `#`:

```
# Titolo principale
## Sottotitolo
### Sotto-sottotitolo
```

Diventa:

> # Titolo principale
> ## Sottotitolo
> ### Sotto-sottotitolo

---

**Testo in grassetto e corsivo**:

```
Questo è **grassetto**.
Questo è *corsivo*.
Questo è ***grassetto e corsivo***.
```

---

**Elenchi puntati**:

```
- Prima voce
- Seconda voce
  - Voce annidata
- Terza voce
```

---

**Elenchi numerati**:

```
1. Prima cosa
2. Seconda cosa
3. Terza cosa
```

---

**Link** — a un sito:

```
[Testo del link](https://esempio.com)
```

---

**Link interni** — tra file del vault (questo è quello che costruisce il grafo):

```
[[nome-del-file]]
[[nome-del-file|testo alternativo]]
```

Questo è il pezzo più importante del sistema. Approfondito nella Parte 2.

---

**Blocchi di codice** — per testo preformattato (comandi, prompt da copiare):

````
```
testo preformattato
```
````

---

**Separatore orizzontale** — tre trattini:

```
---
```

---

**Frontmatter** — un blocco speciale all'inizio del file per i metadati:

```
---
tags: [consulenza, rossi-srl]
parent: "[[progetti/rossi-srl/rossi-srl]]"
created: 2026-05-19
---
```

Il frontmatter sta sempre **in cima al file**, tra i due `---`. Non appare nel testo ma viene letto da Obsidian per costruire il grafo e i filtri. Nel vault del secondo cervello, ogni file ha un frontmatter.

---

### Come creare e modificare un file `.md`

**Con Obsidian** (il modo più comodo):
- Pannello sinistro → click destro su una cartella → "New note"
- Il file si crea direttamente nella cartella giusta
- L'editor mostra il testo formattato (o grezzo, a scelta — vedi il bottone in alto a destra)

**Con un editor di testo qualsiasi**:
- Crea un nuovo file → salvalo con estensione `.md` (es. `rossi-srl.md`)
- Scrivici dentro — è testo normale
- Obsidian lo vede automaticamente appena salvi

**Con Claude (il modo più veloce)**:
- Chiedi a Claude di creare il file per te: *"Crea `progetti/rossi-srl/MEMORY.md` con queste informazioni..."*
- Claude scrive il file al posto tuo, con frontmatter e struttura corretti

Non devi imparare la sintassi a memoria: Claude la conosce. Il tuo lavoro è capire *cosa vuoi* nel file — lui si occupa del *come*.

---

### Il frontmatter del vault — formato standard

Ogni file `.md` del vault segue questo schema:

```markdown
---
tags: [#tag-compartimento]
parent: "[[path/del/file-parent]]"
---

# Titolo

Contenuto...

---
*Parte di [[parent-index]]*
```

I tag identificano il compartimento (`#consulenza`, `#formazione`, `#content`, `#daily`, ecc.). Il `parent` linka all'indice del progetto o dell'area. Il footer `Parte di [[...]]` chiude il file.

Non devi compilare questo a mano ogni volta — il setup-wizard lo fa per i file base, e Claude lo aggiunge automaticamente quando crea file su tua richiesta.

---

## Parte 2 — Il grafo in Obsidian

### Cos'è il grafo

Obsidian ha una vista "Graph view" che mostra visivamente come i tuoi file sono collegati tra loro. Ogni file è un nodo, ogni collegamento `[[...]]` è un arco.

Il risultato assomiglia a una rete di stelle: le note più collegate diventano hub visivi, quelle periferiche sono foglie. Guardando il grafo capisci immediatamente cosa è centrale nel tuo lavoro e cosa è isolato.

Non è solo estetica: il grafo è la rappresentazione fisica del tuo secondo cervello. Più è denso e connesso, più il sistema funziona. Un file senza link in entrata è spesso un segnale che è fuori posto o che non è ancora stato integrato.

### Come si apre

- **Tasto** in basso a sinistra in Obsidian (icona rete) oppure `Cmd+Shift+G` (Mac) / `Ctrl+Shift+G` (Windows)
- Si apre una finestra separata con tutti i nodi
- Puoi zoommare, cliccare i nodi per aprire i file, filtrare per tag

### Come si costruisce il grafo — i wiki-link `[[...]]`

Il grafo si costruisce scrivendo `[[nome-file]]` dentro i tuoi `.md`. Ogni volta che scrivi `[[rossi-srl]]` in un file, stai creando un arco tra quel file e `rossi-srl.md`.

Esempio concreto:

```markdown
# MEMORY.md — radice

## 2026-05-10 — Decisione importante
Ho deciso di strutturare tutti i progetti seguendo la [[Regola-01]].
Il primo progetto adattato è stato [[progetti/rossi-srl/rossi-srl]].
```

Questo crea due archi nel grafo:
- `MEMORY.md` → `Regola-01.md`
- `MEMORY.md` → `rossi-srl.md`

Più scrivi, più il grafo cresce. Non devi farlo manualmente ogni volta: nel vault del secondo cervello, Claude aggiunge automaticamente i link alla prima occorrenza di ogni entità rilevante (clienti, progetti, tool, documenti di riferimento) ogni volta che scrive o modifica un file.

### Navigare il grafo

**Apri un nodo**: click su qualsiasi pallino → si apre il file corrispondente in Obsidian

**Filtra per tag**: nel pannello a destra del grafo → "Filters" → spunta i tag che vuoi vedere (es. solo `#consulenza`)

**Cerca un file**: barra di ricerca in alto → il nodo si evidenzia nel grafo

**Vista locale**: da qualsiasi file aperto, tasto destro → "Open local graph" → vedi solo i file collegati a quello aperto. Utile quando sei dentro un progetto e vuoi vedere solo la sua rete.

**Colori**: Obsidian colora i nodi per tag. Nel vault del secondo cervello, ogni compartimento ha il suo colore:
- Viola → `#consulenza`
- Verde → `#formazione`
- Arancio → `#content`
- Grigio → `#daily`
- Bianco → `#contesto` (references/)

Per configurare i colori: Settings → Graph view → Groups → aggiungi una regola per ogni tag.

### Il grafo come strumento di lavoro, non solo vista

Il grafo non è decorativo. Usalo attivamente per:

**Trovare file orfani**: nodi senza connessioni in entrata sono spesso note dimenticate o mal archiviate. Se vedi un pallino isolato, chiediti: *questo file è nel posto giusto? È collegato all'indice del suo progetto?*

**Capire cosa è centrale**: i nodi più grandi (quelli con più link) sono i tuoi hub. Nel vault tipico, `MEMORY.md`, il MOC di ogni cliente attivo, e i file `references/` sono i nodi più connessi. Se non lo sono, c'è qualcosa che non si è sedimentato bene.

**Navigare per associazione**: invece di cercare un file per nome, clicchi sul MOC del progetto → vedi tutti i file collegati → vai diretto a quello che ti serve.

**Identificare cosa manca**: se hai un progetto con pochi nodi, è un segnale che la struttura non è ancora completa — manca il MEMORY, le note della call, il tasks.md.

---

### Configura il grafo (una volta sola)

Queste impostazioni le fai una volta al setup e poi le dimentichi.

**1. Abilita plugin Community**
Settings → Community plugins → Safe mode OFF → Browse → installa:
- **Tasks** (obbligatorio per la board dei task)
- **Dataview** (opzionale, per query avanzate)
- **Templates** (per il daily automatico)

**2. Configura Templates**
Settings → Templates → Template folder location → scrivi `Daily/templates`

**3. Configura i colori del grafo**
Settings → Graph view → Groups:

| Query | Colore suggerito |
|---|---|
| `tag:#consulenza` | Viola `#9b59b6` |
| `tag:#formazione` | Verde `#27ae60` |
| `tag:#content` | Arancio `#e67e22` |
| `tag:#daily` | Grigio `#95a5a6` |
| `tag:#contesto` | Bianco `#ecf0f1` |
| `tag:#idee` | Giallo `#f1c40f` |

**4. Abilita il "Show attachments"** nel grafo se vuoi vedere anche le immagini e PDF come nodi. Di solito è meglio tenerlo OFF — rende il grafo troppo rumoroso.

---

## Riepilogo

| Cosa | Come |
|---|---|
| Creare un file `.md` | Obsidian (tasto destro) o chiedi a Claude |
| Modificare un file | Apri in Obsidian o in qualsiasi editor di testo |
| Collegare due file | Scrivi `[[nome-file]]` nel testo |
| Aprire il grafo | `Cmd+Shift+G` in Obsidian |
| Vedere solo i file di un progetto | Tasto destro sul file → "Open local graph" |
| Filtrare per area | Pannello Filters del grafo → spunta i tag |
| Trovare file orfani | Cerca nodi isolati nel grafo |
| Configurare colori | Settings → Graph view → Groups |

---

*Torna al [`README.md`](../README.md) per il quadro completo del sistema.*  
*Per l'installazione passo-passo: [`installazione-per-dummies.md`](installazione-per-dummies.md)*
