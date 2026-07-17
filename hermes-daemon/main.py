"""
Hermes Daemon — Backend agent IA (FastAPI)

Responsabilités :
  • Exposer une API REST pour Hermes Studio (chat, agents, tools)
  • Connecter Minimax via l'API compatible OpenAI
  • Déléguer des tâches complexes à n8n via webhooks
  • Coordonner les appels au serveur MCP (filesystem, GitHub)
"""

import os
import json
import secrets
import httpx
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    hermes_env: str = "production"
    hermes_port: int = 8001
    hermes_jwt_secret: str = ""
    minimax_api_key: str = ""
    minimax_base_url: str = "https://api.minimax.chat/v1"
    minimax_model: str = "abab6.5s-chat"
    n8n_webhook_base_url: str = "http://n8n:5678/webhook"
    mcp_server_url: str = "http://mcp-server:3100"
    mcp_auth_token: str = ""
    hermes_allowed_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    postgres_host: str = "host.docker.internal"
    postgres_port: int = 5432
    postgres_db: str = "hermes"
    postgres_user: str = "younes"
    postgres_password: str = ""


settings = Settings()

app = FastAPI(
    title="Hermes Daemon",
    description="Backend d'orchestration multi-agents",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.hermes_allowed_origins.split(",") if origin.strip()],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Modèles de données
# ---------------------------------------------------------------------------
class ChatMessage(BaseModel):
    role: str = Field(..., description="role: system, user, ou assistant")
    content: str = Field(..., description="Contenu du message")


class ChatRequest(BaseModel):
    messages: List[ChatMessage] = Field(..., description="Historique de conversation")
    model: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 2000
    tools: Optional[List[Dict[str, Any]]] = None


class ChatResponse(BaseModel):
    content: str
    model: str
    usage: Dict[str, int]
    finish_reason: str


class ToolCallRequest(BaseModel):
    tool_name: str = Field(..., description="Nom du tool à appeler")
    arguments: Dict[str, Any] = Field(default_factory=dict)


class N8nWebhookRequest(BaseModel):
    webhook_path: str = Field(..., description="Chemin du webhook n8n (ex: /my-flow)")
    method: str = "POST"
    payload: Dict[str, Any] = Field(default_factory=dict)
    headers: Dict[str, str] = Field(default_factory=dict)


class AgentConfig(BaseModel):
    name: str
    system_prompt: str
    model: Optional[str] = None
    tools: List[str] = Field(default_factory=list)


class SettingsUpdate(BaseModel):
    """Mise à jour des clés API (sécurisée côté serveur)."""
    minimax_api_key: Optional[str] = None
    telegram_bot_token: Optional[str] = None
    github_token: Optional[str] = None


class SettingsStatus(BaseModel):
    """État des clés configurées (renvoie juste présence, jamais la valeur)."""
    minimax_configured: bool
    telegram_configured: bool
    github_configured: bool
    model: str
    mcp_ready: bool


# ---------------------------------------------------------------------------
# Auth (JWT simple)
# ---------------------------------------------------------------------------
def verify_token(authorization: Optional[str] = Header(None)) -> bool:
    """Vérifie le secret de service sans jamais échouer ouvertement en production."""
    if not settings.hermes_jwt_secret:
        if settings.hermes_env.lower() in {"dev", "development", "test"}:
            return True
        raise HTTPException(status_code=503, detail="Authentification Hermes non configurée")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token manquant")
    token = authorization.split(" ", 1)[1]
    if not secrets.compare_digest(token, settings.hermes_jwt_secret):
        raise HTTPException(status_code=403, detail="Token invalide")
    return True


# ---------------------------------------------------------------------------
# Endpoints de santé
# ---------------------------------------------------------------------------
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "hermes-daemon",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "0.1.0",
    }


@app.get("/")
async def root():
    return {"message": "Hermes Daemon API", "docs": "/docs"}


# ---------------------------------------------------------------------------
# Endpoints Chat (Minimax via OpenAI-compatible API)
# ---------------------------------------------------------------------------
@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, _: bool = Depends(verify_token)):
    """Envoie une conversation à Minimax et retourne la réponse."""
    if not settings.minimax_api_key:
        raise HTTPException(status_code=500, detail="MINIMAX_API_KEY non configurée")

    messages = [{"role": m.role, "content": m.content} for m in req.messages]

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            resp = await client.post(
                f"{settings.minimax_base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.minimax_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": req.model or settings.minimax_model,
                    "messages": messages,
                    "temperature": req.temperature,
                    "max_tokens": req.max_tokens,
                    "tools": req.tools or [],
                },
            )
            resp.raise_for_status()
            data = resp.json()
            choice = data["choices"][0]
            return ChatResponse(
                content=choice["message"]["content"],
                model=data.get("model", req.model or settings.minimax_model),
                usage=data.get("usage", {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}),
                finish_reason=choice.get("finish_reason", "stop"),
            )
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erreur Minimax: {e}")


# ---------------------------------------------------------------------------
# Endpoints Tools (registre + exécution)
# ---------------------------------------------------------------------------
TOOL_REGISTRY: Dict[str, Dict[str, Any]] = {
    "n8n_webhook": {
        "name": "n8n_webhook",
        "description": "Délègue une tâche à un workflow n8n via webhook",
        "parameters": {
            "type": "object",
            "properties": {
                "webhook_path": {"type": "string", "description": "Chemin du webhook n8n"},
                "method": {"type": "string", "enum": ["GET", "POST"], "default": "POST"},
                "payload": {"type": "object", "description": "Corps de la requête"},
            },
            "required": ["webhook_path"],
        },
    },
    "mcp_filesystem": {
        "name": "mcp_filesystem",
        "description": "Lit/écrit dans le système de fichiers via MCP",
        "parameters": {
            "type": "object",
            "properties": {
                "operation": {"type": "string", "enum": ["read", "write", "list", "delete"]},
                "path": {"type": "string"},
                "content": {"type": "string", "description": "Requis pour write"},
            },
            "required": ["operation", "path"],
        },
    },
    "mcp_github": {
        "name": "mcp_github",
        "description": "Opérations GitHub via MCP",
        "parameters": {
            "type": "object",
            "properties": {
                "operation": {"type": "string", "enum": ["list_repos", "read_file", "create_pr", "search_code"]},
                "repo": {"type": "string"},
                "path": {"type": "string"},
                "branch": {"type": "string"},
            },
            "required": ["operation"],
        },
    },
}


@app.get("/api/tools")
async def list_tools(_: bool = Depends(verify_token)):
    """Liste tous les tools disponibles."""
    return {"tools": list(TOOL_REGISTRY.values())}


@app.post("/api/tools/call")
async def call_tool(req: ToolCallRequest, _: bool = Depends(verify_token)):
    """Exécute un tool par son nom."""
    if req.tool_name not in TOOL_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Tool inconnu: {req.tool_name}")

    if req.tool_name == "n8n_webhook":
        return await _call_n8n_webhook(req.arguments)
    elif req.tool_name.startswith("mcp_"):
        return await _call_mcp(req.tool_name, req.arguments)
    else:
        raise HTTPException(status_code=400, detail="Tool non exécutable directement")


async def _call_n8n_webhook(args: Dict[str, Any]):
    """Appelle un webhook n8n."""
    webhook_path = args.get("webhook_path", "").lstrip("/")
    method = args.get("method", "POST").upper()
    payload = args.get("payload", {})
    headers = args.get("headers", {})

    url = f"{settings.n8n_webhook_base_url.rstrip('/')}/{webhook_path}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            if method == "GET":
                resp = await client.get(url, params=payload, headers=headers)
            else:
                resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            return {"status": "success", "status_code": resp.status_code, "data": resp.json()}
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Erreur n8n: {e}")


async def _call_mcp(tool_name: str, args: Dict[str, Any]):
    """Appelle le serveur MCP via son API HTTP."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(
                f"{settings.mcp_server_url}/tools/{tool_name}/call",
                json={"arguments": args},
                headers={"Authorization": f"Bearer {settings.mcp_auth_token}"},
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Erreur MCP: {e}")


# ---------------------------------------------------------------------------
# Endpoints Agents
# ---------------------------------------------------------------------------
AGENTS_PATH = Path("/data/agents.json")


def _load_agents() -> Dict[str, AgentConfig]:
    if not AGENTS_PATH.exists():
        return {}
    try:
        raw = json.loads(AGENTS_PATH.read_text())
        return {name: AgentConfig.model_validate(agent) for name, agent in raw.items()}
    except (OSError, ValueError):
        return {}


def _save_agents() -> None:
    AGENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = AGENTS_PATH.with_suffix(".tmp")
    temporary.write_text(json.dumps({name: agent.model_dump() for name, agent in AGENTS.items()}, indent=2))
    temporary.replace(AGENTS_PATH)


AGENTS: Dict[str, AgentConfig] = _load_agents()


@app.get("/api/agents")
async def list_agents(_: bool = Depends(verify_token)):
    return {"agents": [a.model_dump() for a in AGENTS.values()]}


@app.post("/api/agents", response_model=AgentConfig)
async def create_agent(agent: AgentConfig, _: bool = Depends(verify_token)):
    AGENTS[agent.name] = agent
    _save_agents()
    return agent


@app.delete("/api/agents/{name}")
async def delete_agent(name: str, _: bool = Depends(verify_token)):
    if name in AGENTS:
        del AGENTS[name]
        _save_agents()
        return {"status": "deleted", "name": name}
    raise HTTPException(status_code=404, detail="Agent introuvable")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=settings.hermes_port)


# ---------------------------------------------------------------------------
# Endpoints Settings (clés API serveur)
# ---------------------------------------------------------------------------
ENV_PATH = "/data/hermes.env"  # Volume persistant du daemon


def _read_env_file() -> Dict[str, str]:
    """Lit le fichier .env persistant du daemon."""
    if not os.path.exists(ENV_PATH):
        return {}
    env: Dict[str, str] = {}
    with open(ENV_PATH, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def _write_env_file(env: Dict[str, str]) -> None:
    """Écrit le fichier .env persistant."""
    os.makedirs(os.path.dirname(ENV_PATH), exist_ok=True)
    with open(ENV_PATH, "w") as f:
        for k, v in env.items():
            f.write(f"{k}={v}\n")
    # Permissions strictes
    os.chmod(ENV_PATH, 0o600)


@app.get("/api/settings/status", response_model=SettingsStatus)
async def settings_status(_: bool = Depends(verify_token)):
    """Indique quelles clés sont configurées (jamais les valeurs)."""
    # Les valeurs sont lues depuis l'env du daemon (settings.* au démarrage)
    # + check du fichier persistant
    persisted = _read_env_file()

    mcp_ready = False
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(
                f"{settings.mcp_server_url}/health",
                headers={"Authorization": f"Bearer {settings.mcp_auth_token}"},
            )
            mcp_ready = response.is_success
    except httpx.HTTPError:
        mcp_ready = False

    return SettingsStatus(
        minimax_configured=bool(settings.minimax_api_key or persisted.get("MINIMAX_API_KEY")),
        telegram_configured=bool(persisted.get("TELEGRAM_BOT_TOKEN")),
        github_configured=bool(persisted.get("GITHUB_TOKEN")),
        model=settings.minimax_model,
        mcp_ready=mcp_ready,
    )


@app.post("/api/settings/update")
async def update_settings(upd: SettingsUpdate, _: bool = Depends(verify_token)):
    """Met à jour les clés API côté serveur (fichier .env persistant)."""
    env = _read_env_file()

    if upd.minimax_api_key:
        env["MINIMAX_API_KEY"] = upd.minimax_api_key
    if upd.telegram_bot_token:
        env["TELEGRAM_BOT_TOKEN"] = upd.telegram_bot_token
    if upd.github_token:
        env["GITHUB_TOKEN"] = upd.github_token

    _write_env_file(env)

    return {
        "status": "ok",
        "updated": [
            k for k, v in [
                ("minimax", bool(upd.minimax_api_key)),
                ("telegram", bool(upd.telegram_bot_token)),
                ("github", bool(upd.github_token)),
            ] if v
        ],
        "message": "Les clés sont sauvegardées. Redémarrer hermes-daemon pour qu'elles prennent effet.",
    }


@app.post("/api/settings/test/minimax")
async def test_minimax(_: bool = Depends(verify_token)):
    """Teste la clé Minimax (appelle /models de l'API)."""
    api_key = settings.minimax_api_key
    if not api_key:
        raise HTTPException(status_code=400, detail="Clé Minimax non configurée")

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.get(
                f"{settings.minimax_base_url}/models",
                headers={"Authorization": f"Bearer {api_key}"},
            )
            return {"status": "ok", "code": resp.status_code, "reachable": resp.status_code == 200}
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Erreur Minimax: {e}")
