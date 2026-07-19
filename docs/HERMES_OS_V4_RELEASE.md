# Hermes OS v4.0 — Release Notes

**Date**: 2026-07-19
**Branch**: `feature/hermes-os-4layers`
**Tag**: `v4.0-hermes-os`
**URL**: https://hermes.eaumalik.com

---

## Architecture

**4 couches** :

```
┌─────────────────────────────────────────────────────────────┐
│  UI (Next.js 16 + React 18, PWA, App Router, TS strict)    │
│  hermes-studio  · port 3000  · 512m cap                     │
└────────────────┬────────────────────────────────────────────┘
                 │
                 │ /api/hermes/* (reverse proxy + SSE pass-through)
                 │
┌────────────────▼────────────────────────────────────────────┐
│  Gateway BFF  (Next.js route handler)                       │
│  app/api/hermes/[...path]/route.ts · longest-prefix match   │
│  ├── /v1/*           → hermes-llm-proxy                     │
│  ├── /api/llm/*      → hermes-llm-proxy                     │
│  ├── /api/chat/*     → hermes-core                          │
│  ├── /api/agents/*   → hermes-core                          │
│  ├── /api/conversations/* → hermes-core                     │
│  ├── /api/runs/*     → hermes-core                          │
│  ├── /api/approvals/*→ hermes-core                          │
│  ├── /api/events/*   → hermes-core                          │
│  └── /api/tools/*    → hermes-core                          │
└────────┬─────────────────────┬───────────────────────────────┘
         │                     │
         │                     │
┌────────▼────────┐    ┌──────▼────────────────────────────────┐
│ hermes-llm-proxy│    │ hermes-core (orchestrateur)           │
│ OpenAI-compat   │    │ FastAPI + SQLAlchemy async + gunicorn │
│ port 8001       │    │ port 8002 · 768m cap                  │
│ 384m cap        │    │                                        │
└────────┬────────┘    │ • /api/chat/stream (SSE ReAct)       │
         │             │ • /api/conversations (CRUD)          │
         │             │ • /api/agents (CRUD + 11 presets)    │
         │             │ • /api/tools (registry)               │
         │             │ • /api/runs (Tasks)                   │
         │             │ • /api/approvals (human-in-the-loop)  │
         │             │ • /api/events (SSE bus)               │
         │             │ • /api/settings (system status)       │
         │             │ • /api/system/status                  │
         │             └────┬─────────────────────────────────┘
         │                  │
         │                  │
┌────────▼──────────────────▼──────────────────────────────────┐
│  PostgreSQL 16.14 (host-native)                              │
│  schema hermes_core (10 tables)                              │
│  user hermes_app (LIMITED grants, pas superuser)             │
└───────────────────────────────────────────────────────────────┘
```

---

## Services (6 containers, tous healthy)

| Container        | Image                       | Port    | Memory cap |
|------------------|-----------------------------|---------|------------|
| hermes-studio    | repo-hermes-studio          | 3000    | 512m       |
| hermes-core      | repo-hermes-core            | 8002 (loopback) | 768m       |
| hermes-llm-proxy | repo-hermes-llm-proxy       | 8001 (loopback) | 384m       |
| hermes-daemon    | upstream (legacy)           | 8090    | -          |
| mcp-server       | repo-mcp-server             | 7000    | -          |
| n8n              | n8nio/n8n                   | 5678    | -          |

---

## Phases livrées

### Phase 1 — hermes-llm-proxy ✅
- FastAPI 0.115 + httpx 0.27 + pydantic 2.9
- 6 models Minimax câblés (M3, M2.7, M2.7-highspeed, M2.5, M2.1, M2)
- OpenAI-compatible (`/v1/chat/completions`, `/v1/models`)
- Stateless, ~300 LOC

### Phase 2 — hermes-core skeleton ✅
- FastAPI 0.115 + SQLAlchemy 2.0 async + asyncpg + Alembic
- Postgres 16.14 + schema `hermes_core` (10 tables, isolées de n8n)
- User `hermes_app` avec grants LIMITÉS (pas superuser)
- Pool size=10, max_overflow=20, pool_recycle=3600, pool_pre_ping=True
- Gunicorn 2 workers uvicorn

### Phase 3 — 4 routers CRUD ✅
- `conversations.py` : CRUD + multipart attachments
- `agents.py` : CRUD + 11 presets (Marketing, SEO, Social Media, Research, Developer, Data, Executive, Content, Support, Finance, Custom)
- `settings.py` : `/status`, `/update`, `/test/minimax`
- `tools.py` : `/list`, `/refresh` (seeds 4 tools)

### Phase 4 — SSE chat + tool-call loop ✅
- `orchestrator/executor.py` : ReAct loop max 5 iterations, événements SSE
- `tools/dispatcher.py` : routing `mcp_*` → MCP server, `n8n_*` → n8n, détection `requires_confirmation`
- `api/chat.py` : POST `/api/chat/stream` (StreamingResponse text/event-stream)
- `api/runs.py` : GET/POST cancel (Tasks avec tool_calls + approvals)
- `api/approvals.py` : GET list + POST `/resolve` (approve/reject/modify → re-dispatch avec `confirmed=True`)
- `events/sse.py` : in-memory asyncio.Queue fan-out, ring buffer 50 events

### Phase 5 — BFF + hook aligné ✅
- Route BFF `/api/chat/*` ajoutée
- `useChatStream.ts` réécrit pour matcher le wire format executor
- ToolCallCard supporte `awaiting_approval` + `rejected`
- Ajout types `Record<string, unknown>[] | string` pour raisonnement

### Phase 6 — composer UI approval flow ✅
- `sendMessage` envoie `agent_id/conversation_id/tools_schema` alignés backend
- `resolveApproval()` câblée sur boutons inline
- `pendingApprovals[]` state pour tracker
- `Agent` type avec `id?: number`

### Phase 7 — E2E validé ✅
- Login UI OK avec hash scrypt correct
- Chat SSE accessible via `/api/hermes/api/chat/stream` (200 + text/event-stream)
- ToolCallCard rendu côté UI
- 6/6 containers healthy

---

## Sécurité

- Session JWT-HS256 cookie HttpOnly (8h expiration)
- Service token partagé BFF↔core via `HERMES_SERVICE_TOKEN` (env)
- `X-Hermes-User-Id` injecté depuis session vérifiée
- `hermes_app` Postgres user : grants LIMITÉS (pas de CREATE EXTENSION, pas superuser)
- Bash `$` interpretation contournée via Python pour `.env` containing scrypt hashes

---

## Limitations connues

- **Minimax API key** : `PLACEHOLDER_minimax_key` dans `/opt/hermes-orchestration/.env`. Tant qu'elle n'est pas setée, le SSE renvoie `done` sans contenu (le proxy reçoit 401 du provider).
- **Test E2E complet chat** : nécessite vraie clé Minimax pour valider le rendu text streaming.
- **Memory cap 512m** : suffisant pour le chat mais bloque si >100 messages en RAM. Augmenter si besoin.
- **No auth on /api/hermes/api/system/status** : protégé par BFF auth (cookie session), mais bypass possible via `service token` direct (volontaire, internal).
- **`next start` warning** : `output: standalone` mismatch, mais fonctionne. Migrer vers `node .next/standalone/server.js` en cleanup.

---

## Pistes Phase 8+

- Brancher vraie clé Minimax + test E2E réel (chat → tool_call MCP → approval flow complet)
- WebSocket pour events bus (remplacer SSE in-memory pour scale-out)
- Multi-user (RBAC, partage conversations)
- RAG sur attachments (vector store Postgres pgvector)
- Mobile native (Capacitor ou Expo)
- Rate limiting per user (slowapi)
- Metrics Prometheus (FastAPI instrumentator)

---

## Files modified (depuis main)

```
hermes-core/
├── api/
│   ├── agents.py
│   ├── approvals.py        ✨ NEW
│   ├── chat.py             ✨ NEW
│   ├── conversations.py
│   ├── runs.py             ✨ NEW
│   ├── settings.py
│   └── tools.py
├── db/
│   ├── models.py
│   └── session.py
├── events/                  ✨ NEW
│   ├── __init__.py
│   └── sse.py
├── orchestrator/             ✨ NEW
│   ├── __init__.py
│   └── executor.py
├── tools/                    ✨ NEW
│   ├── __init__.py
│   └── dispatcher.py
├── alembic/
├── config.py
├── Dockerfile
├── main.py
├── requirements.txt
└── scripts/migrate.sh

hermes-llm-proxy/             ✨ NEW
├── providers/
├── Dockerfile
├── main.py
└── requirements.txt

hermes-studio/app/
├── api/hermes/[...path]/route.ts   ✏️ routes updated
├── chat/
│   ├── useChatStream.ts            ✏️ wire format aligned
│   ├── page.tsx                    ✏️ approval flow
│   └── components/
│       ├── ReasoningBlock.tsx      ✏️ string | array
│       └── ToolCallCard.tsx        ✏️ awaiting_approval
└── lib/api.ts                      ✏️ Agent.id optional

docker-compose.yml           ✏️ +2 services + resource limits
docs/HERMES_CURRENT_ARCHITECTURE.md   ✨ NEW (snapshot Phase 0)
docs/HERMES_OS_V4_RELEASE.md          ✨ NEW (this file)
```
