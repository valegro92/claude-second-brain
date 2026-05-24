# wiki-toolkit — Wiki aziendale per PMI in 4 settimane

Costruisci una wiki ordinata e affidabile sui sistemi di una PMI italiana di 30-50 persone. Toolkit `wiki` (CLI) + 3 atti di delivery presidiati da un consulente + manuale operativo per il Custode interno. Dati sui sistemi del cliente, niente SaaS.

---

## Per chi

PMI italiana, **30-50 dipendenti**, manifatturiera o servizi B2B, 5-15 anni di patrimonio documentale sparso tra Drive condivisi, NAS, caselle email, portatili. Due segnali da verificare:

1. **Un dolore quotidiano**: il commerciale risponde citando offerte vecchie, l'amministrazione cerca contratti e trova tre versioni, ogni nuovo assunto perde 3 settimane a chiedere "dove sta".
2. **Un IT/Office manager interno** disponibile a diventare **Custode** della wiki.

Se manca il Custode, il toolkit non funziona. Se ci sono entrambi i segnali, sì.

---

## Quick start

```bash
# Prerequisiti macOS/Linux
brew install python@3.11 uv pandoc      # Linux: usa apt/dnf equivalenti
brew install tesseract tesseract-lang   # opzionale, per OCR PDF scansionati

# Clone e installazione
git clone https://github.com/valegro92/claude-second-brain.git
cd claude-second-brain
uv venv && source .venv/bin/activate
uv pip install -e ".[dev,ocr]"

# Bootstrap cliente
wiki init                # wizard interattivo: slug, nome, sorgenti
wiki scan --client SLUG  # scandaglia NAS / Drive / email
wiki watch --client SLUG # modalità sempre-in-ascolto sulla `_inbox/`
```

Per la procedura completa (kick-off, scandagliamento, handover) vedi [`bootstrap/RUNBOOK.md`](bootstrap/RUNBOOK.md).

---

## Comandi principali

| Comando | Cosa fa |
|---|---|
| `wiki init` | Wizard di bootstrap: crea `bootstrap/clients/<slug>/config.yml` |
| `wiki scan --client SLUG` | Lancia gli scanner attivi (NAS, gdrive, m365, email, server) |
| `wiki extract --client SLUG` | Estrae il testo dai file dell'inventory |
| `wiki categorize --client SLUG` | Categorizza (regole + Claude) in 5 categorie |
| `wiki reconcile --client SLUG` | Dedup hash + soft (versioni, copie) → bozze di decisione |
| `wiki approve --client SLUG` | Apre la batch UI per approvazione interattiva |
| `wiki watch --client SLUG` | Modalità sempre-in-ascolto sulla `_inbox/<slug>/` |
| `wiki status --client SLUG` | Riepilogo: file per sorgente, estratti, bozze, costo Claude |

---

## Documentazione

Per ogni audience un percorso, vedi [`INIZIA-QUI.md`](INIZIA-QUI.md) per scegliere.

- **Sei Valentino (o consulente)**: [`docs/01-cosa-vendi.md`](docs/01-cosa-vendi.md) → playbook commerciale. Poi [`docs/02-kickoff-checklist.md`](docs/02-kickoff-checklist.md), [`docs/03-scandagliamento.md`](docs/03-scandagliamento.md), [`docs/04-handover-checklist.md`](docs/04-handover-checklist.md).
- **Sei il Custode**: [`docs/05-manuale-custode.md`](docs/05-manuale-custode.md) — il tuo manuale operativo.
- **Sei un Contributor** (dipendente): [`docs/07-manuale-persone.md`](docs/07-manuale-persone.md) — 1 pagina, 5 minuti.
- **Sei un dev che vuole contribuire**: vedi sezione sotto + [`INIZIA-QUI.md`](INIZIA-QUI.md).

Riferimenti operativi:
- [`bootstrap/INSTALL.md`](bootstrap/INSTALL.md) — installazione e dipendenze
- [`bootstrap/RUNBOOK.md`](bootstrap/RUNBOOK.md) — 3 atti di delivery, comando per comando
- [`docs/06-framework-pmi.md`](docs/06-framework-pmi.md) — la teoria: 6 layer, 4 ruoli, 3 rituali

---

## Per sviluppatori

### Struttura

```
wiki/        # CLI + pipeline + watcher
scanners/    # NAS, gdrive, m365, email, server (output: FileRecord)
extractors/  # PDF/DOCX/XLSX/EML/plain (output: ExtractionResult)
categorizers/# rules + Claude (5 categorie)
reconcilers/ # dedup hash, dedup soft, schede oggetto
batch_ui/    # UI di approvazione bozze (Flask)
bootstrap/   # wizard + template config
tests/       # pytest, 190+ test, fixture self-contained
```

### Contribuire

```bash
# Setup ambiente di sviluppo
uv venv && source .venv/bin/activate
uv sync --extra dev

# Lancia i test
pytest tests/ -v

# Lint
ruff check .

# Smoke test end-to-end (genera dataset pilota + esercita la pipeline)
pytest tests/e2e/ -v
```

Le dipendenze opzionali di runtime (`pandoc`, `tesseract`, `reportlab`) sono gestite via marker pytest (`requires_pandoc`, `requires_tesseract`, `requires_reportlab` in `tests/conftest.py`): se non presenti i test relativi sono auto-skippati, niente rumore in CI.

CI: GitHub Actions su Python 3.11 e 3.12, vedi `.github/workflows/test.yml`.

---

## Licenza

MIT.

## Autore

[Valentino Grossi](https://lacassettadegliaitrezzi.substack.com) — La Cassetta degli AI-trezzi.
