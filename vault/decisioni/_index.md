---
tipo: moc
owner: AF
editor: [AF, GB]
visibilita: azienda
stato: vivo
ultima-revisione: 2026-05-23
---

# decisioni/ — ADR aziendali

> **A**rchitectural **D**ecision **R**ecord aziendali. Decisioni
> importanti che vanno spiegate con razionale completo: contesto,
> opzioni considerate, scelta, conseguenze.
>
> Pattern 6 del framework PMI. Vivono qui solo le decisioni che hanno
> bisogno di razionale documentato — le decisioni "operative" stanno
> in [[../MEMORY]] (entry da 2-4 righe).
>
> Numerazione progressiva `NNNN-titolo-slug.md`.

---

## Indice ADR

| Numero | Titolo | Data | Stato |
|---|---|---|---|
| [[0001-_esempio-adr|0001]] | Soglia approvazione AF per offerte commerciali | 2026-04-22 | accettata |

---

## Quando si scrive un ADR

Si scrive un ADR (e non una semplice entry in MEMORY) quando:
- La decisione coinvolge piu' reparti
- Ci sono state opzioni alternative serie scartate
- Le conseguenze sono significative (organizzative, economiche,
  contrattuali)
- C'e' probabilita che qualcuno tra 6 mesi chieda "perche' abbiamo
  scelto cosi'?"

## Stato dei ADR

- **proposta**: in discussione, non applicata
- **accettata**: applicata, vincolante
- **superata-da-NNNN**: sostituita da un'altra ADR (con riferimento)
- **revocata**: non piu' valida (con motivo)

Una ADR non si modifica dopo accettata. Si scrive una nuova ADR che la
supera, segnando la vecchia come `superata-da-NNNN`.

## Manutenzione

Owner: AF. Editor: GB. Le nuove ADR si propongono al rituale mensile
aziendale, si scrivono entro 7 giorni dalla decisione.
