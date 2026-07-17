#!/usr/bin/env bash
# ============================================================================
# setup-orchestration.sh — Préparation du VPS pour la stack d'orchestration
# ----------------------------------------------------------------------------
# Installe Coolify (coexistence avec Caddy existant), configure UFW,
# et crée l'arborescence applicative dans /srv/apps/orchestration/.
#
# Pré-requis :
#   • Docker déjà installé (voir install-base-stack.sh)
#   • Exécuté en root ou via sudo
#   • Connexion SSH fonctionnelle (ssh prodserveur)
#
# Usage :
#   ./scripts/setup-orchestration.sh
# ============================================================================
set -euo pipefail

# ---------- Couleurs --------------------------------------------------------
RED=$'\e[31m'; GREEN=$'\e[32m'; YELLOW=$'\e[33m'; BLUE=$'\e[34m'; NC=$'\e[0m'
log()  { printf '%b[setup]%b %s\n' "${BLUE}" "${NC}" "$*"; }
ok()   { printf '%b[  ok  ]%b %s\n' "${GREEN}" "${NC}" "$*"; }
warn() { printf '%b[ warn ]%b %s\n' "${YELLOW}" "${NC}" "$*"; }
err()  { printf '%b[ err  ]%b %s\n' "${RED}"   "${NC}" "$*" >&2; exit 1; }

[ "$(id -u)" -eq 0 ] || err "Ce script doit être lancé en root (sudo)."

export DEBIAN_FRONTEND=noninteractive

ORCH_DIR="/srv/apps/orchestration"
COOLIFY_PORT=8000
HERMES_STUDIO_PORT=3000
N8N_PORT=5678

# ---------- 1. Vérifications préalables ------------------------------------
log "=== 1/6 — Vérifications préalables ==="
command -v docker >/dev/null 2>&1 || err "Docker non installé. Lance install-base-stack.sh d'abord."
docker info >/dev/null 2>&1 || err "Docker daemon non actif."
ok "Docker opérationnel : $(docker --version)"

# ---------- 2. Installation de Coolify -------------------------------------
log "=== 2/6 — Installation de Coolify (coexistence) ==="
if docker ps --format '{{.Names}}' | grep -q '^coolify$'; then
    ok "Coolify déjà installé"
else
    warn "Installation de Coolify via le script officiel…"
    warn "Coolify utilisera son propre proxy Traefik en parallèle de Caddy."
    warn "Ports Coolify : 8000 (UI), 80/443 (Traefik, partagés avec Caddy)"
    curl -fsSL https://cdn.coollabs.io/coolify/install.sh | bash
    ok "Coolify installé"
fi

# ---------- 3. Configuration UFW -------------------------------------------
log "=== 3/6 — Configuration UFW ==="
if ! command -v ufw >/dev/null 2>&1; then
    apt-get update -qq && apt-get install -y -qq ufw
    ok "UFW installé"
fi

# Politique par défaut : deny incoming
ufw --force default deny incoming
ufw --force default allow outgoing

# Ports de base
ufw allow 22/tcp    comment "SSH"
ufw allow 80/tcp    comment "HTTP (Caddy + Traefik)"
ufw allow 443/tcp   comment "HTTPS (Caddy + Traefik)"

# Ports applicatifs (accès direct si pas de domaine)
ufw allow "${HERMES_STUDIO_PORT}/tcp" comment "Hermes Studio"
ufw allow "${N8N_PORT}/tcp"           comment "n8n"
ufw allow "${COOLIFY_PORT}/tcp"       comment "Coolify UI"

# Activer UFW (attention : ne pas verrouiller le SSH)
ufw --force enable
ok "UFW activé et configuré"

# ---------- 4. Arborescence applicative ------------------------------------
log "=== 4/6 — Arborescence /srv/apps/orchestration ==="
mkdir -p "${ORCH_DIR}"/{hermes-daemon,hermes-studio,mcp-server,n8n-data,tools,docs}
chown -R younes:younes "${ORCH_DIR}"
ok "Dossiers créés : ${ORCH_DIR}/{hermes-daemon,hermes-studio,mcp-server,n8n-data,tools,docs}"

# ---------- 5. Réseau Docker nommé -----------------------------------------
log "=== 5/6 — Réseau Docker orchestration-net ==="
if docker network ls --format '{{.Name}}' | grep -q '^orchestration-net$'; then
    ok "Réseau orchestration-net existe déjà"
else
    docker network create --driver bridge --attachable orchestration-net
    ok "Réseau orchestration-net créé"
fi

# ---------- 6. Résumé ------------------------------------------------------
printf '\n%b═══════════════════════════════════════════════════════%b\n' "${GREEN}" "${NC}"
printf '%b PRÉPARATION TERMINÉE%b\n' "${GREEN}" "${NC}"
printf '%b═══════════════════════════════════════════════════════%b\n' "${GREEN}" "${NC}"
echo
echo "Coolify UI      : http://169.58.30.70:${COOLIFY_PORT}"
echo "Hermes Studio   : http://169.58.30.70:${HERMES_STUDIO_PORT} (après docker compose up)"
echo "n8n             : http://169.58.30.70:${N8N_PORT} (après docker compose up)"
echo
echo "Prochaines étapes :"
echo "  1. Génère les secrets : ./scripts/generate-secrets.sh"
echo "  2. Copie docker-compose.yml dans ${ORCH_DIR}/"
echo "  3. Lance : docker compose -f ${ORCH_DIR}/docker-compose.yml up -d"
echo "  4. Configure Coolify (voir docs/COOLIFY_SETUP.md)"
