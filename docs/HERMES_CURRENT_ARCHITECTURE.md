# Hermes — Architecture actuelle (snapshot 2026-07-19)

> Document de référence capturant l'état **AVANT** les modifications Hermes OS 4 couches.
> Généré lors de la Phase 0 du plan d'implémentation.

---

## 1. Infrastructure

| Élément | Valeur |
|---|---|
| Provider | Contabo Cloud VPS 4 (2026) |
| Hostname | `vmi3445841.contaboserver.net` |
| IP publique | `169.58.30.70` |
| OS | Ubuntu 24.04.4 LTS (Noble) — kernel `6.8.0-134-generic` |
| RAM totale | 7.8 GiB |
| Disque | `/dev/sda1` 96 GiB (~17% used) |
| Docker | 29.6.1 |
| Docker Compose | 5.3.1 |
| Node (host) | 22.23.1 LTS (NodeSource) |
| Python (host) | N/A |
| Reverse proxy | Caddy 2.11.4 |
| Firewall | UFW (actif) |
| SSL | Let's Encrypt via Caddy auto-HTTPS |
| Domaine | `hermes.eaumalik.com` (DNS → 169.58.30.70) |

## 2. Services (containers Docker)

| Service | Container | Port interne | Port externe | Domaine | Health | Dépendances |
|---|---|---|---|---|---|---|
| Hermes Studio | `hermes-studio` | 3000 | `0.0.0.0:3000` | `hermes.eaumalik.com` | ✅ healthy (2h) | hermes-daemon |
| Hermes Daemon | `hermes-daemon` | 8001 | `0.0.0.0:8001` | — (interne) | ✅ healthy (2h) | — |
| n8n | `n8n` | 5678 | `127.0.0.1:5678` | — (interne) | ✅ healthy (37h) | — |
| MCP Server | `mcp-server` | 3100 | `127.0.0.1:3100` | — (interne) | ✅ healthy (2h) | — |

**Total : 4 containers, tous healthy.**

### Images Docker

| Image | Tag | Taille |
|---|---|---|
| `repo-hermes-studio` | latest | 1.66 GB |
| `repo-hermes-daemon` | latest | 604 MB |
| `repo-mcp-server` | latest | 580 MB |
| `docker.n8n.io/n8nio/n8n` | latest | 2.47 GB |
| `hello-world` | latest | 26 KB (à nettoyer) |

### Volumes

- `repo_hermes_data` → `/data` dans hermes-daemon (persiste `/data/hermes.env`)
- `repo_n8n_data` → `/home/node/.n8n` dans n8n
- `repo_mcp_workspace` → `/workspace` dans mcp-server

### Réseaux

- `orchestration-net` (bridge, externe) — utilisé par les 4 services
- `bridge`, `host`, `none` — défaut Docker

## 3. Reverse proxy — Caddy

Vhost actif `/etc/caddy/sites-enabled/hermes.caddy` :

```caddy
hermes.eaumalik.com {
    encode zstd gzip

    # Webhook GitHub (port 9000)
    reverse_proxy /webhook 127.0.0.1:9000
    reverse_proxy /health 127.0.0.1:9000

    # Hermes Studio (port 3000)
    reverse_proxy 127.0.0.1:3000 {
        header_up Host {host}
        header_up X-Real-IP {remote_host}
    }
}
```

Caddy admin API : `127.0.0.1:2019`.

## 4. Data layer

### Postgres 16.14

- Service systemd : `postgresql` (actif)
- `listen_addresses = '*'` ⚠️ **écoute sur toutes les interfaces**
- UFW ouvre `5432/tcp` publiquement ⚠️ **exposition publique confirmée**
- DB existante : `hermes` (owner `postgres`)
- Pas encore de user `hermes_app` limité

### Redis 7.0.15

- Service systemd : `redis-server` (actif)
- `bind 127.0.0.1` ✅ loopback only
- `redis-cli ping` → `PONG` ✅

## 5. Firewall (UFW)

```
Status: active

22/tcp        ALLOW    Anywhere              # SSH
80/tcp        ALLOW    Anywhere              # HTTP → Caddy
443/tcp       ALLOW    Anywhere              # HTTPS → Caddy
5432/tcp      ALLOW    Anywhere              # PostgreSQL ⚠️
3000/tcp      ALLOW    Anywhere              # Hermes Studio (devrait être localhost)
5678/tcp      ALLOW    Anywhere              # n8n (devrait être localhost)
8000/tcp      ALLOW    Anywhere              # rien n'écoute ⚠️ port fantôme
```

**Failles identifiées** :
1. 5432 mondial (Postgres)
2. 3000/5678/8000 mondial (Caddy proxie déjà tout)
3. 8000 : aucun service n'écoute

## 6. Variables d'environnement (`/opt/hermes-orchestration/.env`)

Noms des variables (valeurs jamais listées) :

```
ALLOWED_CHAT_ID              (DOUBLON)
GITHUB_TOKEN                 (DOUBLON)
HERMES_ADMIN_PASSWORD_HASH
HERMES_JWT_SECRET
HERMES_SESSION_SECRET
MCP_AUTH_TOKEN
MINIMAX_API_KEY              (DOUBLON)
MINIMAX_MODEL
POSTGRES_DB
POSTGRES_PASSWORD
POSTGRES_USER
REDIS_PASSWORD
TELEGRAM_BOT_TOKEN           (DOUBLON)
```

**Bug confirmé** : 4 variables en double → le deploy script `set -u` casse sur les lignes dupliquées.

## 7. CI/CD — Webhook deploy

- Service systemd : `hermes-webhook.service` (port 9000, user younes)
- Log : `/var/log/hermes-webhook.log`
- Logs deploy : `/var/log/hermes-orchestration-deploy/deploy-YYYYMMDD-HHMMSS.log`
- **Bug actuel** : deploy cassé sur `unbound variable Q9j9Kw_BHPIrqtK7sMmDqQ` (ligne 40 du .env) → depuis 2026-07-18 23:24
- Tentatives récentes : `df15b32 exit=1` (échec)

## 8. Intelligence artificielle

| Provider | Configuré | Endpoint | Modèles |
|---|---|---|---|
| MiniMax | ⚠️ (doublon .env, valeur active = placeholder) | `https://api.minimax.chat/v1` | `abab6.5s-chat` (default) |
| OpenAI | ❌ | — | — |
| Anthropic | ❌ | — | — |
| Gemini | ❌ | — | — |
| OpenRouter | ❌ | — | — |
| Ollama | ❌ | — | — |

`providerConfigured` lu via `/api/settings/status` du daemon (probablement `false` pour tous à cause du placeholder actif).

## 9. APIs Hermes disponibles (daemon)

| Endpoint | Méthode | Auth | Notes |
|---|---|---|---|
| `/` | GET | none | `{"message": "Hermes Daemon API"}` |
| `/health` | GET | none | `{"status": "ok", ...}` |
| `/api/chat` | POST | bearer | **Non-streaming** (UI attend SSE `/api/chat/stream`) |
| `/api/agents` | GET/POST/DELETE | bearer | Pas de PUT (UI le demande) |
| `/api/tools` | GET | bearer | 3 outils hardcodés (manque `mcp_terminal`) |
| `/api/tools/call` | POST | bearer | Dispatch MCP + n8n |
| `/api/settings/status` | GET | none | Status providers |
| `/api/settings/update` | POST | bearer | Écrit `/data/hermes.env` (reload = restart) |
| `/api/settings/test/minimax` | POST | bearer | Ping Minimax |

## 10. Outils MCP exposés

| Tool | Opérations | Confirmation requise |
|---|---|---|
| `mcp_filesystem` | read, write, list, delete | write/delete (`confirmed: true`) |
| `mcp_github` | list_repos, read_file, create_pr, search_code | create_pr (`confirmed: true`) |
| `mcp_terminal` | 18 commandes whitelist (ls, git, npm…) | commandes sensibles (`confirmed: true`) |

## 11. Points de vigilance

1. **Webhook deploy cassé** depuis 2026-07-18 23:24 → push main ne déploie plus
2. **`.env` doublons** → intégrations silencieusement KO
3. **Postgres exposé publiquement** (5432 mondial)
4. **Ports 3000/5678/8000 mondial** sans raison (Caddy proxie déjà)
5. **Pas de backups automatisés** (cron absent, scripts backup absents)
6. **Pas de monitoring externe** (uniquement healthchecks Docker internes)
7. **`next.config.js` hardcode IP `169.58.30.70:8001`** au lieu du hostname docker `hermes-daemon:8001`
8. **DB `hermes` existe déjà** (owner `postgres`) → utilisable, mais créer user `hermes_app` limité avant
9. **`requires_confirmation` retourne HTTP 200** (pattern à préserver côté Core)
10. **`smartefp` encore référencé** dans 3 fichiers (compose:94, layout:7, PWA_MOBILE.md:138,172)

## 12. URLs actives

| URL | Service |
|---|---|
| `https://hermes.eaumalik.com/` | Hermes Studio UI |
| `https://hermes.eaumalik.com/webhook` | GitHub webhook receiver |
| `https://hermes.eaumalik.com/health` | Webhook health |
| `http://127.0.0.1:3000/login` | Hermes Studio (loopback) |
| `http://127.0.0.1:5678` | n8n UI (loopback) |
| `http://127.0.0.1:3100/health` | MCP server (loopback) |
| `http://127.0.0.1:8001/health` | Hermes daemon (loopback) |
| `http://127.0.0.1:8001/docs` | FastAPI OpenAPI (loopback) |

## 13. Backups effectués (Phase 0)

| Fichier | Taille | Date |
|---|---|---|
| `/opt/backups/env-2026-07-19.bak` | 2.0 KB | 2026-07-19 |
| `/opt/backups/deploy-on-push-2026-07-19.sh` | 4.3 KB | 2026-07-19 |
| `/opt/backups/caddy-sites-2026-07-19/` | (dir) | 2026-07-19 |
| `/opt/backups/hermes_data-2026-07-19.tgz` | 11 KB | 2026-07-19 |
| `/opt/backups/n8n_data-2026-07-19.tgz` | 406 B | 2026-07-19 |
| `/opt/backups/mcp_workspace-2026-07-19.tgz` | 87 B | 2026-07-19 |

Branche git créée : `feature/hermes-os-4layers` (pushée sur `origin`).