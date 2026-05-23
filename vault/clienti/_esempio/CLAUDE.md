---
tipo: kernel-oggetto
cliente: rossi-srl
owner: MR
editor: [MR, LV, GB]
visibilita: azienda
stato: vivo
ultima-revisione: 2026-05-23
---

# CLAUDE.md — Rossi Srl

> Istruzioni Claude specifiche per il cliente Rossi Srl. Si aggiunge ai
> kernel `vault/CLAUDE.md` e `vault/reparti/_esempio/CLAUDE.md`, non li
> sostituisce.

---

## Contesto

Cliente top 5, relazione consolidata dal 2021. MR e' il punto di
contatto unico. Sensibilita alta sulla puntualita consegna (i loro
piani produttivi sono settimanali). Sensibilita media sul prezzo
(entro +5% accetta).

## Regole specifiche

- **Tono**: confidenziale ma professionale. MR e Mario Rossi si danno
  del tu da fine 2022. Vale per mail e telefonate.
- **Mai** menzionare il concorrente principale "Carpenteria Adda"
  nelle comunicazioni con Rossi Srl (Mario Rossi e' particolarmente
  toccato, situazione passata).
- **Mai** promettere consegne sotto 18 giorni lavorativi senza
  conferma SC (loro consegne sempre conferma scritta SC, mai a voce).
- **Sempre** specificare in offerta: "consegna porto franco loro
  sede Cremona" — e' lo standard concordato.
- **Soglia approvazione**: AF firma le offerte sopra 50.000 euro per
  Rossi Srl (eccezione alla soglia 25k generale, vedi
  [[../../decisioni/0001-_esempio-adr]] _eccezione documentata in
  MEMORY cliente_).

## Persone chiave (lato cliente)

Vedi [[persone]] per la tabella completa. In breve:
- Mario Rossi — decisore acquisti, il referente di tutto
- Anna Verdi — ufficio tecnico, riceve i CAD
- Luigi Belotti — magazzino, riceve i pezzi (per emergenze logistiche)

## Output tipici di Claude

- **Bozza offerta** in `knowledge/offerta-vN-YYYY-MM-DD.md` (MR poi
  rivede e produce PDF)
- **Bozza mail di follow-up** in chat
- **Sintesi call** in `riunioni/YYYY-MM-DD_titolo.md`
- **Estrazione punti chiave da capitolato** in `knowledge/`
