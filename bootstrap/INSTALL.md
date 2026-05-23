# wiki-toolkit — Guida di installazione

Setup della macchina di Valentino (o del consulente che porta il prodotto al
cliente). Vale anche per il futuro Custode che vorrà ri-lanciare i comandi
post-handover, anche se in quel caso le dipendenze pesanti (OCR) di solito
non servono.

Il toolkit gira su:
- macOS 13+ (Apple Silicon o Intel) — target primario
- Linux Debian/Ubuntu 22.04+ — pieno supporto, niente sorprese
- Windows — solo via WSL2 (vedi nota in fondo)

---

## macOS

### Prerequisiti via Homebrew

```bash
# Toolchain Python + package manager
brew install python@3.11 uv

# Conversione documenti (DOCX/EML → markdown)
brew install pandoc

# OCR opzionale (solo se il cliente ha PDF scansionati)
brew install tesseract tesseract-lang
```

`tesseract-lang` include i language pack: serve per riconoscere l'italiano nei
PDF scansionati. Senza, ottieni solo inglese.

### Setup del progetto

```bash
git clone https://github.com/valegro92/claude-second-brain.git
cd claude-second-brain

# Crea l'ambiente virtuale
uv venv
source .venv/bin/activate

# Installa il toolkit + dev deps
uv pip install -e ".[dev,ocr]"
```

`-e` (editable) ti permette di modificare il codice senza reinstallare. `[dev]`
porta dentro pytest/ruff, `[ocr]` aggiunge pytesseract+Pillow.

### Verifica

```bash
wiki --version
# wiki, version 0.1.0

wiki --help
# elenco comandi

wiki init
# parte il wizard
```

---

## Linux (Debian/Ubuntu)

```bash
# Prerequisiti
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv python3-pip pandoc \
    tesseract-ocr tesseract-ocr-ita

# uv non è nei repo apt: installalo via script ufficiale
curl -LsSf https://astral.sh/uv/install.sh | sh

# Setup uguale a macOS
git clone https://github.com/valegro92/claude-second-brain.git
cd claude-second-brain
uv venv && source .venv/bin/activate
uv pip install -e ".[dev,ocr]"
```

Se sei su Linux server senza display (es. mini-PC dedicato al cliente), `wiki
approve` aprirà il browser dell'host che ti collega via SSH con port-forward.

---

## Windows

**Raccomandazione**: usa WSL2 con Ubuntu 22.04 e segui la sezione Linux.

I motivi per evitare Windows nativo:
- pdfplumber + pillow su Windows hanno problemi di build noti
- Il filesystem watcher (`watchdog`) ha edge case con SMB su Windows
- Pandoc su Windows installa OK ma alcuni encoding rompono sui DOCX prodotti
  da Office Italia

Setup WSL:
```powershell
# Da PowerShell come admin
wsl --install -d Ubuntu-22.04
```
Poi entra in Ubuntu e segui la sezione Linux qui sopra.

---

## Variabili d'ambiente

Crea un `.env` in radice (è gitignored):
```
ANTHROPIC_API_KEY=sk-ant-...
```

Il toolkit lo legge automaticamente via `python-dotenv`. Le chiavi delle
sorgenti (Google, M365) stanno invece nel `bootstrap/clients/<slug>/config.yml`
o in file separati referenziati dal config (anche loro gitignored).

---

## Troubleshooting installazione

**`uv pip install` fallisce su `lxml`**
Su Mac vecchio: `brew install libxml2 libxslt` e riprova.

**`tesseract` non trova l'italiano**
Verifica con `tesseract --list-langs`. Se `ita` manca, su Mac: `brew install
tesseract-lang`; su Linux: `sudo apt-get install tesseract-ocr-ita`.

**`wiki --version` dice "command not found"**
L'ambiente virtuale non è attivo. `source .venv/bin/activate` (o riapri il
terminale dopo aver aggiunto la riga nel tuo `~/.zshrc`).

**Pandoc non viene chiamato**
Il toolkit lo cerca con `shutil.which("pandoc")`. Verifica con `which pandoc`.
Se è installato ma fuori dal PATH, aggiungi `/opt/homebrew/bin` (Apple
Silicon) o `/usr/local/bin` (Intel) al PATH.
