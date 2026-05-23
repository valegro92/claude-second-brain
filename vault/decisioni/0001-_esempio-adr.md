---
tipo: adr
numero: "0001"
data-decisione: 2026-04-22
owner: AF
editor: [AF, GB]
visibilita: azienda
stato: vivo
applicazione: accettata
ultima-revisione: 2026-04-22
---

# ADR-0001 — Soglia approvazione AF per offerte commerciali

> Pattern 6 del framework PMI: ADR aziendale. Razionale completo della
> decisione.

---

## Stato

**Accettata** dal 2026-04-22, applicata dal 2026-05-01.

## Contesto

Fino al 2026-04 il commerciale (MR) gestiva tutte le offerte in
autonomia, anche oltre i 30.000 euro. Nel Q1 2026 si sono verificate
2 situazioni:

1. **Offerta da 42.000 euro a OEM-Y inviata senza valutazione del
   rischio di pagamento**. OEM-Y ha pagato in 95 giorni invece dei 60
   contrattuali, mettendo sotto stress la cassa.
2. **Offerta da 38.000 euro a NewCustomer SpA con clausole di
   penale anomale**. MR aveva accettato per fretta, AF se ne e' accorta
   solo al contratto, ha dovuto rinegoziare.

Entrambi i casi avrebbero beneficiato di una review esterna prima
dell'invio.

## Decisione

**Tutte le offerte commerciali con importo netto > 25.000 euro
richiedono OK esplicito di AF prima dell'invio al cliente.**

Operativamente:
- MR (o LV) prepara la bozza in `clienti/<slug>/knowledge/`
- MR inoltra ad AF via mail (con bozza in PDF allegato + link al
  vault)
- AF risponde via mail entro 24h: OK / modifiche / no
- Solo dopo OK AF, MR produce il PDF finale e invia al cliente

## Opzioni considerate

1. **Soglia 25.000 euro** (scelta). Cattura ~30% delle offerte annue.
2. Soglia 50.000 euro. Catturerebbe solo ~10% — non riduce abbastanza
   il rischio.
3. Soglia 10.000 euro. Catturerebbe ~60% — diventa collo di bottiglia
   per AF.
4. Approvazione su tutte le offerte verso clienti nuovi (a prescindere
   dall'importo). Scartata: troppo restrittiva, rallenta acquisizione.

## Conseguenze

**Positive**:
- Riduzione rischio finanziario su offerte sopra soglia
- Allineamento commerciale-direzione su clienti significativi
- Coinvolgimento AF su scelte strategiche

**Negative**:
- Tempo aggiuntivo: stimato +1 giorno medio sul ciclo offerta
  per quelle sopra soglia
- Dipendenza dalla disponibilita di AF (rischio mitigato da SLA
  risposta 24h)

**Mitigazioni**:
- Eccezioni documentate per clienti con storico consolidato (es. Rossi
  Srl soglia alzata a 50k, vedi
  [[../clienti/_esempio/MEMORY]] del 2026-03-12)
- Template offerta gia' compilato con campi critici evidenziati
  (riduce tempo review AF)

## Promozioni che ne sono nate

- Entry in [[../MEMORY|MEMORY aziendale]] del 2026-05-12 (versione
  sintetica della decisione)
- Aggiornamento di [[../reparti/_esempio/procedure/sop-_esempio|SOP
  ciclo offerta]] al passo 5 (review e produzione binario)

## Revisione prevista

Tra 12 mesi (2027-04-22) verificare:
- Numero offerte sopra soglia effettivo
- Tempo medio risposta AF
- Eventuali offerte perse per ritardo nella catena di approvazione

Se i numeri non confermano la decisione, candidata a revisione con
ADR-NNNN successiva.
