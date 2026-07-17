#!/usr/bin/env bash
# ============================================================================
# deploy-on-push.sh — Déploiement auto de la stack d'orchestration
#
# Déclenché par le webhook GitHub (server.js :9000).
# Étapes :
#   1. git fetch + git reset --hard <SHA>
#   2. docker compose build (BuildKit) + up -d
#   3. Healthcheck sur les 4 services
#   4. Smoke test HTTP sur les endpoints critiques
#   5. Cleanup images anciennes (> 3 versions)
#
# Adapté du pattern eaumalik.com.
# ============================================================================
set -euo pipefail

# ---------- Config ----------------------------------------------------------
APP="hermes-orchestration"
REPO_DIR="/opt/${APP}/repo"
ENV_FILE="/opt/${APP}/.env"
DOCKER_COMPOSE_FILE="${REPO_DIR}/docker-compose.yml"

SHA="${1:-${DEPLOY_SHA:-unknown}}"
BUILD_TAG="${SHA:0:7}-$(date +%Y%m%d-%H%M%S)"
LOG_DIR="/var/log/${APP}-deploy"
mkdir -p "$LOG_DIR"
LOG_FILE="${LOG_DIR}/deploy-$(date +%Y%m%d-%H%M%S).log"

# Logging
exec > >(tee -a "$LOG_FILE") 2>&1
echo "=== DEPLOY ${APP} ==="
echo "SHA: ${SHA}  Tag: ${BUILD_TAG}  Date: $(date -Iseconds)"

# ---------- 1. Vérifications -------------------------------------------------
[[ -d "$REPO_DIR" ]] || { echo "❌ Répertoire absent: $REPO_DIR"; exit 1; }
[[ -f "$ENV_FILE" ]] || { echo "❌ .env absent: $ENV_FILE"; exit 1; }

# ---------- 2. Git fetch + reset ---------------------------------------------
echo "→ git fetch + reset"
cd "$REPO_DIR"
git fetch origin main --quiet 2>&1
git reset --hard "$SHA" --quiet 2>&1
echo "  HEAD: $(git rev-parse --short HEAD)"

# ---------- 3. Docker Compose build + up ------------------------------------
echo "→ docker compose build + up"

# Exporter les variables d'environnement depuis .env
set -a
source "$ENV_FILE"
set +a

# Build avec BuildKit (cache, parallélisme)
DOCKER_BUILDKIT=1 docker compose -f "$DOCKER_COMPOSE_FILE" build \
  --build-arg "CACHE_BUST=$(date +%s)" \
  2>&1

# Relancer tous les services
docker compose -f "$DOCKER_COMPOSE_FILE" up -d --remove-orphans 2>&1
echo "  Services lancés"

# ---------- 4. Healthcheck (attente active, max 120s) -----------------------
echo "→ Healthchecks…"
SERVICES=("hermes-daemon" "hermes-studio" "n8n" "mcp-server")
ALL_HEALTHY=false

for i in $(seq 1 60); do
  HEALTHY_COUNT=0
  for svc in "${SERVICES[@]}"; do
    STATUS=$(docker inspect --format '{{.State.Health.Status}}' "$svc" 2>/dev/null || echo 'starting')
    if [[ "$STATUS" == "healthy" ]]; then
      HEALTHY_COUNT=$((HEALTHY_COUNT + 1))
    fi
  done
  echo "  [$i/60] ${HEALTHY_COUNT}/${#SERVICES[@]} services healthy"
  if [[ "$HEALTHY_COUNT" -eq "${#SERVICES[@]}" ]]; then
    ALL_HEALTHY=true
    break
  fi
  sleep 2
done

if ! $ALL_HEALTHY; then
  echo "❌ Timeout healthcheck — logs:"
  for svc in "${SERVICES[@]}"; do
    echo "--- $svc ---"
    docker logs "$svc" --tail 20 2>&1 || true
  done
  exit 1
fi

echo "✅ Tous les services sont healthy"

# ---------- 5. Smoke tests HTTP ---------------------------------------------
echo "→ Smoke tests…"
ENDPOINTS=(
  "http://127.0.0.1:3000|Hermes Studio"
  "http://127.0.0.1:5678/healthz|n8n"
  "http://127.0.0.1:8001/health|Hermes Daemon"
  "http://127.0.0.1:3100/health|MCP Server"
)

for endpoint in "${ENDPOINTS[@]}"; do
  URL="${endpoint%%|*}"
  NAME="${endpoint##*|}"
  HTTP_CODE=$(curl -fsS -o /dev/null -w '%{http_code}' "$URL" 2>/dev/null || echo "000")
  if [[ "$HTTP_CODE" -ge 200 && "$HTTP_CODE" -lt 400 ]]; then
    echo "  ✅ $NAME ($URL) → $HTTP_CODE"
  else
    echo "  ❌ $NAME ($URL) → $HTTP_CODE"
    exit 1
  fi
done

# ---------- 6. Cleanup anciennes images -------------------------------------
echo "→ Cleanup (garde 3 derniers tags par service)…"
for svc in "${SERVICES[@]}"; do
  # Trouve l'image du service
  IMAGE=$(docker inspect --format '{{.Config.Image}}' "$svc" 2>/dev/null || echo '')
  if [[ -n "$IMAGE" && "$IMAGE" != *":"* ]]; then
    IMAGE_NAME="${IMAGE%:*}"
    # Supprime toutes les images sauf les 3 plus récentes
    docker images --format '{{.ID}} {{.Repository}}:{{.Tag}}' \
      | grep "^.* ${IMAGE_NAME}:" \
      | sort -r \
      | tail -n +4 \
      | awk '{print $1}' \
      | xargs -r docker rmi 2>/dev/null || true
  fi
done

echo "✅ Déploiement terminé (${BUILD_TAG})"
