#!/usr/bin/env bash
# Avvia la webapp Custodia in locale.
#
# Pre-requisito: aver creato il venv e installato custodia-web + custodia-cli.
# Vedi README.md → Quickstart.

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"

if [[ ! -d .venv ]]; then
    echo "✗ .venv non trovato in $HERE"
    echo "  Esegui: python3 -m venv .venv && source .venv/bin/activate && pip install -e ../cli && pip install -e ."
    exit 1
fi

source .venv/bin/activate

exec streamlit run app.py "$@"
