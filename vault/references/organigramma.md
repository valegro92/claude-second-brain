---
tipo: identita
owner: AF
editor: [AF, GB]
visibilita: azienda
stato: vivo
ultima-revisione: 2026-05-23
---

# Organigramma

> Chi riporta a chi, chi decide cosa. Cambia raramente: solo a
> riorganizzazione.

---

## Direzione

- **AF — Anna Ferrari** — direzione generale, Owner del vault
- **CF — Carlo Ferrari** — fondatore, attualmente consulente part-time
  (non Owner)

---

## Reparti

```
                          AF (direzione)
                                |
        +-----------+-----------+-----------+----------+
        |           |           |           |          |
   Commerciale  Amministr.  Produzione   Qualita   Acquisti
   (MR resp.)   (GB resp.)  (SC resp.)   (PN)      (RM)
                                |
                          (turni / squadre)
```

---

## Reparti in dettaglio

### Commerciale
- **MR — Maria Rossi** — responsabile commerciale, Editor del reparto
- **LV — Luca Verdi** — commerciale junior, Contributor
- Riporta direttamente ad AF. Decide su offerte fino a 25.000 euro;
  sopra soglia, approvazione AF (vedi [[../decisioni/0001-_esempio-adr]]).

### Amministrazione
- **GB — Giulia Bianchi** — responsabile amministrazione, Custode capo
  del vault
- Riporta ad AF. Gestisce fatturazione, casella `info@`, contratti.

### Produzione
- **SC — Stefano Conti** — responsabile produzione, Editor
- 26 operai in 2 turni. Coordinamento turni gestito da SC + 2 capi turno
  (non sono editor del vault, solo lettori).
- Riporta ad AF.

### Qualita
- **PN — Paolo Negri** — responsabile qualita, Contributor
- Riporta a SC per le linee, ad AF per gli audit.

### Acquisti
- **RM — Roberta Marini** — buyer, Contributor
- Riporta a GB per le condizioni di pagamento, ad SC per le specifiche
  tecniche.

---

## Ruoli vault

Vedi [[persone]] per la tabella iniziali → ruolo wiki (Owner / Custode /
Editor / Contributor).

---

## Chi decide cosa (cheat sheet)

| Decisione | Chi decide | Soglia / nota |
|---|---|---|
| Offerta cliente fino a 25.000 euro | MR | senza ulteriore approvazione |
| Offerta cliente sopra 25.000 euro | AF | con istruttoria di MR |
| Nuovo fornitore strategico | RM + AF | RM propone, AF firma |
| Spesa interna sopra 5.000 euro | AF | qualsiasi reparto |
| Modifiche L0 (references/) | AF | rituale trimestrale |
| Modifiche L1 (MEMORY.md) | AF + Custodi | rituale mensile |
| Modifiche L2 (procedure reparto) | Custode reparto | rituale settimanale |
| Assunzioni e licenziamenti | AF | esclusiva |
