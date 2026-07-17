#!/usr/bin/env bash
# ============================================================================
# test-connection.sh — Vérifie la connectivité SSH vers ProdServeur
# ----------------------------------------------------------------------------
# Couvre : DNS/réseau, host key, auth par clé, exécution d'une commande.
# Exit code 0 si tout est OK, 1 sinon.
# Usage :
#   ./scripts/test-connection.sh
#   ./scripts/test-connection.sh --verbose   # ajoute -vvv sur ssh
# ============================================================================
set -euo pipefail

HOST="${HOST:-169.58.30.70}"
USER_REMOTE="${USER_REMOTE:-younes}"
PRIV_KEY="${PRIV_KEY:-${HOME}/.ssh/id_smartserveur}"
VERBOSE=""
[[ "${1:-}" == "--verbose" ]] && VERBOSE="-vvv"

RED=$'\e[31m'; GREEN=$'\e[32m'; YELLOW=$'\e[33m'; BLUE=$'\e[34m'; NC=$'\e[0m'

step() { printf '\n%b== %s ==%b\n' "${BLUE}" "$*" "${NC}"; }
ok()   { printf '%b✓%b %s\n' "${GREEN}" "${NC}" "$*"; }
fail() { printf '%b✗%b %s\n' "${RED}"   "${NC}" "$*" >&2; exit 1; }
warn() { printf '%b!%b %s\n' "${YELLOW}" "${NC}" "$*"; }

# ---------- 1. Réseau -------------------------------------------------------
step "1/4 — Connectivité réseau (${HOST}:22)"
if nc -z -w 5 "${HOST}" 22; then
    ok "Port 22 ouvert"
else
    fail "Port 22 inaccessible. Vérifie : ping ${HOST}, firewall local, statut VPS dans le panel."
fi

# ---------- 2. Host key -----------------------------------------------------
step "2/4 — Host key dans known_hosts"
FINGERPRINT="$(ssh-keyscan -t ed25519 -T 5 "${HOST}" 2>/dev/null | ssh-keygen -lf - 2>/dev/null || true)"
if [[ -z "${FINGERPRINT}" ]]; then
    fail "Impossible de récupérer la host key du serveur."
fi
ok "Host key : ${FINGERPRINT}"

if grep -q "${HOST}" "${HOME}/.ssh/known_hosts" 2>/dev/null; then
    ok "Hôte déjà connu de known_hosts"
else
    warn "Hôte absent de known_hosts — la 1re connexion l'ajoutera automatiquement."
fi

# ---------- 3. Auth par clé -------------------------------------------------
step "3/4 — Authentification par clé (${PRIV_KEY})"
if [[ ! -f "${PRIV_KEY}" ]]; then
    fail "Clé privée introuvable : ${PRIV_KEY}"
fi
PRIV_FP="$(ssh-keygen -lf "${PRIV_KEY}" | awk '{print $2}')"
ok "Clé locale : ${PRIV_FP}"

if ssh ${VERBOSE} -o BatchMode=yes -o ConnectTimeout=8 \
        -o IdentitiesOnly=yes -i "${PRIV_KEY}" \
        "${USER_REMOTE}@${HOST}" 'whoami' 2>/dev/null; then
    ok "Authentification réussie"
else
    fail "Authentification refusée. Lance : ./scripts/bootstrap.sh"
fi

# ---------- 4. Commande distante --------------------------------------------
step "4/4 — Test fonctionnel (commande distante)"
RESULT="$(ssh -o BatchMode=yes -o ConnectTimeout=8 \
        -i "${PRIV_KEY}" "${USER_REMOTE}@${HOST}" \
        'echo "OK $(whoami) @ $(hostname)"; uname -r; uptime' 2>/dev/null)"
echo "${RESULT}"
ok "Commande exécutée avec succès"

printf '\n%bTous les tests sont passés ✅%b\n' "${GREEN}" "${NC}"
echo "Tu peux maintenant utiliser : ssh prodserveur"
