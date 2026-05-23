---
tipo: moc
reparto: commerciale
owner: MR
editor: [MR, LV, GB]
visibilita: azienda
stato: vivo
ultima-revisione: 2026-05-23
---

# Reparto Commerciale (modello _esempio)

> MOC del reparto. Hub che linka alle procedure, ai verbali, ai
> post-mortem, all'onboarding, alla rubrica.
>
> Questo `_esempio/` e' il **template di reparto**. Quando l'azienda crea
> un reparto reale (commerciale, amministrazione, produzione, qualita,
> acquisti), si copia questa cartella, si rinomina, si compila.

---

## Persone del reparto

| Iniziali | Nome           | Ruolo aziendale          | Ruolo wiki   |
|----------|----------------|--------------------------|--------------|
| MR       | Maria Rossi    | Responsabile commerciale | Editor       |
| LV       | Luca Verdi     | Commerciale junior       | Contributor  |
| GB       | Giulia Bianchi | Custode capo             | Custode      |

Custode del reparto: **GB** (in questo caso il Custode capo copre anche
il reparto commerciale; in azienda piu' grande potrebbe esserci un
Custode dedicato).

---

## Cosa fa questo reparto

Gestione del ciclo di vendita: dal primo contatto cliente alla firma
dell'ordine. Non gestisce la produzione (passa la commessa al reparto
Produzione una volta firmato l'ordine — quando esiste, sara' in
`reparti/produzione/`).

---

## Sotto-cartelle

- [`procedure/`](procedure/_index.md) — L2: SOP, modulistica, template
  offerta
- `riunioni/` — verbali stand-up settimanali e revisioni mensili (vedi
  [[riunioni/_esempio-verbale|verbale di esempio]])
- `post-mortem/` — analisi commesse perse o offerte rifiutate (vedi
  [[post-mortem/_esempio|post-mortem di esempio]])
- `onboarding/` — percorso di onboarding role-based (vedi
  [[onboarding/_esempio-ruolo|onboarding commerciale junior]])
- [[contatti]] — rubrica clienti / fornitori / interni / emergenze

---

## File chiave

- [[MEMORY]] — vita del reparto (L3): decisioni interne, stand-up
- [[_proposte-promozione]] — promozioni candidate al rituale settimanale
- [[CLAUDE]] — istruzioni specifiche per il reparto

---

## Rituali del reparto

- **Lunedi 9:00, 15 min**: stand-up di reparto (chi su cosa).
  Verbalizza LV. Sale in `riunioni/YYYY-MM-DD_standup.md` solo se
  emergono decisioni.
- **Venerdi 16:00, 30 min**: rituale Custode. GB rivede
  [[_proposte-promozione]] e decide.
- **Ultimo venerdi del mese, 1h**: revisione pipeline + offerte
  perse → eventuali post-mortem.
