# Configuration Coolify — Stack d'orchestration

> **Méthode recommandée** : Le déploiement via webhook GitHub ([`infra/webhook/`](../infra/webhook/)) est la méthode
> principale (pattern eaumalik.com). Coolify est une alternative pour ceux qui préfèrent une interface graphique.

Ce guide décrit comment configurer Coolify pour déployer la stack Hermes + n8n + MCP sur le VPS ProdServeur.

## Prérequis

- Coolify installé (voir `scripts/setup-orchestration.sh`)
- Accès à l'interface Coolify sur `http://169.58.30.70:8000`
- Le dépôt GitHub contenant ce projet est clonable par Coolify

---

## Étape 1 — Créer le compte admin

1. Ouvre `http://169.58.30.70:8000`
2. Remplis le formulaire de création du premier utilisateur admin
3. ⚠️ **Sécurise immédiatement** — quelqu'un d'autre pourrait prendre le contrôle sinon

---

## Étape 2 — Ajouter le serveur

1. Dans le menu de gauche → **Servers**
2. Clique **Add Server** → sélectionne **localhost** (le serveur actuel)
4. Coolify va générer une clé SSH et l'ajouter à `~/.ssh/authorized_keys`
5. Le serveur apparaît comme "Ready"

---

## Étape 3 — Créer le projet

1. Menu → **Projects** → **Add Project**
2. Nom : `Orchestration`
3. Type : **Production**
4. Clique **Save**

---

## Étape 4 — Ajouter la ressource Docker Compose

1. Dans le projet `Orchestration` → **Add Resource** → **Docker Compose**
2. Configuration :
   - **Name** : `hermes-orchestration`
   - **Source** : Git Repository
   - **Repository** : `https://github.com/<TON_USER>/ProdServeur`
   - **Branch** : `main`
   - **Docker Compose Location** : `/docker-compose.yml` (à la racine du repo)
   - **Docker Compose File** : laisse le défaut (docker-compose.yml)
3. Clique **Continue**

---

## Étape 5 — Configurer les variables d'environnement

Dans l'onglet **Environment Variables** de la ressource :

| Variable | Valeur | Secret |
|---|---|---|
| `MINIMAX_API_KEY` | `MiniMax-xxx` | ✅ |
| `TELEGRAM_BOT_TOKEN` | `123456:ABC-DEF` | ✅ |
| `ALLOWED_CHAT_ID` | `-1001234567890` | ✅ |
| `GITHUB_TOKEN` | `ghp_xxx` | ✅ |
| `N8N_ENCRYPTION_KEY` | (généré par `generate-secrets.sh`) | ✅ |
| `HERMES_JWT_SECRET` | (généré) | ✅ |
| `MCP_AUTH_TOKEN` | (généré) | ✅ |
| `POSTGRES_PASSWORD` | (généré) | ✅ |
| `POSTGRES_USER` | `younes` | ❌ |
| `POSTGRES_DB` | `hermes` | ❌ |

> 💡 Utilise le bouton "Generate" de Coolify pour les secrets, ou copie les valeurs de `/srv/apps/orchestration/.env`

---

## Étape 6 — Configurer le déploiement automatique (webhook)

1. Onglet **Webhooks** de la ressource
2. Clique **Generate Webhook URL** → copie l'URL
3. Sur GitHub → Settings → Webhooks → **Add webhook**
   - **Payload URL** : l'URL copiée
   - **Content type** : `application/json`
   - **Events** : sélectionne "Push"
4. Clique **Add webhook**

Désormais, chaque `git push origin main` déclenche un redéploiement automatique.

---

## Étape 7 — Déployer

1. Clique **Deploy** en haut à droite de la ressource
2. Surveille les logs dans l'onglet **Logs**
3. Une fois "Running", vérifie :
   - `http://169.58.30.70:3000` → Hermes Studio
   - `http://169.58.30.70:5678` → n8n
   - `http://169.58.30.70:8001/health` → Hermes Daemon

---

## Étape 8 — Exposer via domaine (optionnel)

Si tu as un domaine pointant vers `169.58.30.70` :

1. Dans Coolify, ajoute un **Domain** à la ressource (ex: `hermes.tondomaine.com`)
2. Coolify génère automatiquement un certificat SSL via Traefik
3. Répète pour `n8n.tondomaine.com`

> ⚠️ Caddy et Traefik (Coolify) partagent les ports 80/443. Si tu veux utiliser Caddy pour le reverse proxy à la place, désactive le proxy Traefik de Coolify dans les settings serveur.

---

## Dépannage

| Symptôme | Cause probable | Solution |
|---|---|---|
| Coolify inaccessible sur :8000 | UFW bloque le port | `sudo ufw allow 8000/tcp` |
| n8n ne démarre pas | PostgreSQL natif inaccessible | Vérifie `host.docker.internal` + user/password |
| Hermes Daemon 401 | JWT secret mal configuré | Régénère `HERMES_JWT_SECRET` |
| MCP Server 403 | Token incorrect | Vérifie `MCP_AUTH_TOKEN` dans `.env` |
| Build échoue (Next.js) | Mémoire insuffisante | Augmente la limite RAM dans Coolify |
