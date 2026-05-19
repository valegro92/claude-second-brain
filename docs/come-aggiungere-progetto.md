# Come aggiungere un nuovo progetto — Regola 01

Ogni progetto nel vault segue la Regola 01: 5 file obbligatori, struttura identica.

## I 5 file obbligatori

| File | Ruolo | Chi lo scrive |
|---|---|---|
| `[progetto].md` | MOC — hub che linka a tutto | Claude dalla prima sessione |
| `CLAUDE.md` | Istruzioni specifiche di progetto | Tu + Claude |
| `MEMORY.md` | Decisioni datate del progetto | Claude durante il lavoro |
| `tasks.md` | Task attivi | Claude quando gestisci task |
| `references/` | Documenti di riferimento | Tu (caricati on-demand) |

## Procedura

### 1. Crea la struttura

```bash
# Sostituisci [costellazione] con: Business/Consulenza, Business/Formazione, Content-Creator, o Idee
# Sostituisci [progetto] con il nome in kebab-case (es. cliente-acme, corso-excel-base)

mkdir -p ~/Vault\ Claude/[costellazione]/[progetto]/references
cd ~/Vault\ Claude/[costellazione]/[progetto]
touch [progetto].md CLAUDE.md MEMORY.md tasks.md
```

### 2. Dì a Claude di aiutarti a compilare il MOC

```
Ho appena creato la cartella [progetto] in [costellazione]. 
Puoi aiutarmi a compilare il MOC con quello che so finora?
```

Claude chiederà: chi è il cliente/progetto, cosa stai facendo, qual è lo stato attuale.

### 3. Template base dei 5 file

**`[progetto].md`** (MOC):
```markdown
---
tags: [[#consulenza|#formazione|#content|#idee]]
parent: "[[_index]]"
---

# [Nome Progetto]

**Stato**: [attivo | in pausa | chiuso | embrionale]
**Tipo**: [cliente consulenza | corso | canale | idea]

## Overview
[2-3 righe: chi è, cosa stiamo facendo]

## Link rapidi
- [[CLAUDE]] — istruzioni Claude per questo progetto
- [[MEMORY]] — decisioni e context
- [[tasks]] — task attivi

## Output principali
[link ai deliverable in ~/Output Claude/...]

---
Parte di [[_index]]
```

**`CLAUDE.md`**:
```markdown
# Istruzioni Claude — [Nome Progetto]

## Contesto progetto
[2-3 righe sul progetto]

## Regole specifiche
- [es. "Tono formale nelle comunicazioni con questo cliente"]
- [es. "Non menzionare il concorrente X nelle slide"]
- [es. "Budget approvato: 5.000€ — non sforare"]

## Persone chiave
- [Nome]: [ruolo] — [note]

## Dove stanno le cose
- Output: `~/Output Claude/[costellazione]/[progetto]/`
- Input cliente: `~/Output Claude/[costellazione]/[progetto]/input/`
```

**`MEMORY.md`**:
```markdown
---
tags: [[#consulenza|...]]
parent: "[[progetto]]"
---

# MEMORY — [Nome Progetto]

## Decisioni

## YYYY-MM-DD — Setup progetto
**Stato**: Progetto avviato.
**Contesto**: [breve descrizione]

## Lezioni

## Metriche chiave
[es. NPS, fatturato, ore, deliverable]
```

**`tasks.md`**:
```markdown
---
tags: [task, [#consulenza|...]]
parent: "[[progetto]]"
---

# Task — [Nome Progetto]

<!-- Le entry più recenti in cima -->

---
Parte di [[progetto]]
```

### 4. Aggiungi il progetto alla Whitelist

Apri `~/Vault Claude/CLAUDE.md`, sezione **Whitelist entità canoniche**, e aggiungi il nome del progetto nella categoria giusta. Così Claude auto-linkerà automaticamente ogni menzione futura.

## Costellazioni disponibili

| Costellazione | Path | Per cosa |
|---|---|---|
| Consulenza | `Business/Consulenza/[cliente]/` | Clienti con deliverable regolari |
| Formazione | `Business/Formazione/[corso]/` | Corsi, workshop, ricerca |
| Content Creator | `Content-Creator/[canale]/` | Newsletter, YouTube, LinkedIn, podcast |
| Idee | `Idee/[progetto]/` | Idee business, app in sviluppo, startup |

## Quando un progetto finisce

Non cancellare mai la cartella. Aggiorna il MOC:

```markdown
**Stato**: chiuso YYYY-MM-DD
**Motivo**: [perché è finito]
```

Se vuoi liberare il grafo, sposta la cartella in `~/Output Claude/_da-eliminare/cleanup-pending/` — ma mantieni il MOC nel vault con il link alla location dell'archivio.
