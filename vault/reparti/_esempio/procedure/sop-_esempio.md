---
tipo: sop
reparto: commerciale
slug: ciclo-offerta
owner: MR
editor: [MR, GB]
visibilita: azienda
stato: vivo
versione: v3
ultima-revisione: 2026-05-16
revisore: GB
prossima-revisione: 2026-09-23
---

# SOP — Ciclo offerta (v3)

> Procedura operativa per gestire una RFQ dal primo contatto alla firma
> cliente. Vale per tutte le offerte del commerciale.

---

## Scopo

Standardizzare la gestione delle Request For Quotation per ridurre il
tempo di risposta e aumentare il tasso di chiusura.

## Quando si applica

- Ogni RFQ in ingresso da cliente nuovo o esistente
- Sia richieste via mail, sia raccolte in fiera, sia inoltrate da
  altri reparti (es. produzione che riceve disegni)

## Chi e' coinvolto

| Ruolo | Iniziali | Cosa fa |
|---|---|---|
| Raccolta requisiti | LV | Acquisisce RFQ, verifica completezza |
| Fattibilita tecnica | SC | Conferma tempi e fattibilita |
| Quotazione materia prima | RM | Costo MP + finiture speciali |
| Redazione offerta | MR | Compila template e firma |
| Approvazione sopra 25k | AF | OK formale via mail |

---

## Passi

### 1. Triage (max 24h, LV)
- Apri la scheda cliente in `vault/clienti/<slug>/` (se non esiste,
  crea i 5 file di Regola 01-PMI)
- Verifica che la RFQ contenga: CAD o specifica geometrica + quantita +
  data desiderata + finitura
- Se manca CAD, chiedi al cliente entro 4h (vedi lezione 2026-05-05)
- Logga il triage in `clienti/<slug>/tasks.md` con scadenza

### 2. Fattibilita (max 48h, SC)
- SC riceve il CAD e conferma: si fa / non si fa / si fa con modifiche
- Risposta in `clienti/<slug>/MEMORY.md` con data
- Se "non si fa", LV avvisa il cliente con motivazione tecnica

### 3. Quotazione (max 24h dopo fattibilita, RM)
- RM quota MP + finiture in foglio Google `Commerciale/Quotazioni`
- Note in `clienti/<slug>/knowledge/quotazione-YYYY-MM-DD.md`

### 4. Redazione bozza (max 48h, MR)
- MR (o Claude su input MR) genera bozza in
  `clienti/<slug>/knowledge/offerta-vN-YYYY-MM-DD.md`
- Frontmatter `stato: bozza`
- Applica brand voice + chiusura standard ("offerta valida 30 giorni")

### 5. Review e produzione binario (max 24h, MR/AF)
- Se importo > 25.000 euro netti: MR inoltra bozza ad AF via mail. AF
  risponde OK / modifiche. **Aspetta OK esplicito** (Regola 1 — Bozza)
- Se OK: MR produce PDF con naming `<cliente>_offerta_v<n>_YYYY-MM-DD.pdf`
- Salva PDF in Drive `Commerciale/Clienti/<slug>/`

### 6. Invio (entro la giornata, MR/LV)
- Invia via mail con copia a `info@esempio.it`
- Aggiorna `clienti/<slug>/MEMORY.md` con data invio
- Apre task in `clienti/<slug>/tasks.md`: "follow-up a 25 giorni"

### 7. Follow-up
- A 25 giorni: chiamata di MR (o LV)
- A 30 giorni senza risposta: chiusura come "persa" con motivo in
  `clienti/<slug>/MEMORY.md`. Se motivo ricorrente, candidato a
  post-mortem.

---

## SLA complessivi

- RFQ standard: risposta entro 7 giorni lavorativi
- RFQ post-fiera (14 gg dopo evento): risposta entro 5 giorni
  lavorativi (vedi candidato a SOP in [[_proposte-promozione]])
- RFQ piccola serie (sotto 200 pz/mese): +25% sul prezzo serie

---

## Lezioni che hanno generato questa versione

- v3 (2026-05-16): integrato listino piccola serie standardizzato
- v2 (2026-04-12): aggiunto follow-up a 25 giorni (lezione
  [[../MEMORY]] del 2026-04-12)
- v1 (2026-02-01): prima versione formalizzata
