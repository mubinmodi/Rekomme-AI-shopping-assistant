#!/usr/bin/env bash
# Prompts for the two keys Rekomme's demo deployment needs and writes .env.
# Input is hidden; nothing is echoed back and nothing leaves this machine
# except the two validation calls to OpenAI and Tavily.
set -uo pipefail

cd "$(dirname "$0")/.."
ENV_FILE="$PWD/.env"

bold=$(printf '\033[1m'); dim=$(printf '\033[2m'); green=$(printf '\033[32m')
red=$(printf '\033[31m'); yellow=$(printf '\033[33m'); off=$(printf '\033[0m')

echo
echo "${bold}Rekomme — demo environment setup${off}"
echo "${dim}Writing to $ENV_FILE${off}"
echo

if [ -f "$ENV_FILE" ]; then
  printf "%s.env already exists. Overwrite? [y/N] %s" "$yellow" "$off"
  read -r reply
  case "$reply" in
    [yY]*) ;;
    *) echo "Keeping the existing file. Nothing changed."; exit 0 ;;
  esac
  echo
fi

ask_secret() {
  # $1 = prompt, $2 = variable name to set
  local prompt="$1" varname="$2" value=""
  while [ -z "$value" ]; do
    printf "%s" "$prompt"
    read -rs value
    echo
    if [ -z "$value" ]; then
      echo "  ${red}Required — try again.${off}"
    fi
  done
  printf -v "$varname" '%s' "$value"
}

echo "${bold}1/2  OpenAI${off}  ${dim}platform.openai.com/api-keys${off}"
ask_secret "     Paste OPENAI_API_KEY (hidden): " OPENAI_KEY

echo
echo "${bold}2/2  Tavily${off}  ${dim}app.tavily.com${off}"
ask_secret "     Paste TAVILY_API_KEY (hidden): " TAVILY_KEY

echo
printf "Demo login username [reviewer]: "
read -r DEMO_USER
DEMO_USER="${DEMO_USER:-reviewer}"
printf "Demo login password [rekomme]: "
read -r DEMO_PASS
DEMO_PASS="${DEMO_PASS:-rekomme}"

# ── validate before writing ──
echo
echo "${bold}Checking the keys...${off}"

openai_code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 20 \
  -H "Authorization: Bearer $OPENAI_KEY" \
  https://api.openai.com/v1/models)
if [ "$openai_code" = "200" ]; then
  echo "  ${green}OK${off}   OpenAI key accepted"
else
  echo "  ${red}FAIL${off} OpenAI returned HTTP $openai_code"
fi

tavily_code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 25 \
  -X POST https://api.tavily.com/search \
  -H 'Content-Type: application/json' \
  -d "{\"api_key\":\"$TAVILY_KEY\",\"query\":\"test\",\"max_results\":1}")
if [ "$tavily_code" = "200" ]; then
  echo "  ${green}OK${off}   Tavily key accepted"
else
  echo "  ${red}FAIL${off} Tavily returned HTTP $tavily_code"
fi

if [ "$openai_code" != "200" ] || [ "$tavily_code" != "200" ]; then
  echo
  printf "%sOne or both keys failed. Write .env anyway? [y/N] %s" "$yellow" "$off"
  read -r reply
  case "$reply" in
    [yY]*) ;;
    *) echo "Nothing written."; exit 1 ;;
  esac
fi

JWT_SECRET=$(openssl rand -hex 32)

umask 077
cat > "$ENV_FILE" <<EOF
# Rekomme — demo deployment. Generated $(date '+%Y-%m-%d %H:%M').
# Do not commit this file.

OPENAI_API_KEY="$OPENAI_KEY"
TAVILY_API_KEY="$TAVILY_KEY"
JWT_SECRET_KEY="$JWT_SECRET"

DEMO_USERNAME="$DEMO_USER"
DEMO_PASSWORD="$DEMO_PASS"

# Set by the container at runtime; here for local runs.
BACKEND_URI="http://localhost:8000"
POSTGRES_CONN_STRING="postgresql://postgres@localhost:5432/postgres"
POSTGRES_HOSTNAME="localhost"
POSTGRES_USER="postgres"
POSTGRES_PASSWORD="postgres"
POSTGRES_PORT=5432
POSTGRES_DB="postgres"

# Intentionally blank — the app degrades around these.
# Blank PINECONE_API_KEY is what turns DEMO_MODE on.
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

echo
echo "${green}${bold}Written.${off} $ENV_FILE ${dim}(mode 600)${off}"
echo "${dim}Demo login: $DEMO_USER / $DEMO_PASS${off}"
echo
