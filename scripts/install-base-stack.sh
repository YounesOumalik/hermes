#!/usr/bin/env bash
# ============================================================================
# install-base-stack.sh — Installation de la stack de base sur ProdServeur
# ----------------------------------------------------------------------------
# Installe :
#   • Docker CE + Docker Compose + buildx
#   • Node.js 22 LTS (via NodeSource)
#   • Caddy 2 (reverse proxy + HTTPS auto)
#   • PostgreSQL 16 + Redis 7
#   • Arborescence /srv/apps + /opt/backups
# Pré-requis : sudo NOPASSWD actif (cf. HANDOVER.md §7)
# ============================================================================
set -euo pipefail

RED=$'\e[31m'; GREEN=$'\e[32m'; YELLOW=$'\e[33m'; BLUE=$'\e[34m'; NC=$'\e[0m'
log()  { printf '%b[install]%b %s\n' "${BLUE}" "${NC}" "$*"; }
ok()   { printf '%b[  ok  ]%b %s\n' "${GREEN}" "${NC}" "$*"; }
warn() { printf '%b[ warn ]%b %s\n' "${YELLOW}" "${NC}" "$*"; }
err()  { printf '%b[ err  ]%b %s\n' "${RED}"   "${NC}" "$*" >&2; exit 1; }

[ "$(id -u)" -eq 0 ] || err "Ce script doit être lancé via ssh root ou avec sudo."

export DEBIAN_FRONTEND=noninteractive

# ---------- 1. Docker CE + Compose + buildx ---------------------------------
log "=== 1/6 — Docker CE + Compose + buildx ==="
if command -v docker >/dev/null 2>&1; then
    ok "Docker déjà installé : $(docker --version)"
else
    apt-get update -qq
    apt-get install -y -qq ca-certificates curl gnupg
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
        gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/ubuntu noble stable" > /etc/apt/sources.list.d/docker.list
    apt-get update -qq
    apt-get install -y -qq docker-ce docker-ce-cli containerd.io \
        docker-buildx-plugin docker-compose-plugin
    ok "Docker installé : $(docker --version)"
fi

# Activer et démarrer Docker
systemctl enable --now docker
ok "Docker service actif"

# Ajouter younes au groupe docker (pour utiliser docker sans sudo)
if id younes >/dev/null 2>&1; then
    usermod -aG docker younes
    ok "younes ajouté au groupe docker (déconnexion/reconnexion requise)"
fi

# Test
docker run --rm hello-world >/dev/null 2>&1 && ok "Docker hello-world OK" || \
    warn "hello-world a échoué (souvent OK en l'absence de réseau sortant vers Docker Hub)"

# ---------- 2. Node.js 22 LTS ----------------------------------------------
log "=== 2/6 — Node.js 22 LTS ==="
if command -v node >/dev/null 2>&1 && [[ "$(node -v)" == v22* ]]; then
    ok "Node.js déjà installé : $(node -v)"
else
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash - >/dev/null
    apt-get install -y -qq nodejs
    ok "Node.js installé : $(node -v) / npm $(npm -v)"
fi

# ---------- 3. Caddy 2 -----------------------------------------------------
log "=== 3/6 — Caddy 2 ==="
if command -v caddy >/dev/null 2>&1; then
    ok "Caddy déjà installé : $(caddy version)"
else
    apt-get install -y -qq debian-keyring debian-archive-keyring apt-transport-https
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | \
        gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/deb/debian/dists/any-version/InRelease' | \
        tee /etc/apt/sources.list.d/caddy-stable.list >/dev/null
    sed -i 's|^deb |deb [signed-by=/usr/share/keyrings/caddy-stable-archive-keyring.gpg] |' \
        /etc/apt/sources.list.d/caddy-stable.list
    apt-get update -qq
    apt-get install -y -qq caddy
    ok "Caddy installé : $(caddy version)"
fi

# ---------- 4. PostgreSQL 16 + Redis 7 -------------------------------------
log "=== 4/6 — PostgreSQL 16 + Redis 7 ==="
if command -v psql >/dev/null 2>&1; then
    ok "PostgreSQL déjà installé : $(psql --version)"
else
    apt-get install -y -qq postgresql postgresql-contrib
    ok "PostgreSQL installé : $(psql --version)"
fi
if command -v redis-server >/dev/null 2>&1; then
    ok "Redis déjà installé : $(redis-server --version)"
else
    apt-get install -y -qq redis-server
    ok "Redis installé : $(redis-server --version)"
fi

# ---------- 5. Arborescence applicative ------------------------------------
log "=== 5/6 — Arborescence /srv/apps + /opt/backups ==="
mkdir -p /srv/apps /opt/backups /etc/caddy/sites-enabled
chown -R younes:younes /srv/apps
chmod 755 /opt/backups /etc/caddy/sites-enabled
ok "/srv/apps, /opt/backups créés"

# Caddyfile par défaut — proxy_pass vers rien pour l'instant
cat > /etc/caddy/Caddyfile <<'CADDY'
# Caddyfile global — voir /etc/caddy/sites-enabled/*.caddy
{
    # Email pour Let's Encrypt quand un domaine sera ajouté
    # email younes@example.com
    admin localhost:2019
}
import /etc/caddy/sites-enabled/*.caddy
CADDY
ok "Caddyfile par défaut écrit"

# ---------- 6. Activation services ------------------------------------------
log "=== 6/6 — Activation services ==="
systemctl enable --now postgresql redis-server caddy
ok "postgresql + redis-server + caddy activés au boot"

# ---------- 7. Ouvrir les ports standards dans UFW --------------------------
log "=== Bonus — Ouverture ports applicatifs dans UFW ==="
for port in 80/tcp 443/tcp; do
    sudo -n ufw allow "$port" 2>/dev/null && ok "UFW: $port autorisé" || warn "UFW $port: déjà ouvert ou erreur"
done

# ---------- Résumé --------------------------------------------------------
printf '\n%b═══════════════════════════════════════════════════════%b\n' "${GREEN}" "${NC}"
printf '%b INSTALLATION TERMINÉE%b\n' "${GREEN}" "${NC}"
printf '%b═══════════════════════════════════════════════════════%b\n' "${GREEN}" "${NC}"
echo
echo "Versions installées :"
echo "  Docker       : $(docker --version 2>&1 | head -1)"
echo "  Compose      : $(docker compose version 2>&1 | head -1)"
echo "  Node.js      : $(node --version 2>&1)"
echo "  npm          : $(npm --version 2>&1)"
echo "  Caddy        : $(caddy version 2>&1 | head -1)"
echo "  PostgreSQL   : $(psql --version 2>&1)"
echo "  Redis        : $(redis-server --version 2>&1)"
echo
echo "Ports UFW ouverts : 22 (ssh), 80 (http), 443 (https)"
echo
echo "Prochaines étapes :"
echo "  • Déployer une app dans /srv/apps/<nom>/"
echo "  • Créer un vhost Caddy dans /etc/caddy/sites-enabled/<nom>.caddy"
echo "  • Ajouter un domaine pointant vers 169.58.30.70 quand prêt"
echo "  • Pour PostgreSQL : sudo -u postgres createuser -s younes"
