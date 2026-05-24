---
marp: true
theme: default
paginate: true
title: Custodia — la wiki che la tua PMI stava aspettando
---

<!--
Deck di vendita per Custodia.
Formato compatibile Marp / reveal.js: ogni `---` su riga vuota separa una slide.
Render: `marp deck-vendita.md` → PDF/HTML.

Nota sul naming: "Custodia" è il nome di lavoro raccomandato dal brief
`_brief/07-naming-brand.md`. La scelta definitiva richiede verifica
dominio + ricerca marchio EUIPO/UIBM (classi Nizza 9 e 42) prima
dell'adozione commerciale. Fino ad allora trattare come placeholder.
-->

# Custodia

## La wiki che la tua PMI stava aspettando

Costruita partendo dai file che hai già.
Mantenuta da una persona dentro l'azienda.
Leggibile da chiunque — anche da Claude.

*Valentino Grossi — La Cassetta degli AI-trezzi*

---

# Il problema, in 30 secondi

In una PMI da 35 persone, dopo 8 anni di lavoro digitale:

- **Drive caotico**: 3 unità condivise, cartelle "Definitivo_v2_FINAL", nessuno sa più dove sta cosa
- **Conoscenza nelle teste**: il responsabile produzione va in pensione e con lui se ne va il rapporto col fornitore storico
- **Onboarding lento**: il nuovo commerciale passa 4-6 settimane a chiedere "dov'è il file di…"
- **Email come archivio**: metà dei contratti vivi solo come allegato in `info@`

Ogni settimana si perdono ore in "ricerca file". Ogni assunzione costa un mese di ramp-up.

---

# Cosa NON funziona (l'hai già provato)

| Cosa | Perché si blocca |
|---|---|
| **Notion Enterprise** | Caro per 35 persone, in inglese, e va ancora popolato a mano |
| **SharePoint** | Funziona se hai un IT che lo cura. Senza, diventa un altro Drive |
| **"Mettiamo ordine al Drive"** | Riparte ogni 18 mesi, fallisce sempre allo stesso modo |
| **"Ognuno il suo file"** | È il problema, non la soluzione. Cambia col turnover |
| **Wiki interna fatta in casa** | Pagine ferme da 4 anni, nessuno se ne fida più |

Il pattern è sempre lo stesso: si parte con entusiasmo, si fa la struttura, **nessuno scrive**, dopo 6 mesi è morta.

---

# Cosa è Custodia, in una frase

> Le PMI italiane perdono ore ogni settimana cercando file, riunioni, decisioni vecchie.
>
> Custodia installa in 3-4 settimane una **wiki aziendale chiavi-in-mano**, costruita partendo dai vostri Drive, mail e NAS — senza chiedervi di rifare nulla.
>
> Formiamo un vostro collega come **Custode** e lasciamo un sistema leggibile da chiunque, anche da Claude.
>
> Quando un nuovo collega entra, in 2 giorni sa tutto quello che serve.

Categoria: *wiki aziendale chiavi-in-mano*. Non un altro SaaS, non un abbonamento.

---

# Il prodotto: 3 atti

```
   ATTO 1                  ATTO 2                   ATTO 3
   ──────                  ──────                   ──────
   KICK-OFF                SCANDAGLIAMENTO          HANDOVER
   ½ giornata on-site      1-2 settimane remoto     ½ giornata on-site
   ─────────────────       ─────────────────────    ─────────────────
   Test idoneità           Scanner + extractor      Training Custode
   Wizard azienda          su Drive/NAS/email       sui 3 rituali
   Connettori MCP          Batch da 50 bozze        Primo rituale fatto
   Perimetro privacy       Tu approvi               insieme
   Vault scheletro         Custode rivede           Decommissioning
```

Tra Atto 1 e Atto 3 passano **3-4 settimane**. A fine Atto 3 sei autonomo.

Riferimenti: [`docs/02-kickoff-checklist.md`](../02-kickoff-checklist.md), [`docs/03-scandagliamento.md`](../03-scandagliamento.md), [`docs/04-handover-checklist.md`](../04-handover-checklist.md).

---

# Demo flow visuale

I 6 momenti chiave che vedrai nella demo (5-7 minuti):

1. **Cartella `vault/` aperta in Obsidian** — grafo a vista, struttura per reparti e oggetti
2. **`vault/references/persone.md`** — la tabella delle persone con iniziali, ruoli, permessi
3. **"Buongiorno Claude, sono MR"** — Claude legge la memoria aziendale e di reparto, risponde con orientamento
4. **Scheda cliente `clienti/rossi-srl/`** — i 5 file Regola 01-PMI (MOC, CLAUDE.md, MEMORY.md, tasks.md, persone.md)
5. **Rituale settimanale** — il Custode promuove le proposte accumulate, lancia `vault-lint`
6. **Vault aperto offline** — funziona senza Claude, è solo Markdown

Tutta la demo è registrabile e re-eseguibile (vedi [`demo-script.md`](demo-script.md)).

---

# Cosa porti via il cliente

Alla chiusura dell'Atto 3, sul tuo Drive/NAS:

- **Vault popolato** — 100-200 documenti `.md` strutturati per il reparto pilota, con MOC, decisioni, persone, procedure
- **Custode formato** — una persona della tua azienda autonoma sui 3 rituali (giornaliero, settimanale, mensile)
- **Manuale operativo** — il [`manuale-custode.md`](../05-manuale-custode.md) stampato e firmato, riferimento per gli anni a venire
- **Skill installate** — `setup-wizard`, `session-lifecycle`, `rituale-settimanale-custode`, `rituale-mensile-owner`, `vault-lint`
- **Perimetro privacy firmato** — quale cartella è dentro, quale è fuori, chi ha accesso a cosa
- **3 check-up mensili** — gratuiti, post-handover, per verificare adozione

Il vault è **tuo**. Resta sui tuoi sistemi anche se domani Anthropic chiude.

---

# Il framework: 6 layer + 4 ruoli

```
                       STATICO                     VIVO
                       ────────────────────────    ─────────────────────
AZIENDA (tutti)        L0 Identità                 L1 Memoria aziendale
                       references/                 MEMORY.md

REPARTO (team)         L2 Procedure                L3 Vita del reparto
                       reparti/<X>/procedure/      reparti/<X>/MEMORY.md

OGGETTO (1 cosa)       L4 Knowledge                L5 Operativo personale
                       clienti/<X>/                Daily/<XX>/
```

**4 ruoli**: Owner (titolare), Custode capo (IT/Office manager), Editor (senior di reparto), Contributor (tutti gli altri).

Dettaglio in [`docs/06-framework-pmi.md`](../06-framework-pmi.md).

---

# La differenza /1: dimagriamo il Drive, non lo cloniamo

Il 60-70% del materiale esistente **non deve entrare nel vault**. Categorizziamo all'origine in 5 categorie:

| Categoria | Cosa ne facciamo | % tipica |
|---|---|---|
| **VIVO** | Diventa scheda strutturata nel vault | 10-20% |
| **DA CONSULTARE** | Resta dov'è, indicizzato come link dal vault | 25-35% |
| **ARCHIVIO** | Resta dov'è, segnato "non più curato" | 30-40% |
| **CESTINO** | Proposto per cancellazione (mai automatica) | 15-25% |
| **FUORI PERIMETRO** | HR, medico, sindacale: mai toccato | 5-15% |

L'errore tipico delle altre soluzioni: copiare tutto. Noi facciamo l'opposto.

---

# La differenza /2: scrivi una volta, l'AI legge quando serve

Il protocollo "Buongiorno Claude":

```
Maria (commerciale, MR) apre Claude al mattino:
  > "Buongiorno Claude, sono MR"

Claude legge:
  ├── references/persone.md       → MR=Editor, Commerciale
  ├── MEMORY.md aziendale         → 5-10 decisioni cross-reparto
  ├── reparti/commerciale/        → memoria del reparto
  └── Daily/MR/2026-05/.../...md  → cosa stavi facendo ieri

Claude risponde con orientamento sintetico.
La memoria pesante (clienti, fornitori) si carica solo quando serve.
```

**Niente "memoria magica"**: la conoscenza vive in file che le persone giuste controllano. Claude li legge quando serve.

---

# Per chi è — l'ICP

**PMI italiana, 30-50 dipendenti, manifatturiero o servizi B2B.**

I 5 sì che ti rendono cliente ideale:

1. **Dimensione**: 30-50 persone. Sotto i 30 il dolore non è abbastanza forte, sopra i 50 servono ruoli e governance che la v1 non copre
2. **IT/Office manager presente**: c'è una persona — interna o consulente fisso — candidata naturale a diventare **Custode**
3. **Direzione coinvolta**: titolare o COO disponibile a firmare perimetro privacy e investimento
4. **5-15 anni di sedimentazione digitale**: Drive condivisi, NAS, casella `info@` da 10.000 mail, contratti negli allegati
5. **Caos digitale dichiarato**: in prima call lo dici tu — "abbiamo perso il controllo"

**Esempio Srl** — officina manifatturiera di Brescia, 38 persone, conto terzi meccanico, 3 Drive condivisi + NAS Synology + Outlook `info@`. Custode designato: Giulia Bianchi (Office manager, 6 anni in azienda).

---

# Per chi NON è — i 4 casi di non-vendita

Se senti uno di questi segnali in prima call, **non firmare**:

1. **Nessun Custode designato** — *"lo facciamo tutti insieme"*, *"decidiamo dopo"*. Senza una persona con nome e cognome, il vault muore in 6 settimane.
2. **Cultura "ognuno il suo file"** — ogni reparto ha il suo Drive personale, nessuna SSOT. Servirebbe change management prima della documentazione.
3. **Turnover sopra il 30% annuo** — la conoscenza evapora con le persone. Il Custode di oggi non c'è tra 4 mesi.
4. **Troppe persone con potere di veto** — ogni decisione passa per CdA. L'Atto 1 dura mesi anziché mezza giornata.

Riferimento: [`docs/01-cosa-vendi.md`](../01-cosa-vendi.md) e [`docs/05-manuale-custode.md`](../05-manuale-custode.md) Fase 0.

In questi casi proponiamo una **fase 0 a pagamento** (1.500-2.500 €) per fare un assessment scritto, senza vendere la delivery completa.

---

# Cosa serve dal cliente

Per fare bene la delivery devi mettere a budget:

| Cosa | Quando | Quanto |
|---|---|---|
| **½ giornata kickoff on-site** | Atto 1 (giorno 1) | Owner: 1h + ultima 30' / Custode: tutta la mezza giornata / 1-2 Editor del pilota: 1h |
| **Disponibilità Custode in Atto 2** | 1-2 settimane | ~1h/giorno, call settimanale di 30 min, risposte su Slack/email |
| **½ giornata handover on-site** | Atto 3 (giorno finale) | Owner: 1h / Custode: tutta la mezza giornata |
| **Tempo Custode primi 3 mesi** | Post-handover | **40-60 ore totali** per i rituali settimanali |
| **Accessi admin** | Pre Atto 1 | Google Workspace / M365 / NAS / email di servizio |
| **Organigramma + reparto pilota** | Pre Atto 1 | Anche solo PDF + decisione "partiamo dal Commerciale" |

Il tempo interno del Custode è **circa 2.000 € equivalenti** (a 35 €/h fully loaded). Lo diciamo in trattativa, non dopo.

---

# Tempi e investimento

```
   SETTIMANA 1        SETTIMANA 2-3          SETTIMANA 4
   ───────────        ─────────────          ───────────
   Atto 1             Atto 2                 Atto 3
   Kick-off on-site   Scandagliamento        Handover on-site
                      remoto + call sett.

   MESE 2-3 — Custode autonomo, primi 3 check-up gratuiti
   MESE 4+ — Opzionale: manutenzione mensile (Light o Premium)
```

**Investimento**:

| Voce | Range | Quando paghi |
|---|---|---|
| **Setup chiavi-in-mano** | 8.500 – 14.000 € | 50% alla firma, 50% all'handover |
| **Manutenzione Light** (opz.) | 700 €/mese | Trimestrale, 1.5h/mese di presidio |
| **Manutenzione Premium** (opz.) | 1.500 €/mese | Trimestrale, 4h/mese + evolutive |
| **Aggiunta reparto post-handover** | 2.000-4.000 € | Una tantum per nuovo reparto |

Range setup giustificato in trattativa dalla complessità (sedi, sorgenti, volume — vedi [`preventivo-template.md`](preventivo-template.md)).

---

# Privacy & GDPR

**Modello standard**:

- **Titolare** del trattamento: tu (la PMI). Decidi cosa scandagliamo.
- **Responsabile** del trattamento: Valentino, vincolato da DPA art. 28 GDPR.
- **Sub-responsabile**: Anthropic (Claude API). Trasferimento UE→USA coperto da SCC firmate.

**Due modalità**:

| Modalità | Quando | Dove vanno i dati |
|---|---|---|
| **Safe** (default) | PMI B2B servizi/manifatturiero standard | Worktree cifrato sul portatile + cache temporanea Anthropic (no training) |
| **Full perimetro stretto** | Manifatturiero con IP CAD/R&D | Esclusione preventiva di cartelle a monte. Niente filtro a valle, mai esposte a Claude |
| **On-premise** (Step 3, in roadmap) | Sanitario, finanziario, legale | Modello locale, niente traffico USA. Tempi e prezzi a parte |

A 30 giorni dall'handover: cancellazione documentata di tutto. Il vault **resta sui tuoi sistemi**.

---

# Risultati attesi

Quello che cambia, misurabile a 3 e a 6 mesi:

| KPI | Prima | Dopo 6 mesi |
|---|---|---|
| **Onboarding nuovo dipendente operativo** | 4-6 settimane | 5-8 giorni lavorativi |
| **Tempo settimanale "dov'è il file di X?"** | 3-5 ore/persona | <1 ora/persona |
| **Decisioni storiche documentate** | "Lo sa Mario" | Tracciato in `clienti/X/MEMORY.md` |
| **Continuità in caso di uscita persona** | 2-3 settimane di affiancamento | Sostituto operativo in 3-5 giorni |
| **Versioni contrastanti dello stesso documento** | Frequenti | Quasi zero (regola SSOT) |

Quello che **non** garantiamo: ROI in euro. Dipende da quanto il Custode mantiene viva la wiki. Per quello facciamo 3 check-up scritti.

---

# Case study — Esempio Srl

> *Officina manifatturiera, Brescia. 38 persone (30 produzione, 8 ufficio). Conto terzi meccanico.*
> *Direzione: Anna Ferrari (AF). Custode designato: Giulia Bianchi (GB), Office manager.*
> *Reparto pilota: Commerciale (3 persone — Mario Rossi MR, Luca Verdi LV, AF stessa).*

**Situazione iniziale**:
- 3 Drive condivisi, ~180 GB. NAS Synology 6 anni, 420 GB di disegni e foto.
- Outlook `info@`: 14.000 mail, allegati unica copia di metà dei contratti vivi.
- 12 clienti attivi che valgono l'80% del fatturato.

**Cosa è successo in 4 settimane**:
- Atto 1 (½ giornata): vault scheletro, perimetro privacy firmato, NAS produzione escluso (resta dov'è).
- Atto 2 (12 giorni lavorativi): 14 clienti mappati, 47 offerte 2024-2025 indicizzate, 8 SOP commerciali estratte.
- Atto 3 (½ giornata): GB autonoma sui 3 rituali, 3 check-up mensili schedulati.

**Risultato a 3 mesi** (autodichiarato in check-up): AF dichiara di aver risparmiato ~2 ore/settimana solo sulle "dov'è il file di Rossi?". Onboarding del nuovo commerciale (entrato al mese 3): operativo in 6 giorni.

*Cliente reale arriverà dopo il primo deal — questo è uno scenario realistico.*

---

# Q&A — le 5 obiezioni tipiche

**1. "I miei dati passano per Anthropic / USA?"**
Sì, durante la delivery. Anthropic ha SCC firmate e nel DPA si impegna a non usare i tuoi dati per training. Cache temporanea, cancellazione a fine delivery. Puoi escludere preventivamente qualunque cartella.

**2. "Cosa succede se Anthropic cambia prezzi o smette?"**
Il vault è 100% tuo, in Markdown. Funziona offline con Obsidian. Anthropic è strumento di costruzione, non fornitore continuativo. Te lo mostro fisicamente in demo.

**3. "Voglio una garanzia che funzioni."**
Garantisco l'output al momento della consegna e bug-fix 30 giorni. Non garantisco l'adozione del Custode — quella è cultura aziendale. Per quello facciamo 3 check-up.

**4. "Mi state buttando dentro un'AI in azienda."**
No. L'AI è uno strumento che uso io in fase di setup. Quello che resta a te è una raccolta di Markdown — il Custode aggiorna a mano. L'AI sparisce all'handover.

**5. "Devo coinvolgere il mio DPO / legale?"**
Se ce l'hai, sì — mandagli il DPA prima di firmare. Se sei una PMI 30-50 B2B senza DPO obbligatorio, il DPA standard ex art. 28 basta. Posso aspettare 1-2 settimane.

Dettaglio in [`faq.md`](faq.md) e in [`_brief/06-cost-and-risk.md`](../../\_brief/06-cost-and-risk.md) sezione B.6.

---

# Prossimi passi

```
   1                              2                              3
   ──                             ──                             ──
   CHIAMATA DI                    KICK-OFF                       AVVIO
   SCOPERTA                       CON PREVENTIVO                 DELIVERY
   ──────────                     FIRMATO                        ──────────
   30 minuti, gratuita            ──────────────                 Atto 1 in agenda
   Capire se il tuo               Mando preventivo               entro 2-3 settimane
   caso è servibile               personalizzato                 dalla firma
   in v1                          DPA + contratto
                                  pronti per firma
```

Per partire dalla chiamata di scoperta:

**valentino@cassettadegliaitrezzi.it** *(placeholder)*
**+39 …** *(placeholder)*
**linkedin.com/in/valentinogrossi** *(placeholder)*

Tempi medi di risposta: 24h lavorative.

---

# Custodia

## La wiki che la tua PMI stava aspettando

*Il sapere della tua azienda, in ordine.*

Valentino Grossi
La Cassetta degli AI-trezzi

→ [`docs/01-cosa-vendi.md`](../01-cosa-vendi.md) per il playbook completo
→ [`faq.md`](faq.md) per le domande frequenti
→ [`landing-page.md`](landing-page.md) per la versione web
