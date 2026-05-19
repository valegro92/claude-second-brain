---
name: vault-lint
description: Health-check periodico del vault. Trova link rotti, file orfani, progetti non conformi alla Regola 01, MEMORY.md sovraccarichi, file stale. Produce un report datato in Daily/Appunti/vault-lint/. Trigger - "lint del vault", "check vault", "vault health", "vault-lint", "come sta il vault".
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, TodoWrite
---

# Vault-lint — health-check del secondo cervello

Lint periodico del vault. Non fa fix automatici — produce la lista, l'utente decide cosa sistemare.

## Quando girare

- **On-demand** — "fai il lint del vault", "come sta il vault".
- **Settimanale** — domenica mattina (se impostato come routine).
- **Dopo migrazioni strutturali** — es. dopo aver rinominato top-level o spostato progetti.

## Cosa NON fa

- **Non cancella** nulla. Solo segnala.
- **Non modifica** file del vault. Solo legge.

---

## Le 5 dimensioni

### 1. Link rotti

Wiki-link `[[nome]]` che puntano a file non esistenti.

```bash
# Estrai tutti i target di wiki-link
grep -rhoE '\[\[[^]|]+\]?\]?' "/path/vault" --include="*.md" \
  | sed -E 's/\[\[([^|]+).*/\1/; s/\]\]$//' \
  | sort -u
# Per ogni target: controlla se esiste un .md con quel nome
```

### 2. File orfani

File `.md` senza frontmatter `parent:` o footer `Parte di [[...]]`.

```bash
# File senza parent:
grep -rL "^parent:" "/path/vault" --include="*.md" --exclude-dir=.obsidian --exclude-dir=.claude

# File senza footer:
grep -rL "^Parte di \[\[" "/path/vault" --include="*.md" --exclude-dir=.obsidian --exclude-dir=.claude
```

### 3. Regola 01 compliance

Ogni progetto deve avere: `[progetto].md` + `CLAUDE.md` + `MEMORY.md` + `tasks.md`.

```bash
for costellazione in "Business/Consulenza" "Business/Formazione" "Content-Creator" "Idee"; do
  for progetto in "/path/vault/$costellazione"/*/; do
    nome=$(basename "$progetto")
    for f in "${nome}.md" "CLAUDE.md" "MEMORY.md" "tasks.md"; do
      [ -f "$progetto$f" ] || echo "$progetto manca $f"
    done
  done
done
```

### 4. Dimensione anomala

- **MEMORY.md con >20 entry** → trigger rotazione.
- **MOC stub** (<15 righe significative) → dimenticato o non popolato.
- **Daily con sessioni non chiuse** → header `## Sessione N (HH:MM — )` con fine vuota.

### 5. Stale files

File non toccati da >90 giorni in aree che dovrebbero essere vive.

```bash
find "/path/vault/Business/Consulenza" "/path/vault/Content-Creator" \
  -name "*.md" -mtime +90 -not -path "*/.obsidian/*"
```

---

## Formato del report

Output in `Daily/Appunti/vault-lint/vault-lint-YYYY-MM-DD.md`.

```markdown
---
tags: [daily, vault-lint]
parent: "[[sparks]]"
date: YYYY-MM-DD
---

# Vault-lint — YYYY-MM-DD

**Sommario**: N link rotti · N orfani · N non-01 · N anomalie · N stale.

## 1. Link rotti (N)
- `[[target-x]]` → non trovato. In: `path/file1.md`. Fix: rinomina o crea stub.

## 2. Orfani (N)
- `path/file.md` → manca `parent:`. Fix: aggiungi frontmatter.

## 3. Regola 01 (N non conformi)
- `Business/Consulenza/cliente-x/` manca `MEMORY.md`. Fix: crea stub.

## 4. Anomalie (N)
- `MEMORY.md` (root): 23 entry → trigger rotazione.

## 5. Stale (N)
- `Business/Consulenza/cliente-y/MEMORY.md`: 120 giorni. Fix: verifica se chiuso.

---

## Azioni proposte
1. [alta — link rotti bloccano il grafo]
2. [media — Regola 01, rotazione]
3. [bassa — stale, anomalie]

Parte di [[sparks]]
```

---

## NON FARE

- Non modificare il vault. Solo scrivere il report in `Daily/Appunti/vault-lint/`.
- Non cancellare file mai.
- Non fare fix automatici — è l'utente a decidere.
