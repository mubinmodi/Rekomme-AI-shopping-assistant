#!/usr/bin/env bash
# Prompts for the Supabase connection string, verifies it, makes sure the
# schema is there, and folds it into .env. The value is never printed.
set -uo pipefail

cd "$(dirname "$0")/.."
ENV_FILE="$PWD/.env"
LOG="$PWD/.supabase-setup.log"
: > "$LOG"
log() { printf '%s\n' "$1" >> "$LOG"; }

if [ ! -f "$ENV_FILE" ]; then
  log "No .env found — run deploy/ask-keys.sh first."
  exit 1
fi

CONN=$(osascript \
  -e 'display dialog "Supabase SESSION POOLER connection string\n\nDashboard → Connect → Session pooler → URI\n\nIt must be the pooler host, not db.<ref>.supabase.co — direct connections are IPv6-only and neither Docker nor ECS Fargate can reach them.\n\npostgresql://postgres.<ref>:PASSWORD@aws-0-<region>.pooler.supabase.com:5432/postgres" with title "Rekomme — Supabase" default answer "" with hidden answer buttons {"Cancel","OK"} default button "OK"' \
  -e 'text returned of result' 2>/dev/null)

if [ -z "$CONN" ]; then
  log "CANCELLED. .env left as it was (in-container Postgres)."
  exit 1
fi

# Parse out the pieces the app's settings object wants separately.
proto_stripped="${CONN#postgresql://}"
creds="${proto_stripped%%@*}"
hostpart="${proto_stripped#*@}"
PG_USER="${creds%%:*}"
PG_PASS="${creds#*:}"
hostport="${hostpart%%/*}"
PG_HOST="${hostport%%:*}"
PG_PORT="${hostport##*:}"
PG_DB="${hostpart#*/}"
PG_DB="${PG_DB%%\?*}"
[ "$PG_PORT" = "$PG_HOST" ] && PG_PORT=5432

log "host   $PG_HOST"
log "port   $PG_PORT"
log "user   $PG_USER"
log "db     $PG_DB"

case "$PG_HOST" in
  db.*.supabase.co)
    log "REJECTED: $PG_HOST is the direct connection host, which Supabase serves"
    log "          over IPv6 only. Neither Docker nor ECS Fargate can reach it."
    log "          Use the Session pooler URI instead:"
    log "          Dashboard -> Connect -> Session pooler"
    log "          postgresql://postgres.<ref>:PASS@aws-0-<region>.pooler.supabase.com:5432/postgres"
    exit 1
    ;;
esac

if [ "$PG_PORT" = "6543" ]; then
  log "WARNING: port 6543 is the transaction pooler. SQLAlchemy's connection"
  log "         pooling wants session mode on 5432. Continuing anyway."
fi

# ── connectivity + schema ──
# psql isn't installed locally, so borrow one from a throwaway container.
pg() {
  docker run --rm -i \
    -e PGPASSWORD="$PG_PASS" \
    -v "$PWD/deploy/schema.sql:/schema.sql:ro" \
    postgres:17-alpine \
    psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$PG_DB" "$@"
}

if ! docker info >/dev/null 2>&1; then
  log "Docker is not running — cannot verify the connection. Start Docker and re-run."
  exit 1
fi

log "Testing the connection..."
if pg -c 'SELECT 1' >/dev/null 2>>"$LOG"; then
  log "CONNECTED"
else
  log "CONNECTION FAILED — see the error above. Nothing changed."
  exit 1
fi

log "Applying schema (idempotent; CREATE TABLE IF NOT EXISTS)..."
if pg -v ON_ERROR_STOP=1 -f /schema.sql >>"$LOG" 2>&1; then
  log "SCHEMA   ok"
else
  log "SCHEMA   FAILED — see errors above"
  exit 1
fi

log "Existing rows:"
pg -t -A -c "SELECT 'users=' || count(*) FROM public.users" >>"$LOG" 2>&1 || true
pg -t -A -c "SELECT 'chat_sessions=' || count(*) FROM public.chat_session" >>"$LOG" 2>&1 || true

# ── rewrite the Postgres block in .env ──
tmp=$(mktemp)
grep -v -E '^(POSTGRES_CONN_STRING|POSTGRES_HOSTNAME|POSTGRES_USER|POSTGRES_PASSWORD|POSTGRES_PORT|POSTGRES_DB)=' \
  "$ENV_FILE" > "$tmp"
{
  echo ""
  echo "# Supabase"
  echo "POSTGRES_CONN_STRING=\"$CONN\""
  echo "POSTGRES_HOSTNAME=\"$PG_HOST\""
  echo "POSTGRES_USER=\"$PG_USER\""
  echo "POSTGRES_PASSWORD=\"$PG_PASS\""
  echo "POSTGRES_PORT=$PG_PORT"
  echo "POSTGRES_DB=\"$PG_DB\""
} >> "$tmp"
umask 077
mv "$tmp" "$ENV_FILE"
chmod 600 "$ENV_FILE"

log "WRITTEN  .env now points at Supabase"
