# Brief — Product Vision (Step 1)

Cartella di brief temporanea per i 3 cantieri dello Step 1. Sarà rimossa a fine Step 1.

## Cos'è il prodotto

**Toolkit consulenziale** che Valentino porta dal cliente PMI per costruire una wiki aziendale.

- **Modello consegna**: Toolkit + Valentino nel ciclo (kick-off on-site, scandagliamento supervisionato da remoto, handover on-site)
- **Target v1**: PMI 30-50 persone con IT/Office manager presente come Custode
- **Fonti da scandagliare** (Step 2, non Step 1): Google Drive, Microsoft 365/OneDrive/SharePoint, Email (Gmail/Outlook), NAS, Server
- **Autonomia agente**: tu approvi ogni batch di 50 bozze

## 3 atti della delivery

1. **Kick-off on-site** (½ giornata) — wizard azienda, connettori MCP, perimetro privacy
2. **Scandagliamento supervisionato** (1-2 settimane, remoto + call settimanale) — agente lavora a batch, Valentino approva
3. **Handover on-site** (½ giornata) — training Custode, primo rituale settimanale, mail decommissioning

## Lo Step 1 NON include

- Scanner, extractor, batch-approval, dashboard `_status/` — sono Step 2-3
- Modalità on-premise (privacy stretta) — è Step 3 o v1.5
- Connettori a gestionali italiani (TeamSystem, Zucchetti, ecc.) — esclusi dalla v1

## Lo Step 1 include

- Repo pulito (audit fix dove non auto-risolti dalla sostituzione del vault)
- Nuovo `vault/` con framework PMI istanziato come esempio
- `_legacy-single-user/` con archivio del vault solista (per riferimento, non più mantenuto)
- `skills/` riscritte per il modello multi-utente
- `docs/` riscritti secondo il piano (7 doc, niente triplicazioni)

## Branch e merge

- Branch corrente: `product-v1-step-1` (dal branch `claude/wiki-construction-review-5NKQt`)
- A fine Step 1: PR draft verso main (o verso il branch di review)
- I 3 cantieri lavorano in isolation worktree per non collidere

## Decisioni già prese (non riaprire)

- `vault/` viene sostituito (non duplicato): il vecchio diventa `_legacy-single-user/`, il nuovo prende il nome `vault/`
- Le 3 documentazioni `INIZIA-QUI.md`, `installazione-per-dummies.md`, `guida-formazione.md` triplicate vanno consolidate, non mantenute in parallelo
- Tono: italiano, diretto, niente buzzword, esempi concreti con nomi realistici (vedi `framework.md` e `installazione-per-dummies.md` attuali)
- Niente emoji
