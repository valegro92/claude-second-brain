# Brief — Draft del manuale custode (subagente 3)

Questo file è il **draft del documento `docs/05-manuale-custode.md`** prodotto dal subagente 3, già 90% pronto. Il cantiere DOCS deve:

1. Validare il contenuto
2. Adattarlo al modello prodotto (terminologia: "wiki", "custode", "vault", coerente)
3. Sostituire i riferimenti single-user con il modello PMI (es. "Anna HR" → "Laura custode di un'officina meccanica")
4. Salvarlo come `docs/05-manuale-custode.md`
5. Linkarlo da README e dal nuovo `INIZIA-QUI.md`

---

# Migrazione da file sparsi — il protocollo per PMI reali

Questo documento risponde alla domanda che il resto della doc non affronta: *"Ho 200 GB sparsi tra Drive, email, NAS e portatili di 5 colleghi — da dove parto?"*

Se stai partendo da zero, vuoto, senza patrimonio digitale pregresso — questo documento **non fa per te**. Vai a `INIZIA-QUI.md` e poi a `installazione-per-dummies.md`. Lì il template funziona così com'è.

Se invece sei una PMI con 10 anni di sedimentazione caotica alle spalle — Drive condivisi nati per esigenza, cartelle "Definitivo_v2_FINAL", Excel vivi che girano per email, PDF di contratti mai OCR-ati, allegati Outlook che sono l'unica copia di certi documenti — leggi questo prima di toccare Markdown o Obsidian.

**Regola d'oro:** non si "migra il Drive nel vault". Si **decide cosa entra, cosa resta fuori, cosa muore**. Il 60-70% del materiale esistente non deve nemmeno entrare nel vault. Più passi sei in grado di saltare, più probabilità hai di arrivare in fondo.

---

## Indice

- Fase 0 — Decidere se farlo davvero (10 min)
- Fase 1 — Inventario (1-2 giorni)
- Fase 2 — Categorizzazione (1 giorno)
- Fase 3 — Mapping al vault (mezza giornata)
- Fase 4 — Migrazione progressiva (settimane)
- Fase 5 — Decommissioning del vecchio (1 settimana)
- Le 6 trappole

---

## Fase 0 — Decidere se farlo davvero (10 min)

Prima di spendere una settimana di lavoro su questo, fermati 10 minuti e fai il test di idoneità.

### Quando ha senso

- C'è **una persona** che si prende la responsabilità del vault. Non un comitato. Una persona, identificata con nome e cognome, che ha l'ultima parola.
- Il team è tra **2 e 15 persone**. Sotto i 2 stai usando un cannone per una zanzara. Sopra i 15 servono ruoli, governance e probabilmente uno strumento più strutturato.
- L'azienda è in una **fase stabile o di crescita ordinata**. Se siete nel mezzo di una ristrutturazione, fermati: stai investendo su sabbia che si muove.
- Esiste già una **abitudine minima a scrivere**. Se nessuno scrive mai nulla, il vault diventa una cartella vuota.

### Quando NON ha senso (4 casi di fallimento)

1. **Nessun custode.** Se "lo facciamo tutti insieme" è la risposta a *"chi è il custode?"*, il vault muore in 6 settimane.
2. **Cultura "ognuno il suo file".** Cambiare questa cultura è change management, non documentazione.
3. **Turnover sopra il 30% annuo.** La conoscenza evapora con le persone.
4. **Troppe persone con potere di veto.** Se ogni decisione passa per 5 persone, non si parte mai.

### Test rapido (4 sì = procedi)

1. C'è una persona con nome e cognome che farà da custode?
2. Quella persona ha 2-4 ore a settimana per i prossimi 3 mesi?
3. Il titolare è d'accordo che il vault diventi *il* posto canonico?
4. Esiste un caso d'uso doloroso quotidiano che il vault risolverebbe?

### Output Fase 0

Una mail al titolare con: chi è il custode, ore a settimana, dolore risolto, check-up a 3 mesi. Senza questa mail scritta — non sei al riparo dalla **trappola del consenso implicito**.

---

## Fase 1 — Inventario (1-2 giorni)

### Chi è coinvolto

Una persona sola, il custode designato. Eventualmente 30 min di IT per gli accessi admin.

### Cosa devi sapere

Per ogni "isola" di file (Drive, NAS, email, cartella locale):
- **Volume**: GB e numero file
- **Tipi di file dominanti**: docx, xlsx, pdf, jpg, eml
- **Freschezza**: quante cose toccate negli ultimi 12 mesi?
- **Autori**: chi ha creato la maggior parte?
- **Ridondanza apparente**: nomi come `_v2`, `_FINAL`, `copia_di_`?

### Strumenti pratici

```bash
# GB totali
du -sh /Volumes/NAS/condiviso/

# Albero a 2 livelli con dimensione
du -h --max-depth=2 /Volumes/NAS/condiviso/ | sort -h

# File toccati negli ultimi 12 mesi
find /Volumes/NAS/condiviso/ -type f -mtime -365 | wc -l

# File non toccati da 3+ anni (candidati archivio)
find /Volumes/NAS/condiviso/ -type f -mtime +1095 | wc -l

# Top 10 estensioni
find /Volumes/NAS/condiviso/ -type f | sed 's/.*\.//' | sort | uniq -c | sort -rn | head -10

# Candidati duplicati per nome
find /Volumes/NAS/condiviso/ -type f \( -iname '*final*' -o -iname '*definitivo*' -o -iname '*copia*' \) | head -50
```

Per Google Drive: admin console o `rclone`. Per M365: PowerShell `Get-PnPListItem`. Per email: NON tutto, solo cartelle/etichette dove vivono gli allegati "unica copia" (Clienti, Fornitori, Contratti).

### Output

Un foglio (Google Sheet o CSV), 5 colonne:

| Isola | Volume (GB) | File totali | File freschi (12 mesi) | Note |
|---|---|---|---|---|
| Drive "Commerciale" | 47 | 12.400 | 3.100 | Molti _FINAL, struttura a clienti |
| NAS "Produzione" | 120 | 45.000 | 4.500 | Disegni CAD, foto cantieri |
| Allegati Outlook "Clienti" | ~3 | ~600 | 600 | Ordini, conferme |

Cinque colonne. Stop. Aggiungere "categoria"/"azione" = trappola.

### Esempio

> **Officina meccanica, Brescia, 12 persone.** Laura inventario in un giorno. NAS 320 GB (240 GB CAD vivi, 60 GB foto cantieri, 20 GB varie), Drive 25 GB offerte+contratti, casella `info@` 7000 mail, 3 portatili "che nessuno sa". Scopre: NAS va lasciato lì (CAD vivi), il problema vero è Drive + casella `info@`.

### Trappole

- **Inventario perfetto**: 1-2 giorni, non 2 settimane
- **"Guardiamo dentro"**: non aprire i file. Conti, non leggi
- **Giudizio anticipato**: niente "questo lo buttiamo" in Fase 1

---

## Fase 2 — Categorizzazione (1 giorno)

Decidi **per categoria**, non file per file. Il file-per-file è la **trappola dell'archivista perfetto**.

### Le 5 categorie

| Categoria | Cos'è | Dove va |
|---|---|---|
| **VIVO** | Toccato nelle ultime 4-12 settimane, lavoro corrente | Migra nel vault o linka |
| **DA CONSULTARE** | Riferimenti saltuari: contratti firmati, normative | Resta dov'è, linkato dal vault |
| **ARCHIVIO** | Vecchio ma da tenere: bilanci, progetti chiusi | `_ARCHIVIO/` sul Drive vecchio, sola lettura |
| **CESTINO** | Duplicati, bozze obsolete, `_v2_OLD` | Cestino dopo backup |
| **DA CHIARIRE** | Non si capisce cos'è o di chi | Lista, smaltita in Fase 4 |

### Come decidi

Non apri file. Apri **cartelle** e decidi a livello cartella.

| Cartella | GB | Categoria | Note |
|---|---|---|---|
| `/Drive/Clienti/Attivi/` | 12 | VIVO | Migra |
| `/Drive/Clienti/Persi-2018-2020/` | 4 | ARCHIVIO | Sposta in `_ARCHIVIO/` |
| `/Drive/_vecchio_NON_USARE/` | 15 | CESTINO | Backup + cestina |

### Chi decide

Una persona, il custode. Un'ora silenziosa col foglio. **Antipattern micidiale**: meeting di 2 ore con 5 persone. Esito: 0 decisioni, tutti si ricordano un caso particolare, si rimanda.

### Output

Il foglio di Fase 1 con colonna **categoria** compilata per ogni cartella.

### Trappole

- **Archivista perfetto**: cartella, non file
- **"Ma chissà se serve"**: default = ARCHIVIO, non VIVO
- **Comitato**: non si decide in 5

---

## Fase 3 — Mapping al vault (mezza giornata)

### Il vault NON è un Drive

Il vault contiene:
- File `.md` (note, MOC, MEMORY, decisioni)
- Pochi PDF/immagini piccoli (logo, schema chiave)
- **Link** a tutto il resto

Il vault NON contiene:
- File CAD, video, archivi ZIP → restano dove sono, linkati
- Excel "vivi" condivisi → linkati
- PDF contratti firmati 50 MB → linkati
- Backup, log, dump → mai

**Test**: se `vault/` supera 1 GB, hai sbagliato. Sano: 50-500 MB.

### Esempio mapping

```
Categoria VIVO ──→ vault/clienti/<X>/ (con i 5 file Regola 01-PMI)
Categoria DA CONSULTARE ──→ vault/references/ + vault/knowledge/ (indice MD, file su Drive)
Categoria ARCHIVIO ──→ NON entra. Resta sul Drive in sola lettura.
Categoria CESTINO ──→ Cestinato.
Categoria DA CHIARIRE ──→ vault/migrazione/da-chiarire.md (temporanea)
```

### Convenzione di link a file esterni

**Modo 1 — URL Drive (raccomandato per cloud)**
```markdown
- [Contratto Rossi Srl 2024](https://drive.google.com/file/d/1aB2cD.../view)
```
Pro: funziona ovunque. Contro: se sposti, link si rompe (ma Google/SharePoint redirectano).

**Modo 2 — Path locale (per NAS)**
Definisci `/Volumes/NAS/condiviso/` (Mac) o `Z:\condiviso\` (Windows) in `CLAUDE.md`.
```markdown
- [Disegno CAD 4521](file:///Volumes/NAS/condiviso/CAD/4521.dwg)
```
Pro: offline. Contro: path Mac vs Windows differente.

**Modo 3 — Path logico + mappa**
```markdown
- Vedi `[NAS]/CAD/4521.dwg`
```
In `vault/references/dove-sta-cosa.md`:
```markdown
- `[NAS]` → `/Volumes/NAS/condiviso/` (Mac) o `Z:\condiviso\` (Windows)
```

Scegli **un solo modo** all'inizio. Cambiare a metà = **trappola della doppia convenzione**.

### Naming dei link

Cattivo: `[Documento](https://drive.google.com/...)`
Buono: `[Contratto Rossi Srl – firmato 2024-03-12](https://drive.google.com/...)`

### Output

1. Struttura vault decisa nel foglio
2. Convenzione di link scritta in `vault/CLAUDE.md`
3. Script bash che crea le cartelle

### Trappole

- **Clone del Drive**: tentazione di copiare tutto. No
- **Doppia convenzione**: scegli uno e attienitici
- **Top-level infinito**: 4-6 top-level all'inizio, max

---

## Fase 4 — Migrazione progressiva (settimane, non giorni)

Non si migra tutto in una volta. Batch settimanali.

### Strategie di batching (scegli UNA)

| Strategia | Quando | Esempio |
|---|---|---|
| **Per cliente** | 5-30 clienti attivi | Sett 1: Rossi. Sett 2: Bianchi |
| **Per anno** | Dati strutturati per anno | Sett 1: 2024. Sett 2: 2023. Stop |
| **Per ruolo** | Categorie funzionali nette | Sett 1: commerciale. Sett 2: amministrazione |
| **Per criticità** | Un dolore specifico | Sett 1: scheda dei top 10 clienti |

**Raccomandazione**: per cliente o per criticità per la maggior parte delle PMI.

### Estrai vs linki

| Situazione | Cosa fai |
|---|---|
| PDF 80 pp, contratto firmato, 1-2 volte/anno | Linki |
| PDF 20 pp, manuale fornitore consultato ogni settimana | Estrai passaggi chiave, linki originale |
| PDF 5 pp, brief cliente arrivato oggi | Estrai tutto in `knowledge/brief-YYYY-MM-DD.md` |
| Email lunga con decisioni | Estrai decisioni in MEMORY del cliente |
| Trascrizione call 1h | Estrai punti chiave, trascrizione full linkata |

### Ruolo di Claude

> *Tu*: "Brief Rossi (4 pagine, incollato). Estraimi: obiettivi, vincoli, scadenze, decisioni. Markdown in `clienti/rossi-srl/knowledge/brief-2024-03-12.md`."
> 
> *Claude*: produce la nota. Tu rileggi, correggi, salvi.

Vale la **Regola della Bozza**: prima bozza, OK esplicito, poi salvataggio.

### Settimana tipo

> **Studio commercialista, Verona — settimana 3 (cliente "Verdi Costruzioni")**
> - **Lun 90 min**: 200 file → 30 VIVO, 140 ARCHIVIO, 25 CESTINO, 5 DA CHIARIRE
> - **Mar 60 min**: estrazione con Claude dei 5 doc più importanti
> - **Mer 30 min**: scrive a mano in MEMORY le 10 decisioni "in testa"
> - **Gio 30 min**: compila MOC con link Drive
> - **Ven 15 min**: sposta CESTINO in `_DA_CESTINARE_2024-03/`, messaggio a Sara per i DA CHIARIRE
> 
> **Totale: 3,5 ore.** Cliente migrato. Done.

### Definizione di "done"

1. MOC esiste
2. MEMORY ha almeno 5 decisioni/contesti
3. Link funzionano
4. CESTINO in `_DA_CESTINARE_/`
5. Nota datata in Daily

### Trappole

- **Big Bang**: 2-4h/sett × 8-12 sett, non 2 settimane filate
- **Estrazione totale**: estrai solo cose dense e ricorrenti
- **Perfezionismo**: vera e linkata > bella
- **"Non ho tempo questa settimana"**: 1h/sett ogni sett > 6h una volta al mese

---

## Fase 5 — Decommissioning (1 settimana, dopo 2-3 mesi di uso)

### Quando attivare

3 sì:
1. Vault in uso quotidiano da 2+ mesi?
2. Tutti i clienti/aree VIVE migrati?
3. Drive vecchio aperto < 3 volte negli ultimi 30 gg per cose VIVE?

### Comunicazione

Mail, non meeting. Modello:

> Oggetto: Drive `[nome]` passa in sola lettura dal [data, +14 giorni]
> 
> Da [data]:
> - **Lavoro corrente**: solo nel vault `[link]`
> - **Consultare vecchio**: Drive resta in lettura
> - **Cose non migrate**: scrivetemi entro [data]
> 
> Custode: [nome]

### Esecuzione

Drive Google/M365: revoca scrittura a tutti tranne custode. NAS: read-only o sposta in `_ARCHIVIO/`.

### Le 2-3 persone che continuano

1. Pair-working di 30 min con chi si lamenta
2. Recidivi: colloquio col titolare, non con te
3. **Non riapri scrittura sul vecchio**. Mai. Se lo fai, hai perso

### A 6 mesi

```bash
find /Volumes/Drive-vecchio/ -type f -atime +180 | wc -l
```

Probabilmente 90% non acceduto = categorizzazione giusta. 10% acceduto: o lo migri (mini-batch), o lo lasci dov'è.

**Non chiudi mai definitivamente il Drive vecchio.** Sola lettura, indefinitamente.

### Output

1. Mail al team partita
2. Drive in sola lettura (testato)
3. Nota in `references/dove-sta-cosa.md`
4. Nota in `MEMORY.md`: "Migrazione completata il [data]"

### Trappole

- **Soft-deadline**: data scritta, azione tecnica, mail
- **Deroga**: una persona = tutti
- **"Cancelliamo il vecchio"**: sola lettura, mai cancellato

---

## Le 6 trappole

| Trappola | Fase | Antidoto |
|---|---|---|
| **Archivista perfetto** | 2 | Cartella, non file |
| **Big Bang** | 4 | 2-4h/sett × 8-12 sett |
| **Comitato** | 0, 2, 5 | Custode decide, non si vota |
| **Doppia convenzione** | 3 | Scegli un modo, scrivilo in CLAUDE.md |
| **Consenso implicito** | 0 | Mail al titolare scritta |
| **Soft-deadline** | 5 | Data scritta + azione tecnica |

---

## Checklist di chiusura

- [ ] F0: mail al titolare, custode identificato, 4 sì
- [ ] F1: foglio inventario 5 colonne
- [ ] F2: ogni cartella categorizzata
- [ ] F3: struttura vault decisa, convenzione link scritta
- [ ] F4: aree VIVE migrate, log in `migrazione/log.md`
- [ ] F5: Drive in sola lettura, mail partita

---

## Quanto tempo

PMI tipica (5-15 persone, 50-200 GB):

| Fase | Tempo |
|---|---|
| F0 | 1h custode + 30 min titolare |
| F1 | 1-2 giorni |
| F2 | 1 giorno |
| F3 | mezza giornata |
| F4 | **2-4h/sett × 8-12 sett** |
| F5 | 1 sett rollout + check a 6 mesi |
| **Calendario** | **3-4 mesi** |
| **Ore custode** | **40-60 ore distribuite** |

---

## Cosa NON fa questo protocollo

- Non risolve problemi organizzativi (li evidenzia)
- Non automatizza la migrazione (Claude assiste, non sostituisce)
- Non è per "archiviare tutto per sempre" (è per "avere a portata di mano ciò che serve oggi")
- Non funziona senza custode

---

## NOTE PER IL CANTIERE DOCS

- **Versione PMI 30-50**: il subagente ha scritto per 5-15 persone. Va adattato verso l'alto: aggiungere considerazioni su ruoli multipli (Custodi per reparto), volumi maggiori (500 GB-2 TB plausibili), governance più strutturata
- **Versione "tu nel ciclo"**: il manuale parla al custode interno. Va aggiunta una premessa "questo manuale ti è stato consegnato da Valentino Grossi alla chiusura dell'Atto 3 della delivery prodotto" + un link a un "playbook venditore" parallelo (`01-cosa-vendi.md`) dove ci sei tu
- **Coerenza terminologica**: usa "wiki" insieme a "vault", non solo "vault". Il pubblico PMI riconosce "wiki".
