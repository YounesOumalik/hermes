# ProdServeur

Hébergement du **nouveau VPS de production** Contabo (vmi3445841, IP `169.58.30.70`).

## Quick-start

```bash
# 1. Injecter la clé publique (si pas déjà fait)
./scripts/bootstrap.sh

# 2. Vérifier que la connexion marche
./scripts/test-connection.sh

# 3. Une fois opérationnel, se connecter en une commande
ssh prodserveur
```

## Sommaire

- [HANDOVER.md](./HANDOVER.md) — Procédure complète d'amorçage SSH, hardening, stack applicative, troubleshooting.
- [`scripts/bootstrap.sh`](./scripts/bootstrap.sh) — Injecte `id_smartserveur.pub` sur le serveur (mode auto sshpass ou mode manuel).
- [`scripts/test-connection.sh`](./scripts/test-connection.sh) — 4 vérifs : réseau, host key, auth par clé, commande distante.
- [`scripts/inventory.sh`](./scripts/inventory.sh) — Diagnostic complet du serveur (10 sections : ressources, réseau, apps, services…).
- [`scripts/install-base-stack.sh`](./scripts/install-base-stack.sh) — Script idempotent d'installation de la stack (Docker, Node, Caddy, Postgres, Redis).
- [`scripts/setup-orchestration.sh`](./scripts/setup-orchestration.sh) — Préparation VPS pour la stack d'orchestration (Coolify + UFW + arborescence).
- [`scripts/generate-secrets.sh`](./scripts/generate-secrets.sh) — Génération des secrets dans `.env`.
- [`docker-compose.yml`](./docker-compose.yml) — Stack d'orchestration (Hermes Daemon, Hermes Studio, n8n, MCP-Server).
- [`docs/COOLIFY_SETUP.md`](./docs/COOLIFY_SETUP.md) — Guide de configuration Coolify.
- [`infra/webhook/`](./infra/webhook/) — Déploiement auto via webhook GitHub (pattern eaumalik.com).

## Stack d'orchestration multi-agents

Une stack complète d'orchestration IA est déployable sur ce VPS :

| Service | Port | Rôle |
|---|---|---|
| Hermes Daemon | 8001 | Backend agent IA (FastAPI + Minimax) |
| Hermes Studio | 3000 | Interface graphique (Next.js) |
| n8n | 5678 | Moteur d'automatisation |
| MCP-Server | 3100 | Serveur Model Context Protocol (filesystem + GitHub) |

### 🚀 Déploiement auto (webhook) — recommandé

Même pattern que `eaumalik.com` : `git push main` → déploiement en 1-3 min.

```bash
# 1. Depuis le poste local — installer le webhook sur le VPS
./infra/webhook/install-webhook.sh --remote --repo https://github.com/<TON_USER>/ProdServeur.git

# 2. Copier le secret HMAC affiché → GitHub Settings → Webhooks
#    URL: https://<TON_DOMAINE>/webhook
#    Content type: application/json
#    Events: push

# 3. Premier déploiement manuel (ou laisser le webhook faire)
ssh prodserveur
cd /opt/hermes-orchestration/repo
source /opt/hermes-orchestration/.env
docker compose -f docker-compose.yml up -d --build

# 4. Vérifier
curl http://localhost:3000   # Hermes Studio
curl http://localhost:5678   # n8n
curl http://localhost:8001/health  # Hermes Daemon

# 5. Désormais, chaque git push origin main → redéploiement auto
```

**Architecture :**

```
Utilisateur → (Telegram/n8n) → Hermes (Minimax) → (Actions/MCP/n8n) → Résultat
```

## État actuel (au 2026-07-16)

- ✅ Auth SSH par clé **opérationnelle** : `ssh prodserveur`
- ✅ Réseau joignable (port 22 ouvert, ping OK, latence ~75 ms)
- ✅ Alias `prodserveur` dans `~/.ssh/config` (HostName `169.58.30.70`, clé `id_smartserveur`)
- ✅ User `younes` créé + clé injectée + sudo activé
- ✅ Host key enregistrée dans `~/.ssh/known_hosts`
- ⏳ Hardening restant : sudo NOPASSWD, désactivation password auth, UFW, fail2ban (voir `HANDOVER.md` §7)
test 1784292308
