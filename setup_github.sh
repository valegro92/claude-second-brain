#!/bin/bash
# Pubblica claude-second-brain su GitHub
# Esegui da Terminal nella cartella del repo:
#   cd ~/Output\ Claude/Idee/claude-second-brain && bash setup_github.sh

set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
GITHUB_USER="valegro92"
REPO_NAME="claude-second-brain"
REMOTE_URL="https://github.com/$GITHUB_USER/$REPO_NAME.git"

echo "📁 $REPO_DIR"
echo "🐙 $REMOTE_URL"
echo ""

cd "$REPO_DIR"

# Init git se non esiste già
if [ ! -d ".git" ]; then
  echo "→ git init..."
  git init
  git branch -M main
else
  echo "→ repo git già inizializzata"
fi

# Configura autore se non impostato
git config user.email "valegro92@gmail.com" 2>/dev/null || true
git config user.name "Valentino Grossi" 2>/dev/null || true

# Stage tutti i file (rispetta .gitignore)
echo "→ git add ..."
git add .

# Verifica se c'è qualcosa da committare
if git diff --cached --quiet; then
  echo "→ nessuna modifica nuova da committare"
else
  echo "→ git commit..."
  git commit -m "feat: add setup-wizard skill + Obsidian section + La Cassetta links"
fi

# Remote
if git remote | grep -q "^origin$"; then
  echo "→ remote origin già presente"
else
  echo "→ aggiungo remote origin..."
  git remote add origin "$REMOTE_URL"
fi

echo ""
echo "→ git push..."
git push -u origin main

echo ""
echo "✅ Push completato."
echo "   https://github.com/$GITHUB_USER/$REPO_NAME"
