#!/usr/bin/env bash
# log-append.sh — appende una riga al log nel posto giusto
# (subito sotto il commento <!-- Le entry più recenti in cima --> dentro la sezione ## Log)
# Mai sotto il footer "Parte di [[...]]".
#
# Usage:
#   log-append.sh "2026-04-25 09:05 | task-name | esito | note"
# oppure:
#   echo "..." | log-append.sh
#
# Exit codes:
#   0 = ok
#   1 = uso errato
#   2 = log non trovato
#   3 = pattern di ancoraggio non trovato (file corrotto)

set -euo pipefail

LOG="$HOME/Vault Claude/Daily/Appunti/vault-lint/auto-close-log.md"

# Acquisisci la riga: argomento o stdin
if [ "${1:-}" != "" ]; then
  NEW_LINE="$1"
elif [ ! -t 0 ]; then
  NEW_LINE="$(cat)"
else
  echo "Usage: $0 'log-line'  (oppure pipe da stdin)" >&2
  exit 1
fi

[ -z "$NEW_LINE" ] && { echo "ERR: riga vuota" >&2; exit 1; }
[ ! -f "$LOG" ] && { echo "ERR: log non trovato: $LOG" >&2; exit 2; }

# Verifica presenza ancora
if ! grep -q "^<!-- Le entry più recenti in cima" "$LOG"; then
  echo "ERR: ancora non trovata in $LOG (file corrotto?)" >&2
  exit 3
fi

# Inserisce NEW_LINE + blank line subito dopo la riga del commento HTML
TMP="$(mktemp)"
awk -v line="$NEW_LINE" '
  /^<!-- Le entry più recenti in cima/ {
    print
    print ""
    print line
    next
  }
  { print }' "$LOG" > "$TMP" && mv "$TMP" "$LOG"

echo "OK: appended | $NEW_LINE"
