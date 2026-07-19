"""
hermes-llm-proxy/main.py

Proxy LLM OpenAI-compat. Refactor de l'ancien hermes-daemon/main.py :
- Strip : tool registry, agent CRUD, settings, _call_n8n/_call_mcp
- Add   : /v1/models, /v1/chat/completions (avec SSE stream), /v1/embeddings, lifespan httpx pool
- Garde : /health, auth Bearer token
"""

import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional, List, Dict, Any, AsyncIterator

import httpx
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from providers import (
    MinimaxProvider,
    OpenAIProvider,
    ProviderError,
    ProviderUnavailable,
)
from router import ModelRouter

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("hermes.llm-proxy")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    hermes_env: str = "production"
    hermes_port: int = 8001

    # Auth : token partagé avec hermes-core (BFF injecte ce token)
    hermes_service_token: str = ""

    # Providers — seul Minimax est câblé dans le MVP
    minimax_api_key: str = ""
    minimax_base_url: str = "https://api.minimax.chat/v1"
    minimax_default_model: str = "MiniMax-M2.7"

    # Futures : OpenAI, Codex, Anthropic, etc.
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"

    codex_api_key: str = ""
    codex_base_url: str = "https://api.openai.com/v1"

    # HTTP client
    http_timeout_seconds: float = 60.0
    http_max_connections: int = 100
    http_max_keepalive: int = 20


settings = Settings()


# ---------------------------------------------------------------------------
# Lifespan : httpx pool partagé entre toutes les requêtes
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Démarre le client httpx global + enregistre les providers câblés."""
    logger.info("Démarrage hermes-llm-proxy...")

    # Client httpx partagé (pool keep-alive, gain -150-300ms par requête)
    timeout = httpx.Timeout(settings.http_timeout_seconds, connect=10.0)
    limits = httpx.Limits(
        max_connections=settings.http_max_connections,
        max_keepalive_connections=settings.http_max_keepalive,
        keepalive_expiry=30.0,
    )
    app.state.http = httpx.AsyncClient(timeout=timeout, limits=limits)

    # Router + providers
    router = ModelRouter()

    # MinimaxProvider — câblé MVP (peut être désactivé si clé absente/placeholder)
    try:
        minimax = MinimaxProvider(
            api_key=settings.minimax_api_key,
            base_url=settings.minimax_base_url,
            default_model=settings.minimax_default_model,
        )
        minimax.set_http_client(app.state.http)
        router.register("minimax", minimax)
        if not settings.minimax_api_key or "PLACEHOLDER" in settings.minimax_api_key:
            logger.warning("MINIMAX_API_KEY absente ou placeholder — Minimax désactivé")
        else:
            logger.info(f"Minimax câblé (default={settings.minimax_default_model})")
    except Exception as e:
        logger.error(f"Erreur init Minimax provider: {e}")

    # OpenAIProvider — stub (décommenter + fournir OPENAI_API_KEY pour activer)
    # if settings.openai_api_key and "PLACEHOLDER" not in settings.openai_api_key:
    #     openai = OpenAIProvider(api_key=settings.openai_api_key, base_url=settings.openai_base_url)
    #     openai.set_http_client(app.state.http)
    #     router.register("openai", openai)
    #     logger.info("OpenAI câblé")

    app.state.router = router
    logger.info(f"hermes-llm-proxy prêt ({len(router._providers)} provider(s))")

    yield

    # Cleanup
    logger.info("Arrêt hermes-llm-proxy...")
    await app.state.http.aclose()


app = FastAPI(
    title="Hermes LLM Proxy",
    description="Proxy LLM OpenAI-compat pour Hermes OS",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Backend interne, atteint via BFF (pas de credentials)
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
def verify_token(authorization: Optional[str] = Header(None)) -> bool:
    """Vérifie le token Bearer. En l'absence de token configuré, accepte tout (dev only)."""
    if not settings.hermes_service_token:
        return True  # Mode dev : pas de token requis
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token Bearer manquant")
    token = authorization.split(" ", 1)[1]
    if token != settings.hermes_service_token:
        raise HTTPException(status_code=401, detail="Token invalide")
    return True


# ---------------------------------------------------------------------------
# Modèles Pydantic (OpenAI-compat)
# ---------------------------------------------------------------------------
class ChatMessage(BaseModel):
    role: str = Field(..., description="system | user | assistant | tool")
    content: str = Field(..., description="Contenu du message")


class ChatRequest(BaseModel):
    """Format OpenAI-compat."""
    messages: List[ChatMessage]
    model: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 2000
    stream: bool = False
    tools: Optional[List[Dict[str, Any]]] = None


class EmbeddingRequest(BaseModel):
    input: List[str]
    model: Optional[str] = "text-embedding-3-small"


# ---------------------------------------------------------------------------
# Endpoints de santé
# ---------------------------------------------------------------------------
@app.get("/health")
async def health():
    """Health check : ping tous les providers câblés (avec ProviderUnavailable skip)."""
    router: ModelRouter = app.state.router
    providers_status: Dict[str, str] = {}

    for name, provider in router._providers.items():
        try:
            models = await provider.list_models()
            providers_status[name] = f"ok ({len(models)} models)"
        except ProviderUnavailable:
            providers_status[name] = "not_configured"
        except Exception as e:
            providers_status[name] = f"error: {e}"

    return {
        "status": "ok",
        "service": "hermes-llm-proxy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "0.2.0",
        "providers": providers_status,
    }


@app.get("/")
async def root():
    return {
        "message": "Hermes LLM Proxy",
        "service": "OpenAI-compat proxy for Hermes OS",
        "version": "0.2.0",
        "endpoints": ["/v1/models", "/v1/chat/completions", "/v1/embeddings", "/health", "/docs"],
    }


# ---------------------------------------------------------------------------
# Endpoints OpenAI-compat
# ---------------------------------------------------------------------------
@app.get("/v1/models")
async def list_models(_: bool = Depends(verify_token)):
    """Liste tous les modèles de tous les providers câblés (OpenAI-compat)."""
    router: ModelRouter = app.state.router
    models = await router.list_all_models()
    return {"object": "list", "data": models}


@app.post("/v1/chat/completions")
async def chat_completions(req: ChatRequest, _: bool = Depends(verify_token)):
    """Endpoint chat OpenAI-compat avec support streaming SSE."""
    router: ModelRouter = app.state.router

    model_name = req.model or settings.minimax_default_model
    provider = router.resolve(model_name)

    messages = [{"role": m.role, "content": m.content} for m in req.messages]

    if req.stream:
        # Streaming SSE
        async def event_generator() -> AsyncIterator[str]:
            try:
                async for chunk in provider.stream_chat(
                    messages=messages,
                    model=model_name,
                    temperature=req.temperature,
                    max_tokens=req.max_tokens,
                    tools=req.tools,
                ):
                    yield f"data: {json.dumps(chunk)}\n\n"
                yield "data: [DONE]\n\n"
            except ProviderError as e:
                err_payload = {"error": {"message": str(e), "type": "provider_error"}}
                yield f"data: {json.dumps(err_payload)}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",  # Désactive buffering nginx/caddy
                "Connection": "keep-alive",
            },
        )

    # Non-streaming
    try:
        result = await provider.chat(
            messages=messages,
            model=model_name,
            temperature=req.temperature,
            max_tokens=req.max_tokens,
            tools=req.tools,
        )
        return result
    except ProviderUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e))
    except ProviderError as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.post("/v1/embeddings")
async def embeddings(req: EmbeddingRequest, _: bool = Depends(verify_token)):
    """Endpoint embeddings — stub MVP (Phase 5 RAG)."""
    raise HTTPException(
        status_code=501,
        detail="Embeddings non implémentés dans le MVP. Voir Phase 5 (RAG) du plan.",
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=settings.hermes_port)