#!/usr/bin/env bash
# ============================================================================
# generate-secrets.sh — Génère le fichier .env avec secrets aléatoires
# ----------------------------------------------------------------------------
# Crée /srv/apps/orchestration/.env à partir de .env.template si absent,
# et remplit les valeurs sensibles avec des secrets cryptographiques.
#
# Usage :
#   ./scripts/generate-secrets.sh
# ============================================================================
set -euo pipefail

ORCH_DIR="/srv/apps/orchestration"
ENV_FILE="${ORCH_DIR}/.env"
TEMPLATE="${ORCH_DIR}/.env.template"

RED=$'\e[31m'; GREEN=$'\e[32m'; YELLOW=$'\e[33m'; BLUE=$'\e[34m'; NC=$'\e[0m'
log()  { printf '%b[secrets]%b %s\n' "${BLUE}" "${NC}" "$*"; }
ok()   { printf '%b[  ok   ]%b %s\n' "${GREEN}" "${NC}" "$*"; }
warn() { printf '%b[ warn  ]%b %s\n' "${YELLOW}" "${NC}" "$*"; }
err()  { printf '%b[ error ]%b %s\n' "${RED}"   "${NC}" "$*" >&2; exit 1; }

[ -f "${TEMPLATE}" ] || err "Template introuvable : ${TEMPLATE}. Lance setup-orchestration.sh d'abord."

if [[ -f "${ENV_FILE}" ]]; then
    warn "${ENV_FILE} existe déjà — conservation des valeurs existantes."
    warn "Pour régénérer, supprime le fichier et relance ce script."
    exit 0
fi

# Génération des secrets
gen_secret() {
    openssl rand -base64 32 | tr -d '/+=' | head -c 48
}

log "Génération des secrets…"
N8N_KEY="$(gen_secret)"
JWT_SECRET="$(gen_secret)"
MCP_TOKEN="$(gen_secret)"
POSTGRES_PASSWORD="$(gen_secret)"
REDIS_PASSWORD="$(gen_secret)"

# Copie du template et remplacement des placeholders
cp "${TEMPLATE}" "${ENV_FILE}"

sed -i "s|__N8N_ENCRYPTION_KEY__|${N8N_KEY}|g" "${ENV_FILE}"
sed -i "s|__HERMES_JWT_SECRET__|${JWT_SECRET}|g" "${ENV_FILE}"
sed -i "s|__MCP_AUTH_TOKEN__|${MCP_TOKEN}|g" "${ENV_FILE}"
sed -i "s|__POSTGRES_PASSWORD__|${POSTGRES_PASSWORD}|g" "${ENV_FILE}"
sed -i "s|__REDIS_PASSWORD__|${REDIS_PASSWORD}|g" "${ENV_FILE}"

chmod 600 "${ENV_FILE}"
chown younes:younes "${ENV_FILE}"

ok "Secrets générés dans ${ENV_FILE}"
warn "Garde ce fichier secret — il n'est PAS versionné (voir .gitignore)."
echo
echo "Variables générées :"
echo "  N8N_ENCRYPTION_KEY  = ${N8N_KEY:0:8}…"
echo "  HERMES_JWT_SECRET   = ${JWT_SECRET:0:8}…"
echo "  MCP_AUTH_TOKEN      = ${MCP_TOKEN:0:8}…"
echo "  POSTGRES_PASSWORD   = ${POSTGRES_PASSWORD:0:8}…"
echo
echo "⚠️  Renseigne manuellement les clés API dans ${ENV_FILE} :"
echo "   MINIMAX_API_KEY, TELEGRAM_BOT_TOKEN, ALLOWED_CHAT_ID, GITHUB_TOKEN"
