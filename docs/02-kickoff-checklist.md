# 02 — Kick-off checklist (Atto 1)

Mezza giornata on-site dal cliente. Questo è l'Atto 1 della delivery prodotto.

Obiettivo: alla fine della mezza giornata il cliente ha un **vault scheletro funzionante**, un **Custode formato sul wizard**, un **perimetro privacy scritto**, e una **lista delle sorgenti da scandagliare** nell'Atto 2.

---

## Pre-requisiti — cosa serve PRIMA del kick-off

Da concordare con il cliente nei 7-10 giorni prima dell'on-site. Email scritta, non telefonata. Se manca anche uno solo di questi punti, **rimanda**.

### Persone presenti

| Ruolo | Presenza | Per quanto |
|---|---|---|
| **Owner** (titolare o COO firmatario) | Obbligatorio | Almeno la prima ora + l'ultima mezz'ora |
| **Custode designato** (IT/Office manager) | Obbligatorio | Tutta la mezza giornata |
| **1-2 Editor del reparto pilota** | Consigliato | Per il wizard del reparto pilota (1 ora) |

Se l'Owner dice "non posso esserci, ci sarà il mio sostituto" → rimanda. È lui che deve firmare il perimetro privacy in presenza.

### Materiale dal cliente

- **Organigramma** (anche solo PDF o slide). Serve a popolare `references/organigramma.md` e `references/persone.md`.
- **Accessi admin alle sorgenti che vorranno scandagliare**:
  - Google Workspace: Super Admin o delega temporanea su Admin Console
  - Microsoft 365: Global Admin o Site Collection Admin sui SharePoint coinvolti
  - NAS / file server: account con lettura su tutte le condivisioni
  - Email: nominativo dell'account `info@` o equivalente, con accesso letture
- **Lista preliminare delle sorgenti** (anche fatta a voce in pre-call): "abbiamo un Drive condiviso 'Commerciale', uno 'Amministrazione', il NAS 'Produzione', e la casella `info@'`."
- **1 reparto pilota identificato**: con quale partono. Tipicamente Commerciale o Amministrazione. Non Produzione (troppi binari).

### Logistica

- Slot di **4 ore consecutive** (es. 9:00-13:00 o 14:00-18:00)
- Una sala riunioni con proiettore o TV per screen share
- Wi-Fi aziendale **e** tethering del tuo telefono (backup — se il loro Wi-Fi cade, l'Atto 1 si blocca)
- I tuoi laptop + Cowork già installato + Claude account loggato
- Repo `claude-second-brain` clonato sul tuo laptop, ramo `main`, sincronizzato

---

## Runtime — checklist ordinata della mezza giornata

Tempi indicativi. Aggiusta se il cliente è veloce o lento, ma non saltare blocchi.

### Blocco 1 — Test di idoneità (15 min)

Apertura. Owner + Custode presenti.

Domanda 1: *"Chi è il Custode? Una persona, nome e cognome?"*
- Se la risposta è una persona presente in sala → ✓
- Se la risposta è "lo decidiamo dopo" o "il team" → **stop**. Riprogramma. Non ha senso andare avanti.

Domanda 2: *"[Nome Custode], hai 2-4 ore a settimana per i prossimi 3 mesi su questa cosa?"*
- Se sì → ✓
- Se "vediamo" o "dipende dai progetti" → flag rosso. Spiega al Custode + Owner che è il punto debole e probabilmente fallirà. Lasciali decidere se procedere.

Domanda 3 (all'Owner): *"Sei d'accordo che il vault diventi *il* posto canonico della conoscenza aziendale del reparto pilota?"*
- Se sì → ✓ (importante: "del reparto pilota", non "di tutta l'azienda". Si parte da uno, si estende dopo).
- Se "lo vediamo strada facendo" → flag rosso, ma si può procedere se Custode è solido.

Domanda 4: *"C'è un caso d'uso doloroso quotidiano che il wiki risolverebbe? Datemi un esempio concreto, non la teoria."*
- Devi sentire una storia concreta, non un'astrazione. Es. *"Quando entra un commerciale nuovo passa 3 settimane a chiedere a Mario dove sono i contratti dei clienti grandi."*
- Se non c'è una storia concreta → flag arancione. Spiega che senza dolore quotidiano il vault non viene usato.

**Output del blocco**: 4 sì espliciti scritti su un foglio (anche un Notion al volo, una mail, un appunto). Senza i 4 sì non si va avanti. Tu hai la responsabilità di dirlo.

### Blocco 2 — Perimetro privacy (30 min)

Owner + Custode. Owner deve firmare.

Si compila a voce, tu scrivi su `vault/references/perimetro-privacy.md`. Domande:

1. **Cosa Claude può leggere**:
   - Quali Drive condivisi? Quali cartelle?
   - Quale casella email? Quali etichette/cartelle dentro la casella?
   - Quale NAS? Quali share?
   - Quali sistemi NON tocca esplicitamente (es. cartelle HR, retribuzioni, dossier sensibili)?

2. **Dove vivono i dati durante l'elaborazione**:
   - Claude Cowork/Code legge i file localmente sul laptop del Custode
   - Per lo scandagliamento di Atto 2, le bozze passano sui server Anthropic via API — dichiararlo esplicitamente
   - Non c'è server intermedio terzo, non c'è copia in cloud nostro

3. **Cosa resta nel vault e cosa no**:
   - Nel vault entrano `.md` (testo) e link ai binari originali. Mai copie dei binari.
   - Per dati personali (PII): si convertono in iniziali / ID interni nei file `.md`. Es. "Mario Rossi" → "MR".

4. **Diritto di cancellazione**:
   - Il vault è una cartella sui sistemi del cliente. Si cancella eliminando la cartella.
   - Le bozze passate ad Anthropic seguono la loro retention policy (vedi documentazione Anthropic — riportare URL nel doc).

**Output**: `vault/references/perimetro-privacy.md` compilato, stampato, firmato dall'Owner. Una copia resta in azienda, una scansione resta sul tuo laptop.

### Blocco 3 — Wizard azienda (60 min)

Custode al timone, Owner per le risposte di posizionamento. Tu siedi accanto, suggerisci ma non scrivi tu.

Apri Cowork sul vault. Fai eseguire al Custode il prompt della skill `setup-wizard-azienda` (descritta in `skills/setup-wizard/` — il Custode la lancia, non sei tu):

```
Leggi skills/setup-wizard-azienda/SKILL.md e segui le istruzioni
per configurare la wiki della nostra azienda.
```

La skill chiede 5-8 informazioni:

1. Nome azienda, settore, dimensione (popola `references/chi-siamo.md`)
2. Organigramma (popola `references/organigramma.md` da quello che hanno portato)
3. Persone — iniziali, ruoli, email, ruolo wiki (Owner/Custode/Editor/Contributor) → popola `references/persone.md`
4. Reparti che esistono in azienda → crea scheletro `vault/reparti/<X>/`
5. Reparto pilota da cui partire → segna in `MEMORY.md`
6. Brand voice / tono di scrittura aziendale (1-2 frasi) → popola `references/brand-voice.md`
7. Glossario di base (5-10 termini specifici del settore) → popola `references/glossario.md`

Alla fine il Custode rivede, conferma. Il vault scheletro è in piedi.

**Output**: vault popolato con i 5 file di `references/` + scheletro `reparti/`. Si vede in Obsidian.

### Blocco 4 — Connessione MCP (45 min)

Custode al tasto, tu accanto. Owner non serve qui.

Si configurano gli MCP per le sorgenti dichiarate nel perimetro:

1. **Google Drive MCP** (se serve) — login Custode con account che ha lettura sui Drive concordati
2. **Microsoft 365 MCP** (se serve) — login Custode su tenant aziendale
3. **NAS** — montaggio share su laptop Custode con permessi di lettura
4. **Email** — IMAP read-only sull'account dichiarato, oppure MCP Gmail/Outlook se disponibile

Test rapido per ognuno: si fa chiedere a Claude *"elenca le top 10 cartelle in /Drive/Commerciale ordinate per dimensione"* e si verifica che risponda con qualcosa di sensato.

Se uno degli MCP non si connette in 15 minuti: NON insistere in sala. Annotalo come azione di follow-up del Custode entro 48h. Si rimanda lo scandagliamento di quella sorgente di una settimana.

**Output**: lista delle sorgenti con stato (✓ connessa / ⏳ da connettere entro X) nel file `vault/_audit/sources.md`.

### Blocco 5 — Inventario rapido (30 min)

Custode al tasto, tu osservi. Owner può rientrare.

Si esegue manualmente (NON con scanner — quello è Atto 2) un inventario rapido per orientare l'Atto 2. Comandi bash sulle sorgenti, o le query MCP equivalenti:

```bash
# GB totali e numero file per ogni sorgente concordata
du -sh /Volumes/NAS/condiviso/Commerciale/
find /Volumes/NAS/condiviso/Commerciale/ -type f | wc -l

# File toccati negli ultimi 12 mesi (proxy di "vivo")
find /Volumes/NAS/condiviso/Commerciale/ -type f -mtime -365 | wc -l
```

Si compila a mano una tabella in `vault/_audit/sources.md`:

| Sorgente | Volume (GB) | File totali | File freschi (12 mesi) | Reparto principale | Priorità Atto 2 |
|---|---|---|---|---|---|
| Drive "Commerciale" | 47 | 12.400 | 3.100 | Commerciale | Alta |
| Drive "Amministrazione" | 22 | 6.800 | 1.900 | Amministrazione | Media |
| NAS "Produzione" | 240 | 45.000 | 4.500 | Produzione | Bassa (CAD vivi, restano lì) |
| Casella `info@` | 7 | 8.200 mail | 8.200 | Commerciale | Alta (allegati unica copia) |

**Output**: `vault/_audit/sources.md` compilato, priorità concordate con Custode + Owner.

### Blocco 6 — Reparto pilota e prossimi passi (30 min)

Tutti presenti. Si chiude.

1. Si conferma il **reparto pilota** scelto e lo si scrive in `vault/MEMORY.md` come prima decisione aziendale (ADR-001).
2. Si stabilisce la **call settimanale Atto 2**: giorno fisso, orario fisso, 30 minuti, Custode + tu. Calendar invite creato in sala.
3. Si concorda il **canale operativo Atto 2**: email o Slack/Teams condiviso. Owner non serve nei daily — serve solo per gli sblocchi.
4. Si scrive una **mail riepilogativa** all'Owner e al Custode con: cosa fatto oggi, prossima call (data), prossimo on-site previsto (Atto 3, data tentativa). La mail include il perimetro privacy firmato in allegato.

---

## Output atteso a fine giornata

Sul laptop del Custode (e sincronizzato con copia tua):

```
vault/
├── CLAUDE.md                        # kernel multi-utente (già nel template)
├── MEMORY.md                        # ADR-001 = reparto pilota
├── references/
│   ├── chi-siamo.md                 ✓ compilato
│   ├── organigramma.md              ✓ compilato
│   ├── persone.md                   ✓ compilato
│   ├── brand-voice.md               ✓ compilato
│   ├── glossario.md                 ✓ compilato (5-10 termini)
│   └── perimetro-privacy.md         ✓ compilato e firmato
├── reparti/
│   ├── commerciale/                 ✓ scheletro (se è il pilota)
│   ├── amministrazione/             ✓ scheletro
│   └── ...
└── _audit/
    └── sources.md                   ✓ compilato con priorità
```

E sul calendar:
- Call settimanale Atto 2 ricorrente (4-6 occorrenze)
- Slot proposto per Atto 3 (½ giornata on-site, +3-4 settimane)

E in azienda:
- Perimetro privacy firmato, copia cartacea o scan archiviato dall'Owner

---

## Anti-pattern — cose che vanno male

Riconoscile in tempo. Spesso si presentano nel Blocco 1, prima ancora di toccare il toolkit.

### Titolare assente

Sintomo: arrivi, c'è il Custode da solo. *"Il direttore ha avuto un imprevisto, dice che ci fidiamo del tuo giudizio."*

Cosa fai: **rinvii i Blocchi 1 e 2**. Spieghi che il perimetro privacy richiede firma in presenza. Resti per i Blocchi 3-5 solo se il Custode è autorizzato a procedere "tecnicamente" senza il perimetro firmato. Altrimenti smonti la sala e rifissi.

Eccezione: se l'Owner ti raggiunge nel tardo pomeriggio in remoto via call per firmare via DocuSign il perimetro che hai scritto col Custode, si può recuperare. Tutto il resto no.

### IT solo on-call

Sintomo: il Custode non è in sala, "ma se servono accessi lo chiamiamo".

Cosa fai: **stop, non si parte**. Senza Custode in sala l'Atto 1 non ha senso — il wizard è in mano sua, non tua. Rifissi.

### Perimetro vago

Sintomo: alla domanda "cosa Claude può leggere?", l'Owner risponde *"tutto quello che serve"*, *"vediamo strada facendo"*, *"a tua discrezione"*.

Cosa fai: spiega che non è negoziabile. Insisti per avere risposte secche per OGNI sorgente in `_audit/sources.md`. Se l'Owner non vuole impegnarsi, restringi tu: parti dal solo reparto pilota, ignori il resto. Aggiungi una nota in `perimetro-privacy.md`: *"Perimetro iniziale ristretto al solo reparto X. Estensioni richiedono nuovo perimetro firmato."*

### "Partiamo con tutti i reparti"

Sintomo: l'Owner spinge per coinvolgere tutti subito.

Cosa fai: spiega che il modello di crescita previsto è: mese 1 reparto pilota → mese 3 2-3 reparti → mese 6 azienda intera (vedi [`06-framework-pmi.md`](06-framework-pmi.md), sezione "Modello di crescita"). Partire con tutti = caos garantito, fallimento in 8 settimane. Insisti sul pilota.

### Custode che dice "io non ho tempo questa settimana"

Sintomo: il Custode dichiarato, in Blocco 1, spiega che ha 3 progetti urgenti e che parte tra 3 settimane.

Cosa fai: **proponi di rimandare il kick-off di 3 settimane**, fissalo ora con date. Non è recuperabile facendo l'Atto 1 e aspettando — il momentum si perde, le sorgenti scandagliate diventano stantie, il Custode arriva all'Atto 2 senza contesto.

### Wi-Fi che cade

Sintomo: il loro Wi-Fi non regge un account Google con SSO + Cowork + MCP attivi.

Cosa fai: switcha al tuo tethering. Annota in `MEMORY.md` di valutare con il Custode se serve una linea dedicata per le sessioni di scandagliamento. È un problema, non un blocco.

---

## Documenti collegati

- [`01-cosa-vendi.md`](01-cosa-vendi.md) — playbook commerciale, riferimento per le esclusioni dichiarate in pre-call
- [`03-scandagliamento.md`](03-scandagliamento.md) — cosa fai nelle 1-2 settimane dopo l'Atto 1
- [`04-handover-checklist.md`](04-handover-checklist.md) — l'Atto 3 chiude il ciclo
- [`05-manuale-custode.md`](05-manuale-custode.md) — Fase 0 e Fase 1 del manuale custode coprono la stessa materia dal lato cliente
