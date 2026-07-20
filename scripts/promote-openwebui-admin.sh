#!/usr/bin/env bash
# ============================================================================
# promote-openwebui-admin.sh — Promouvoir un utilisateur en admin dans Open WebUI
#
# Quand DEFAULT_USER_ROLE=pending, le premier compte Google qui se connecte
# est bloqué sur "Account Activation Pending". Ce script lit l'email dans
# .env (SUPERADMIN_EMAIL) et le promeut directement dans la SQLite
# d'Open WebUI.
#
# Usage local :
#   ./scripts/promote-openwebui-admin.sh                          # email depuis .env
#   ./scripts/promote-openwebui-admin.sh user@example.com         # email custom
#
# Idempotent : peut être appelé plusieurs fois sans risque.
# ============================================================================
set -euo pipefail

# ---------- Args / Config --------------------------------------------------
EMAIL="${1:-${SUPERADMIN_EMAIL:-}}"
if [[ -z "$EMAIL" ]]; then
  echo "❌ Usage: $0 <email>"
  echo "   ou bien définir SUPERADMIN_EMAIL dans .env"
  exit 1
fi

HOST="${OW_HOST:-prodserveur}"
OW_CONTAINER="${OW_CONTAINER:-open-webui}"
# Dans le container, la DB est accessible via docker exec (pas besoin de sudo,
# pas de problème de permissions root sur le volume mount).
DB_PATH_IN_CONTAINER="/app/backend/data/webui.db"

# ---------- 1. Vérifier la DB ---------------------------------------------
echo "→ Recherche de la DB Open WebUI dans le container '${OW_CONTAINER}' sur ${HOST}"

ssh "${HOST}" bash -s -- "${EMAIL}" "${OW_CONTAINER}" "${DB_PATH_IN_CONTAINER}" <<'REMOTE_SCRIPT'
set -euo pipefail
EMAIL="$1"
OW_CONTAINER="$2"
DB_PATH="$3"

# Vérifier que le container tourne
if ! docker ps --format '{{.Names}}' | grep -q "^${OW_CONTAINER}$"; then
  echo "❌ Container '${OW_CONTAINER}' pas running (docker ps)"
  exit 1
fi

# ---------- 2. Installer sqlite3 dans le container si absent --------------
if ! docker exec "${OW_CONTAINER}" sh -c "command -v sqlite3" >/dev/null 2>&1; then
  echo "⚠️  sqlite3 absent dans le container — tentative d'installation..."
  docker exec "${OW_CONTAINER}" sh -c \
    "apt-get update -qq && apt-get install -y --no-install-recommends sqlite3 2>&1 | tail -3" \
    || {
      echo "❌ Impossible d'installer sqlite3 dans le container (peut-être offline)"
      echo "   Fallback : utiliser une copie de la DB sur l'hôte via:"
      echo "   docker cp ${OW_CONTAINER}:${DB_PATH} /tmp/webui.db && sqlite3 /tmp/webui.db ..."
      exit 1
    }
fi

# ---------- 3. Lister les users existants --------------------------------
echo ""
echo "→ Users existants:"
docker exec "${OW_CONTAINER}" sqlite3 -header -column "${DB_PATH}" \
  "SELECT id, email, role, SUBSTR(created_at,1,19) AS created FROM user ORDER BY id;"

# ---------- 4. Promotion --------------------------------------------------
echo ""
echo "→ Tentative de promotion de '${EMAIL}' en admin..."

USER_COUNT=$(docker exec "${OW_CONTAINER}" sqlite3 "${DB_PATH}" \
  "SELECT COUNT(*) FROM user WHERE email='${EMAIL}';")
if [[ "$USER_COUNT" == "0" ]]; then
  echo "  ⚠️  User absent de la DB — il faut te connecter une 1re fois avec Google"
  echo "     pour que Open WebUI crée ton user (role=pending). Puis relance ce script."
  exit 0
fi

CURRENT_ROLE=$(docker exec "${OW_CONTAINER}" sqlite3 "${DB_PATH}" \
  "SELECT role FROM user WHERE email='${EMAIL}';")
echo "  Role actuel: ${CURRENT_ROLE}"

if [[ "$CURRENT_ROLE" == "admin" ]]; then
  echo "  ✅ Déjà admin, rien à faire"
else
  docker exec "${OW_CONTAINER}" sqlite3 "${DB_PATH}" \
    "UPDATE user SET role='admin' WHERE email='${EMAIL}';"
  NEW_ROLE=$(docker exec "${OW_CONTAINER}" sqlite3 "${DB_PATH}" \
    "SELECT role FROM user WHERE email='${EMAIL}';")
  if [[ "$NEW_ROLE" == "admin" ]]; then
    echo "  ✅ ${EMAIL} promu admin"
  else
    echo "  ❌ Échec : role actuel = '${NEW_ROLE}'"
    exit 1
  fi
fi

echo ""
echo "→ État final:"
docker exec "${OW_CONTAINER}" sqlite3 -header -column "${DB_PATH}" \
  "SELECT id, email, role FROM user WHERE email='${EMAIL}';"
REMOTE_SCRIPT

echo ""
echo "✅ Terminé. Reconnecte-toi sur https://agentai.smartefp.com (peut-être vider les cookies / logout d'abord)."