#!/usr/bin/env bash
# Prompts for OxyLabs credentials, checks them against the real endpoint,
# and folds them into .env. Neither value is ever printed.
set -uo pipefail

cd "$(dirname "$0")/.."
ENV_FILE="$PWD/.env"
LOG="$PWD/.oxylabs-setup.log"
: > "$LOG"
log() { printf '%s\n' "$1" >> "$LOG"; }

if [ ! -f "$ENV_FILE" ]; then
  log "No .env found — run deploy/ask-keys.sh first."
  exit 1
fi

ask() {
  osascript \
    -e "display dialog \"$1\" with title \"Rekomme — OxyLabs\" default answer \"\" with hidden answer buttons {\"Cancel\",\"OK\"} default button \"OK\"" \
    -e 'text returned of result' 2>/dev/null
}

OXY_USER=$(ask "OxyLabs username\n\noxylabs.io — Realtime / Google Shopping Scraper credentials.\nRestores live merchant prices on each product card.")
if [ -z "$OXY_USER" ]; then
  log "CANCELLED. Listings stay disabled; everything else is unaffected."
  exit 1
fi

OXY_PASS=$(ask "OxyLabs password")
if [ -z "$OXY_PASS" ]; then
  log "CANCELLED. Listings stay disabled; everything else is unaffected."
  exit 1
fi

log "Testing against realtime.oxylabs.io..."
code=$(curl -s -o /tmp/oxy-probe.$$ -w '%{http_code}' --max-time 60 \
  -X POST https://realtime.oxylabs.io/v1/queries \
  -u "$OXY_USER:$OXY_PASS" \
  -H 'Content-Type: application/json' \
  -d '{"source":"google_shopping_search","domain":"com","query":"sony wh-1000xm5","pages":1,"parse":true}')

log "HTTP $code"
if [ "$code" = "200" ]; then
  n=$(python3 -c "
import json,sys
try:
    d=json.load(open('/tmp/oxy-probe.$$'))
    r=d.get('results',[])
    print(len(r[0].get('content',{}).get('results',{}).get('organic',[])) if r else 0)
except Exception:
    print(0)
")
  log "OK — probe query returned $n listings"
elif [ "$code" = "401" ] || [ "$code" = "403" ]; then
  log "REJECTED — credentials not accepted. Nothing written."
  rm -f /tmp/oxy-probe.$$
  exit 1
else
  log "Unexpected status. First 200 bytes of the response:"
  head -c 200 /tmp/oxy-probe.$$ >> "$LOG" 2>/dev/null
  echo "" >> "$LOG"
fi
rm -f /tmp/oxy-probe.$$

tmp=$(mktemp)
grep -v -E '^(OXYLABS_USERNAME|OXYLABS_PASSWORD)=' "$ENV_FILE" > "$tmp"
{
  echo ""
  echo "# OxyLabs — live merchant listings"
  echo "OXYLABS_USERNAME=\"$OXY_USER\""
  echo "OXYLABS_PASSWORD=\"$OXY_PASS\""
} >> "$tmp"
umask 077
mv "$tmp" "$ENV_FILE"
chmod 600 "$ENV_FILE"
log "WRITTEN  .env now carries OxyLabs credentials"
