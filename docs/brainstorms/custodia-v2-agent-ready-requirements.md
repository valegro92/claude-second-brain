# Custodia v2 — Second Brain Agent-Ready

**Stato:** brainstorm → requirements (rev 2)
**Data:** 2026-05-24 (rev iniziale) — aggiornato 2026-05-24 con sharpening shape prodotto
**Autore:** Valentino Grossi (brainstorm con ce-brainstorm)
**Successore di:** Custodia v0.2.0 (wiki ordinata per PMI)

---

## TL;DR

Custodia smette di vendere "wiki ordinata" e inizia a vendere **second brain agent-ready** — un knowledge layer strutturato per essere letto da agenti off-the-shelf (Claude Code, Codex, OpenClaw, Cowork, Hermes) che rispondono a clienti/fornitori usando lo storico aziendale. Il pitch è: "gli agenti senza knowledge sono colleghi intelligenti che non conoscono la tua azienda — Custodia crea il second brain che li mette al lavoro".

Il deliverable consegnato al cliente è un **vault Obsidian con file `.md` strutturati** (di sua proprietà, portabile), prodotto da un **CLI a stadi guidato dal consulente** che si collega alle sorgenti aziendali e popola il vault. Il cliente collega autonomamente l'agente che preferisce al vault via un MCP server incluso.

Custodia gira in due modalità di inferenza interscambiabili, scelte all'Atto 1 con il cliente: **Cloud** (Claude API, default, GDPR-compliant) e **Sovrano** (LLM su server dedicato in Italia / UE presso provider di inferenza sovrana — Xference.ai osservato come candidato, non vincolante). Vault prodotto identico nelle due modalità.

Stesso modello consulenziale chiavi-in-mano. Su un cliente pilota si testa un layer "outcome service" (es. 10 risposte preparate/mese) come seme di un futuro revenue stream ricorrente.

---

## Problema e ipotesi

### Problema dichiarato
PMI italiane 30-50 dipendenti hanno patrimonio documentale sparso (Drive, NAS, email, portatili). Il commerciale perde tempo ogni mattina a ricostruire lo storico col cliente prima di rispondere. Strumenti emergenti (Copilot, ChatGPT, agenti) non funzionano sopra il caos.

### Ipotesi del prodotto
1. **L'ondata Karpathy-2026 sul second brain** (personal → organizational) crea una finestra di mercato in cui "agent-ready" diventa una categoria comprensibile.
2. **edra.ai dimostra la feature**, ma non può servire PMI italiane non-tech perché vende SaaS self-serve. La consulenza on-site è il *moat* difendibile in Italia.
3. **Un knowledge layer strutturato + MCP server** è sufficiente: gli agenti li mette già il mercato (Claude Code, Codex, Hermes). Custodia fa solo la base.

### Assumption critiche da validare PRIMA di costruire molto
- ⚠️ **Evidence gap**: la motivazione del progetto oggi è "trend + copycat + tesi del fondatore". Non ci sono ancora 3 PMI che hanno detto "questo lo compro". → **Da validare con 3 customer discovery call entro lo Sprint 1.**
- ⚠️ **ROI agente percepito**: assumiamo che PMI veda valore in "agente che risponde al cliente Rossi". Da provare con demo live davanti al cliente, non a parole.
- ⚠️ **Durability** (18-24 mesi): Microsoft Copilot e Google Gemini stanno integrando agenti nativi su M365/Workspace. Tesi di difesa: PMI italiane senza CRM strutturato hanno SOLO Drive+email caotico, e nessun agente nativo funziona sopra il caos. Da monitorare.

---

## Chi serviamo

### Cliente pagante
PMI italiana, **30-50 dipendenti**, manifatturiera o servizi B2B, con:
- 5-15 anni di patrimonio documentale sparso
- Un IT/Office manager interno disponibile a diventare **Custode** (2-4 ore/settimana per 3 mesi)
- Un dolore quotidiano di knowledge nel commerciale (recupero storico cliente)

### Persona primaria che genera valore
Il **commerciale** della PMI — quello che ogni mattina deve rispondere a 5-10 mail di clienti e oggi perde 30-60 min/cliente a recuperare il contesto. È a lui che la demo deve far dire "lo voglio".

### Operatore del prodotto
**Valentino o consulente certificato** (fase 2). Non la PMI da sola. "Plug-and-play" significa: il toolkit gira liscio per il consulente, non self-serve per la PMI.

---

## Cosa cambia rispetto a Custodia v0.2.0

| Dimensione | v0.2.0 (oggi) | v2 (target) |
|---|---|---|
| Pitch | "wiki ordinata in 4 settimane" | "gli agenti senza knowledge sono colleghi che non conoscono la tua azienda — Custodia crea il second brain agent-ready in 4 settimane" |
| Deliverable | Vault Obsidian leggibile da umani | Vault Obsidian + schede strutturate + MCP server, **di proprietà del cliente** (portabile, non lock-in) |
| Meccanismo di produzione del vault | Consulente scrive markdown a mano | **CLI a stadi** che il consulente avvia in azienda: connettori a sorgenti (Drive, Outlook, NAS, gestionali), estrazione assistita da LLM, review umana a ogni stadio prima del successivo |
| Schema schede cliente | Markdown prose | Markdown prose **+ frontmatter YAML strutturato** (storico contatti, prezzi praticati, eccezioni datate, red flag, stato relazione) |
| Modalità di inferenza | n/a (no LLM in v0.2.0) | **Doppia modalità scelta all'Atto 1**: Cloud (Claude API) o Sovrano (LLM su provider di inferenza sovrana italiano/EU) |
| Closing dell'Atto 3 | Training Custode + consegna manuale | Training Custode + **demo live agente che risponde al cliente Rossi** davanti al team |
| Pricing | €8.5-14K setup | €12-18K setup Cloud; +€2-4K setup Sovrano (range indicativo, da validare con vendor) |
| Manutenzione | €800-1.500/mese | Stesso + opzione "outcome service" pilota (vedi sotto) |

### Seme outcome service (challenger di C)
Su **1 cliente pilota** offrire gratis 1 settimana di "10 risposte preparate ai clienti più attivi" usando Custodia + agente. Obiettivo: capire se PMI paga per outcome ricorrente. Se sì, è la roadmap del revenue stream 2027.

## Architettura concettuale: ingestion vs consumption

Due flussi distinti che il prodotto serve, da non confondere:

- **Ingestion** — Custodia legge dalle sorgenti del cliente (Drive, Outlook, NAS, gestionali) e *costruisce* il vault. Qui servono connettori e LLM (Cloud o Sovrano).
- **Consumption** — l'agente del cliente legge dal vault via MCP server e *risponde* al cliente finale. Qui non serve niente di nostro lato LLM: il cliente porta il suo agente.

Solo l'ingestion richiede la decisione Cloud/Sovrano. La consumption usa qualunque agente off-the-shelf scelga il cliente.

## Modalità di inferenza (decisione Atto 1)

La privacy è una paura verbalizzata frequentemente dai prospect ("dove finiscono i miei dati?"). Custodia la indirizza con due modalità interscambiabili, scelte insieme al cliente all'Atto 1.

### Cloud (default)
- LLM: Claude API (Anthropic), endpoint EU, DPA firmato, no-training su dati cliente
- Vantaggi: prezzo a consumo basso, velocità di generazione vault, zero hardware extra
- Adatto a: clienti pragmatici, no blocker espliciti sulla privacy

### Sovrano
- LLM: modello open-source di livello (es. Qwen 3 Max o equivalente) ospitato su **provider di inferenza sovrana italiano/UE con server dedicato per cliente**
- Candidato osservato: **Xference.ai** (Italia, server dedicati, posizione legale di "inference provider non data processor"). Non vincolante: altri provider equivalenti vanno valutati prima della scelta operativa.
- Vantaggi: pitch onesto "i dati non escono dall'Italia / dall'UE", differenziazione vs Big Tech US
- Costi: +€2-4K setup, +mensile dedicato (range indicativo, da quotare con vendor scelto)
- Adatto a: clienti che verbalizzano esplicitamente il blocker privacy
- **Cadenza di costruzione: on-demand al primo cliente che la chiede e la finanzia.** Sales-side è dichiarata come "tier disponibile, 2-3 settimane di lead time". Non costruita preventivamente.

### Cosa NON è la modalità Sovrano
- Non è "Qwen su RunPod/Hetzner generici": tecnicamente i dati escono dall'azienda comunque, viene meno la promessa
- Non è on-premise nel cliente (workstation fisica nel loro CED): rimandato, troppo costoso e complesso per v0.1
- Non è self-host Valentino (Mac Studio nel proprio studio): rimandato

### Architettura interna che permette la doppia modalità
Il CLI Custodia astrae l'LLM dietro un'interfaccia provider sin dallo Sprint 1, anche se v0.1 contiene solo l'adapter Anthropic. L'adapter per il provider Sovrano si scrive quando arriva il primo cliente che lo finanzia. Costo stimato: 1-2 giorni di lavoro.

## Discovery sorgenti e connettori (Atto 1)

L'auto-discovery magica degli strumenti del cliente non esiste e non serve. La discovery è un **questionario di Atto 1** condotto dal consulente con il Custode/IT:

> Email su che piattaforma? File aziendali principali dove? Fatturazione con quale software? CRM? ERP/gestionale?

Il CLI offre poi il menu dei connettori disponibili per quello stack.

### Connettori prioritari per v0.1 (4-5 pre-costruiti)
- Google Drive (90% delle PMI italiane su Workspace o GSuite legacy)
- Outlook 365 / Exchange (l'altra metà del mercato)
- Filesystem locale (NAS, cartelle di rete) + parsing PDF / Excel / Word
- Fatture in Cloud (regolato, fatturazione elettronica diffusissima)
- *Candidato 5°*: TeamSystem o Zucchetti (uno dei due, da scegliere via discovery Sprint 0)

### Connettori fuori v0.1
- ERP legacy (AS400, gestionali custom): export manuale a CSV
- CRM (HubSpot, Pipedrive): rinviato a quando un cliente lo richiede
- WhatsApp Business: rinviato (ma frequente nelle PMI italiane, da tenere d'occhio)
- Connettori a tutti gli altri gestionali italiani: backlog, scritti on-demand

---

## Successo

### Definizione di "fatto" per v2 (12 mesi)
- ✅ 5 delivery Custodia v2 a clienti paganti
- ✅ 1 demo "agent answers a real customer email" filmata e usata in sales
- ✅ 3 case study con metrica before/after sul tempo di risposta cliente
- ✅ 1 cliente pilota con outcome service attivo e in pagamento
- ✅ Schema vault agent-ready documentato e riusabile

### Metriche di prodotto (per cliente)
- **Time-to-response cliente**: misurare prima/dopo. Target: -50% sul tempo medio di stesura risposta.
- **Tasso di accettazione bozza agente**: il commerciale invia la bozza dell'agente con quante modifiche? Target sprint 3: >50% inviate con modifiche minori.
- **Adozione interna**: quanti commerciali usano l'agente almeno 1x/giorno dopo 30gg. Target: 60%.

### Quando smettere
Se dopo **3 delivery v2** nessun cliente accende l'agente più di 2 settimane post-handover, l'ipotesi "agent-ready vale più di wiki ordinata" è falsa. Torna a vendere Custodia v0.2.0 e riposiziona.

---

## Roadmap SCRUM-style (sprint da 2 settimane)

Lavoriamo per incrementi vendibili. Ogni sprint chiude con qualcosa di mostrabile a un cliente.

### Sprint 0 — Validazione (settimana 1-2)
**Goal:** verificare l'evidence gap prima di costruire.
- 3 customer discovery call con PMI 30-50 (rete tua o cold)
- Script: "se aveste un assistente che risponde al cliente con tutto lo storico in mano, lo paghereste? Quanto? Cosa vi farebbe dire di no?"
- **Exit gate:** almeno 2/3 dicono "sì, se costa X". Se no, rivedi pitch prima di proseguire.

### Sprint 1 — Schema agent-friendly (settimana 3-4)
**Goal:** vault Obsidian che un agente legge bene.
- Frontmatter YAML strutturato per schede `clienti/`, `fornitori/`, `commesse/`
- Aggiornare reconcilers per popolare frontmatter (non solo body)
- Test con Claude Code: "rispondi al cliente Esempio Srl" su vault demo. Funziona o no?
- **Mostrabile:** screen recording di Claude Code che pesca dal vault e produce bozza coerente.

### Sprint 2 — MCP server (settimana 5-6)
**Goal:** vault espone tool MCP standard.
- Tool: `get_client_history`, `find_similar_offers`, `recent_communications`, `search_vault`
- Stdio + HTTP transports
- Documentazione installazione per Claude Code/Codex/Hermes
- **Mostrabile:** Claude Code locale connesso via MCP al vault demo, agente risponde con dati reali.

### Sprint 3 — Demo da closing (settimana 7-8)
**Goal:** rifare l'Atto 3 dell'handover con demo agente live.
- Script demo: cliente vede l'agente rispondere a 3 sue mail reali davanti a lui
- Materiali commerciali aggiornati (deck, FAQ, video demo)
- **Mostrabile:** ripeti l'Atto 3 con un cliente esistente di v0.2.0 come pilota retroattivo.

### Sprint 4-5 — Pilota cliente reale v2 (settimana 9-12)
**Goal:** prima delivery full v2 a PMI vera. Pricing €12-18K.
- Run del playbook v2 completo da Atto 1 ad Atto 3
- Misurazione metriche before/after
- **Mostrabile:** case study scritto.

### Sprint 6 — Esperimento outcome service (settimana 13-14)
**Goal:** 1 settimana gratis di "10 risposte/mese" sul cliente pilota.
- Tu (o sub-agente) operi l'agente sopra il vault, consegni le bozze al commerciale
- Domanda al cliente alla fine: "questo lo vuoi sempre?"
- **Mostrabile:** sì/no del cliente, e dato sul tempo di operatore.

### Oltre lo Sprint 6
- Se outcome service valida → progetta SaaS-like managed service (B)
- Se NO → punta su rete consulenti certificati (era B nel brainstorm, diventa la fase 2)

---

## Scope boundaries

### Dentro (v2)
- CLI a stadi (`custodia init`, `custodia scan <fonte>`, `custodia build <entità>`, `custodia review`) con consulente in loop
- 4-5 connettori sorgente pre-costruiti (Google Drive, Outlook 365, filesystem+PDF/Excel, Fatture in Cloud, + 1 gestionale da validare)
- Schema vault agent-friendly + MCP server (già implementato in `product/mcp-server/`)
- Schede cliente/fornitore/commessa strutturate con frontmatter YAML
- Modalità Cloud (Claude API) costruita in v0.1
- Modalità Sovrano predisposta come opzione visibile in sales, costruita on-demand al primo cliente che la finanzia
- Astrazione provider LLM (interfaccia) presente sin dallo Sprint 1
- Demo live agente nel closing Atto 3
- Riposizionamento narrativo "agent-ready"
- Pilota outcome service su 1 cliente
- Materiali commerciali aggiornati

### Deferred for later (rimandato, può rientrare in v2.1+)
- Modalità Sovrano costruita preventivamente prima del primo cliente che la chiede
- Self-host del consulente (Mac Studio M4 Ultra) come terza modalità di inferenza
- On-premise nel cliente (workstation fisica nel loro CED) come quarta modalità
- Auto-aggiornamento del vault in tempo reale dalle sorgenti (v0.1 è batch via rerun CLI)
- Multi-provider simultaneo (Anthropic + Sovrano + LLM locale tutti insieme)
- Connettori ERP legacy (AS400, gestionali custom)
- Connettori CRM (HubSpot, Pipedrive)
- Connettore WhatsApp Business — da tenere d'occhio perché frequente in PMI italiane
- Rete consulenti certificati — solo dopo 5 delivery v2 dirette
- App mobile, dashboard analytics, multi-tenant cloud

### Outside this product's identity (mai)
- Agenti custom costruiti da noi (no — il cliente porta Claude Code / Codex / OpenClaw / Cowork / Hermes off-the-shelf)
- SaaS self-serve per PMI (no — l'edge è la consulenza on-site)
- CRM completo (no — il vault NON è un CRM, è uno strato di contesto)
- Auto-discovery magica degli MCP/strumenti del cliente (no — il discovery è manuale via Atto 1 e resterà tale)
- Toggle runtime tra Cloud e Sovrano da parte dell'utente finale (no — è una scelta consulente-cliente all'Atto 1)
- Competitor di Salesforce, HubSpot, Notion AI, edra.ai, Microsoft Copilot

Custodia è il **layer di contesto italiano agent-ready** per PMI che nessuno di questi può servire perché richiede presenza fisica + lingua + cultura aziendale + lavoro sopra il caos documentale reale (non sopra dati già strutturati).

---

## Dipendenze e rischi

### Dipendenze
- Disponibilità Claude API (Haiku per estrazione/categorizzazione, Sonnet per generazione contenuto strutturato, opus 4.7 quando serve ragionamento)
- Stabilità protocollo MCP (Anthropic + ecosistema 2026)
- Obsidian come UI di visualizzazione (locale, sempre disponibile, no vendor lock-in sul deliverable)
- Disponibilità di un provider di inferenza sovrana italiano/UE quando si attiva la modalità Sovrano (Xference.ai osservato come candidato — vedi assunzioni sotto)
- Accesso del consulente alle sorgenti del cliente (credenziali Drive/Outlook/gestionali) — vincolo organizzativo dell'Atto 1, non tecnico

### Assunzioni da validare
1. La privacy è verbalizzata come blocker reale dai prospect — segnale aneddotico positivo dal fondatore, da confermare con i numeri dello Sprint 0 (quanti dei 3 prospect la nominano spontaneamente?)
2. Il provider di inferenza sovrana candidato (Xference.ai) è ancora in pre-registration: vendor risk concreto. Mitigato dal fatto che il vault resta del cliente in formato markdown; perdi solo la capacità di rigenerarlo in modalità Sovrano finché non si integra un altro provider.
3. Pricing del provider Sovrano non pubblico oggi: il delta "+€2-4K setup" è un range indicativo che va validato con quotazione vera prima di promettere a un cliente.
4. Il primo cliente Sovrano accetterà di finanziare un lead time di 2-3 settimane di setup. Se non lo accetta, perdiamo quel cliente o ci tocca anticipare la costruzione preventivamente.

### Rischi principali
1. **Evidence gap** non si chiude (Sprint 0 dice no) → pivot narrativo, torna a wiki ordinata
2. **PMI non vede valore agente** nella demo Atto 3 → seme del fallimento, ripensare deliverable
3. **Microsoft/Google integrano agenti nativi** prima dei 18 mesi → tesi di difesa è "noi sopra il caos Drive/NAS/gestionali, loro hanno bisogno di dati strutturati che le PMI non hanno"
4. **Tempo di Valentino single point of failure** → mitigato solo entrando in fase 2 (consulenti)
5. **Costo Claude per cliente** se agente sopra il vault esplode in token → monitorare da Sprint 2
6. **Vendor risk sul provider Sovrano** → se il candidato chiude, riscrivere l'adapter per provider equivalente (~1-2 giorni di lavoro). Il vault del cliente resta intatto.
7. **Promessa Sovrano svenduta** prima di costruirla → se più di un cliente la chiede contemporaneamente, lead time si allunga e bruciamo credibilità. Mitigato dalla cautela commerciale ("disponibile su richiesta, prenotiamo lo slot").

---

## Prossimi passi immediati

1. **Sprint 0 — in corso**: 3 PMI da chiamare per discovery. Script, qualificazione, outreach e tracker già pronti in `docs/commerciale/v2/`.
2. **Quotazione vendor Sovrano**: contattare Xference.ai (e 1-2 alternative) per range pricing reale, in parallelo con Sprint 0.
3. **MVP consumption già funzionante** in `product/` — usabile per la demo Atto 3 di un cliente esistente di v0.2.0 come pilota retroattivo.
4. Decidi nome v2 (Custodia resta? "Custodia AI"? altro?) — coordina con verifica EUIPO già in corso.
5. Quando Sprint 0 chiude positivo → `/ce-plan` su Sprint 1 (CLI ingestion + primi connettori).

---

## Idee future (non per v2, da non perdere)

### Avatar AI per scalare i punti giusti del processo
Idea emersa 2026-05-24. **Non in scope per Sprint 0-6 di v2.** Annotata per quando il prodotto sarà validato.

- **NO discovery call con avatar** — distrugge la fiducia con PMI italiana 50enne. Sprint 0 resta umano.
- **SÌ avatar-PMI per allenamento Valentino** — usabile già in Sprint 0 come tool di training prima delle call vere (Test 2 del flow attuale).
- **SÌ avatar dentro il prodotto post-vendita** — wizard di onboarding del Custode, demo asincrona sul sito, formazione del personale PMI dopo l'handover. Tipico Sprint 7+.
- **Tech stack candidato**: HeyGen/Synthesia per video sintetico asincrono, Vapi/Bland.ai per voicebot, Claude/GPT per la conversazione interna. Da valutare quando il caso d'uso sarà chiaro.
- **Rischio principale**: sostituire troppo presto la presenza umana = perdita del valore difendibile di Custodia v2 (consulenza on-site come moat). L'avatar è strumento di scala, non di vendita.

---

## Note di handoff per /ce-plan

### Stato implementativo al 2026-05-24 (MVP già costruito durante questo brainstorm)

Durante la conversazione di rev 2 è stato costruito un MVP funzionante della **consumption side**:

- `product/vault-demo/` — vault Obsidian con 3 schede cliente reali (Rossetto, Bianchi, Torrelli) con frontmatter YAML strutturato + 1 mail inbox da rispondere
- `product/mcp-server/custodia_mcp.py` — MCP server Python stdio con 4 tool: `list_clients`, `get_client`, `search_vault`, `recent_communications`. Verificato end-to-end via protocollo MCP.
- `product/README.md` — istruzioni setup e snippet di config per agganciare Claude Code

La **ingestion side** (CLI a stadi che costruisce il vault dalle sorgenti) è da costruire.

### Aree tecniche da pianificare in profondità

**Ingestion (CLI + connettori)**
- Struttura comandi CLI a stadi: nomi, contratti input/output, stato persistente tra stadi
- 4-5 connettori sorgente: Google Drive, Outlook 365, filesystem+PDF/Excel, Fatture in Cloud, + 1 gestionale
- Astrazione `LLMProvider` per supportare adapter Cloud (Anthropic) e Sovrano (provider sovrana, da scegliere quando arriva il cliente)
- Prompting per estrazione strutturata: come ottenere consistentemente frontmatter YAML coerente dai dati grezzi
- Strategia di "review umana" tra stadi: cosa mostra il CLI al consulente, come accetta correzioni

**Consumption (consolidamento)**
- Schema YAML frontmatter definitivo per schede cliente/fornitore/commessa (validare contro le 3 schede MVP costruite)
- Tool MCP da aggiungere: `get_offer_history`, `find_similar_clients`, eventuale `search_by_field`
- Trasporto HTTP del server MCP (oltre stdio) per agenti remoti — rinviabile

**Testing**
- Fixture sintetiche `tests/fixtures/finto-drive/` per CI deterministico
- Dogfood plan: cosa testare sul Drive/Gmail di Valentino in primo step
- Definizione operativa di "l'agente risponde bene": rubric o LLM-as-judge sulla bozza prodotta

### Aree non tecniche da non scordare
- Sales: come riscrivere `docs/01-cosa-vendi.md` per il nuovo pitch (centrato su "agenti senza knowledge sono inutili")
- Slide pitch già scritte in `docs/commerciale/v2/pitch-slides.md` — da rivedere per coerenza con dual-mode di inferenza
- Customer discovery: chi sono i 3 PMI dello Sprint 0 (script e tracker già pronti)
- Demo Atto 3: setup tecnico per fare girare l'agente live davanti al cliente — l'MCP server di v0.1 è già adatto, manca solo il "vault pre-popolato del cliente" prima dell'Atto 3
- Quotazione vendor inferenza sovrana: contattare Xference + 1-2 alternative italiane/UE per range pricing reale prima di promettere "+€2-4K setup"
