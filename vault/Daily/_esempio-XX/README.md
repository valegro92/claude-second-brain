---
tipo: readme
owner: GB
editor: [GB]
visibilita: azienda
stato: vivo
ultima-revisione: 2026-05-23
---

# Daily/_esempio-XX/ — placeholder per cartelle Daily per-persona

Questa cartella e' un **placeholder di esempio**. Nel vault reale, al
suo posto ci sono le cartelle delle persone con le loro iniziali
(es. `Daily/MR/`, `Daily/GB/`, `Daily/LV/`).

## Cosa va in `Daily/<XX>/`

Il layer L5 (operativo personale) di ogni persona. Solo la persona
stessa scrive nel suo Daily. Le altre persone lo possono leggere se
hanno `visibilita: reparto` o `visibilita: azienda` nei file (ma di
default i daily sono `visibilita: privato`).

## Struttura tipica

```
Daily/<XX>/
├── README.md             # opzionale, note di servizio della persona
├── YYYY-MM/
│   ├── YYYY-MM-DD.md     # un file per giornata
│   ├── YYYY-MM-DD.md
│   └── ...
└── sparks.md             # opzionale, idee grezze non datate
```

## Quando si crea

Al primo "Buongiorno Claude, sono XX" di una persona nuova: il
`setup-wizard-persona` crea la cartella e il primo daily del giorno.

## Cosa contiene un daily tipico

Vedi il file di esempio in [`2026-05/2026-05-23.md`](2026-05/2026-05-23.md)
in questa cartella.

## Promozioni

A fine giornata, "Buonanotte Claude" propone 0-3 cose da promuovere a
L3 (reparto) o L1 (azienda). Le proposte vanno in
`vault/reparti/<reparto-della-persona>/_proposte-promozione.md`,
firmate con le iniziali della persona. **Niente** viene promosso
direttamente da L5: passa sempre per il Custode al rituale settimanale.

## Privacy

Il contenuto del daily personale e' di proprieta della persona. Il
Custode puo' leggerlo per il rituale settimanale, ma non puo'
modificarlo. Owner della cartella: la persona stessa.
