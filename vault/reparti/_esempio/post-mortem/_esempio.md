---
tipo: post-mortem
reparto: commerciale
oggetto: bianchi-spa-rfq-staffe-2026-04
data-evento: 2026-04-28
data-postmortem: 2026-05-02
owner: MR
editor: [MR, GB, AF]
visibilita: azienda
stato: vivo
ultima-revisione: 2026-05-02
---

# Post-mortem — Offerta persa Bianchi SpA, RFQ staffe (aprile 2026)

> Post-mortem aperto entro 5 giorni lavorativi dall'evento (vedi
> lezione aziendale [[../../../MEMORY|2026-05-05]]: i post-mortem
> chiusi a caldo generano azioni implementate, quelli tardivi no).

---

## Cosa e' successo

RFQ ricevuta il 2026-03-20: 1.500 staffe in alluminio per illuminazione
tecnica, finitura ossidata nera, consegna richiesta entro 2026-05-30.
Offerta inviata il 2026-04-02 a 18.400 euro netti. Cliente ha
confermato il 2026-04-28 di aver scelto un concorrente a 14.800 euro
(-19%).

## Timeline

- 2026-03-20: RFQ via mail da Bianchi SpA, completa di CAD
- 2026-03-23: fattibilita OK da SC, finitura ossidata nera **da
  confermare** con fornitore esterno
- 2026-03-27: RM conferma finitura via [[../../../fornitori/_esempio]]
  (Bianchi Forniture, fornitore di nostro nome ma diverso da cliente
  Bianchi SpA) a 2,80 euro/pz
- 2026-04-02: offerta inviata a 18.400 euro
- 2026-04-15: follow-up MR via mail, nessuna risposta
- 2026-04-25: chiamata di MR, cliente dice "stiamo valutando"
- 2026-04-28: mail di Bianchi SpA "abbiamo scelto altro fornitore"

## Cosa e' andato bene

- RFQ completa di CAD → fattibilita rapida
- Tempi di risposta nei 7 gg SLA standard
- Follow-up rispettati (15 + 25 gg)

## Cosa non ha funzionato

- **Prezzo finitura ossidata nera fuori mercato**: 2,80 euro/pz da
  Bianchi Forniture. Il concorrente probabilmente la fa in casa o ha un
  fornitore a 1,80-2,00 euro/pz. Differenza sul totale: ~1.500 euro,
  che spiega gran parte del gap di 3.600 euro
- **Non abbiamo proposto un'alternativa di finitura**: il cliente
  voleva "ossidato nero" ma forse avrebbe accettato verniciato nero
  RAL 9005, molto piu' economico
- **Mancanza di una controfferta**: dopo la chiamata del 25 aprile
  potevamo proporre una variante a 16.500 euro con finitura alternativa

## Causa radice

Manca un processo di "controfferta strutturata" quando il cliente
tergiversa. Manca anche un secondo fornitore qualificato per finiture
ossidate.

## Azioni correttive

1. **Aprire ricerca fornitore alternativo per ossidato nero/colorato**.
   Owner: RM. Scadenza: 2026-06-30. Task in
   [[../../../fornitori/_esempio/tasks]].
2. **Aggiornare SOP ciclo offerta** con passo "valuta controfferta" al
   follow-up 25 gg. Owner: MR. Scadenza: 2026-06-15. Task in
   [[../procedure/sop-_esempio]] versione v4.
3. **Candidare a L1**: la lezione "valutare sempre alternativa di
   finitura prima di quotare" e' candidata a promozione cross-reparto.
   Owner: GB. Vedi [[../_proposte-promozione]].

## Promozioni candidate

- L3 (MEMORY reparto): "Dopo follow-up 25 gg senza risposta, valutare
  controfferta prima di chiudere come persa"
- L1 (MEMORY azienda): "Sempre proporre alternativa di finitura
  economica quando il prezzo finitura supera il 15% del totale offerta"

## Stato chiusura

Post-mortem chiuso il 2026-05-02. Azioni tracciate. Prossima
verifica: rituale mensile di giugno 2026 — controllare che le 3
azioni siano implementate.
