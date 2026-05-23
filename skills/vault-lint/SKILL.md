---
name: vault-lint
description: Health-check periodico del vault PMI multi-utente. Trova link rotti, file orfani, oggetti non conformi alla Regola 01-PMI (5 file), MEMORY.md sovraccarichi, file stale, frontmatter permessi mancanti. Produce un report datato nel Daily del Custode che lancia il lint. Trigger - "lint del vault", "check vault", "vault health", "vault-lint", "come sta il vault".
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# vault-lint — health-check del vault PMI

Lint periodico del vault multi-utente. Non fa fix automatici — produce la lista, l'utente decide cosa sistemare.

Vedi `_brief/02-framework-pmi.md` per la Regola 01-PMI (5 file invece di 4) e per il frontmatter permessi standard.

---

## Quando girare

- **On-demand** — "fai il lint del vault", "come sta il vault".
- **Settimanale** — tipicamente prima del rituale settimanale del Custode (giovedì o venerdì mattina).
- **Dopo migrazioni strutturali** — es. dopo aver rinominato reparti, spostato clienti, o cambiato la tassonomia.

## Cosa NON fa

- **Non cancella** nulla. Solo segnala.
- **Non modifica** file del vault. Solo legge.

---

## Pre-flight

1. Identifica l'utente attivo (via `session-lifecycle`). Tipicamente è un Custode.
2. Verifica esistenza struttura attesa: `vault/MEMORY.md`, `vault/references/`, `vault/reparti/`, `vault/clienti/`, `vault/fornitori/`, `vault/commesse/`, `vault/decisioni/`, `vault/Daily/`. Se manca qualcosa di critico, segnalalo come issue 0 nel report.

---

## Le 6 dimensioni

### 1. Link rotti

Wiki-link `[[nome]]` che puntano a file non esistenti.

```bash
# Estrai tutti i target di wiki-link nel vault
grep -rhoE '\[\[[^]|]+\]?\]?' "vault/" --include="*.md" \
  | sed -E 's/\[\[([^|]+).*/\1/; s/\]\]$//' \
  | sort -u > /tmp/wikilink-targets.txt

# Per ogni target, cerca un .md con quel nome (basename match)
while read target; do
  found=$(find vault/ -name "${target}.md" -not -path "*/.obsidian/*" | head -1)
  [ -z "$found" ] && echo "MANCA: [[$target]]"
done < /tmp/wikilink-targets.txt
```

Per ciascun link rotto, identifica il file `.md` sorgente (con `grep -rl`) e riportalo nel report.

### 2. File orfani

File `.md` senza frontmatter o senza un `parent:` esplicito né un footer `Parte di [[...]]`. Esclude i MOC top-level (`vault/MEMORY.md`, `vault/references/*`, `vault/decisioni/*`, file `_*.md` che sono indici/template).

```bash
# File senza qualunque frontmatter (no `---` in testa)
find vault/ -name "*.md" -not -path "*/.obsidian/*" -not -path "*/.claude/*" \
  | while read f; do
      head -1 "$f" | grep -q '^---$' || echo "NO-FM: $f"
    done

# File con frontmatter ma senza parent: né footer
grep -rL "^parent:" vault/ --include="*.md" --exclude-dir=.obsidian --exclude-dir=.claude \
  | while read f; do
      grep -q "^Parte di \[\[" "$f" || echo "NO-PARENT: $f"
    done
```

### 3. Regola 01-PMI compliance

Ogni oggetto in `vault/clienti/`, `vault/fornitori/`, `vault/commesse/` deve avere **5 file**: `<slug>.md` (MOC) + `CLAUDE.md` + `MEMORY.md` + `tasks.md` + `persone.md`.

```bash
for area in "clienti" "fornitori" "commesse"; do
  base="vault/$area"
  [ -d "$base" ] || continue
  for oggetto in "$base"/*/; do
    nome=$(basename "$oggetto")
    [ "$nome" = "_esempio" ] && continue
    for f in "${nome}.md" "CLAUDE.md" "MEMORY.md" "tasks.md" "persone.md"; do
      [ -f "$oggetto$f" ] || echo "MANCA $area/$nome/$f"
    done
  done
done
```

Per i reparti, la Regola è diversa (vedi struttura framework): ogni `vault/reparti/<X>/` deve avere `<X>.md` (MOC) + `MEMORY.md` + cartella `procedure/` + `_proposte-promozione.md`. `_candidate-L1.md` può non esistere se vuoto.

```bash
for reparto in vault/reparti/*/; do
  nome=$(basename "$reparto")
  [ "$nome" = "_esempio" ] && continue
  for f in "${nome}.md" "MEMORY.md" "_proposte-promozione.md"; do
    [ -f "$reparto$f" ] || echo "MANCA reparti/$nome/$f"
  done
  [ -d "$reparto/procedure" ] || echo "MANCA reparti/$nome/procedure/"
done
```

### 4. Dimensione anomala

- **MEMORY.md (qualsiasi livello) con > 25 entry** → trigger rotazione: il Custode/Owner dovrebbe archiviare le più vecchie.
- **MOC stub** (< 15 righe non vuote) → dimenticato o non popolato.
- **Daily con sessioni non chiuse** → header `## Sessione N aperta — HH:MM` senza corrispondente `## Sessione N chiusa`.
- **`_proposte-promozione.md` con > 15 proposte** → il Custode salta i rituali settimanali, segnala.

```bash
# MEMORY.md sovraccarichi
find vault/ -name "MEMORY.md" -not -path "*/.obsidian/*" | while read f; do
  n=$(grep -c '^## ' "$f")
  [ "$n" -gt 25 ] && echo "OVER-MEMORY: $f ($n entry)"
done

# MOC stub: file con meno di 15 righe non vuote
find vault/clienti vault/fornitori vault/commesse vault/reparti -maxdepth 2 -name "*.md" \
  | while read f; do
      [[ "$(basename "$f")" =~ ^(MEMORY|CLAUDE|tasks|persone|_).*\.md$ ]] && continue
      n=$(grep -cv '^[[:space:]]*$' "$f")
      [ "$n" -lt 15 ] && echo "STUB-MOC: $f ($n righe)"
    done

# Daily con sessioni aperte non chiuse
grep -rl '^## Sessione [0-9]\+ aperta' vault/Daily/ | while read f; do
  ap=$(grep -c '^### Sessione [0-9]\+ aperta' "$f" 2>/dev/null)
  ch=$(grep -c '^### Sessione [0-9]\+ chiusa' "$f" 2>/dev/null)
  [ "$ap" != "$ch" ] && echo "SESSIONI-APERTE: $f (aperte=$ap chiuse=$ch)"
done
```

### 5. Stale files

File non toccati da > 90 giorni in aree vive (clienti attivi, reparti, commesse in corso). Esclude `_archivio/` e `_legacy-*`.

```bash
find vault/clienti vault/fornitori vault/commesse vault/reparti \
  -name "*.md" -mtime +90 \
  -not -path "*/_archivio/*" \
  -not -path "*/.obsidian/*" \
  -not -path "*/.claude/*"
```

### 6. Frontmatter permessi mancanti (NUOVA, PMI-specifica)

File in L4 (clienti/fornitori/commesse), L2 (procedure), L3 (MEMORY reparto) o L1 (`vault/MEMORY.md`, `vault/references/*`) devono avere frontmatter con almeno `owner:` ed `editor:`. Senza, il filtro permessi della `session-lifecycle` non funziona.

```bash
# File "sensibili" senza owner o editor nel frontmatter
for path in vault/MEMORY.md vault/references/*.md \
            vault/reparti/*/MEMORY.md \
            vault/reparti/*/procedure/*.md \
            vault/clienti/*/*.md vault/fornitori/*/*.md vault/commesse/*/*.md; do
  [ -f "$path" ] || continue
  # estrai blocco frontmatter (tra i primi due ---)
  fm=$(awk '/^---$/{c++; if(c==2)exit} c==1' "$path")
  if [ -z "$fm" ] || ! echo "$fm" | grep -q '^owner:'; then
    echo "NO-OWNER: $path"
  fi
  if [ -z "$fm" ] || ! echo "$fm" | grep -q '^editor:'; then
    echo "NO-EDITOR: $path"
  fi
done
```

Per ogni file: se mancano sia `owner:` che `editor:`, segnala come critico (rosso). Se manca solo `editor:`, segnala come warning (giallo). Per i file in L0 (`references/`) un solo `owner:` può bastare se la convenzione aziendale è "tutti leggono, solo Owner scrive", ma segnala comunque.

---

## Formato del report

Output: `vault/Daily/<XX>/<YYYY-MM>/vault-lint-<YYYY-MM-DD>.md` dove `<XX>` è il Custode che ha lanciato il lint.

```markdown
---
tipo: vault-lint
data: <YYYY-MM-DD>
owner: <XX>
editor: [<XX>]
visibilita: reparto
stato: vivo
---

# Vault-lint — <YYYY-MM-DD>

**Lanciato da**: <XX> (<ruolo>).
**Sommario**: <N1> link rotti · <N2> orfani · <N3> non-01 · <N4> anomalie · <N5> stale · <N6> permessi mancanti.

## 1. Link rotti (<N1>)

- `[[target-x]]` in `path/file1.md` → non trovato. Fix: rinomina o crea stub.

## 2. Orfani (<N2>)

- `path/file.md` → manca `parent:` e footer. Fix: aggiungi frontmatter o sposta sotto il MOC giusto.

## 3. Regola 01-PMI (<N3> non conformi)

- `vault/clienti/rossi-srl/` manca `persone.md`. Fix: crea stub con tabella vuota.
- `vault/reparti/commerciale/` manca `_proposte-promozione.md`. Fix: crea da template.

## 4. Anomalie (<N4>)

- `vault/reparti/commerciale/MEMORY.md`: 28 entry → trigger rotazione (sposta entry > 90gg in `_archivio/MEMORY-<YYYY>.md`).
- `vault/Daily/MR/2026-05/2026-05-18.md`: sessione aperta non chiusa. Fix: aggiungi `### Sessione N chiusa` manualmente.

## 5. Stale (<N5>)

- `vault/clienti/cliente-x/MEMORY.md`: 120 giorni. Fix: verifica se cliente è chiuso, eventualmente sposta in `_archivio/`.

## 6. Permessi mancanti (<N6>)

- **Critico** — `vault/reparti/commerciale/procedure/sop-offerte.md`: manca `owner:` e `editor:`. Senza, chiunque puo scrivere.
- **Warning** — `vault/clienti/rossi-srl/CLAUDE.md`: manca `editor:`. Aggiungi lista.

---

## Azioni proposte (ordinate per impatto)

1. **Alta** — Permessi mancanti su file L2/L4 (bloccano filtro multi-utente). Fix: aggiungi frontmatter `owner` + `editor`.
2. **Alta** — Link rotti (bloccano grafo e navigazione).
3. **Media** — Regola 01-PMI non conforme (oggetti incompleti).
4. **Media** — Rotazione MEMORY sovraccarichi (porta al rituale settimanale).
5. **Bassa** — Stale, anomalie sessioni.

---

## Note

Lint generato automaticamente dalla skill `vault-lint`. Per fix automatici, candidate da considerare al prossimo rituale settimanale del reparto interessato.
```

---

## NON FARE

- Non modificare il vault. Solo scrivere il report nel Daily del Custode.
- Non cancellare file mai.
- Non fare fix automatici — è il Custode (in rituale settimanale) o l'Owner (in rituale mensile) a decidere.
- Non lanciare il lint da utente senza Daily configurato — segnala "lancia prima `setup-wizard-persona`".

## Regole di comportamento

- Tono: sintetico, da check-up. Numeri prima delle parole.
- Lingua: italiano.
- Mai inventare file inesistenti nei suggerimenti di fix.
- Se un controllo bash fallisce (es. `grep` non disponibile), prova con `find`/`rg` o segnala il check come "non eseguito" nel report — mai bloccare l'intero lint per un controllo.
