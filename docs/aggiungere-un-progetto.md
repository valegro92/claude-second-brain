# Come aggiungere un nuovo progetto

Ogni progetto (cliente, corso, idea, canale) ha la stessa struttura — 4 file in una cartella.

---

## 1. Copia la cartella esempio

```bash
cp -r ~/Vault\ Claude/progetti/_esempio ~/Vault\ Claude/progetti/nome-del-progetto
```

## 2. Rinomina i file

```bash
cd ~/Vault\ Claude/progetti/nome-del-progetto
mv _esempio.md nome-del-progetto.md
```

## 3. Compila i 4 file

Apri ogni file e sostituisci i placeholder con i dati reali:

- **nome-del-progetto.md** → chi è, cosa stai facendo, link rapidi
- **CLAUDE.md** → regole specifiche per questo progetto, persone chiave
- **MEMORY.md** → parti vuoto, si riempie mentre lavori
- **tasks.md** → aggiungi i primi task

## 4. Di' a Claude

```
Ho aggiunto [nome-progetto] in progetti. Puoi aiutarmi a compilare il MOC?
```

Claude leggerà i file e ti chiederà le informazioni mancanti.

---

## Struttura finale

```
progetti/
└── nome-del-progetto/
    ├── nome-del-progetto.md   ← hub del progetto
    ├── CLAUDE.md              ← istruzioni specifiche
    ├── MEMORY.md              ← decisioni e contesto
    ├── tasks.md               ← task attivi
    └── references/            ← documenti del cliente (opzionale)
        └── brief.md
```

---

## Dove mettere i file non-Markdown del cliente

Brief in PDF, contratti, presentazioni ricevute → vanno nella cartella Output, non nel vault:

```
~/Output Claude/progetti/nome-del-progetto/input/
```

Il vault contiene solo `.md`. Tutto il resto nell'output.
