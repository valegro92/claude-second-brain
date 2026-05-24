---
title: "feat: Custodia v2 Sprint 0 — Validazione pitch agent-ready"
type: feat
status: active
date: 2026-05-24
origin: docs/brainstorms/custodia-v2-agent-ready-requirements.md
---

# feat: Custodia v2 Sprint 0 — Validazione pitch agent-ready

## Summary

Sprint 0 di Custodia v2 (durata 2 settimane). Obiettivo: validare con 3 PMI italiane reali se il pitch "second brain agent-ready" genera domanda di acquisto, **prima** di investire tempo nello schema agent-friendly del vault (Sprint 1) e nel MCP server (Sprint 2). Output: gate GO/NO-GO documentato, con dati. Nessun codice di prodotto. Solo discovery, materiali sales, e una decisione.

---

## Problem Frame

L'origin doc segnala un evidence gap esplicito: la motivazione di Custodia v2 oggi è "trend Karpathy + copycat edra.ai + tesi del fondatore", non "ho 3 PMI che me l'hanno chiesto". Costruire schema agent-friendly e MCP server prima di validare il pitch significa rischiare 8 settimane di lavoro per scoprire che il mercato non capisce il messaggio. Sprint 0 chiude questo gap a costo minimo (1-2 settimane part-time, zero codice nuovo).

---

## Requirements

- R1. **3 customer discovery call** con PMI italiane 30-50 dipendenti completate ed analizzate (origin: assumption critica "Evidence gap")
- R2. **Script intervista** strutturato e riusabile per future call (riusabile anche per Sprint 4 case study e B2C content)
- R3. **Materiali sales v2** minimi pronti: one-pager + 3 slide pitch + FAQ "agent-ready" (per condurre la call, non per chiudere)
- R4. **Decisione GO/NO-GO documentata** con criteri espliciti (origin: metriche di successo)
- R5. **Eventuale pivot di pitch identificato** se NO-GO (cosa cambiare prima di riprovare)

---

## Scope Boundaries

- Nessun codice di prodotto (schema, MCP, reconcilers) — è Sprint 1+
- Nessuna pre-vendita né closing in Sprint 0 — solo discovery
- Nessuna ricerca competitor approfondita oltre edra.ai (è già nell'origin)
- No telefonate fredde a freddo se la tua rete non basta — meglio rimandare di una settimana che chiamare 3 sconosciuti che non rispondono

### Deferred to Follow-Up Work

- Pricing finale del tier "agent-ready" → Sprint 4 quando hai dato il pilota
- Aggiornamento `docs/01-cosa-vendi.md` completo → Sprint 3 dopo demo
- Naming/branding v2 ("Custodia AI"? altro?) → in parallelo a EUIPO, non bloccante per Sprint 0

---

## Context & Research

### Relevant Code and Patterns

- `docs/brainstorms/custodia-v2-agent-ready-requirements.md` — origin doc (sezioni: Problema/Ipotesi, Chi serviamo, Roadmap Sprint 0)
- `docs/commerciale/` (se esiste già) — materiali sales v1 di Custodia da cui partire
- `_brief/` — note di pianificazione storiche con materiali pitch pregressi
- `README.md` sezione "Per chi" — definizione attuale del target PMI

### Institutional Learnings

- Custodia v0.2.0 ha già una definizione operativa del target ("30-50 dip., dolore knowledge nel commerciale, Custode disponibile"). Riusare verbatim per qualificare le 3 PMI.

### External References

- edra.ai — leggere homepage + 1 case study per estrarre 3 frasi chiave del loro pitch (da NON copiare, da rispondere)
- Karpathy second-brain wave 2026 — 1 post di riferimento da citare in apertura call come "social proof culturale"

---

## Key Technical Decisions

- **Niente discovery survey, solo call** — survey su PMI italiane non-tech ha tasso risposta sotto 5%. Call 1:1 da rete esistente di Valentino.
- **Recording opt-in con Fireflies/Otter** — per estrarre quote verbatim da riusare in landing e sales deck (chiedere consenso esplicito a inizio call).
- **Pitch in 2 varianti A/B** — variante A "second brain agent-ready" (tesi Karpathy), variante B "il tuo assistente che conosce i tuoi clienti" (job-to-be-done). Testare entrambe per capire quale linguaggio risuona.

---

## Open Questions

### Resolved During Planning

- Chi chiamare? → 3 PMI dalla rete diretta di Valentino. Se la rete non ne ha 3 qualificate, allungare Sprint 0 di 1 settimana per cold reach mirato (LinkedIn, non email).
- Quanto durano le call? → 30-45 min. Più lungo = bias di compiacenza.

### Deferred to Implementation

- Quale tool di recording (Fireflies vs Otter vs trascrizione manuale)? — sceglie U2 in base a cosa hai già attivo
- Quale formato pitch slide (Gamma? Google Slides? PDF?) — sceglie U3, ottimizza per condivisione post-call

---

## Implementation Units

### U1. Script intervista discovery

**Goal:** Script strutturato per 3 call. Domande aperte, ordine progressivo (situazione → dolore → soluzioni attuali → reazione al pitch → willingness to pay).

**Requirements:** R1, R2

**Dependencies:** Nessuna

**Files:**
- Create: `docs/commerciale/discovery-script-v2.md`

**Approach:**
- 5 sezioni: (1) Contesto azienda 5min, (2) Routine commerciale 10min, (3) Dolore knowledge attuale 10min, (4) Reazione al pitch A vs B 10min, (5) Pricing sensitivity 5min
- Domande aperte ("raccontami una giornata tipo del tuo commerciale"), no leading questions ("non saresti d'accordo che...")
- Sezione pitch include 2 frasi prelevate da edra.ai per misurare se la tesi globale è già nota
- Template di compilazione strutturata post-call (timestamp delle quote chiave + verbatim)

**Patterns to follow:**
- Mom Test (Rob Fitzpatrick) — domande sul passato concreto, non sul futuro ipotetico
- Se esiste `docs/commerciale/discovery-v1.md`, ereditare la sezione Contesto

**Test scenarios:**
- Happy path: scrivere lo script, rileggerlo, simulare risposte di un amico fittizio "Carlo del commerciale di una PMI metalmeccanica" → script regge senza buchi
- Edge case: l'intervistato dice "no, da noi non c'è quel problema" alla sezione 3 → lo script ha un ramo di approfondimento "cosa fa diventare la giornata difficile invece?"
- Edge case: pitch A flop totale → variante B deve essere presentabile in isolamento

**Verification:**
- Script in markdown, leggibile in 3 minuti, ogni sezione ha durata stimata e domande numerate
- Variante A e B del pitch riportate verbatim (le userai 3 volte, devono essere identiche tra call)

---

### U2. Setup logistico delle 3 call

**Goal:** 3 PMI qualificate, 3 slot in calendar, recording attivo, prep mentale.

**Requirements:** R1

**Dependencies:** U1

**Files:**
- Create: `docs/commerciale/discovery-tracker.md` (foglio leggero: chi/quando/stato/quote chiave)

**Approach:**
- Lista 5-7 PMI candidate dalla rete (sovrabbondanza per attrito di scheduling)
- Reach via canale più caldo (LinkedIn DM, email da contatto comune, telefonata diretta). Mai cold email a freddo.
- Pitch del reach: "sto validando un'idea, non ti vendo niente, 30 minuti, ti mando dopo 1 paginetta di valore" — la promessa di valore di ritorno è chiave
- Calendar booking con Cal.com / Calendly o calendar invite diretto
- Recording: chiedi consenso esplicito a inizio call ("posso registrare per non perdere le tue parole?")

**Patterns to follow:**
- Tracker stile Notion ma in markdown locale (vivibile in Obsidian, coerente con prodotto)

**Test scenarios:**
- Happy path: 3 call confermate entro 10 giorni
- Edge case: solo 2 PMI rispondono → decidere se allungare 1 settimana o procedere con 2 (criterio: se entrambe danno stesso segnale forte = sufficiente per GO; se discordi = serve la 3a)
- Error path: PMI cancella all'ultimo → slot di buffer pre-pianificato in settimana 2

**Verification:**
- 3 slot calendarizzati e confermati, link recording pronto, script aperto

---

### U3. Materiali pitch minimi (one-pager + 3 slide + FAQ)

**Goal:** Materiale da condividere POST call, non durante. Serve perché la PMI possa girarlo internamente (al titolare, all'IT) e per misurare se chiamano indietro.

**Requirements:** R3

**Dependencies:** U1 (script definisce il messaggio)

**Files:**
- Create: `docs/commerciale/v2/one-pager.md`
- Create: `docs/commerciale/v2/pitch-slides.md` (markdown ora, conversione in slide solo se serve)
- Create: `docs/commerciale/v2/faq-agent-ready.md`

**Approach:**
- **One-pager:** 1 pagina, 5 sezioni — Cos'è / Per chi / Cosa porti a casa in 4 settimane / Prezzo orientativo / Come iniziare
- **3 slide:** problema (PMI senza wiki ≠ agent-ready), soluzione (Custodia v2), prova (screenshot vault + frame "agente che risponde a Rossi" — anche solo mockup statico va bene per Sprint 0)
- **FAQ:** 8-10 domande prevedibili (sicurezza dati, GDPR, cosa cambia se cambio fornitore, quanto serve il Custode, cosa succede se l'agente sbaglia, integrazione con gestionale esistente)
- Tono: pragmatico italiano, no buzzword AI-pump

**Patterns to follow:**
- `docs/commerciale/` di v1 se esiste — eredita struttura, cambia messaggio
- Non investire in design grafico in Sprint 0 — Markdown + screenshot Obsidian = sufficiente

**Test scenarios:**
- Happy path: 1 amico non-Custodia legge l'one-pager in 2 min e sa spiegare cos'è
- Edge case: 1 amico tech-skeptic legge la FAQ → identifica 2 domande che mancano → integrare prima della call

**Verification:**
- 3 file in `docs/commerciale/v2/`, condivisibili come link/PDF
- Non sono pronti per closing, sono pronti per discovery

---

### U4. Analisi e decisione GO/NO-GO

**Goal:** Sintetizzare le 3 call e prendere una decisione documentata.

**Requirements:** R4, R5

**Dependencies:** U1, U2, U3 (e ovviamente le 3 call eseguite)

**Files:**
- Create: `docs/commerciale/v2/sprint-0-report.md`
- Modify: `docs/brainstorms/custodia-v2-agent-ready-requirements.md` (aggiunge in coda: "Sprint 0 outcome: GO/NO-GO, data, evidence summary")

**Approach:**
- Per ogni call, estrarre: 3 quote verbatim, willingness-to-pay espressa, top 3 obiezioni, reazione pitch A vs B
- **Criteri GO** (devono essere veri 2/3): (a) almeno 2 PMI hanno detto "sì, se costa €X lo compro / discuterei con il titolare", (b) il dolore "recupero storico cliente" emerge spontaneamente in almeno 2 call **prima** che tu lo nomini, (c) nessuna delle 3 dice "questo lo fa già il nostro [strumento esistente]"
- **Criteri NO-GO**: nessuna PMI mostra intent di acquisto, oppure il pitch agent-ready è percepito come "fantascienza"
- **Pivot identificato in caso NO-GO**: variante di pitch testata nelle call (B vs A), o segmento diverso (es. studi professionali invece di manifatturiero), o deliverable diverso (es. "wiki ordinata" senza agente)

**Patterns to follow:**
- Report breve, max 2 pagine. Quote verbatim > prosa di sintesi.

**Test scenarios:**
- Happy path GO: report scritto, decisione GO, Sprint 1 inizia
- Happy path NO-GO: report scritto, pivot identificato, ritorno a `/ce-brainstorm` con dati nuovi
- Edge case: 2 GO + 1 NO-GO discordi → 4a call extra prima di decidere (no decisione 50/50)

**Verification:**
- Report letto, decisione comunicata, origin doc aggiornata con outcome

---

## Agenti del team da richiamare in parallelo (raccomandazione meta)

Hai chiesto quali agenti tenere sempre attivi in parallelo. Mappa per Sprint, dal CLAUDE.md utente:

### Sempre attivi (ogni sprint)
- **`product-manager`** — proprietario di requisiti, user stories, decisione GO/NO-GO. In Sprint 0: aiuta a rifinire script intervista (U1) e criteri GO (U4). In sprint successivi: scrive user stories, prioritizza backlog.
- **`code-reviewer`** — review finale prima di ogni merge. In Sprint 0 minimo (poco codice), ma da Sprint 1 ogni unit chiude con review.

### Sprint 0 (questo)
- **`product-manager`** (lead) — owns U1, U4
- **`ux-designer`** — per definire persona "commerciale PMI" che usa in U1 e U3
- **`data-analyst`** — per template di estrazione strutturata delle quote in U4 e schema metriche before/after
- **`tech-writer`** — per U3 (one-pager + FAQ), assicura tono e leggibilità

### Sprint 1 (schema agent-friendly)
- **`software-architect`** (lead) — schema YAML frontmatter, decisioni su modello dati
- **`fullstack-developer`** — modifiche ai reconcilers in `reconcilers/`
- **`qa-engineer`** — test su vault demo, criteri "l'agente risponde bene"
- **`product-manager`** — verifica che lo schema serva il job-to-be-done (risposte a Rossi)

### Sprint 2 (MCP server)
- **`software-architect`** (lead) — design MCP server, stdio/HTTP, autenticazione
- **`fullstack-developer`** — implementazione
- **`security-engineer`** — review sicurezza (il MCP espone dati cliente, non scherzare)
- **`qa-engineer`** — test integrazione con Claude Code reale

### Sprint 3 (demo closing)
- **`ux-designer`** — script demo, sequenza "wow moment"
- **`tech-writer`** — aggiornamento materiali sales completi
- **`product-manager`** — coordinamento

### Sprint 4-5 (pilota cliente)
- **Tutti**, con `qa-engineer` e `data-analyst` particolarmente attivi per misurare metriche before/after

### Sprint 6 (outcome service pilot)
- **`product-manager`** (lead) — definisce SLA e cosa significa "10 risposte/mese"
- **`data-analyst`** — misura tempo operatore e qualità output
- **`devops-engineer`** — se l'agente gira in modo continuativo serve infrastruttura

### Quando NON usare agenti
- Conversazioni one-shot di chiarimento con un cliente (fallo tu, l'agente non aggiunge)
- Decisioni strategiche che richiedono il tuo intuito di founder (es. pricing finale, naming) — usa l'agente come sparring partner, non come decisore

### Pattern di lavoro raccomandato per ogni unit
1. Apri sessione con `/ce-plan` o `/ce-work` sulla unit
2. Chiama l'agente lead dell'area (product-manager, software-architect, ecc.) per il primo round
3. Implementazione con `fullstack-developer` o `ml-engineer` se ML
4. Chiusura con `code-reviewer` + `qa-engineer`
5. `/clear` tra unit diverse per evitare contaminazione (regola d'oro del tuo CLAUDE.md)

---

## System-Wide Impact

- **Interaction graph:** Sprint 0 tocca solo `docs/commerciale/v2/` e l'origin brainstorm. Nessun impatto su codice esistente.
- **Decision blast radius:** l'output di Sprint 0 condiziona tutti gli sprint successivi. Un GO debole (2/3) richiede ulteriore validazione in Sprint 1.
- **Reputation surface:** stai parlando con PMI vere a nome di un prodotto non finito. Pitch onesto ("sto validando, non ti vendo") protegge il brand "La Cassetta degli AI-trezzi".

---

## Risks & Dependencies

| Rischio | Mitigazione |
|---|---|
| La rete di Valentino non ha 3 PMI qualificate | Buffer di 1 settimana, fallback su cold reach LinkedIn mirato (no email) |
| Bias di compiacenza (gli amici dicono "bello" per cortesia) | Mom Test: solo passato concreto, no opinioni sul futuro |
| Pitch agent-ready troppo astratto per PMI non-tech | Variante B ("assistente che conosce i clienti") in A/B, demo screenshot statici |
| 2 GO discordi vs 1 NO-GO → analysis paralysis | Criteri GO espliciti scritti PRIMA delle call. Se 2/3 + dolore spontaneo → GO. |
| Investo Sprint 0 e poi salto subito a Sprint 2 ignorando feedback | Vincolo: `/ce-plan` Sprint 1 può partire SOLO dopo che U4 ha emesso GO scritto |

---

## Documentation / Operational Notes

- Tutti i materiali in `docs/commerciale/v2/` non finiscono nel deploy del sito `site/`. Restano interni.
- Recording delle call: stoccare in cartella **fuori repo** (Drive privato) — contengono dati di terzi
- Quote verbatim usate in landing future: anonimizzate (settore + ruolo, no nome azienda) salvo consenso scritto

---

## Sources & References

- **Origin document:** [docs/brainstorms/custodia-v2-agent-ready-requirements.md](../brainstorms/custodia-v2-agent-ready-requirements.md)
- Related code: `reconcilers/`, `categorizers/`, `vault/`
- External: edra.ai homepage, Rob Fitzpatrick "The Mom Test", Karpathy second-brain 2026 wave
