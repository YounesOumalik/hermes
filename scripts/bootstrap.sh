#!/usr/bin/env bash
# ============================================================================
# bootstrap.sh — Amorçage SSH du ProdServeur (vmi3445841 / 169.58.30.70)
# ----------------------------------------------------------------------------
# Contexte : nouveau VPS Contabo Cloud VPS 4 (2026), provisionné "sans config".
# Aucune clé publique pré-injectée. Ce script couvre 2 scénarios :
#   (A) Connexion root ou user avec mot de passe du panel Contabo
#       → on injecte la clé publique locale id_smartserveur.pub.
#   (B) Le panel refuse d'exposer un user sshable (rare) → on affiche la clé
#       à copier-coller dans l'onglet "SSH-Key" du panel.
#
# Usage :
#   ./scripts/bootstrap.sh                    # affiche la clé à coller (mode B)
#   SSH_PASSWORD='xxx' ./scripts/bootstrap.sh # injecte via sshpass (mode A)
#
# Pré-requis : sshpass installé pour le mode A.
#   sudo apt install -y sshpass
# ============================================================================
set -euo pipefail

# ---------- Config ----------------------------------------------------------
HOST="169.58.30.70"
HOST_ALIAS="prodserveur"
USER_REMOTE="younes"
USER_ROOT="root"
PUB_KEY_PATH="${HOME}/.ssh/id_smartserveur.pub"
SSH_CONFIG="${HOME}/.ssh/config"

# Couleurs
RED=$'\e[31m'; GREEN=$'\e[32m'; YELLOW=$'\e[33m'; BLUE=$'\e[34m'; NC=$'\e[0m'

log()  { printf '%b[bootstrap]%b %s\n' "${BLUE}" "${NC}" "$*"; }
ok()   { printf '%b[  ok    ]%b %s\n' "${GREEN}" "${NC}" "$*"; }
warn() { printf '%b[  warn  ]%b %s\n' "${YELLOW}" "${NC}" "$*"; }
err()  { printf '%b[ error  ]%b %s\n' "${RED}"    "${NC}" "$*" >&2; }

# ---------- Sanity checks ---------------------------------------------------
if [[ ! -f "${PUB_KEY_PATH}" ]]; then
    err "Clé publique introuvable : ${PUB_KEY_PATH}"
    err "Régénère-la : ssh-keygen -t ed25519 -C 'prodserveur' -f ~/.ssh/id_smartserveur -N ''"
    exit 1
fi

PUB_KEY="$(cat "${PUB_KEY_PATH}")"
PUB_FP="$(ssh-keygen -lf "${PUB_KEY_PATH}" | awk '{print $2}')"

log "Hôte cible     : ${HOST} (alias SSH: ${HOST_ALIAS})"
log "User distant   : ${USER_REMOTE}"
log "Clé publique   : ${PUB_KEY_PATH}"
log "Fingerprint    : ${PUB_FP}"
echo

# ---------- Étape 1 : s'assurer que l'alias SSH existe ----------------------
if ! grep -qE "^Host[[:space:]]+${HOST_ALIAS}\b" "${SSH_CONFIG}" 2>/dev/null; then
    warn "Alias '${HOST_ALIAS}' absent de ${SSH_CONFIG} — ajoute-le (voir HANDOVER.md §3)."
else
    ok "Alias '${HOST_ALIAS}' déjà présent dans ${SSH_CONFIG}"
fi

# ---------- Étape 2 : tester la connectivité --------------------------------
log "Test réseau (ping + port 22)…"
if ! nc -z -w 5 "${HOST}" 22 2>/dev/null; then
    err "Port 22 inaccessible sur ${HOST}. Vérifie ton pare-feu ou celui du panel."
    exit 1
fi
ok "Port 22 ouvert sur ${HOST}"

# ---------- Étape 3 : tester l'auth par clé ---------------------------------
log "Test auth par clé publique…"
if ssh -o BatchMode=yes -o ConnectTimeout=8 \
        -o IdentitiesOnly=yes -i "${PUB_KEY_PATH%.pub}" \
        "${USER_REMOTE}@${HOST}" 'echo OK' 2>/dev/null; then
    ok "Auth par clé déjà fonctionnelle — rien à faire."
    exit 0
fi
warn "Auth par clé refusée — la clé n'est pas encore côté serveur."

# ---------- Étape 4 : choisir le mode d'injection ----------------------------
echo
printf '%bMode d'\''injection :%b\n' "${YELLOW}" "${NC}"
echo "  (A) Via sshpass (tu connais le mot de passe root ou younes du panel)"
echo "  (B) Manuel : copier la clé dans l'onglet SSH-Key du panel Contabo"
echo

if [[ -n "${SSH_PASSWORD:-}" ]] && command -v sshpass >/dev/null 2>&1; then
    log "Mode A — injection via sshpass (user=${USER_REMOTE})"
    # Tente d'abord avec younes, sinon root
    TARGET_USER="${USER_REMOTE}"
    if ! sshpass -p "${SSH_PASSWORD}" \
            ssh -o StrictHostKeyChecking=accept-new -o ConnectTimeout=8 \
                "${TARGET_USER}@${HOST}" 'whoami' >/dev/null 2>&1; then
        warn "Login '${USER_REMOTE}' échoué — tentative avec root…"
        TARGET_USER="${USER_ROOT}"
        sshpass -p "${SSH_PASSWORD}" \
            ssh -o StrictHostKeyChecking=accept-new -o ConnectTimeout=8 \
                "${TARGET_USER}@${HOST}" 'whoami' >/dev/null
    fi

    INJECT_CMD=$(cat <<EOF
set -e
mkdir -p /home/${USER_REMOTE}/.ssh
chmod 700 /home/${USER_REMOTE}/.ssh
echo '${PUB_KEY}' >> /home/${USER_REMOTE}/.ssh/authorized_keys
chmod 600 /home/${USER_REMOTE}/.ssh/authorized_keys
if id ${USER_REMOTE} >/dev/null 2>&1; then
  chown -R ${USER_REMOTE}:${USER_REMOTE} /home/${USER_REMOTE}/.ssh
fi
echo 'INJECTION_OK'
EOF
)
    sshpass -p "${SSH_PASSWORD}" \
        ssh -o StrictHostKeyChecking=accept-new "${TARGET_USER}@${HOST}" "${INJECT_CMD}"
    ok "Clé injectée. Test immédiat…"
    sleep 1
    if ssh -o BatchMode=yes -o ConnectTimeout=8 "${USER_REMOTE}@${HOST}" 'whoami'; then
        ok "Auth par clé opérationnelle pour ${USER_REMOTE}@${HOST}."
        exit 0
    fi
    err "L'injection a réussi mais l'auth échoue. Vérifie les logs : ssh -vvv ${USER_REMOTE}@${HOST}"
    exit 1
fi

# ---------- Mode B : affichage pour copier-coller ---------------------------
log "Mode B — copie cette clé dans le panel Contabo :"
echo "------------------------------------------------------------"
printf '%b%s%b\n' "${GREEN}" "${PUB_KEY}" "${NC}"
echo "------------------------------------------------------------"
echo
echo "Étapes Contabo :"
echo "  1. Ouvre le panel Contabo → 'Serveurs & Hébergement'"
echo "  2. Clique sur vmi3445841 (ProdServeur) → 'Réinitialiser les informations'"
echo "  3. Onglet 'SSH-Key' (à droite de 'Mot de passe')"
echo "  4. Colle la clé ci-dessus → 'Réinitialiser les informations d'identification'"
echo "  5. Attends ~30s puis relance : ./scripts/bootstrap.sh"
echo
warn "Astuce : pour automatiser plus tard, installe sshpass et utilise :"
warn "  SSH_PASSWORD='ton_mdp_panel' ./scripts/bootstrap.sh"
