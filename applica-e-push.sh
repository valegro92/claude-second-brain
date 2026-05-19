#!/bin/bash
# Applica le ultime modifiche locali al repo claude-second-brain e pusha su GitHub.
#
# Uso (dal Terminal del Mac):
#   bash "$HOME/Output Claude/Idee/claude-second-brain/applica-e-push.sh"
#
# Cosa fa:
# 1. Clona una copia fresca del repo in /tmp/csb-fresh-... (ignora il .git locale eventualmente corrotto)
# 2. Confronta i 6 file chiave del repo locale (~/Output Claude/Idee/claude-second-brain/)
#    con la versione remota
# 3. Per ogni file effettivamente modificato → crea 1 commit specifico con messaggio dedicato
# 4. Push su origin/main
#
# Lo script è IDEMPOTENTE: file non modificati = nessun commit.

set -e

REPO_URL="https://github.com/valegro92/claude-second-brain.git"
WORK_DIR="/tmp/csb-fresh-$(date +%s)"
SOURCE_DIR="$HOME/Output Claude/Idee/claude-second-brain"

echo "📁 Sorgente file aggiornati: $SOURCE_DIR"
echo "🔧 Cartella di lavoro temporanea: $WORK_DIR"
echo "🐙 Remote: $REPO_URL"
echo ""

# File monitorati e i loro messaggi di commit dedicati
# (ordine = ordine in cui verranno committati, se modificati)
FILES=(
  "docs/framework.md"
  "README.md"
  "vault/CLAUDE.md"
  "skills/setup-wizard/SKILL.md"
  "docs/installazione-per-dummies.md"
  "INIZIA-QUI.md"
)

commit_message_for() {
  case "$1" in
    "docs/framework.md")
      echo "docs: 'OS personale' positioning + 4 new Mermaid diagrams in framework.md (4-components overview, OS analogy, before/after, growth model)"
      ;;
    "README.md")
      echo "docs: expand README with deep explanation per component (Memory · Protocol · Workflow · Extensions) — concept, why-it-matters, sub-elements, examples, who-writes-what tables; add Extensions section with Skills/MCP/Knowledge details; new growth-phases table"
      ;;
    "vault/CLAUDE.md")
      echo "feat(vault): rewrite CLAUDE.md with explicit 4-layer memory architecture and 3 non-negotiable rules"
      ;;
    "skills/setup-wizard/SKILL.md")
      echo "feat(skill): extend setup-wizard to 4 layers (Context/Data/Intelligence/Skill-Automations)"
      ;;
    "docs/installazione-per-dummies.md")
      echo "docs: add dummy-friendly installation walkthrough (3 install paths, troubleshooting, FAQ)"
      ;;
    "INIZIA-QUI.md")
      echo "docs: cross-link installation guide from INIZIA-QUI"
      ;;
    *)
      echo "docs: update $1"
      ;;
  esac
}

# Verifica che tutti i 6 file aggiornati esistano nella sorgente
for f in "${FILES[@]}"; do
  if [ ! -f "$SOURCE_DIR/$f" ]; then
    echo "❌ Manca il file: $SOURCE_DIR/$f"
    echo "   Verifica che Cowork abbia scritto i file aggiornati prima di lanciare lo script."
    exit 1
  fi
done
echo "✓ tutti i 6 file di riferimento trovati nella sorgente"
echo ""

# Clone fresco
echo "→ git clone..."
git clone "$REPO_URL" "$WORK_DIR" --quiet
cd "$WORK_DIR"

git config user.email "valegro92@gmail.com"
git config user.name "Valentino Grossi"
echo "✓ clone fresco ok"
echo ""

# Per ogni file: copia, e se differente → 1 commit dedicato
COMMITS_MADE=0
mkdir -p docs

for f in "${FILES[@]}"; do
  cp "$SOURCE_DIR/$f" "$f"
  # Se il file è diverso (modificato o nuovo), committalo
  if ! git diff --quiet -- "$f" 2>/dev/null || git ls-files --others --exclude-standard "$f" | grep -q "^$f$"; then
    msg=$(commit_message_for "$f")
    git add "$f"
    git commit -m "$msg" --quiet
    echo "✓ commit: $f"
    echo "   → $msg" | head -c 120
    echo ""
    COMMITS_MADE=$((COMMITS_MADE + 1))
  fi
done

echo ""

if [ "$COMMITS_MADE" -eq 0 ]; then
  echo "⚠️  Nessuna modifica rispetto al remote. Il repo è già aggiornato."
  rm -rf "$WORK_DIR"
  exit 0
fi

echo "→ git push origin main ($COMMITS_MADE nuovi commit)..."
git push origin main

echo ""
echo "✅ Push completato."
echo ""
echo "📜 Storia recente:"
git log --oneline -10
echo ""
echo "🌐 Verifica su: https://github.com/valegro92/claude-second-brain"
echo ""
echo "🧹 Cartella di lavoro: $WORK_DIR"
echo "   Puoi eliminarla quando vuoi:  rm -rf $WORK_DIR"
