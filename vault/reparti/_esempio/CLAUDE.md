---
tipo: kernel-reparto
reparto: commerciale
owner: MR
editor: [MR, GB]
visibilita: azienda
stato: vivo
ultima-revisione: 2026-05-23
---

# CLAUDE.md — Reparto Commerciale

> Istruzioni specifiche per Claude quando lavora su task del reparto
> commerciale. Si aggiunge al kernel `vault/CLAUDE.md`, non lo sostituisce.

---

## Contesto del reparto

Carpenteria leggera conto terzi, 22 clienti attivi, ciclo di vendita
medio 4-8 settimane. Le offerte sono il deliverable principale
(template in `procedure/sop-_esempio.md`). Sopra 25.000 euro netti
l'offerta passa per AF prima di partire.

---

## Regole specifiche

- **Tono offerte**: brand voice azienda + chiusura concreta con
  scadenza esplicita ("offerta valida 30 giorni dalla data del
  documento")
- **Mai promettere consegne sotto 15 giorni lavorativi** senza
  conferma di SC (produzione)
- **Mai promettere finiture speciali** (verniciatura RAL custom,
  zincatura nera) senza conferma di RM (acquisti)
- **Mai citare prezzi al telefono o in mail informali**: solo
  in offerta PDF firmata

---

## Persone chiave (interne)

| Iniziali | Nome           | Quando coinvolgerla                          |
|----------|----------------|----------------------------------------------|
| MR       | Maria Rossi    | Tutte le offerte, sempre. E' Editor finale   |
| LV       | Luca Verdi     | Bozza primo contatto, raccolta requisiti    |
| SC       | Stefano Conti  | Fattibilita tecnica, conferma tempi         |
| RM       | Roberta Marini | Quotazione materia prima, finiture speciali |
| AF       | Anna Ferrari   | Offerte sopra 25.000 euro                   |

---

## Dove stanno le cose

- **Schede clienti vive**: `vault/clienti/<slug>/`
- **Allegati binari** (offerte PDF, disegni cliente, conferme ordine):
  Drive condiviso `Commerciale/Clienti/<slug>/`
- **Pipeline e forecast**: foglio Google `Commerciale/Pipeline-2026`
  (linkato da MEMORY del reparto)
- **CRM**: TeamSystem modulo "Anagrafiche e ordini" (sola lettura dal
  vault, scrittura solo da MR/LV)

---

## Output tipici di Claude in questo reparto

1. **Bozza offerta** in `clienti/<slug>/knowledge/offerta-vN-YYYY-MM-DD.md`
   → review MR → produzione PDF in Drive
2. **Bozza mail cliente** in chat → MR copia/incolla
3. **Sintesi call** in `clienti/<slug>/riunioni/YYYY-MM-DD_titolo.md`
4. **Pre-analisi pipeline** in chat → input al rituale settimanale
