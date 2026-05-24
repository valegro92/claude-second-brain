# Custodia

**La wiki aziendale che la tua PMI stava aspettando.**

Trasformiamo Drive, NAS ed email della tua azienda in una wiki ordinata. In 3-4 settimane. Un Custode interno formato. Un manuale operativo per tenerla viva.

Custodia è un **servizio di consulenza chiavi-in-mano**, non un software che ti vendiamo e ti lasciamo solo.

> Sito vetrina: [`site/`](site/) (deploy su Vercel in 2 minuti) · Toolkit operativo: questo repo · Nome in fase di verifica EUIPO/UIBM.

---

## Per chi

PMI italiana, **30-50 dipendenti**, manifatturiera o servizi B2B, 5-15 anni di patrimonio documentale sparso tra Drive condivisi, NAS, caselle email, portatili. Due segnali da verificare:

1. **Un dolore quotidiano** di knowledge: il commerciale risponde citando offerte vecchie, l'amministrazione cerca contratti e trova tre versioni, ogni nuovo assunto perde 3 settimane a chiedere "dove sta".
2. **Un IT/Office manager interno** disponibile a diventare **Custode** della wiki (2-4 ore/settimana per 3 mesi).

Se manca il Custode, Custodia non funziona. Se ci sono entrambi i segnali, sì.

---

## I 3 atti della delivery

| Atto | Quando | Durata | Cosa succede |
|---|---|---|---|
| **1 — Kick-off** | Settimana 1 | ½ giornata on-site | Wizard azienda, accessi sorgenti, perimetro privacy |
| **2 — Scandagliamento** | Settimane 2-3 | 1-2 sett. supervisionate | Toolkit gira, bozze approvate a batch da 50, call settimanale Custode |
| **3 — Handover** | Settimana 4 | ½ giornata on-site | Training Custode sui 3 rituali, consegna manuale, mail decommissioning |

Cosa porti a casa: vault popolato, Custode formato, manuale operativo, mappa "dove sta cosa" per il vecchio Drive.

---

## Prezzi

- **Setup**: €8.500 — €14.000 una tantum (in base a taglia e complessità sorgenti)
- **Manutenzione opzionale**: €800 — €1.500/mese (1 call/mese, lint mensile, supporto)

[Prenota una scoperta gratuita di 30 minuti →](mailto:valentino@lacassettadegliaitrezzi.com?subject=Custodia%20-%20richiesta%20scoperta%20gratuita)

---

## Come è fatto

Custodia è composto da:

- **Toolkit `wiki`** (CLI Python): scanner per Drive/M365/email/NAS, extractor PDF/DOCX/XLSX/EML, categorizer con Claude, dedup, UI di approvazione, watcher daemon sempre-in-ascolto
- **Framework PMI**: 6 layer di memoria, 4 ruoli, 4 regole non-negoziabili, protocollo a 3 livelli
- **Vault scheletro Obsidian** con esempi compilati (reparti, clienti, fornitori, commesse)
- **Manuale del Custode** (6 fasi di migrazione da Drive caotico a wiki funzionante)
- **Materiali commerciali** (deck, FAQ, preventivo, contratto, demo script)

Tutto MIT, dati sui sistemi del cliente, niente lock-in, niente SaaS.

---

## Per sviluppatori — Quick start

```bash
# Prerequisiti
brew install python@3.11 uv pandoc      # Linux: apt/dnf equivalenti
brew install tesseract tesseract-lang   # opzionale, per OCR PDF scansionati

# Clone e installazione
git clone https://github.com/valegro92/claude-second-brain.git
cd claude-second-brain
uv sync --extra dev

# Verifica installazione (237 test, ~6s)
uv run pytest tests/
uv run wiki --help

# Demo end-to-end self-contained (48 file finti → pipeline completa → dashboard)
uv run wiki demo
```

Per la procedura completa di delivery a un cliente vero: [`bootstrap/RUNBOOK.md`](bootstrap/RUNBOOK.md).

---

## Comandi principali

| Comando | Cosa fa |
|---|---|
| `wiki init` | Wizard bootstrap cliente → crea `bootstrap/clients/<slug>/config.yml` |
| `wiki scan --client SLUG` | Lancia gli scanner attivi (NAS, gdrive, m365, email, server) |
| `wiki extract --client SLUG` | Estrae il testo dai file dell'inventory |
| `wiki categorize --client SLUG` | Categorizza in 5 categorie (regole italiane + Claude) |
| `wiki reconcile --client SLUG` | Dedup hash + soft → bozze schede cliente/fornitore |
| `wiki approve --client SLUG` | Apre la batch UI su `127.0.0.1:7423` |
| `wiki watch --client SLUG` | **Sempre-in-ascolto** su `_inbox/<slug>/` |
| `wiki dashboard --client SLUG` | Genera `_status/<slug>/dashboard.html` |
| `wiki status --client SLUG` | Riepilogo file/estratti/bozze/costo Claude |
| `wiki doctor [--strict]` | Health check (Python, tool, env, config, dir, disco) |
| `wiki demo` | Demo end-to-end self-contained con dataset finto |

---

## Documentazione completa

Per ogni audience un percorso (scegli in [`INIZIA-QUI.md`](INIZIA-QUI.md)):

| Audience | Inizia da |
|---|---|
| **Valentino / consulente** | [`docs/01-cosa-vendi.md`](docs/01-cosa-vendi.md) → poi `02-04` (3 atti) |
| **Custode** in azienda | [`docs/05-manuale-custode.md`](docs/05-manuale-custode.md) — 6 fasi migrazione |
| **Dipendente** (Contributor) | [`docs/07-manuale-persone.md`](docs/07-manuale-persone.md) — 1 pagina |
| **Dev** che contribuisce | Questa sezione + [`bootstrap/INSTALL.md`](bootstrap/INSTALL.md) |

Per il framework teorico: [`docs/06-framework-pmi.md`](docs/06-framework-pmi.md) (6 layer, 4 ruoli, 3 rituali).

Per la modalità on-premise (settori regolamentati, Bedrock, Docker): [`docs/08-on-premise.md`](docs/08-on-premise.md).

---

## Architettura repo

```
custodia/
├── site/             # landing page statica, deploy su Vercel
├── wiki/             # CLI + pipeline + watcher (Python)
├── scanners/         # NAS, gdrive, m365, email, server
├── extractors/       # PDF / DOCX / XLSX / EML / plain / OCR
├── categorizers/     # rules italiane + Claude Haiku
├── reconcilers/      # dedup hash/soft, schede cliente/fornitore, persone
├── batch_ui/         # Flask + HTMX su 127.0.0.1:7423
├── bootstrap/        # wizard + template config + INSTALL/RUNBOOK
├── vault/            # scheletro Obsidian, esempi compilati
├── skills/           # 6 skill Claude (setup, lifecycle, rituali, lint)
├── docs/             # 8 doc tecnici + commerciale/ (deck, FAQ, contratto, demo)
└── tests/            # pytest, 237 passing, 77% coverage
```

## Quality gates

- 237 test pytest passing (77.1% coverage)
- Ruff strict + mypy gradual
- CI: GitHub Actions matrix Python 3.11 + 3.12
- `wiki doctor` health check pre-delivery
- `test_no_secrets.py` per scan credenziali hardcoded

## Storia delle versioni

Vedi [`CHANGELOG.md`](CHANGELOG.md).

- **v0.2.0** (2026-05-24) — Polish production: helpers (errors/atomic/retry/subprocess), wiki doctor, wiki demo, stress test italiano (82% categorizzazione deterministica)
- **v0.1.0** (2026-05-23) — MVP: vault PMI multi-utente, 5 scanner, 6 extractor, batch UI, watcher, materiali commerciali

## Licenza

MIT — il codice è libero. Il nome "Custodia" e il marchio sono in fase di verifica EUIPO/UIBM.

## Autore

[Valentino Grossi](https://lacassettadegliaitrezzi.substack.com) — La Cassetta degli AI-trezzi.
