# Inizia qui

Hai clonato il repo `claude-second-brain`. Bene. Prima di toccare niente, capisci cos'è.

**Questo è un toolkit di delivery consulenziale, non un'app self-service.**

Non puoi "installarlo e partire" da solo come un'app. È pensato per essere portato in una PMI di 30-50 persone da Valentino (o da un consulente con il suo metodo) in 3 atti — kick-off on-site, scandagliamento supervisionato, handover on-site. La consegna porta in azienda il vault popolato, il Custode formato, il manuale operativo.

Se hai clonato il repo per altri motivi (curiosità, formazione, valutazione), benvenuto. Scegli sotto il percorso giusto.

---

## 3 percorsi di lettura

### Sei Valentino (o un consulente che porta il prodotto al cliente)

Leggi in ordine:

1. [`docs/01-cosa-vendi.md`](docs/01-cosa-vendi.md) — playbook commerciale
2. [`docs/02-kickoff-checklist.md`](docs/02-kickoff-checklist.md) — Atto 1
3. [`docs/03-scandagliamento.md`](docs/03-scandagliamento.md) — Atto 2
4. [`docs/04-handover-checklist.md`](docs/04-handover-checklist.md) — Atto 3

Poi, come riferimento parallelo:

5. [`docs/06-framework-pmi.md`](docs/06-framework-pmi.md) — la teoria
6. [`docs/05-manuale-custode.md`](docs/05-manuale-custode.md) — quello che consegnerai al Custode
7. [`docs/07-manuale-persone.md`](docs/07-manuale-persone.md) — quello che il Custode farà leggere al personale

### Sei il Custode appena formato in azienda

Leggi:

1. [`docs/05-manuale-custode.md`](docs/05-manuale-custode.md) — il tuo manuale operativo

E come riferimento di contesto:

2. [`docs/06-framework-pmi.md`](docs/06-framework-pmi.md) — la teoria, capisci perché le cose sono fatte così
3. [`docs/07-manuale-persone.md`](docs/07-manuale-persone.md) — quello che fai leggere ai tuoi colleghi

### Sei un dipendente normale dell'azienda (Contributor)

Una sola pagina. 5 minuti:

1. [`docs/07-manuale-persone.md`](docs/07-manuale-persone.md)

Per tutto il resto, chiedi al Custode di reparto.

---

## Cosa contiene il repo

```
claude-second-brain/
├── README.md                          ← landing del prodotto
├── INIZIA-QUI.md                      ← sei qui
├── docs/                              ← 7 documenti, vedi sopra
├── vault/                             ← scheletro del vault PMI (template)
├── skills/                            ← skill operative per Claude
│   ├── setup-wizard-azienda/          (Atto 1: kick-off Custode)
│   ├── setup-wizard-persona/          (onboarding nuovo collega)
│   ├── session-lifecycle/             (Buongiorno/Buonanotte multi-utente)
│   ├── rituale-settimanale-custode/   (review reparto, venerdì)
│   ├── rituale-mensile-owner/         (review aziendale)
│   └── vault-lint/                    (health-check periodico)
├── _legacy-single-user/               ← archivio del template solista (non mantenuto)
└── _brief/                            ← planning Step 2-3 (tech plan, MCP audit, cost+risk, naming)
```

Il `vault/` è uno scheletro: contiene la struttura (cartelle, esempi compilati con un'azienda fittizia "Esempio Srl"). Si popola con dati reali durante la delivery, in Atto 2.

I file in `_brief/` sono note di pianificazione per gli Step 2 e 3 della roadmap del prodotto (scanner+extractor, modalità on-premise, playbook commerciale finale). Non sono documentazione utente — vivono lì come riferimento di design.

---

## Una nota sugli script storici

Versioni precedenti del repo contenevano due script in radice — `applica-e-push.sh` e `setup_github.sh` — usati da Valentino per il workflow di sviluppo personale del template (commit selettivi, push a GitHub di file specifici della sua macchina). Erano legati a path locali (`~/Output Claude/Idee/claude-second-brain/`) della sua workstation e a un modello di lavoro single-user.

Sono stati **rimossi** in questa versione: non hanno senso nel prodotto v1 (delivery consulenziale a PMI). Eventuali script utili al flusso di delivery v1 (es. scaffold automatico di reparti aggiuntivi post-handover) andranno in una cartella `bootstrap/` quando saranno costruiti, nello Step 2 della roadmap.

---

*Sistema creato da [Valentino Grossi](https://lacassettadegliaitrezzi.substack.com) — La Cassetta degli AI-trezzi*
*Repository: [github.com/valegro92/claude-second-brain](https://github.com/valegro92/claude-second-brain)*
