#!/usr/bin/env bash
# Pops a native macOS dialog with a masked field for each key, then writes .env.
# The values go straight from the dialog into the file — never printed, never
# echoed, never returned to the caller.
set -uo pipefail

cd "$(dirname "$0")/.."
ENV_FILE="$PWD/.env"
LOG="$PWD/.env-setup.log"
: > "$LOG"

log() { printf '%s\n' "$1" >> "$LOG"; }

ask() {
  # $1 = dialog text ; prints the typed value on stdout
  osascript \
    -e "display dialog \"$1\" with title \"Rekomme — demo setup\" default answer \"\" with hidden answer buttons {\"Cancel\",\"OK\"} default button \"OK\"" \
    -e 'text returned of result' 2>/dev/null
}

OPENAI_KEY=$(ask "OpenAI API key\n\nplatform.openai.com/api-keys\nRuns gpt-4o-mini for generation and all four graders.")
if [ -z "$OPENAI_KEY" ]; then
  log "CANCELLED at the OpenAI prompt. Nothing written."
  exit 1
fi

TAVILY_KEY=$(ask "Tavily API key\n\napp.tavily.com\nThe only retrieval source in this deployment: web search, live Reddit, news, YouTube, prices.")
if [ -z "$TAVILY_KEY" ]; then
  log "CANCELLED at the Tavily prompt. Nothing written."
  exit 1
fi

log "Both keys captured. Validating..."

openai_code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 20 \
  -H "Authorization: Bearer $OPENAI_KEY" https://api.openai.com/v1/models)
log "OpenAI  HTTP $openai_code"

tavily_code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 25 \
  -X POST https://api.tavily.com/search -H 'Content-Type: application/json' \
  -d "{\"api_key\":\"$TAVILY_KEY\",\"query\":\"test\",\"max_results\":1}")
log "Tavily  HTTP $tavily_code"

JWT_SECRET=$(openssl rand -hex 32)

umask 077
cat > "$ENV_FILE" <<EOF
# Rekomme — demo deployment. Generated $(date '+%Y-%m-%d %H:%M').
# Do not commit this file.

OPENAI_API_KEY="$OPENAI_KEY"
TAVILY_API_KEY="$TAVILY_KEY"
JWT_SECRET_KEY="$JWT_SECRET"

DEMO_USERNAME="${DEMO_USERNAME:-reviewer}"
DEMO_PASSWORD="${DEMO_PASSWORD:-rekomme}"

BACKEND_URI="http://localhost:8000"
POSTGRES_CONN_STRING="postgresql://postgres@localhost:5432/postgres"
POSTGRES_HOSTNAME="localhost"
POSTGRES_USER="postgres"
POSTGRES_PASSWORD="postgres"
POSTGRES_PORT=5432
POSTGRES_DB="postgres"

# Blank on purpose — blank PINECONE_API_KEY is what turns DEMO_MODE on.
PINECONE_API_KEY=""
PINECONE_ENVIRONMENT=""
PINECONE_INDEX_NAME="damg-final-proj"
OXYLABS_USERNAME=""
OXYLABS_PASSWORD=""
AWS_ACCESS_KEY_ID=""
AWS_SECRET_ACCESS_KEY=""
AWS_REGION="us-east-1"
AWS_S3_BUCKET=""
EOF
chmod 600 "$ENV_FILE"

if [ "$openai_code" = "200" ] && [ "$tavily_code" = "200" ]; then
  log "WRITTEN  $ENV_FILE (mode 600) — both keys valid"
else
  log "WRITTEN  $ENV_FILE (mode 600) — but a key was rejected, see codes above"
fi
