---
tipo: identita
owner: GB
editor: [GB, AF, MR, SC, PN]
visibilita: azienda
stato: vivo
ultima-revisione: 2026-05-23
---

# Glossario aziendale

> Sigle e termini interni. Claude lo carica quando trova una sigla che
> non riconosce nel testo che sta producendo o leggendo.

---

## Sigle interne

| Sigla | Sciolta | Cosa significa nel contesto |
|---|---|---|
| OdL | Ordine di Lavoro | Documento che apre la lavorazione di una commessa in officina. Numerato `OdL-YYYY-NNNN` |
| BoM | Bill of Materials | Distinta base. Per noi e' l'elenco materie prime + semilavorati per un pezzo |
| CdC | Centro di Costo | Codice contabile per imputare ore e materiali (CdC-100 = laser, CdC-200 = piega, ecc.) |
| RNC | Rapporto di Non Conformita | Modulo qualita aperto quando un pezzo o un lotto non rispetta la specifica |
| PdP | Piano di Produzione | Documento settimanale di SC con le commesse schedulate |

---

## Termini di prodotto

| Termine | Cosa intendiamo noi |
|---|---|
| **Conto terzi** | Produzione su disegno del cliente, senza nostro marchio |
| **Co-progettazione** | Cliente porta concept, noi mettiamo la fattibilita e la quotazione costruttiva |
| **Serie media** | 200-2.000 pezzi/mese per articolo. E' il nostro sweet spot |
| **Piccola serie** | Sotto 200 pezzi/mese. La facciamo solo se margine sopra 35% |
| **Prototipo** | 1-10 pezzi, listino dedicato (sopra +40% sul prezzo serie) |

---

## Termini commerciali

| Termine | Cosa intendiamo noi |
|---|---|
| **Offerta** | PDF firmato MR (o AF se sopra 25k) inviato al cliente. Versionata `_v1`, `_v2` |
| **Ordine confermato** | Quando il cliente firma e rimanda + abbiamo numero d'ordine TeamSystem |
| **Commessa** | Equivale a "ordine in corso di produzione". Numerata `YYYY-clientebreve-titolo` |
| **Cliente attivo** | Cliente con almeno 1 ordine negli ultimi 12 mesi |
| **Cliente dormiente** | Tra 12 e 36 mesi senza ordini. Resta in CRM, scheda vault congelata |

---

## Termini vault (per chi e' nuovo)

| Termine | Cosa significa qui dentro |
|---|---|
| **MOC** | Map Of Content. File `<slug>.md` che fa da hub a tutto il resto dell'oggetto |
| **L0...L5** | I 6 layer di memoria. Vedi `CLAUDE.md` per la matrice |
| **Promozione** | Far salire una entry da L5 (daily personale) a L3 (reparto) o L1 (azienda) |
| **ADR** | Architectural Decision Record. Decisione importante con razionale. Vivono in `decisioni/` |
| **Custode** | La persona che mantiene la salute del vault. Una per reparto, una capo per l'azienda |

---

*Aggiungere una sigla qui non costa nulla: se la usi in piu' di un
documento, scrivila qui.*
