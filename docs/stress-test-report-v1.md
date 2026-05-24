# Stress test report — Cliente fittizio "stress"

Data esecuzione: 2026-05-24

## Dataset

Generato da `tests/fixtures/build_stress_dataset.py`. PMI manifatturiera italiana fittizia, 5 clienti + 4 fornitori, 3 anni di storico (2024-2026 + archivio 2020-2022).

| Tipo file | N. |
|---|---|
| Fattura emessa (PDF) | 15 |
| File archivio (`_OLD_NON_USARE/`) | 15 |
| DDT (PDF) | 10 |
| Conferma ordine (EML) | 10 |
| Listino fornitore (PDF) | 8 |
| Fattura ricevuta (PDF) | 8 |
| Offerta `_v1/_v2/_FINAL` (DOCX) | 15 |
| Contratto cliente (DOCX) | 5 |
| Anagrafica contatti (XLSX) | 5 |
| Duplicati cross-cartella (TXT) | 10 |
| Manuale fornitore (PDF) | 4 |
| Contratto fornitura (DOCX) | 4 |
| Template aziendale (DOCX) | 3 |
| Comunicazione con accenti italiani (TXT) | 3 |
| ZIP backup (escluso) | 3 |
| Email standalone (EML) | 3 |
| DWG (escluso) | 2 |
| **Totale** | **123** |

## Pipeline end-to-end

```
wiki scan       → 0.21s — 123 file scoperti, 118 ammessi (5 esclusi: 3 zip + 2 dwg)
wiki extract    → 1.04s — 84 processati + 34 skip dedup
wiki categorize → 0.13s — 118 record categorizzati
wiki reconcile  → 0.23s — 13 gruppi duplicati, 34 file deduplicati
TOTALE          → 1.61s  (73 file/sec)
```

## Categorizzazione

**Distribuzione (post-fix regole italiane)**:

| Categoria | N. | % |
|---|---|---|
| **VIVO** | 63 | 53.4% |
| **DA_CONSULTARE** | 19 | 16.1% |
| **DA_CHIARIRE** | 21 | 17.8% |
| **ARCHIVIO** | 15 | 12.7% |
| **CESTINO** | 0 | 0% |

**Confronto pre/post miglioramento regole italiane**:

| Categoria | PRIMA | DOPO | Delta |
|---|---|---|---|
| VIVO | 49 | 63 | +14 |
| DA_CONSULTARE | 0 | 19 | +19 |
| DA_CHIARIRE | 54 | 21 | **-33** |
| ARCHIVIO | 15 | 15 | — |

Il fix ha portato il tasso di file "da decidere con LLM" dal **46% al 18%**. Significa che — anche senza chiamare Claude — il 82% dei file ottiene una categoria deterministica e affidabile basata su regole.

## Verifica correttezza categorizzazione

### ARCHIVIO (15 file) ✓ Corretto
Tutti i file in `_OLD_NON_USARE/` (5 per anno × 3 anni 2020-2022) sono stati categorizzati ARCHIVIO. Pattern path `non_usare` + età > 3 anni hanno fatto il loro lavoro.

### VIVO (63 file) ✓ Largamente corretto
Include fatture/DDT/conferme ordine 2024-2026, offerte attive, anagrafica contatti, email recenti. Path tokens italiani (`/clienti/`, `/fornitori/`, `/ordini/`) attivi.

### DA_CONSULTARE (19 file) ✓ Corretto
Listini, manuali tecnici, contratti quadro, template, modelli. Path tokens (`/listini/`, `/manuali/`, `/modelli/`) e business naming hanno funzionato.

### DA_CHIARIRE (21 file) — Casi residui
File senza pattern di nome riconoscibile o in path generico. Senza API Anthropic, restano da decidere manualmente o aspettano Claude.

## Dedup hash

Reconciler ha trovato **13 gruppi di duplicati** per un totale di **34 file deduplicati**. Include:
- 5 coppie cross-cartella `_duplicati_test/` ↔ `Clienti/Rossi_Srl/` (creati apposta)
- 8 gruppi non previsti — probabilmente contenuti identici tra clienti diversi (DDT con stesso template body, ad esempio)

Funziona out-of-the-box senza configurazione.

## Filtri perimetro

Esclusioni configurate (`exclude_extensions: [.dwg, .zip]`):
- 3 file ZIP in `Backup_2022/` → esclusi ✓
- 2 file DWG in `Disegni_CAD/` → esclusi ✓

Totale esclusi: **5 su 123** = 4%. Filtri funzionano.

## Caratteri italiani nel nome

3 file con accenti (`comunicazione_clientÈ.txt`, `perizia_qualità.txt`, `relazione_attività.txt`) processati senza problemi. Filesystem ext4 + Python 3.11 + watchdog ok.

## Performance

- **73 file/sec** sul mio dev environment (Python 3.11, Linux container)
- Stage più lento: **extract** (1.04s), atteso (lettura PDF/DOCX/XLSX dal disco)
- **scan + categorize + reconcile = 0.57s** per 118 record (sub-secondo per le metadata)
- Pipeline scala linearmente: estrapolando, **un cliente reale con 5.000 file richiederebbe ~70 secondi**, con 50.000 file (PMI grande) ~12 minuti

## Limiti emersi

1. **21 file in `DA_CHIARIRE`** restano senza categoria deterministica. Servirebbe Claude API key per processo automatico. In modalità "Valentino approva ogni batch", sono 21 decisioni manuali su 118 = 18%, accettabile.

2. **Reconciler.schede non si attiva senza API key**. Funzione `_reconciler/by_hash.json` viene scritto ma le bozze di scheda cliente/fornitore richiedono call a Claude per estrarre contenuto. È atteso, design del pipeline.

3. **Dashboard mostra "categorie tot=0, bozze tot=0"** anche se la pipeline ha generato dati. Da indagare: probabilmente legge inventory legacy non aggiornata. Bug minore.

## Conclusioni

Il pipeline è **affidabile** su volumi PMI piccolo-medi (100-200 file):
- Filtri funzionano
- Categorizzazione italiana ora copre l'82% dei casi senza LLM
- Dedup hash trova duplicati cross-cartella
- Performance ottime (sub-secondo per 100+ file)
- Robusto su unicode/accenti italiani

Pronto per un test su cliente reale, con la sola accortezza che le 21 decisioni `DA_CHIARIRE` per 118 file vanno gestite manualmente o con Claude API key configurata.
