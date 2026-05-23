---
tipo: identita
owner: GB
editor: [GB, AF]
visibilita: azienda
stato: vivo
ultima-revisione: 2026-05-23
---

# Persone — mappa iniziali / nome / ruolo

> Tabella canonica delle persone con accesso al vault. Claude la legge
> ad ogni "Buongiorno Claude, sono XX" per risolvere XX → nome /
> reparto / ruolo / email.
>
> **Iniziali** sono univoche all'interno dell'azienda. Se due persone
> hanno le stesse iniziali, si distingue aggiungendo una lettera
> ulteriore (es. MR1, MR2 — ma evitabile cambiando ordine nome /
> cognome).

---

## Tabella attiva

| Iniziali | Nome              | Reparto         | Ruolo wiki   | Email                          |
|----------|-------------------|-----------------|--------------|--------------------------------|
| AF       | Anna Ferrari      | Direzione       | Owner        | a.ferrari@esempio.it           |
| GB       | Giulia Bianchi    | Amministrazione | Custode capo | g.bianchi@esempio.it           |
| MR       | Maria Rossi       | Commerciale     | Editor       | m.rossi@esempio.it             |
| LV       | Luca Verdi        | Commerciale     | Contributor  | l.verdi@esempio.it             |
| SC       | Stefano Conti     | Produzione      | Editor       | s.conti@esempio.it             |
| PN       | Paolo Negri       | Qualita         | Contributor  | p.negri@esempio.it             |
| RM       | Roberta Marini    | Acquisti        | Contributor  | r.marini@esempio.it            |
| CF       | Carlo Ferrari     | Direzione       | Lettore      | c.ferrari@esempio.it           |

---

## Cosa puo fare ogni ruolo

| Ruolo | Layer scrivibili | Layer leggibili | Note |
|---|---|---|---|
| **Owner** | tutti | tutti | Approva L0 e L1. Firma decisioni cross-reparto. Una sola persona per azienda. |
| **Custode** | tutti tranne L0 (richiede OK Owner) | tutti | Garantisce salute L2/L3. Rituale settimanale di promozione. Una per reparto, una "capo" trasversale. |
| **Editor** | L2/L3/L4 del proprio reparto | tutti | Scrive e revisiona. Tipicamente senior di reparto. |
| **Contributor** | L4 (solo dove e' in `editor:`) + proprio L5 | L0, L1, L3 del reparto, L4 dove e' in `editor:` | Scrive bozze. Logga la giornata. Non fa merge in L1/L2 da solo. |
| **Lettore** | nessuno | L0, L1 e quanto esplicitamente concesso | Esterni, tirocinanti, fornitori temporanei. |

---

## Onboarding nuove persone

1. AF (o GB) aggiunge la riga qui sopra (iniziali univoche, ruolo wiki
   coerente con ruolo aziendale).
2. Custode capo lancia `setup-wizard-persona` sulla macchina della
   nuova persona: crea `Daily/<XX>/` e compila il `[CONFIGURA QUI]`
   locale.
3. Se la persona ha un reparto, viene aggiunta come `editor:` nei file
   pertinenti del reparto via PR (non a mano).
4. Prima sessione: "Buongiorno Claude, sono XX". Claude conferma
   identita e propone tour guidato dei 3 file piu' rilevanti per il
   ruolo.

---

## Offboarding

Quando una persona esce:
1. Marcare la riga qui sopra come `[ex-collaboratore, uscita YYYY-MM-DD]`.
   Non cancellare (la cronologia dei file riferisce alle iniziali).
2. Rimuovere le iniziali da tutti i campi `editor:` aperti (script
   `vault-lint --offboard XX`).
3. `Daily/<XX>/` resta in archivio: contiene contesto storico che puo'
   servire al successore.
