#!/usr/bin/env bash
set -euo pipefail

export PGDATA="${PGDATA:-/home/user/pgdata}"
export POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-postgres}"
# Debian's postgres major version varies by base image; take the newest installed.
PG_BIN=$(ls -d /usr/lib/postgresql/*/bin 2>/dev/null | sort -V | tail -1)
if [ -z "$PG_BIN" ]; then
  echo "[start] no postgres installation found under /usr/lib/postgresql" >&2
  exit 1
fi
export PATH="$PG_BIN:$PATH"
echo "[start] using postgres at $PG_BIN"

# ── Postgres (in-container; storage resets on every redeploy) ──
if [ ! -s "$PGDATA/PG_VERSION" ]; then
  echo "[start] initialising postgres cluster"
  mkdir -p "$PGDATA"
  initdb -D "$PGDATA" -U postgres --auth-local=trust --auth-host=trust >/dev/null
fi

# The container runs as an unprivileged user. Debian's default Unix-socket
# directory (/var/run/postgresql) is not writable, so keep the socket beside
# the disposable database files. Application connections use TCP localhost,
# but PostgreSQL still requires a writable socket directory at startup.
pg_ctl -D "$PGDATA" -l /home/user/postgres.log \
  -o "-c listen_addresses=localhost -c unix_socket_directories=/home/user -p 5432" \
  -w start

echo "[start] applying schema"
psql -h localhost -U postgres -d postgres -v ON_ERROR_STOP=1 -f /app/deploy/schema.sql >/dev/null

echo "[start] seeding demo user"
python /app/deploy/seed_demo_user.py

# ── FastAPI + React ──
echo "[start] launching FastAPI and React on :8080"
mkdir -p /app/logs /app/resources/cached /app/resources/extracts /app/resources/scraped
exec uvicorn backend.main:app --host 0.0.0.0 --port 8080
