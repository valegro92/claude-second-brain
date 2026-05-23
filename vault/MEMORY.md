---
tipo: memory-aziendale
owner: AF
editor: [AF, GB]
visibilita: azienda
stato: vivo
ultima-revisione: 2026-05-23
revisore: AF
---

# MEMORY aziendale (L1)

> Memoria persistente dell'azienda. Solo decisioni e lezioni che valgono
> per piu' reparti. Le decisioni di reparto stanno in
> `reparti/<X>/MEMORY.md` (L3). Le decisioni di singoli clienti /
> fornitori / commesse stanno in `clienti/<X>/MEMORY.md`,
> `fornitori/<X>/MEMORY.md`, `commesse/<X>/MEMORY.md` (L4).
>
> Aggiornata nel rituale mensile Owner + Custodi (Livello 3 del
> protocollo). Max 15-20 entry per sezione: quando cresce, condensare le
> piu' vecchie in una entry di sintesi.
>
> Formato: `## YYYY-MM-DD — titolo breve` poi 2-4 righe di contesto +
> link al ADR se esiste.

---

## Decisioni cross-reparto

## 2026-05-12 — Tutte le offerte sopra 25.000 euro passano per AF prima di partire
Decisione presa al rituale mensile di maggio. Vale per commerciale e per
service. Soglia ferma a 25k netti, IVA esclusa. Owner: AF. Editor che
puo' modificare la soglia: solo AF. Vedi
[[decisioni/0001-_esempio-adr]] per il razionale completo.

## 2026-04-08 — Adottato il vault PMI come SSOT per clienti, fornitori e commesse
Il Drive condiviso "Commerciale" resta in sola lettura dal 2026-06-01.
Le schede vive di clienti e fornitori vivono nel vault. Allegati binari
restano su Drive ma linkati dal MOC. Custode capo: GB. Decisione
firmata da AF al rituale di aprile.

## 2026-03-20 — Brand voice unificato fra commerciale e marketing
Stop a tono "noi siamo leader" nelle offerte. Si scrive come parla AF
in azienda: diretto, esempi concreti, mai superlativi. La fonte e'
`references/brand-voice.md`. Vale anche per le mail commerciali, non
solo per i materiali pubblici.

---

## Lezioni aziendali

## 2026-05-05 — I post-mortem chiusi a caldo perdono il 50% delle azioni correttive
Su 4 post-mortem fatti nel Q1, i 2 chiusi entro 48h hanno generato
azioni che sono state davvero implementate. Gli altri 2, chiusi dopo 2+
settimane, sono rimasti carta. **Regola operativa**: il post-mortem si
fa entro 5 giorni lavorativi dall'evento, e le azioni vanno in
`tasks.md` dell'oggetto con scadenza.

## 2026-02-14 — I fornitori "occasionali" non vanno tenuti nel vault
Nel Q4 2025 avevamo creato schede fornitore anche per chi usavamo una
volta l'anno. Risultato: 40 schede morte. **Regola operativa**: si crea
una scheda fornitore solo se ci sono almeno 3 ordini all'anno o se vale
sopra 5k euro. Sotto soglia → solo riga nella contatti del reparto.

---

## Stack tool aziendale

## 2026-05-23 — Stack attivo
- **Gestionale**: TeamSystem (anagrafiche, ordini, fatturazione). Sola
  lettura dal vault.
- **Cloud**: Google Workspace (Drive condiviso "Commerciale",
  "Produzione", "Amministrazione"). Drive resta per gli allegati
  binari, non per le schede vive.
- **Email**: Gmail per tutti. Casella `info@` gestita da GB.
- **NAS produzione**: `/Volumes/produzione/` (Mac) o `Z:\produzione\`
  (Windows). Disegni CAD e foto cantieri, non entrano nel vault.
- **Vault**: questo repo, sincronizzato via Git su tutte le macchine
  delle persone con `editor:` in qualche file.
- **Claude**: assistente AI. Accesso a vault (lettura/scrittura via
  bozza), niente accesso diretto a TeamSystem.

---

*Storia precedente al 2026-02 condensata in entry di sintesi se serve.*
