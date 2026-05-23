# 05 — Manuale custode

Il manuale operativo del Custode della wiki aziendale. Letto e usato dal Custode, non da chi vende.

---

## Premessa

Questo manuale ti è stato consegnato da Valentino Grossi alla chiusura dell'Atto 3 della delivery prodotto (vedi [`04-handover-checklist.md`](04-handover-checklist.md) — il documento che descrive cosa è successo nella mezza giornata in cui abbiamo chiuso il lavoro insieme).

Da oggi sei tu il Custode. Il vault (che chiameremo qui dentro anche "wiki" — usiamo i due termini come sinonimi) è sotto la tua responsabilità. Questo manuale è il tuo riferimento operativo.

Non è un'introduzione al framework — quella è in [`06-framework-pmi.md`](06-framework-pmi.md). Non è il playbook di chi te lo ha venduto — quello è in [`01-cosa-vendi.md`](01-cosa-vendi.md). Questo è **il protocollo che usi per gestire e far crescere il wiki nel quotidiano**.

Risponde alle domande:
- *Come gestisco la migrazione dei file ancora sparsi tra Drive, NAS, email?*
- *Come tengo pulito il vault settimana dopo settimana?*
- *Come faccio crescere il wiki da 1 reparto a 3-4 reparti senza che esploda?*
- *Cosa faccio quando un collega "scrive male" o non scrive affatto?*

---

## Per chi è davvero questo manuale

Sei una PMI tra **30 e 50 persone**, con sedimentazione digitale di 5-15 anni alle spalle: Drive condivisi nati per esigenza, cartelle "Definitivo_v2_FINAL", Excel vivi che girano per email, PDF di contratti mai OCR-ati, allegati Outlook che sono l'unica copia di certi documenti, NAS interno con disegni CAD e foto di cantieri, casella `info@` da 10.000+ email.

Se sei una PMI più piccola (5-15 persone), il manuale funziona ugualmente — basta scalare verso il basso i tempi e semplificare la governance (un Custode unico invece di Custodi per reparto, un solo rituale settimanale di mezz'ora invece di uno per ogni reparto).

Se sei una struttura grande (100+ persone, multi-sede, multi-business unit), il manuale è insufficiente — servono ruoli formali, sponsor esecutivo, change management. Riconvocaci.

**Regola d'oro:** non si "migra il Drive nel vault". Si **decide cosa entra, cosa resta fuori, cosa muore**. Il 60-70% del materiale esistente non deve nemmeno entrare nel vault. Più passi sei in grado di saltare, più probabilità hai di arrivare in fondo.

---

## Indice

- Fase 0 — Decidere se farlo davvero (10 min — già fatto in Atto 1, qui per riferimento)
- Fase 1 — Inventario (1-2 giorni — già fatto in Atto 1)
- Fase 2 — Categorizzazione (1 giorno)
- Fase 3 — Mapping al vault (mezza giornata)
- Fase 4 — Migrazione progressiva (settimane — l'Atto 2 ne ha già fatta una parte)
- Fase 5 — Decommissioning del vecchio (1 settimana — la mail è partita nell'Atto 3)
- Fase 6 — A regime: i rituali settimanali e mensili (per sempre)
- Le 6 trappole

---

## Fase 0 — Decidere se farlo davvero (riferimento)

Hai già fatto questo test in Atto 1 di delivery. Se ora stai leggendo questo manuale, hai superato i 4 sì. Lo lasciamo qui come **promemoria**: se qualcuno in azienda dovesse rimettere in discussione il progetto fra 6 mesi, ecco i 4 sì che avete dato.

### Quando ha senso

- C'è **una persona** (sei tu) che si prende la responsabilità del vault. Non un comitato.
- Il team coinvolto è tra **30 e 50 persone**. Per organizzarci useremo **Custodi per reparto** (vedi più sotto): una persona per il commerciale, una per l'amministrazione, una per la produzione, ecc.
- L'azienda è in una **fase stabile o di crescita ordinata**. Se siete nel mezzo di una ristrutturazione, il wiki si ferma.
- Esiste già una **abitudine minima a scrivere**. Se nessuno scrive mai nulla, il vault diventa una cartella vuota.

### Quando NON ha senso (4 casi di fallimento)

1. **Nessun custode.** Senza Custodi (uno o più) con nome e cognome, il vault muore in 6 settimane.
2. **Cultura "ognuno il suo file".** Cambiare questa cultura è change management, non documentazione.
3. **Turnover sopra il 30% annuo.** La conoscenza evapora con le persone.
4. **Troppe persone con potere di veto.** Se ogni decisione passa per 5 persone, non si parte mai.

### Test rapido (4 sì = procedi)

1. C'è una persona con nome e cognome (e per ogni reparto principale, idealmente) che farà da custode?
2. Ogni Custode ha **3-5 ore a settimana** per i prossimi 3 mesi (di più rispetto a una micro-impresa, perché qui ci sono più reparti e più volume)?
3. La direzione è d'accordo che il wiki diventi *il* posto canonico, almeno per i reparti coinvolti?
4. Esistono **almeno 2-3 casi d'uso dolorosi** quotidiani che il wiki risolverebbe?

### Output Fase 0

Una mail al titolare con: chi è il Custode (o i Custodi per reparto), ore a settimana, 2-3 dolori da risolvere, check-up a 3 mesi. È stata mandata in Atto 1 — verifica che ne hai una copia in `vault/references/perimetro-privacy.md` o in `MEMORY.md`.

---

## Custodi per reparto — il modello in PMI 30-50

In una PMI di 30-50 persone con 4-6 reparti, **un Custode unico è insufficiente** dopo i primi 2-3 mesi. Il modello a regime è:

- **1 Custode "capo"** (idealmente tu, se sei IT/Office manager) — coordina, gestisce il rituale mensile con l'Owner, è il riferimento per i casi complessi
- **1 Custode di reparto** per ogni reparto attivo sul wiki — è una persona "senior" del reparto stesso, idealmente un Editor con autorità tecnica e relazionale

| Custode di | Ruolo tipico | Carico di lavoro |
|---|---|---|
| Commerciale | Senior commerciale, capo-area, sales ops | 3-4 h/sett |
| Amministrazione | Responsabile amministrativo | 2-3 h/sett |
| Produzione | Capo-reparto produzione, RTP | 2-3 h/sett |
| Acquisti / Fornitori | Buyer senior | 1-2 h/sett |

Il Custode capo (tu) ha responsabilità trasversali:
- Setup tecnico e accessi
- Rituale mensile con Owner
- Risoluzione conflitti tra reparti
- Mantenimento dei file `references/` aziendali (chi-siamo, organigramma, persone, glossario)
- Coordinamento dei rituali settimanali dei Custodi di reparto

**Quando designare un Custode di reparto**: appena un reparto inizia a usare il wiki regolarmente (3-5 persone che ci scrivono ogni settimana). Prima è inutile, dopo è tardi.

---

## Fase 1 — Inventario (riferimento — già fatto in Atto 1)

Il primo inventario l'avete fatto in Atto 1 (Blocco 5 di [`02-kickoff-checklist.md`](02-kickoff-checklist.md)). I risultati sono in `vault/_audit/sources.md`.

Quando aprite un **reparto nuovo** post-handover (mese 3, 6, ecc.), rifate l'inventario per quel reparto. Stessa procedura, stessi comandi. Per PMI 30-50, ogni nuovo reparto può comportare 100-500 GB di sorgenti aggiuntive — non sottovalutarlo.

### Strumenti pratici

```bash
# GB totali
du -sh /Volumes/NAS/condiviso/Produzione/

# Albero a 2 livelli con dimensione
du -h --max-depth=2 /Volumes/NAS/condiviso/Produzione/ | sort -h

# File toccati negli ultimi 12 mesi
find /Volumes/NAS/condiviso/Produzione/ -type f -mtime -365 | wc -l

# File non toccati da 3+ anni (candidati archivio)
find /Volumes/NAS/condiviso/Produzione/ -type f -mtime +1095 | wc -l

# Top 10 estensioni
find /Volumes/NAS/condiviso/Produzione/ -type f | sed 's/.*\.//' | sort | uniq -c | sort -rn | head -10

# Candidati duplicati per nome
find /Volumes/NAS/condiviso/Produzione/ -type f \( -iname '*final*' -o -iname '*definitivo*' -o -iname '*copia*' \) | head -50
```

Per Google Drive: admin console o `rclone`. Per M365: PowerShell `Get-PnPListItem`. Per email: NON tutto, solo cartelle/etichette dove vivono gli allegati "unica copia" (Clienti, Fornitori, Contratti).

### Output

Aggiornamento di `_audit/sources.md` con le nuove sorgenti del reparto:

| Isola | Volume (GB) | File totali | File freschi (12 mesi) | Reparto | Note |
|---|---|---|---|---|---|
| Drive "Commerciale" | 47 | 12.400 | 3.100 | Commerciale | Molti _FINAL, struttura a clienti |
| NAS "Produzione" | 240 | 45.000 | 4.500 | Produzione | Disegni CAD, foto cantieri |
| Allegati Outlook "Clienti" | 7 | 8.200 | 8.200 | Commerciale | Ordini, conferme |
| Drive "Acquisti" | 30 | 8.500 | 1.800 | Acquisti | Listini, contratti fornitori |

### Esempio

> **Officina meccanica conto-terzi, Brescia, 38 persone.** Laura (Custode capo) coordina con Marco (Custode commerciale) e Giulia (Custode produzione). Inventario in 2 giorni distribuiti. NAS 1,2 TB (800 GB CAD vivi, 200 GB foto cantieri, 200 GB varie), Drive "Commerciale" 60 GB offerte+contratti, Drive "Acquisti" 30 GB listini+fornitori, casella `info@` 18.000 mail. Decisione: NAS Produzione resta lì (CAD vivi), si lavora su Commerciale + Acquisti + casella `info@`.

### Trappole

- **Inventario perfetto**: 2 giorni distribuiti, non 2 settimane
- **"Guardiamo dentro"**: non aprire i file. Conti, non leggi
- **Giudizio anticipato**: niente "questo lo buttiamo" in Fase 1

---

## Fase 2 — Categorizzazione (1 giorno per reparto)

Decidi **per categoria**, non file per file. Il file-per-file è la **trappola dell'archivista perfetto**.

### Le 5 categorie

| Categoria | Cos'è | Dove va |
|---|---|---|
| **VIVO** | Toccato nelle ultime 4-12 settimane, lavoro corrente | Migra nel vault o linka |
| **DA CONSULTARE** | Riferimenti saltuari: contratti firmati, normative | Resta dov'è, linkato dal vault |
| **ARCHIVIO** | Vecchio ma da tenere: bilanci, progetti chiusi | `_ARCHIVIO/` sul Drive vecchio, sola lettura |
| **CESTINO** | Duplicati, bozze obsolete, `_v2_OLD` | Cestino dopo backup |
| **DA CHIARIRE** | Non si capisce cos'è o di chi | Lista, smaltita in Fase 4 (in Atto 3 sono chiuse, dopo torneranno in altri reparti) |

### Come decidi

Non apri file. Apri **cartelle** e decidi a livello cartella.

| Cartella | GB | Categoria | Note |
|---|---|---|---|
| `/Drive/Clienti/Attivi/` | 12 | VIVO | Migra |
| `/Drive/Clienti/Persi-2018-2020/` | 4 | ARCHIVIO | Sposta in `_ARCHIVIO/` |
| `/Drive/_vecchio_NON_USARE/` | 15 | CESTINO | Backup + cestina |

### Chi decide

Il **Custode di reparto** decide per il suo reparto. Un'ora silenziosa col foglio. **Antipattern micidiale**: meeting di 2 ore con 5 persone. Esito: 0 decisioni, tutti si ricordano un caso particolare, si rimanda.

Il **Custode capo** ha veto solo su categorie di sicurezza/privacy (es. "questa cartella ha PII, non si tocca").

### Output

Il foglio di Fase 1 con colonna **categoria** compilata per ogni cartella. Vive in `vault/_audit/sources.md`.

### Trappole

- **Archivista perfetto**: cartella, non file
- **"Ma chissà se serve"**: default = ARCHIVIO, non VIVO
- **Comitato**: non si decide in 5

---

## Fase 3 — Mapping al vault (mezza giornata per reparto)

### Il vault NON è un Drive

Il vault contiene:
- File `.md` (note, MOC, MEMORY, decisioni, schede)
- Pochi PDF/immagini piccoli (logo, schema chiave, organigramma)
- **Link** a tutto il resto

Il vault NON contiene:
- File CAD, video, archivi ZIP → restano dove sono, linkati
- Excel "vivi" condivisi → linkati
- PDF contratti firmati 50 MB → linkati
- Backup, log, dump → mai

**Test**: per PMI 30-50, se `vault/` supera 5 GB hai sbagliato. Sano: 200 MB - 2 GB. Se sta crescendo perché ci sono PDF "incollati dentro", separali e linkali.

### Esempio mapping

```
Categoria VIVO ──→ vault/clienti/<X>/, vault/fornitori/<X>/, vault/commesse/<X>/
                   (con i 5 file Regola 01-PMI: <slug>.md, CLAUDE.md, MEMORY.md, tasks.md, persone.md)
Categoria DA CONSULTARE ──→ vault/references/, indici in vault/reparti/<X>/
                            (file su Drive, riferimenti nel vault)
Categoria ARCHIVIO ──→ NON entra. Resta sul Drive in sola lettura.
Categoria CESTINO ──→ Cestinato.
Categoria DA CHIARIRE ──→ vault/_pending/da-chiarire.md (temporanea, risolta nei rituali)
```

### Convenzione di link a file esterni

In una PMI 30-50 spesso convivono **più ambienti** (Drive aziendale + SharePoint per amministrazione + NAS produzione). Per non impazzire, scegli **una convenzione e definiscila in `vault/CLAUDE.md`**.

**Modo 1 — URL Drive/SharePoint (raccomandato per cloud)**
```markdown
- [Contratto Rossi Srl 2024](https://drive.google.com/file/d/1aB2cD.../view)
- [Procedura ISO 9001 vers. 7](https://azienda.sharepoint.com/sites/qualita/...)
```
Pro: funziona ovunque. Contro: se sposti, link si rompe (ma Google/SharePoint redirectano).

**Modo 2 — Path locale (per NAS)**
Definisci `/Volumes/NAS/produzione/` (Mac) o `Z:\produzione\` (Windows) in `CLAUDE.md`.
```markdown
- [Disegno CAD 4521](file:///Volumes/NAS/produzione/CAD/4521.dwg)
```
Pro: offline. Contro: path Mac vs Windows differente.

**Modo 3 — Path logico + mappa**
```markdown
- Vedi `[NAS-PROD]/CAD/4521.dwg`
```
In `vault/references/dove-sta-cosa.md`:
```markdown
- `[NAS-PROD]` → `/Volumes/NAS/produzione/` (Mac) o `Z:\produzione\` (Windows)
- `[NAS-COMM]` → `/Volumes/NAS/commerciale/` (Mac) o `Y:\commerciale\` (Windows)
```

Scegli **un solo modo per ambiente**. Cambiare a metà = **trappola della doppia convenzione**.

### Naming dei link

Cattivo: `[Documento](https://drive.google.com/...)`
Buono: `[Contratto Rossi Srl – firmato 2024-03-12](https://drive.google.com/...)`

### Governance della struttura

In PMI 30-50 ci sono **molti potenziali top-level**. Tieni una lista ristretta. Il vault tipico ha:

```
vault/
├── CLAUDE.md
├── MEMORY.md                       # L1 aziendale
├── references/                     # L0
├── reparti/                        # L2 + L3 per reparto
│   ├── commerciale/
│   ├── amministrazione/
│   ├── produzione/
│   └── acquisti/
├── clienti/                        # L4
├── fornitori/                      # L4
├── commesse/                       # L4 (se gestite a commessa)
└── decisioni/                      # ADR aziendali
```

Resisti alla tentazione di creare top-level "per progetto trasversale" (es. `vault/iso-9001/`). Quelle stanno in `reparti/qualita/` o in `decisioni/`.

### Output

1. Struttura vault decisa nel foglio
2. Convenzione di link scritta in `vault/CLAUDE.md`
3. Script bash che crea le cartelle (o si fa creare alla skill `setup-wizard-azienda` per il reparto nuovo)

### Trappole

- **Clone del Drive**: tentazione di copiare tutto. No
- **Doppia convenzione**: scegli uno e attienitici
- **Top-level infinito**: 4-6 top-level all'inizio, max

---

## Fase 4 — Migrazione progressiva (settimane, non giorni)

Per il reparto pilota una parte è già stata fatta in Atto 2 con Valentino al fianco. Per i **reparti successivi** (mese 3, mese 6) la fai tu o il Custode di reparto, da soli o con la skill `vault-extract`.

Non si migra tutto in una volta. Batch settimanali.

### Strategie di batching (scegli UNA per reparto)

| Strategia | Quando | Esempio |
|---|---|---|
| **Per cliente** | 30-100 clienti attivi | Sett 1: top 10 cliente. Sett 2: 10-20 |
| **Per anno** | Dati strutturati per anno | Sett 1: 2024. Sett 2: 2023. Stop |
| **Per ruolo** | Categorie funzionali nette | Sett 1: commerciale. Sett 2: amministrazione |
| **Per criticità** | Un dolore specifico | Sett 1: scheda dei top 10 clienti più richiesti |

**Raccomandazione per PMI 30-50**: per cliente o per criticità. Procedi a strati: top 10 clienti / top 10 fornitori / top 10 commesse attive. Poi cresci.

### Estrai vs linki

| Situazione | Cosa fai |
|---|---|
| PDF 80 pp, contratto firmato, 1-2 volte/anno | Linki |
| PDF 20 pp, manuale fornitore consultato ogni settimana | Estrai passaggi chiave, linki originale |
| PDF 5 pp, brief cliente arrivato oggi | Estrai tutto in `knowledge/brief-YYYY-MM-DD.md` |
| Email lunga con decisioni | Estrai decisioni in MEMORY del cliente |
| Trascrizione call 1h | Estrai punti chiave, trascrizione full linkata |
| Disegno CAD | NON estrai mai. Linki e basta. |
| Foglio Excel "calcolo offerte 2024" vivo | Linki, NON copi. Eventualmente aggiungi una scheda `.md` con la spiegazione di cosa fa |

### Ruolo di Claude

> *Tu (Custode)*: "Brief Rossi (4 pagine, incollato). Estraimi: obiettivi, vincoli, scadenze, decisioni. Markdown in `clienti/rossi-srl/knowledge/brief-2024-03-12.md`."
> 
> *Claude*: produce la nota. Tu rileggi, correggi, salvi.

Vale la **Regola della Bozza**: prima bozza, OK esplicito, poi salvataggio.

### Settimana tipo (per Custode di reparto a regime)

> **Studio amministrativo dentro PMI manifatturiera, 35 persone, Custode Giulia — settimana 3 post-handover, sta migrando i 10 fornitori principali**
> - **Lun 90 min**: 200 file fornitori → 40 VIVO, 130 ARCHIVIO, 25 CESTINO, 5 DA CHIARIRE
> - **Mar 60 min**: estrazione con Claude dei 5 fornitori più importanti (contratti, listini, persone)
> - **Mer 30 min**: scrive a mano in MEMORY le 8 decisioni "in testa" su fornitori (es. "il fornitore Bianchi Forniture risponde solo via PEC, non email")
> - **Gio 30 min**: compila MOC fornitore + scheda persone
> - **Ven 15 min**: sposta CESTINO in `_DA_CESTINARE_2026-05/`, manda i 5 DA CHIARIRE in agenda del rituale settimanale del Custode capo (Laura)
> 
> **Totale: 3,5 ore.** 5 fornitori migrati. Settimana prossima i prossimi 5.

### Definizione di "done" per un oggetto migrato

1. MOC esiste con frontmatter completo
2. CLAUDE.md ha 2-3 righe di contesto specifico
3. MEMORY ha almeno 3-5 decisioni/contesti
4. persone.md ha la rubrica delle persone interne ed esterne
5. tasks.md ha almeno 1 task aperto (anche solo "ricontatta a settembre")
6. Link funzionano
7. CESTINO in `_DA_CESTINARE_/`
8. Nota datata in Daily del Custode

### Trappole

- **Big Bang**: 2-4h/sett × 8-12 sett per reparto. Non 2 settimane filate
- **Estrazione totale**: estrai solo cose dense e ricorrenti
- **Perfezionismo**: vera e linkata > bella
- **"Non ho tempo questa settimana"**: 1h/sett ogni sett > 6h una volta al mese

---

## Fase 5 — Decommissioning (1 settimana, dopo 2-3 mesi di uso del reparto)

Per il reparto pilota, la mail di decommissioning è partita in Atto 3 ([`04-handover-checklist.md`](04-handover-checklist.md), Blocco 4). L'esecuzione tecnica (Drive in sola lettura) la fai tu nei 14 giorni successivi.

Per i reparti successivi (mese 3, 6, ecc.), ricominci il ciclo Fase 0 → Fase 5 per quel reparto.

### Quando attivare

3 sì:
1. Vault in uso quotidiano del reparto da 2+ mesi?
2. Tutti gli oggetti VIVI del reparto migrati?
3. Drive vecchio aperto < 3 volte negli ultimi 30 gg per cose VIVE?

### Comunicazione

Mail, non meeting. Modello già usato in Atto 3 — riusalo per i reparti successivi adattandolo.

### Esecuzione

Drive Google/M365: revoca scrittura a tutti tranne Custode di reparto. NAS: read-only o sposta in `_ARCHIVIO/`. Per evitare panico: prima di revocare, fai un test con 2-3 persone chiave (es. "ti faccio togliere la scrittura su Drive Commerciale, ti aspetto venerdì per il riscontro").

### Le 2-3 persone che continuano

1. Pair-working di 30 min con chi si lamenta
2. Recidivi: colloquio con il loro responsabile, non con te. In PMI 30-50 c'è una catena gerarchica — usala
3. **Non riapri scrittura sul vecchio**. Mai. Se lo fai, hai perso

### A 6 mesi (per reparto)

```bash
find /Volumes/Drive-vecchio/Reparto-X/ -type f -atime +180 | wc -l
```

Probabilmente 90% non acceduto = categorizzazione giusta. 10% acceduto: o lo migri (mini-batch), o lo lasci dov'è.

**Non chiudi mai definitivamente il Drive vecchio.** Sola lettura, indefinitamente.

### Output

1. Mail al team del reparto partita
2. Drive del reparto in sola lettura (testato)
3. Nota in `references/dove-sta-cosa.md`
4. Nota in `reparti/<X>/MEMORY.md`: "Migrazione completata il [data]"

### Trappole

- **Soft-deadline**: data scritta, azione tecnica, mail
- **Deroga**: una persona = tutti
- **"Cancelliamo il vecchio"**: sola lettura, mai cancellato

---

## Fase 6 — A regime: i rituali settimanali e mensili

Dopo i primi 2-3 mesi su un reparto, il lavoro di **migrazione** scende, sale il lavoro di **mantenimento**. Sono i 3 rituali del framework PMI (vedi [`06-framework-pmi.md`](06-framework-pmi.md), sezione "Protocollo a 3 livelli"). Te li ricordiamo qui in chiave operativa.

### 6.1 — Rituale personale giornaliero

> Chi: ogni dipendente che usa Claude.
> Quanto: 2 minuti al mattino + 2 minuti alla sera.
> Skill: `session-lifecycle`.

Ognuno apre la propria sessione con *"Buongiorno Claude, sono [iniziali]"*, lavora, chiude con *"Buonanotte Claude"*. Le iniziali servono perché Claude carichi il **suo daily**, non quello di qualcun altro.

Tuo ruolo: **non controlli i daily delle persone**. Sono privati al loro autore (frontmatter `visibilita: privato`). Controlli solo che la skill `session-lifecycle` sia configurata correttamente in `vault/CLAUDE.md`.

Se un nuovo collega entra: lanci la skill `setup-wizard-persona` (2 minuti), che:
- Aggiunge la riga in `vault/references/persone.md`
- Crea `vault/Daily/<XX>/`
- Aggiorna il `[CONFIGURA QUI]` sulla sua macchina

### 6.2 — Rituale settimanale del Custode di reparto

> Chi: ogni Custode di reparto (compreso te per i reparti che presidi direttamente).
> Quanto: 30 minuti, venerdì pomeriggio fisso.
> Skill: `rituale-settimanale-custode`.

Loop fisso ogni venerdì:

1. **Apri `vault/reparti/<X>/_proposte-promozione.md`** — vedi le proposte accumulate durante la settimana
2. **Decidi per ogni proposta**:
   - Sale a L3 (`reparti/<X>/MEMORY.md`)
   - Sale a L2 (`reparti/<X>/procedure/sop-<slug>.md`)
   - Candidata a L1 (mensile con Owner)
   - Scartata
3. **Lancia `vault-lint`** — verifica frontmatter, link rotti, file orfani, naming. Risolvi gli errori che riporta
4. **Pulisci `_pending/da-chiarire.md`** del reparto — chiudi le voci ferme da > 14 giorni (o decidendo, o eliminandole)
5. **Aggiorna `reparti/<X>/MEMORY.md`** con le decisioni del reparto della settimana

Se sei Custode di più di un reparto: 30 min × reparto, distribuiti nella giornata.

### 6.3 — Rituale mensile Owner + Custodi

> Chi: Owner + tutti i Custodi (capo + di reparto).
> Quanto: 1 ora, primo venerdì del mese fisso.
> Skill: `rituale-mensile-owner`.

Loop fisso:

1. **Rivedi candidate a L1**: ogni Custode porta 0-5 proposte accumulate nei 4 rituali settimanali. Owner decide chi sale a `vault/MEMORY.md` aziendale
2. **Rivedi ADR cross-reparto** in `vault/decisioni/`: Owner firma quelle pendenti (`approvato-da: AF`)
3. **Salute del vault**: 5 minuti di check sintetico
   - Numero file vivi per reparto (trend rispetto al mese scorso)
   - MOC mancanti o vuoti
   - Reparti con `_proposte-promozione.md` vuoto da > 4 settimane (segnale di disuso)
   - Costo Claude API mensile (se misurato — vedi sotto)
4. **Decisioni di espansione**: serve aprire un nuovo reparto? Designare un nuovo Custode di reparto? Pensionare un Custode che ha cambiato ruolo?

### Tracciamento del costo Claude

Se usate Cowork o Claude Code con piani a consumo (Pro/Team), tieni una nota mensile in `vault/_status/costi.md`:

```markdown
| Mese | Custodi attivi | Editor attivi | Costo totale (€) | Note |
|---|---|---|---|---|
| 2026-05 | 3 | 8 | 142 | Picco lunedì 5 (chiusura mese amm.) |
| 2026-04 | 3 | 7 | 128 | Normale |
```

Da portare al rituale mensile. Se cresce in modo anomalo, indagate il perché (es. una skill nuova che gira troppo, qualcuno che usa Claude in modo improprio).

### Cosa NON è tuo compito

- **Non controlli cosa scrivono i Contributor nelle loro Daily** (privacy)
- **Non scrivi tu il contenuto operativo dei reparti**: lo scrivono gli Editor
- **Non decidi tu cosa è importante per un reparto**: lo decide il Custode di reparto con l'Editor senior

---

## Le 6 trappole

Tienile sotto gli occhi. Stampale in formato A5 e mettile vicino alla scrivania se serve.

| Trappola | Fase | Antidoto |
|---|---|---|
| **Archivista perfetto** | 2 | Cartella, non file |
| **Big Bang** | 4 | 2-4h/sett × 8-12 sett per reparto |
| **Comitato** | 0, 2, 5 | Custode di reparto decide, non si vota |
| **Doppia convenzione** | 3 | Scegli un modo per ambiente, scrivilo in CLAUDE.md |
| **Consenso implicito** | 0 | Mail al titolare scritta, con perimetro firmato |
| **Soft-deadline** | 5 | Data scritta + azione tecnica |

---

## Checklist di chiusura (per ogni reparto attivato)

- [ ] F0: mail al titolare, Custode di reparto identificato, 4 sì
- [ ] F1: foglio inventario aggiornato in `_audit/sources.md`
- [ ] F2: ogni cartella del reparto categorizzata
- [ ] F3: convenzione link scritta in `vault/CLAUDE.md`, struttura del reparto creata
- [ ] F4: oggetti VIVI migrati (almeno top 10), log in `reparti/<X>/migrazione.md`
- [ ] F5: Drive del reparto in sola lettura, mail partita
- [ ] F6: rituale settimanale fissato e fatto almeno 2 volte

---

## Quanto tempo

PMI 30-50, **per ogni reparto attivato** (oltre il pilota già fatto in Atto 1-3):

| Fase | Tempo |
|---|---|
| F0 | 1h Custode di reparto + 30 min Owner |
| F1 | 1-2 giorni Custode di reparto |
| F2 | 1 giorno Custode di reparto |
| F3 | mezza giornata Custode capo + Custode di reparto |
| F4 | **3-4h/sett × 8-12 sett** Custode di reparto |
| F5 | 1 sett rollout + check a 6 mesi |
| F6 | 30 min/sett a regime per sempre |
| **Calendario per reparto** | **3-4 mesi** |
| **Ore Custode di reparto** | **50-80 ore distribuite** |

Modello di crescita tipico:
- **Mese 1-3**: reparto pilota (già coperto dalla delivery prodotto)
- **Mese 4-6**: 2° e 3° reparto (in parallelo o sequenziale, dipende dalla capacità)
- **Mese 6-12**: azienda intera (tutti i reparti coperti)

---

## Cosa NON fa questo manuale

- Non risolve problemi organizzativi (li evidenzia)
- Non automatizza la migrazione (Claude assiste, non sostituisce)
- Non è per "archiviare tutto per sempre" (è per "avere a portata di mano ciò che serve oggi")
- Non funziona senza Custodi attivi

---

## Quando chiamare Valentino

Inclusi nel setup:
- 3 check-up mensili (mese 1, 3, 6 post-handover), 30 min ciascuno. Già fissati su calendar
- 30 giorni di "garanzia" per bug e correzioni post-handover, gratis via email

Su contratto di manutenzione (se firmato):
- Call mensile dedicata
- Risposte via email entro 48h
- Aggiornamento del repo `claude-second-brain` quando esce nuova versione del toolkit

Casi che giustificano una chiamata fuori contratto:
- Apertura di un nuovo reparto e dubbi strutturali (es. "abbiamo aperto la divisione export, come la organizziamo nel vault?")
- Cambio del Custode capo (es. tu cambi ruolo, viene un'altra persona — serve handover)
- Espansione multi-sede o multi-business unit (potrebbe servire ripensare l'architettura)
- 6+ mesi di uso e voglia di valutare skill custom o connettori MCP avanzati

Per tutto il resto, riferisciti a questo manuale + ai 3 rituali. Il sistema è fatto per essere autonomo.

---

## Documenti collegati

- [`01-cosa-vendi.md`](01-cosa-vendi.md) — il playbook commerciale parallelo di chi te lo ha venduto (riferimento per la trattativa)
- [`04-handover-checklist.md`](04-handover-checklist.md) — cosa è successo nella mezza giornata in cui questo manuale ti è stato consegnato
- [`06-framework-pmi.md`](06-framework-pmi.md) — la teoria che sta sotto al manuale (6 layer, 4 ruoli, 4 regole, 3 rituali)
- [`07-manuale-persone.md`](07-manuale-persone.md) — la pagina che fai leggere a chi entra in azienda nuovo
