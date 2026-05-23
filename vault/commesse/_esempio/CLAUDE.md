---
tipo: kernel-oggetto
commessa: 2026-rossi-revamp
owner: MR
editor: [MR, SC, LV]
visibilita: azienda
stato: vivo
ultima-revisione: 2026-05-23
---

# CLAUDE.md — 2026-rossi-revamp

> Istruzioni Claude specifiche per la commessa Revamp linea T-series
> Rossi Srl. Si aggiunge ai kernel `vault/CLAUDE.md` e
> `vault/clienti/_esempio/CLAUDE.md` (cliente Rossi Srl).

---

## Contesto

Commessa "linea continua" potenziale, 78.000 euro per la baseline,
ricorrenza 24 mesi. Cliente top 5 esistente, quindi rischio basso ma
attenzione alta sul packaging (loro nuovo cliente retail).

## Regole specifiche

- **Stato pre-firma**: tutte le decisioni operative passano per MR.
  Niente preparazione MP o slot produzione finche' non e' firmato.
- **Packaging**: novita assoluta per Rossi Srl. Coinvolgere PN su
  campionatura packaging prima del primo articolo (non solo dei pezzi).
- **Schedulazione**: SC apre slot in produzione **solo a firma
  arrivata** + conferma data consegna MP da Acciai Lombardi.
- **Pagamenti**: condizioni standard Rossi Srl (60 gg fine mese DF, vedi
  contratto quadro). Niente modifiche senza GB + AF.
- **Comunicazioni cliente**: MR unico punto di contatto. SC se serve
  parlare con Anna Verdi (tecnica), avvisa MR prima.

## Persone chiave

Vedi [[persone]] per la tabella completa.

## Output tipici di Claude

- **Bozza ordine acquisto MP** (per RM) in `knowledge/`
- **Bozza piano controlli qualita** (per PN) in `knowledge/`
- **Sintesi avanzamento settimanale** in `MEMORY` durante la
  produzione
- **Sintesi visite cliente** in `riunioni/`

## Cosa NON deve fare Claude

- Non inserire date in TeamSystem (solo scrittura `.md`)
- Non aprire OdL (lo fa SC manualmente)
- Non comunicare direttamente con il cliente o il fornitore
