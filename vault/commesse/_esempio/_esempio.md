---
tipo: scheda-commessa
commessa: 2026-rossi-revamp
cliente: rossi-srl
owner: MR
editor: [MR, SC, LV]
visibilita: azienda
stato: vivo
ultima-revisione: 2026-05-23
revisore: MR
---

# 2026-rossi-revamp — commessa (MOC)

> MOC della commessa "Revamp linea T-series per Rossi Srl". Hub che
> linka agli altri file dell'oggetto.
>
> Questo `_esempio/` e' il template di scheda commessa. Apre quando il
> cliente firma l'ordine (al momento e' ancora in fase offerta inviata,
> ma teniamo la cartella aperta per esempio).

---

## Dati base

- **Codice commessa**: 2026-rossi-revamp
- **Cliente**: [[../../clienti/_esempio|Rossi Srl]]
- **Importo previsto**: 78.000 euro netti (offerta v1)
- **Volume**: 600 pz/mese x 3 modelli (T03, T05, T07) per 24 mesi
- **Inizio previsto produzione**: 2026-10-01
- **Stato**: offerta inviata (2026-05-19), in attesa firma cliente

---

## I 5 file Regola 01-PMI

- [[_esempio|2026-rossi-revamp.md]] — questo file, MOC
- [[CLAUDE]] — istruzioni Claude specifiche
- [[MEMORY]] — decisioni datate, vincoli, cambi
- [[tasks]] — task aperti
- [[persone]] — chi e' chi sul progetto

---

## In una riga

Commessa "linea continua" potenziale: 3 modelli basi tavolo, volume
mensile costante per 24 mesi. Sweet spot dimensionale per la nostra
officina. Driver decisione cliente: nuovo packaging (loro hanno
nuovo cliente retail). Coinvolge anche Bianchi Forniture per finitura
verniciata.

---

## Reparti coinvolti

| Reparto | Iniziali | Cosa fa |
|---|---|---|
| Commerciale | MR, LV | Offerta, follow-up, primo punto di contatto |
| Produzione | SC | Schedulazione, supervisione lavorazioni |
| Acquisti | RM | Ordine MP (acciaio Acciai Lombardi) + finitura (Bianchi Forniture) |
| Qualita | PN | Piano controlli, primi articoli |
| Amministrazione | GB | Fatturazione, controllo pagamenti (cliente attualmente OK) |

---

## Allegati esterni

- Offerta corrente: Drive
  `Commerciale/Clienti/rossi-srl/Offerte/rossi-srl_offerta_v1_2026-05-19.pdf`
- CAD ricevuti: Drive `Commerciale/Clienti/rossi-srl/CAD/T03_T05_T07_2026/`
- (Quando firmata) Conferma ordine cliente: Drive
  `Commerciale/Clienti/rossi-srl/Ordini/`
- (Quando aperta in produzione) OdL: TeamSystem,
  numero `OdL-2026-NNNN`

---

## Stato d'avanzamento

| Milestone | Data prevista | Data effettiva | Note |
|---|---|---|---|
| Offerta inviata | 2026-05-19 | 2026-05-19 | OK |
| Firma cliente | 2026-06-15 | — | follow-up MR a 25 gg |
| Apertura OdL produzione | 2026-09-15 | — | dopo firma + lead time MP |
| Primo articolo | 2026-09-25 | — | PN qualifica i 3 modelli |
| Inizio produzione serie | 2026-10-01 | — | volume target da subito |
| Fine commessa | 2028-09-30 | — | 24 mesi |
