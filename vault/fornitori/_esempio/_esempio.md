---
tipo: scheda-fornitore
fornitore: bianchi-forniture
owner: RM
editor: [RM, SC, GB]
visibilita: azienda
stato: vivo
ultima-revisione: 2026-05-23
revisore: RM
---

# Bianchi Forniture — scheda fornitore (MOC)

> MOC del fornitore Bianchi Forniture. Hub che linka agli altri file
> dell'oggetto.
>
> Questo `_esempio/` e' il template di scheda fornitore. Pattern 4 del
> framework PMI (vedi [[../../../docs/06-framework-pmi]] _se esiste_).

---

## Dati anagrafica

- **Ragione sociale**: Bianchi Forniture Srl
- **P.IVA**: IT 09876543210
- **Sede**: Bergamo (BG), via Industriale 8
- **Cosa fornisce**: finiture (ossidazione, verniciatura RAL,
  zincatura nera), lavorazioni di superficie
- **Dimensione**: ~25 dipendenti
- **Anno primo ordine con noi**: 2019
- **Stato**: fornitore strategico (categoria A)

---

## I 5 file Regola 01-PMI

- [[_esempio|bianchi-forniture.md]] — questo file, MOC
- [[CLAUDE]] — istruzioni Claude specifiche
- [[MEMORY]] — decisioni datate, qualifiche, contestazioni
- [[tasks]] — task aperti
- [[persone]] — chi e' chi

---

## In una riga

Fornitore unico per finiture ossidate e verniciate. Qualita alta,
prezzi sopra mercato (10-15%), tempi 8-12 gg. Relazione consolidata
ma fragile sul fronte prezzo (vedi post-mortem Bianchi SpA del
2026-05-02 — abbiamo perso una offerta proprio per il sovrapprezzo
finitura).

---

## Storico forniture sintesi

- **2023**: 18 ordini, ~95.000 euro
- **2024**: 22 ordini, ~118.000 euro
- **2025**: 24 ordini, ~135.000 euro
- **2026 ad oggi**: 9 ordini, ~58.000 euro

---

## Cosa ci forniscono (catalogo nostro)

| Codice nostro | Lavorazione | Tempo std | Prezzo medio 2026 |
|---|---|---|---|
| F-OSS-NER | Ossidazione nera su alluminio | 10 gg | 2,80 euro/dm² |
| F-VER-RAL | Verniciatura RAL std (poliestere) | 8 gg | 1,90 euro/dm² |
| F-ZIN-NER | Zincatura elettrolitica nera | 12 gg | 2,40 euro/dm² |

---

## Link esterni

- Drive fornitore: `Acquisti/Fornitori/bianchi-forniture/`
- Cartella TeamSystem: anagrafica fornitore codice `F-0012`
- Ultimo contratto quadro firmato:
  `Acquisti/Fornitori/bianchi-forniture/Contratti/quadro-2025.pdf`
- Listino vigente: `Acquisti/Fornitori/bianchi-forniture/Listini/listino-2026-01.pdf`

---

## Criticita aperte

- Prezzo ossidato nero fuori mercato (vedi post-mortem
  [[../../reparti/_esempio/post-mortem/_esempio]] — abbiamo perso una
  offerta di 18k a causa di questo)
- Aperta ricerca fornitore alternativo (task in [[tasks]], owner RM)
