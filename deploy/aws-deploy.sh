#!/usr/bin/env bash
# Build the Rekomme demo image, push it to ECR, and run it on ECS Express Mode.
# Idempotent: safe to re-run for a redeploy.
set -euo pipefail

cd "$(dirname "$0")/.."

PROFILE="${AWS_PROFILE:-incubator}"
REGION="${AWS_REGION:-us-east-2}"
REPO="${ECR_REPO:-rekomme-demo}"
CLUSTER="${ECS_CLUSTER:-default}"
SERVICE="${ECS_SERVICE:-rekomme}"
TAG="${IMAGE_TAG:-$(date -u +%Y%m%d-%H%M%S)}"

INFRA_ROLE="${ECS_INFRA_ROLE:-ecsInfrastructureRoleForExpressServices}"
EXECUTION_ROLE="${ECS_EXECUTION_ROLE:-ecsTaskExecutionRole}"

aws() { command aws --profile "$PROFILE" --region "$REGION" "$@"; }
say() { printf '\n\033[1m==> %s\033[0m\n' "$1"; }

say "Checking AWS session"
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
echo "account $ACCOUNT, region $REGION, profile $PROFILE"

REGISTRY="$ACCOUNT.dkr.ecr.$REGION.amazonaws.com"
IMAGE="$REGISTRY/$REPO:$TAG"

# ── secrets into SSM ─────────────────────────────────────────────────────────
say "Storing API keys in SSM Parameter Store"
if [ ! -f .env ]; then
  echo "No .env found. Run deploy/make-env.sh first." >&2
  exit 1
fi
set -a; . ./.env; set +a

SECRET_VARS=()

for var in OPENAI_API_KEY TAVILY_API_KEY JWT_SECRET_KEY; do
  value="${!var:-}"
  if [ -z "$value" ]; then
    echo "$var is empty in .env" >&2
    exit 1
  fi
  aws ssm put-parameter --name "/rekomme/$var" --value "$value" \
    --type SecureString --overwrite >/dev/null
  SECRET_VARS+=("$var")
  echo "  /rekomme/$var"
done

# Optional: present only if the matching setup script has been run.
for var in OXYLABS_USERNAME OXYLABS_PASSWORD POSTGRES_CONN_STRING; do
  value="${!var:-}"
  case "$value" in
    ""|*localhost*) continue ;;
  esac
  aws ssm put-parameter --name "/rekomme/$var" --value "$value" \
    --type SecureString --overwrite >/dev/null
  SECRET_VARS+=("$var")
  echo "  /rekomme/$var"
done

if [ ${#SECRET_VARS[@]} -eq 3 ]; then
  echo "  (no OxyLabs or external Postgres configured — listings off, local DB)"
fi

# ── ECR ──────────────────────────────────────────────────────────────────────
say "Ensuring ECR repository"
aws ecr describe-repositories --repository-names "$REPO" >/dev/null 2>&1 \
  || aws ecr create-repository --repository-name "$REPO" \
       --image-scanning-configuration scanOnPush=true >/dev/null
echo "  $REGISTRY/$REPO"

say "Logging Docker in to ECR"
aws ecr get-login-password | docker login --username AWS --password-stdin "$REGISTRY"

say "Building for linux/amd64 and pushing $TAG"
docker buildx build --platform linux/amd64 -t "$IMAGE" --push .

# ── IAM ──────────────────────────────────────────────────────────────────────
say "Ensuring ECS IAM roles"

roles_created=0
infra_trust='{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"ecs.amazonaws.com"},"Action":"sts:AssumeRole"}]}'
if ! aws iam get-role --role-name "$INFRA_ROLE" >/dev/null 2>&1; then
  aws iam create-role --role-name "$INFRA_ROLE" \
    --assume-role-policy-document "$infra_trust" >/dev/null
  echo "  created $INFRA_ROLE"
  roles_created=1
fi
aws iam attach-role-policy --role-name "$INFRA_ROLE" \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSInfrastructureRoleforExpressGatewayServices >/dev/null

execution_trust='{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"ecs-tasks.amazonaws.com"},"Action":"sts:AssumeRole"}]}'
if ! aws iam get-role --role-name "$EXECUTION_ROLE" >/dev/null 2>&1; then
  aws iam create-role --role-name "$EXECUTION_ROLE" \
    --assume-role-policy-document "$execution_trust" >/dev/null
  echo "  created $EXECUTION_ROLE"
  roles_created=1
fi
aws iam attach-role-policy --role-name "$EXECUTION_ROLE" \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy >/dev/null

aws iam put-role-policy --role-name "$EXECUTION_ROLE" \
  --policy-name ReadRekommeParameters \
  --policy-document "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":[\"ssm:GetParameter\",\"ssm:GetParameters\"],\"Resource\":\"arn:aws:ssm:$REGION:$ACCOUNT:parameter/rekomme/*\"}]}" >/dev/null

if [ "$roles_created" -eq 1 ]; then
  echo "  waiting for new IAM roles to propagate"
  sleep 10
fi

INFRA_ROLE_ARN="arn:aws:iam::$ACCOUNT:role/$INFRA_ROLE"
EXECUTION_ROLE_ARN="arn:aws:iam::$ACCOUNT:role/$EXECUTION_ROLE"
SSM_PREFIX="arn:aws:ssm:$REGION:$ACCOUNT:parameter/rekomme"

# ── ECS Express Mode ────────────────────────────────────────────────────────
secrets_json='[]'
for var in "${SECRET_VARS[@]}"; do
  secrets_json=$(jq -c --arg name "$var" --arg valueFrom "$SSM_PREFIX/$var" \
    '. + [{name: $name, valueFrom: $valueFrom}]' <<<"$secrets_json")
done

primary_container=$(jq -nc \
  --arg image "$IMAGE" \
  --arg username "${DEMO_USERNAME:-reviewer}" \
  --arg password "${DEMO_PASSWORD:-rekomme}" \
  --argjson secrets "$secrets_json" \
  '{image:$image,containerPort:8080,
    environment:[{name:"DEMO_USERNAME",value:$username},{name:"DEMO_PASSWORD",value:$password}],
    secrets:$secrets}')

ARN="arn:aws:ecs:$REGION:$ACCOUNT:service/$CLUSTER/$SERVICE"
if ! aws ecs describe-express-gateway-service --service-arn "$ARN" >/dev/null 2>&1; then
  say "Creating ECS Express service"
  ARN=$(aws ecs create-express-gateway-service \
    --service-name "$SERVICE" \
    --cluster "$CLUSTER" \
    --infrastructure-role-arn "$INFRA_ROLE_ARN" \
    --execution-role-arn "$EXECUTION_ROLE_ARN" \
    --health-check-path '/api/health' \
    --primary-container "$primary_container" \
    --cpu 1024 \
    --memory 4096 \
    --cpu-architecture X86_64 \
    --scaling-target 'minTaskCount=1,maxTaskCount=1,autoScalingMetric=AVERAGE_CPU,autoScalingTargetValue=60' \
    --query 'service.serviceArn' --output text)
else
  say "Updating existing ECS Express service"
  # The versioned image creates a fresh revision while ECS preserves its
  # managed networking, logging, secrets, and scaling configuration.
  image_update=$(jq -nc --arg image "$IMAGE" '{image:$image}')
  aws ecs update-express-gateway-service \
    --service-arn "$ARN" \
    --health-check-path '/api/health' \
    --primary-container "$image_update" >/dev/null
fi

say "Waiting for the ECS service to become stable (this can take several minutes)"
aws ecs wait services-stable --cluster "$CLUSTER" --services "$SERVICE"

URL=$(aws ecs describe-express-gateway-service --service-arn "$ARN" \
  --query 'service.activeConfigurations[0].ingressPaths[0].endpoint' --output text)

curl -fsS --retry 6 --retry-delay 10 "$URL/api/health" >/dev/null
printf '\n\033[32m\033[1mLive:\033[0m %s\n' "$URL"
printf 'Sign in as %s / %s\n\n' "${DEMO_USERNAME:-reviewer}" "${DEMO_PASSWORD:-rekomme}"
