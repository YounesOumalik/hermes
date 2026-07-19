# AgentAI — Multi-Agent Workspace

Stack de production pour la plateforme SaaS multi-tenant **AgentAI** (ex-Hermes Nebula), déployée sur VPS Contabo (`169.58.30.70`) et exposée via `https://agentai.smartefp.com`.

> 📋 Audit complet et plan de nettoyage disponibles dans [`docs/AUDIT_2026-07-19.md`](./docs/AUDIT_2026-07-19.md).

## Architecture (3 services buildés + 2 services managés)

```
                    ┌─────────────────────────────────────┐
                    │  agentai.smartefp.com (Caddy + TLS) │
                    └──────────────┬──────────────────────┘
                                   │
                ┌──────────────────┴──────────────────┐
                │                                     │
        ┌───────▼────────┐                  ┌─────────▼────────┐
        │ agentai-frontend│                  │   /api/* (Caddy  │
        │ Next.js 15      │                  │   strip /api)    │
        │ :3000           │                  └─────────┬────────┘
        └─────────────────┘                            │
                                              ┌───────▼────────┐
                                              │  agentai-api   │
                                              │  FastAPI       │
                                              │  :8000         │
                                              └───┬──────┬─────┘
                              ┌───────────────────┘      └─────────────┐
                       ┌──────▼──────┐  ┌──────────▼─────┐  ┌──────────▼──────┐
                       │  postgres   │  │ celery-worker │  │   llm-proxy     │
                       │  :5432      │  │ + celery-beat │  │  MiniMax/OpenAI │
                       └─────────────┘  └───────────────┘  └─────────────────┘
                                                │
                                       ┌────────▼────────┐
                                       │  redis :6379    │
                                       └─────────────────┘
```

| Service | Image / Build | Rôle | Port interne |
|---|---|---|---|
| `agentai-frontend` | `./hermes-nebula` (Next.js 15) | UI React | 3000 |
| `agentai-api` | `./hermes-nebula-api` (FastAPI) | API REST + auth | 8000 |
| `llm-proxy` | `./hermes-llm-proxy` (FastAPI) | Routeur LLM (MiniMax/OpenAI/Codex) | 8001 |
| `celery-worker` | `./hermes-nebula-api` | Jobs async | — |
| `celery-beat` | `./hermes-nebula-api` | Scheduler | — |
| `postgres` | `postgres:16-alpine` | Base de données | 5432 |
| `redis` | `redis:7-alpine` | Cache + file Celery | 6379 |

## Démarrage rapide

### Prérequis
- Docker + Docker Compose v2
- Fichier `.env` à la racine (voir `.env.template` pour le modèle)

### Lancer la stack

```bash
# 1. Copier le template et renseigner les secrets
cp .env.template .env
#   → DB_PASSWORD, JWT_SECRET, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET,
#     ENCRYPTION_KEY, NEXT_PUBLIC_API_URL, FRONTEND_URL, DOMAIN...

# 2. Build + démarrer
docker compose up -d --build

# 3. Vérifier
docker compose ps
curl http://localhost:8000/health        # → {"status":"healthy"}
curl http://localhost:3000/login         # → page HTML
```

### Variables d'environnement critiques

| Variable | Description |
|---|---|
| `DOMAIN` | Domaine public (`agentai.smartefp.com`) |
| `FRONTEND_URL` | URL frontend pour OAuth redirect |
| `NEXT_PUBLIC_API_URL` | URL API publique (compilée dans le bundle Next.js) |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Credentials Google OAuth |
| `JWT_SECRET` | Secret signature JWT |
| `ENCRYPTION_KEY` | Clé Fernet pour chiffrer les API keys |
| `DB_PASSWORD` | Mot de passe PostgreSQL |
| `HERMES_ENV` | `development` (active dev-login) ou `production` |

## Structure du dépôt

```
ProdServeur/
├── hermes-nebula/           # Frontend Next.js 15 (UI)
│   ├── src/app/             # Pages: login, page, admin, pending
│   ├── Dockerfile
│   └── .env.production      # Variables NEXT_PUBLIC_* pour le build
│
├── hermes-nebula-api/       # Backend FastAPI
│   ├── app/
│   │   ├── api/             # Routers: auth, agents, workspaces, tools, models_api
│   │   ├── models/          # 14 modèles SQLAlchemy
│   │   ├── services/        # encryption, llm_router, quota_checker
│   │   ├── workers/         # Celery tasks
│   │   ├── main.py          # Entry FastAPI
│   │   └── config.py
│   ├── alembic/             # Migrations DB
│   └── Dockerfile
│
├── hermes-llm-proxy/        # Routeur LLM (MiniMax / OpenAI / Codex)
│   ├── providers/           # Implémentations par provider
│   ├── router.py
│   └── Dockerfile
│
├── caddy/                   # Configs vhosts Caddy (référence)
├── docs/
│   ├── AUDIT_2026-07-19.md  # Audit complet
│   └── design/nebula-mockups/  # 37 mockups de design
├── infra/webhook/           # Webhook GitHub pour déploiement auto
├── scripts/                 # Bootstrap VPS, génération secrets, etc.
├── tools/                   # Définitions JSON des tools MCP/agents
├── docker-compose.yml       # Stack complète
├── .env.template            # Modèle de configuration
└── README.md                # Ce fichier
```

## Déploiement sur VPS

Le déploiement se fait via webhook GitHub (voir `infra/webhook/`). Pattern Vercel-like : `git push main` → déploiement en 1-3 min.

```bash
# Sur le VPS, la stack vit dans /srv/agentai/
ssh prodserveur
cd /srv/agentai
docker compose ps
docker compose logs -f agentai-api
```

## Endpoints utiles

| Endpoint | Méthode | Description |
|---|---|---|
| `/api/health` | GET | Healthcheck API |
| `/api/auth/google` | GET | Démarre le flow Google OAuth |
| `/api/auth/google/callback` | GET | Callback OAuth (reçoit le code) |
| `/api/auth/me` | GET | Profil utilisateur (JWT requis) |
| `/api/auth/dev-login` | POST | Login dev (`HERMES_ENV=development` uniquement) |
| `/api/workspaces` | GET/POST | Gestion workspaces |
| `/api/admin/stats` | GET | Stats admin (superadmin requis) |

## Stack technique

- **Backend** : Python 3.12, FastAPI, SQLAlchemy 2.0 async, Pydantic v2, Alembic, asyncpg, Celery, Redis
- **Frontend** : Next.js 15, React 18, TypeScript 5.6, Zustand, lucide-react, CSS vanilla (design system glassmorphism dark)
- **DB** : PostgreSQL 16
- **Proxy** : Caddy (TLS auto Let's Encrypt)
- **Conteneurisation** : Docker Compose
- **Auth** : JWT (access + refresh) + Google OAuth 2.0

## Voir aussi

- [`docs/AUDIT_2026-07-19.md`](./docs/AUDIT_2026-07-19.md) — Audit complet et plan de nettoyage
- [`HANDOVER.md`](./HANDOVER.md) — Procédure d'amorçage SSH et hardening VPS
- [`docs/design/nebula-mockups/`](./docs/design/nebula-mockups/) — 37 mockups de design

