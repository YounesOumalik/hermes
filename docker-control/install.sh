#!/usr/bin/env bash
# ============================================================================
# install.sh — Installe docker-control sur le VPS
#
# Usage :
#   ./docker-control/install.sh             # depuis le VPS
#   ./docker-control/install.sh --remote    # depuis le poste local
#
# Crée :
#   - /opt/agentai/docker-control/ (code + venv)
#   - /opt/agentai/docker-control/.env (DOCKER_CONTROL_TOKEN)
#   - /etc/systemd/system/docker-control.service (systemd unit)
#   - Caddy reverse_proxy /api/control/* → 127.0.0.1:9100
# ============================================================================
set -euo pipefail

APP_DIR="/opt/agentai/docker-control"
SERVICE_FILE="/etc/systemd/system/docker-control.service"
SERVICE_USER="${SUDO_USER:-younes}"
VPS_HOST="${VPS_HOST:-prodserveur}"
REMOTE=false

[[ "${1:-}" == "--remote" ]] && REMOTE=true

if $REMOTE; then
  ssh_run() { ssh "$VPS_HOST" "$@"; }
  scp_put() { scp -q "$1" "$VPS_HOST:$2"; }
  echo "→ Installation à distance sur $VPS_HOST"
else
  ssh_run() { bash -c "$@"; }
  scp_put() { cp "$1" "$2"; }
  [[ $(id -u) -eq 0 ]] || { echo "❌ Lance en sudo ou utilise --remote"; exit 1; }
fi

# ---------- 1. Dossiers ------------------------------------------------------
ssh_run "mkdir -p $APP_DIR && chown -R $SERVICE_USER:$SERVICE_USER $APP_DIR"

# ---------- 2. Code + venv --------------------------------------------------
scp_put "$(dirname "$0")/main.py" "$APP_DIR/main.py"
scp_put "$(dirname "$0")/requirements.txt" "$APP_DIR/requirements.txt"
ssh_run "cd $APP_DIR && python3 -m venv venv && venv/bin/pip install --quiet --no-cache-dir -r requirements.txt"

# ---------- 3. Token --------------------------------------------------------
if ! ssh_run "[ -f $APP_DIR/.env ]"; then
  TOKEN=$(head -c 32 /dev/urandom | base64 | tr -d '/+=' | head -c 48)
  ssh_run "cat > $APP_DIR/.env <<EOF
DOCKER_CONTROL_TOKEN=$TOKEN
EOF
chmod 600 $APP_DIR/.env && chown $SERVICE_USER:$SERVICE_USER $APP_DIR/.env"
  echo "→ Token généré : $TOKEN"
  echo "  (copie-le pour configurer le tool Open WebUI plus tard)"
else
  echo "→ Token déjà existant : $APP_DIR/.env (préservé)"
fi

# ---------- 4. Systemd service ----------------------------------------------
ssh_run "cat > $SERVICE_FILE <<'EOF'
[Unit]
Description=docker-control mini-API for Open WebUI
After=docker.service
Requires=docker.service

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$APP_DIR
EnvironmentFile=$APP_DIR/.env
ExecStart=$APP_DIR/venv/bin/uvicorn main:app --host 127.0.0.1 --port 9100 --workers 1
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF"

# ---------- 5. Activation ---------------------------------------------------
ssh_run "systemctl daemon-reload && systemctl enable docker-control && systemctl restart docker-control"
sleep 2
ssh_run "systemctl status docker-control --no-pager" | head -15

# ---------- 6. Caddy reverse proxy -----------------------------------------
CADDY_FILE="/etc/caddy/sites-enabled/agentai-control.caddy"
if ! ssh_run "[ -f $CADDY_FILE ]"; then
  ssh_run "cat > $CADDY_FILE <<'EOF'
agentai.smartefp.com {
    @control path /api/control/*
    handle @control {
        reverse_proxy 127.0.0.1:9100
    }
    handle {
        reverse_proxy 127.0.0.1:3000
    }
}
EOF
caddy reload --config /etc/caddy/Caddyfile" 2>&1 | tail -3
fi

echo ""
echo "✅ docker-control installé"
echo ""
echo "Test :"
echo "  curl -H 'Authorization: Bearer \$DOCKER_CONTROL_TOKEN' \\"
echo "       https://agentai.smartefp.com/api/control/health"
echo ""
echo "Token (sur le VPS) :"
ssh_run "cat $APP_DIR/.env"