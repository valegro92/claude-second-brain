---
tipo: kernel-oggetto
fornitore: bianchi-forniture
owner: RM
editor: [RM, SC, GB]
visibilita: azienda
stato: vivo
ultima-revisione: 2026-05-23
---

# CLAUDE.md — Bianchi Forniture

> Istruzioni Claude specifiche per il fornitore Bianchi Forniture.
> Si aggiunge al kernel `vault/CLAUDE.md`.

---

## Contesto

Fornitore unico per finiture ossidate / verniciate / zincate. Categoria
A (strategico, sostituirlo richiede tempo). Relazione consolidata ma
gestita con un occhio al prezzo (vedi MEMORY 2026-05-02 — abbiamo
perso una offerta cliente per il loro sovrapprezzo finitura).

## Regole specifiche

- **Tono comunicazioni**: formale, "Lei", in italiano. Carlo Bianchi
  preferisce mail concise (max 6-7 righe).
- **Mai** scavalcare RM per nuovi ordini: tutti gli ordini passano via
  RM, anche le urgenze. SC se urgente avvisa RM via Slack interno,
  non chiama Carlo direttamente.
- **Mai** menzionare al fornitore che stiamo cercando alternative
  (ricerca in corso, task in [[tasks]]) finche' non e' avviata la
  qualifica con seconda opzione.
- **Sempre** specificare in ordine: codice nostro (F-OSS-NER, ecc.) +
  riferimento al disegno cliente. Loro tracciano per codice nostro,
  non per disegno.

## Persone chiave (lato fornitore)

Vedi [[persone]] per la tabella completa. In breve:
- Carlo Bianchi — titolare, decisore commerciale
- Sara Bianchi (figlia) — operativa, riceve ordini, gestisce avanzamenti
- Tecnico produzione (Ing. Lanzi) — solo per non conformita tecniche

## Output tipici di Claude

- **Bozza ordine** in `knowledge/ordine-NNNN-YYYY-MM-DD.md` (RM rivede e
  invia)
- **Bozza mail richiesta quotazione** in chat
- **Sintesi visite / call** in `riunioni/YYYY-MM-DD_titolo.md`
- **Verbali apertura RNC** (Rapporto Non Conformita) — pattern post-mortem
  ridotto, in `post-mortem/`
