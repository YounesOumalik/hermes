#!/usr/bin/env bash
# ============================================================================
# install-webhook.sh — Installation one-shot du webhook Hermes
#
# À exécuter SUR LE VPS (prodserveur) ou depuis le poste local.
# Automatise :
#   1. Création de /opt/hermes-orchestration/{repo,webhook}/
#   2. Clone du repo GitHub (si pas déjà fait)
#   3. Génération du secret HMAC
#   4. Installation et activation du service systemd
#   5. Affichage du secret pour configurer GitHub
#
# Usage :
#   # Sur le VPS directement :
#   sudo ./infra/webhook/install-webhook.sh
#
#   # Depuis le poste local (avec --remote) :
#   ./infra/webhook/install-webhook.sh --remote
#
# Variables d'environnement :
#   VPS_HOST        prodserveur (alias SSH)
#   VPS_USER        younes
#   GITHUB_REPO     https://github.com/<user>/ProdServeur.git
# ============================================================================
set -euo pipefail

APP="hermes-orchestration"
APP_DIR="/opt/${APP}"
REPO_DIR="${APP_DIR}/repo"
WEBHOOK_DIR="${APP_DIR}/webhook"
SECRET_FILE="/etc/eaumalik/${APP}-webhook-secret"
WEBHOOK_PORT=9000
REMOTE=false
VPS_HOST="${VPS_HOST:-prodserveur}"
VPS_USER="${VPS_USER:-younes}"
GITHUB_REPO="${GITHUB_REPO:-}"

# ---------- Args ----------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --remote) REMOTE=true; shift ;;
    --repo) GITHUB_REPO="$2"; shift 2 ;;
    *) echo "Option inconnue : $1"; exit 1 ;;
  esac
done

# ---------- Couleurs ----------
RED=$'\e[31m'; GREEN=$'\e[32m'; YELLOW=$'\e[33m'; BLUE=$'\e[34m'; NC=$'\e[0m'
log()  { printf '%b[install]%b %s\n' "${BLUE}" "${NC}" "$*"; }
ok()   { printf '%b[  ok   ]%b %s\n' "${GREEN}" "${NC}" "$*"; }
warn() { printf '%b[ warn  ]%b %s\n' "${YELLOW}" "${NC}" "$*"; }
err()  { printf '%b[ error ]%b %s\n' "${RED}"   "${NC}" "$*" >&2; exit 1; }

# ---------- Helpers ----------
if $REMOTE; then
  ssh_exec() { ssh "$VPS_HOST" "$@"; }
  scp_to()   { scp -q "$1" "$VPS_HOST:$2"; }
  REMOTE_PREFIX="ssh $VPS_HOST"
else
  ssh_exec() { bash -c "$@"; }
  scp_to()   { cp "$1" "$2"; }
  REMOTE_PREFIX=""
  [ "$(id -u)" -eq 0 ] || err "Exécute en sudo (ou utilise --remote depuis le poste local)"
fi

log "Installation du webhook pour ${APP}"
log "Mode : $($REMOTE && echo "remote (${VPS_HOST})" || echo "local")"
echo

# ---------- 1. Créer les dossiers -------------------------------------------
log "=== 1/5 — Arborescence ==="
ssh_exec "mkdir -p ${APP_DIR}/{repo,webhook} /var/log/${APP}-webhook.log /var/log/${APP}-deploy /etc/eaumalik"
ssh_exec "chown -R ${VPS_USER}:${VPS_USER} ${APP_DIR} /var/log/${APP}-webhook.log /var/log/${APP}-deploy"
ok "Dossiers créés"

# ---------- 2. Cloner le repo -----------------------------------------------
log "=== 2/5 — Cloner le repo ==="
if ssh_exec "[ -d ${REPO_DIR}/.git ]"; then
  ok "Repo déjà cloné dans ${REPO_DIR}"
else
  if [[ -z "$GITHUB_REPO" ]]; then
    err "GITHUB_REPO non défini. Utilise --repo https://github.com/<user>/ProdServeur.git"
  fi
  ssh_exec "git clone ${GITHUB_REPO} ${REPO_DIR}"
  ok "Repo cloné"
fi

# ---------- 3. Générer le secret HMAC ---------------------------------------
log "=== 3/5 — Secret HMAC ==="
if ssh_exec "[ -f ${SECRET_FILE} ]"; then
  ok "Secret HMAC déjà présent"
  SECRET=$(ssh_exec "sudo cat ${SECRET_FILE}")
else
  SECRET=$(ssh_exec "openssl rand -hex 32")
  ssh_exec "echo '${SECRET}' | sudo tee ${SECRET_FILE} > /dev/null && sudo chmod 600 ${SECRET_FILE}"
  ok "Secret généré dans ${SECRET_FILE}"
fi

# ---------- 4. Copier les fichiers webhook ----------------------------------
log "=== 4/5 — Installation des fichiers webhook ==="
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
scp_to "${SCRIPT_DIR}/server.js" "${WEBHOOK_DIR}/server.js"
scp_to "${SCRIPT_DIR}/deploy-on-push.sh" "${REPO_DIR}/deploy-on-push.sh"
scp_to "${SCRIPT_DIR}/package.json" "${WEBHOOK_DIR}/package.json"
ssh_exec "chmod +x ${REPO_DIR}/deploy-on-push.sh"
ok "Fichiers copiés"

# ---------- 5. Installer le service systemd ---------------------------------
log "=== 5/5 — Service systemd ==="
# Copier le service
scp_to "${SCRIPT_DIR}/hermes-webhook.service" "/etc/systemd/system/hermes-webhook.service"
# Modifier le chemin si l'utilisateur est différent
if [[ "$VPS_USER" != "root" ]]; then
  ssh_exec "sudo sed -i 's|User=root|User=${VPS_USER}|g' /etc/systemd/system/hermes-webhook.service"
fi
ssh_exec "sudo systemctl daemon-reload"
ssh_exec "sudo systemctl enable hermes-webhook"
ssh_exec "sudo systemctl restart hermes-webhook"
ok "Service systemd activé et démarré"

# ---------- Résumé ----------------------------------------------------------
printf '\n%b══════════════════════════════════════════════════%b\n' "${GREEN}" "${NC}"
printf '%b INSTALLATION TERMINÉE%b\n' "${GREEN}" "${NC}"
printf '%b══════════════════════════════════════════════════%b\n' "${GREEN}" "${NC}"
echo
echo "  Webhook : http://localhost:${WEBHOOK_PORT}/webhook"
echo "  Health  : http://localhost:${WEBHOOK_PORT}/health"
echo "  Logs    : journalctl -u hermes-webhook -f"
echo
echo "⚠️  COPIE CE SECRET DANS GITHUB (Settings → Webhooks) :"
printf '%b%s%b\n' "${YELLOW}" "${SECRET}" "${NC}"
echo
echo "  URL webhook  : https://<TON_DOMAINE>/webhook"
echo "  Content type : application/json"
echo "  Secret       : (copie la valeur ci-dessus)"
echo "  Events       : Just the push event"
echo
echo "⚠️  Ajoute ce bloc dans Caddy (/etc/caddy/Caddyfile) :"
echo
echo "  @hermesWebhook path /webhook /health"
echo "  handle @hermesWebhook {"
echo "      reverse_proxy 127.0.0.1:${WEBHOOK_PORT}"
echo "  }"
echo
echo "Puis : sudo systemctl reload caddy"
