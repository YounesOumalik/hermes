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
from typing import Optional, List, Dict, Any, Tuple

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_MINIMAX_BASE_URL = "https://api.minimax.io/v1"
DEFAULT_MINIMAX_MODEL = "MiniMax-M2.7"
LEGACY_MINIMAX_MODELS = {"abab6.5s-chat", "abab6.5t-chat"}


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    hermes_env: str = "production"
    hermes_port: int = 8001
    hermes_jwt_secret: str = ""
    minimax_api_key: str = ""
    minimax_base_url: str = DEFAULT_MINIMAX_BASE_URL
    minimax_model: str = DEFAULT_MINIMAX_MODEL
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
    agent_name: Optional[str] = Field(default=None, max_length=80)


class ChatResponse(BaseModel):
    content: str
    model: str
    usage: Dict[str, int]
    finish_reason: str
    agent_name: Optional[str] = None


class ToolCallRequest(BaseModel):
    tool_name: str = Field(..., description="Nom du tool à appeler")
    arguments: Dict[str, Any] = Field(default_factory=dict)


class N8nWebhookRequest(BaseModel):
    webhook_path: str = Field(..., description="Chemin du webhook n8n (ex: /my-flow)")
    method: str = "POST"
    payload: Dict[str, Any] = Field(default_factory=dict)
    headers: Dict[str, str] = Field(default_factory=dict)


class AgentConfig(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    system_prompt: str
    model: Optional[str] = None
    tools: List[str] = Field(default_factory=list)


class SettingsUpdate(BaseModel):
    """Mise à jour des clés API (sécurisée côté serveur)."""
    minimax_api_key: Optional[str] = None
    minimax_base_url: Optional[str] = None
    minimax_model: Optional[str] = None
    telegram_bot_token: Optional[str] = None
    github_token: Optional[str] = None

    @field_validator("*")
    @classmethod
    def reject_env_file_injection(cls, value: Optional[str]) -> Optional[str]:
        """Empêche une valeur de paramètre de créer des lignes .env supplémentaires."""
        if value is not None and ("\n" in value or "\r" in value):
            raise ValueError("Les paramètres ne peuvent pas contenir de retour à la ligne.")
        return value


class SettingsStatus(BaseModel):
    """État des clés configurées (renvoie juste présence, jamais la valeur)."""
    minimax_configured: bool
    telegram_configured: bool
    github_configured: bool
    model: str
    minimax_base_url: str
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
    api_key, base_url, configured_model = _get_minimax_config()
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="MiniMax n’est pas configuré. Ajoutez une clé API valide dans Configuration.",
        )

    messages = [{"role": m.role, "content": m.content} for m in req.messages]
    selected_agent: Optional[AgentConfig] = None
    if req.agent_name:
        selected_agent = AGENTS.get(req.agent_name)
        if not selected_agent:
            raise HTTPException(status_code=404, detail="Agent introuvable. Rechargez la liste des agents.")
        system_prompt = selected_agent.system_prompt.strip()
        if selected_agent.tools:
            system_prompt += f"\n\nOutils autorisés pour cette mission : {', '.join(selected_agent.tools)}."
        if system_prompt:
            messages.insert(0, {"role": "system", "content": system_prompt})

    model = req.model or (selected_agent.model if selected_agent and selected_agent.model else None) or configured_model
    payload: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": req.temperature,
        "max_tokens": req.max_tokens,
    }
    if req.tools:
        payload["tools"] = req.tools

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            resp = await client.post(
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            choice = data["choices"][0]
            content = choice.get("message", {}).get("content")
            if not content:
                raise HTTPException(status_code=502, detail="MiniMax a renvoyé une réponse vide.")
            return ChatResponse(
                content=content,
                model=data.get("model", model),
                usage=data.get("usage", {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}),
                finish_reason=choice.get("finish_reason", "stop"),
                agent_name=selected_agent.name if selected_agent else None,
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise HTTPException(
                    status_code=502,
                    detail="MiniMax a refusé la clé API. Remplacez-la dans Configuration avec une clé créée sur la plateforme MiniMax.",
                ) from e
            if e.response.status_code == 404:
                raise HTTPException(
                    status_code=502,
                    detail=f"MiniMax ne trouve pas le modèle ou l’endpoint demandé ({model}). Vérifiez la configuration.",
                ) from e
            if e.response.status_code == 429:
                raise HTTPException(status_code=429, detail="MiniMax limite temporairement les requêtes. Réessayez dans un instant.") from e
            raise HTTPException(status_code=502, detail=f"MiniMax a renvoyé HTTP {e.response.status_code}.") from e
        except httpx.TimeoutException as e:
            raise HTTPException(status_code=504, detail="MiniMax met trop de temps à répondre. Réessayez.") from e
        except HTTPException:
            raise
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
    if agent.name in AGENTS:
        raise HTTPException(status_code=409, detail="Un agent porte déjà ce nom.")
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


# ---------------------------------------------------------------------------
# Endpoints Settings (clés API serveur)
# ---------------------------------------------------------------------------
ENV_PATH = Path("/data/hermes.env")  # Volume persistant du daemon


def _read_env_file() -> Dict[str, str]:
    """Lit le fichier .env persistant du daemon."""
    if not ENV_PATH.exists():
        return {}
    env: Dict[str, str] = {}
    with ENV_PATH.open("r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def _write_env_file(env: Dict[str, str]) -> None:
    """Écrit le fichier .env persistant."""
    ENV_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = ENV_PATH.with_suffix(".tmp")
    with temporary.open("w") as f:
        for k, v in env.items():
            f.write(f"{k}={v}\n")
    os.chmod(temporary, 0o600)
    temporary.replace(ENV_PATH)


def _usable_value(value: Optional[str]) -> str:
    value = (value or "").strip().strip('"').strip("'")
    return "" if not value or value.startswith("__") else value


def _get_minimax_config() -> Tuple[str, str, str]:
    """Retourne la configuration effective, avec priorité aux réglages sauvegardés."""
    persisted = _read_env_file()
    api_key = _usable_value(persisted.get("MINIMAX_API_KEY")) or _usable_value(settings.minimax_api_key)
    base_url = (_usable_value(persisted.get("MINIMAX_BASE_URL")) or _usable_value(settings.minimax_base_url) or DEFAULT_MINIMAX_BASE_URL).rstrip("/")
    model = _usable_value(persisted.get("MINIMAX_MODEL")) or _usable_value(settings.minimax_model) or DEFAULT_MINIMAX_MODEL
    if base_url == DEFAULT_MINIMAX_BASE_URL and model in LEGACY_MINIMAX_MODELS:
        model = DEFAULT_MINIMAX_MODEL
    return api_key, base_url, model


@app.get("/api/settings/status", response_model=SettingsStatus)
async def settings_status(_: bool = Depends(verify_token)):
    """Indique quelles clés sont configurées (jamais les valeurs)."""
    persisted = _read_env_file()
    api_key, base_url, model = _get_minimax_config()

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
        minimax_configured=bool(api_key),
        telegram_configured=bool(persisted.get("TELEGRAM_BOT_TOKEN")),
        github_configured=bool(persisted.get("GITHUB_TOKEN")),
        model=model,
        minimax_base_url=base_url,
        mcp_ready=mcp_ready,
    )


@app.post("/api/settings/update")
async def update_settings(upd: SettingsUpdate, _: bool = Depends(verify_token)):
    """Met à jour les clés API côté serveur (fichier .env persistant)."""
    env = _read_env_file()

    if upd.minimax_api_key:
        env["MINIMAX_API_KEY"] = upd.minimax_api_key.strip()
    if upd.minimax_base_url:
        env["MINIMAX_BASE_URL"] = upd.minimax_base_url.strip().rstrip("/")
    if upd.minimax_model:
        env["MINIMAX_MODEL"] = upd.minimax_model.strip()
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
                ("minimax base URL", bool(upd.minimax_base_url)),
                ("minimax model", bool(upd.minimax_model)),
                ("telegram", bool(upd.telegram_bot_token)),
                ("github", bool(upd.github_token)),
            ] if v
        ],
        "message": "Les paramètres sont sauvegardés et pris en compte immédiatement.",
    }


@app.post("/api/settings/test/minimax")
async def test_minimax(_: bool = Depends(verify_token)):
    """Teste réellement la clé et le modèle Minimax configurés."""
    api_key, base_url, model = _get_minimax_config()
    if not api_key:
        raise HTTPException(status_code=400, detail="Clé Minimax non configurée")

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": "Réponds uniquement : OK"}],
                    "max_tokens": 4,
                    "temperature": 0,
                },
            )
            resp.raise_for_status()
            return {"status": "ok", "code": resp.status_code, "reachable": True, "model": model}
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise HTTPException(status_code=422, detail="MiniMax a refusé la clé API configurée.") from e
            raise HTTPException(status_code=502, detail=f"MiniMax a renvoyé HTTP {e.response.status_code} pendant le test.") from e
        except httpx.TimeoutException as e:
            raise HTTPException(status_code=504, detail="MiniMax ne répond pas au test dans le délai imparti.") from e
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Erreur Minimax: {e}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=settings.hermes_port)
