# Brief — Framework PMI (subagente 2)

Proposta sintetica dell'edizione PMI del framework. Va istanziata nel nuovo `vault/` (cantiere VAULT) e descritta nel doc `06-framework-pmi.md` (cantiere DOCS).

---

## 1. I 6 layer di memoria (al posto dei 4 single-user)

Matrice 2 assi: *cosa* (statico vs vivo) × *chi* (azienda vs reparto vs oggetto/persona).

```
                       STATICO (cambia mesi)        VIVO (cambia giorni)
                       ────────────────────────     ───────────────────────
AZIENDA (tutti)        L0 — Identità aziendale      L1 — Memoria aziendale
                       references/                  MEMORY.md (radice)

REPARTO (team)         L2 — Procedure & playbook    L3 — Vita del reparto
                       reparti/<X>/procedure/       reparti/<X>/MEMORY.md

OGGETTO (1 cosa)       L4 — Knowledge di X          L5 — Operativo / Daily
                       clienti/<X>/, fornitori/<X>/  Daily/<iniziali>/
                       commesse/<X>/
```

### Tabella canonica

| Layer | Nome | Path | Cosa contiene | Frequenza scrittura | Quando viene caricato |
|---|---|---|---|---|---|
| **L0** | Identità aziendale | `vault/references/` | Chi siamo, brand voice, valori, organigramma, glossario | trimestrale | on-demand quando il task richiede tono/posizionamento/glossario |
| **L1** | Memoria aziendale | `vault/MEMORY.md` | Decisioni cross-reparto | mensile | a ogni "Buongiorno" di chiunque |
| **L2** | Procedure & playbook | `vault/reparti/<reparto>/procedure/` | SOP, checklist, modulistica, template | mensile | quando il task tocca quel reparto |
| **L3** | Vita del reparto | `vault/reparti/<reparto>/MEMORY.md` | Decisioni di reparto, stand-up sintetici | settimanale | quando apri un task del reparto |
| **L4** | Knowledge di oggetto | `vault/clienti/<X>/`, `vault/fornitori/<X>/`, `vault/commesse/<X>/` | Schede, storico, decisioni datate, persone, allegati linkati | per evento | quando apri quell'oggetto |
| **L5** | Operativo personale | `vault/Daily/<iniziali>/YYYY-MM/YYYY-MM-DD.md` | Journal della persona, sparks, suoi task | quotidiana | sempre, per la persona loggata |

### Esempio caricamento

> Maria (commerciale, MR) apre alle 9:00. Claude legge L1 (MEMORY.md) + L5 di MR. Alle 9:30 lavora su offerta Rossi Srl → Claude carica L4 (`clienti/rossi-srl/`). Apre template offerta → richiama L2 (`reparti/commerciale/procedure/sop-offerte.md`). Stesura testo → L0 (`references/brand-voice.md`) on-demand. Mai tutto insieme.

---

## 2. Top-level del vault PMI

```
vault/
├── CLAUDE.md                   # kernel (multi-utente, ruoli, regole)
├── MEMORY.md                   # L1 aziendale
├── references/                 # L0
│   ├── chi-siamo.md
│   ├── organigramma.md
│   ├── glossario.md
│   ├── persone.md              # tabella iniziali/ruoli/email (vedi sezione 3)
│   └── brand-voice.md
├── reparti/                    # L2 + L3
│   └── _esempio/
│       ├── _esempio.md         # MOC del reparto
│       ├── MEMORY.md           # L3
│       ├── procedure/          # L2
│       │   └── sop-_esempio.md
│       └── _proposte-promozione.md
├── clienti/                    # L4
│   └── _esempio/
│       ├── _esempio.md         # MOC
│       ├── CLAUDE.md
│       ├── MEMORY.md
│       ├── tasks.md
│       ├── persone.md          # 5° file Regola 01-PMI
│       └── riunioni/
├── fornitori/                  # L4
│   └── _esempio/
├── commesse/                   # L4
│   └── _esempio/
├── decisioni/                  # ADR aziendali
└── Daily/                      # L5 per-persona
    └── _esempio-XX/            # XX = iniziali persona
        └── 2026-05/
```

---

## 3. Ruoli (4 + 1)

| Ruolo | Quanti per azienda | Cosa fa | Cosa NON fa |
|---|---|---|---|
| **Owner** | 1 (direzione) | Approva L0 e L1. Decide perimetro. Firma decisioni cross-reparto | Non scrive contenuti operativi |
| **Custode** | 1 ogni 10-15 dipendenti (per reparto se 30-50) | Garantisce salute L2/L3. Rituale settimanale di promozione. Tiene puliti i template | Non decide contenuto di business |
| **Editor** | 3-8 a seconda taglia | Scrive e revisiona L2/L3/L4. Tipicamente senior di ogni reparto | Non tocca L0/L1 senza Owner |
| **Contributor** | tutti gli altri | Scrive bozze in L4/L5. Logga la propria giornata in L5 | Non merge in L1/L2 da solo |
| **(Lettore)** | esterni (tirocinanti, fornitori) | Solo lettura | Tutto il resto |

### `vault/references/persone.md` — meccanismo

```markdown
| Iniziali | Nome           | Reparto       | Ruolo wiki   | Email                    |
|----------|----------------|---------------|--------------|--------------------------|
| MR       | Maria Rossi    | Commerciale   | Editor       | m.rossi@azienda.it       |
| LV       | Luca Verdi     | Commerciale   | Contributor  | l.verdi@azienda.it       |
| GB       | Giulia Bianchi | Amministraz.  | Custode      | g.bianchi@azienda.it     |
| AF       | Anna Ferrari   | Direzione     | Owner        | a.ferrari@azienda.it     |
```

### Frontmatter permessi per file

```yaml
---
tipo: scheda-cliente
cliente: rossi-srl
owner: MR
editor: [MR, LV, GB]
visibilita: reparto            # azienda | reparto | privato
stato: vivo                    # bozza | vivo | archiviato
ultima-revisione: 2026-05-23
revisore: GB
---
```

Claude, prima di scrivere, legge il frontmatter e applica i permessi. Se l'utente attivo (variabile sessione: si dichiara con "Buongiorno Claude, sono MR") non è in `editor`, **rifiuta** e propone bozza in `_bozze/`.

---

## 4. Le 4 regole (3 mantenute + 1 nuova)

### Regola 1 — Bozza (rafforzata)
1. Leggi → 2. Bozza `.md` con `stato: bozza` → 3. Review interna (se editor multipli) → 4. OK owner → 5. Binario con naming `[cliente]_[tipo]_v[n]_YYYY-MM-DD.[ext]`

### Regola 2 — Regola 01-PMI (5 file invece di 4)
Ogni oggetto in `clienti/`, `fornitori/`, `commesse/`, `processi/`:
- `<slug>.md` (MOC)
- `CLAUDE.md`
- `MEMORY.md`
- `tasks.md`
- `persone.md` ← **NUOVO 5° file** (chi è chi, da entrambi i lati)

Opzionali: `riunioni/`, `knowledge/`, `post-mortem/`, `_archivio/`.

### Regola 3 — Verify-or-redo (estesa)
Aggiunge: verifica include il canale di pubblicazione (binario salvato nel posto giusto con naming convenzionale).

### Regola 4 — SSOT per oggetto (NUOVA, anti-Drive-caotico)
Per ogni cliente/fornitore/commessa/persona esiste **un solo** file di verità nel vault. Tutto il resto (allegati Drive, righe Excel) linka a quel file o ci viene riconciliato.

---

## 5. Protocollo a 3 livelli (sostituisce Buongiorno/Buonanotte single-user)

**Livello 1 — Personale (giornaliero)**
- "Buongiorno Claude, sono MR" → legge L1 + suo L5
- "Buonanotte Claude" → scrive nel suo daily. Propone promozioni → vanno in `reparti/<X>/_proposte-promozione.md`, NON in L1

**Livello 2 — Reparto (settimanale, Custode)**
- Venerdì 16:00, 30 min. Custode rivede `_proposte-promozione.md`. Decide: sale a L3, sale a L2 (nuova SOP), candidata a L1, scartata
- Aggiorna `reparti/<X>/MEMORY.md`

**Livello 3 — Azienda (mensile, Owner + Custodi)**
- Una volta al mese, 1h. Rivedono candidate a L1 e nuovi ADR. Aggiornano `MEMORY.md` aziendale

---

## 6. Gli 8 pattern di scrittura

(Da istanziare come `_esempio/` nel vault e descrivere in `06-framework-pmi.md`)

1. **Verbale riunione** — `reparti/<X>/riunioni/YYYY-MM-DD_titolo.md` o `clienti/<X>/riunioni/...`
2. **SOP** — `reparti/<X>/procedure/sop-<slug>.md` con versione, revisore, prossima-revisione
3. **Scheda cliente** — `clienti/<X>/<X>.md` (MOC) + 4 file Regola 01-PMI
4. **Scheda fornitore** — `fornitori/<X>/<X>.md` simile a cliente
5. **Post-mortem** — `reparti/<X>/post-mortem/...` con timeline, azioni correttive, candidate promozione
6. **ADR** — `vault/decisioni/YYYY-MM-DD_titolo.md` numerato (014, 015...)
7. **Onboarding role-based** — `reparti/<X>/onboarding/<ruolo>.md` (giorno 1, 2, 3...)
8. **Contatti rubrica** — `reparti/<X>/contatti.md` (tabella clienti/fornitori/interni/emergenze)

Ogni pattern ha: frontmatter standard, struttura base 5-8 righe, caso d'uso reale. Vedi il brief completo del subagente 2 nei dettagli (non duplico qui, lo trovi in `_brief-source/framework-pmi-full.md` se serve).

---

## 7. Variabile utente attivo

L'utente, all'apertura, dice "Buongiorno Claude, sono MR". Claude scrive le iniziali in una variabile di sessione e da quel momento:
- Filtra permessi sui file (frontmatter `editor`)
- Scrive log nel suo Daily/<XX>/
- Le promozioni proposte le firma con le sue iniziali

Se non dichiarate, Claude chiede "chi sei?" prima di scrivere.

---

## 8. Skill setup-wizard sdoppiata

- **setup-wizard-azienda**: una volta sola, lanciato dal Custode in Atto 1. Compila `references/chi-siamo.md`, `organigramma.md`, `persone.md`, scheletro reparti
- **setup-wizard-persona**: per ogni nuovo collega, 2 min. Aggiunge riga in `persone.md`, crea `Daily/<XX>/`, configura `[CONFIGURA QUI]` locale sulla sua macchina
