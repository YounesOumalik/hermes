"""
hermes-core/main.py — FastAPI app entrypoint.

Endpoints Phase 2 :
  - GET /health : ping DB + LLM proxy + MCP
  - GET /api/system/status : agrège tous les composants

Endpoints Phase 3+ seront ajoutés via routers dans api/.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from db.session import engine, async_session
from api import conversations_router, agents_router, settings_router, tools_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("hermes.core")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Démarre le client httpx partagé + vérifie la connectivité DB."""
    logger.info("Démarrage hermes-core...")

    # HTTP client partagé (pool keep-alive pour SSE/MCP/LLM proxy)
    timeout = httpx.Timeout(settings.http_timeout_seconds, connect=10.0)
    limits = httpx.Limits(
        max_connections=settings.http_max_connections,
        max_keepalive_connections=settings.http_max_keepalive,
        keepalive_expiry=30.0,
    )
    app.state.http = httpx.AsyncClient(timeout=timeout, limits=limits)
    logger.info("httpx pool initialisé")

    # Smoke check DB
    try:
        async with async_session() as session:
            from sqlalchemy import text
            result = await session.execute(text("SELECT 1"))
            result.scalar()
        logger.info("DB connection OK")
        app.state.db_status = "ok"
    except Exception as e:
        logger.error(f"DB connection FAILED: {e}")
        app.state.db_status = f"error: {e}"

    logger.info("hermes-core prêt")
    yield
    logger.info("Arrêt hermes-core...")
    await app.state.http.aclose()
    await engine.dispose()


app = FastAPI(
    title="Hermes Core",
    description="Orchestrateur Hermes OS (Phase 2 du plan)",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Backend interne via BFF
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Health & System status
# ---------------------------------------------------------------------------
@app.get("/")
async def root():
    return {
        "message": "Hermes Core",
        "service": "Orchestrateur Hermes OS",
        "version": "0.2.0",
        "endpoints": ["/health", "/api/system/status", "/docs"],
    }


@app.get("/health")
async def health():
    """Health check : ping DB + LLM proxy + MCP."""
    components = {}

    # DB
    try:
        async with async_session() as session:
            from sqlalchemy import text
            await session.execute(text("SELECT 1"))
        components["db"] = "up"
    except Exception as e:
        components["db"] = f"down: {e}"

    # LLM proxy
    try:
        resp = await app.state.http.get(
            f"{settings.hermes_llm_proxy_url}/health",
            timeout=5.0,
        )
        components["llm_proxy"] = "up" if resp.status_code == 200 else f"http {resp.status_code}"
    except Exception as e:
        components["llm_proxy"] = f"unreachable: {e}"

    # MCP server
    try:
        resp = await app.state.http.get(
            f"{settings.mcp_server_url}/health",
            timeout=5.0,
        )
        components["mcp"] = "up" if resp.status_code == 200 else f"http {resp.status_code}"
    except Exception as e:
        components["mcp"] = f"unreachable: {e}"

    # n8n (optionnel MVP)
    try:
        resp = await app.state.http.get(
            f"{settings.n8n_webhook_base_url.replace('/webhook', '')}/healthz",
            timeout=5.0,
        )
        components["n8n"] = "up" if resp.status_code == 200 else f"http {resp.status_code}"
    except Exception as e:
        components["n8n"] = f"unreachable: {e}"

    overall = "ok" if all(v == "up" for v in [components["db"], components["llm_proxy"]]) else "degraded"

    return {
        "status": overall,
        "service": "hermes-core",
        "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
        "version": "0.2.0",
        "components": components,
    }


@app.get("/api/system/status")
async def system_status():
    """Status complet (Master Prompt §120)."""
    health_resp = await health()
    return {
        "service": "hermes-core",
        "version": "0.2.0",
        "components": health_resp["components"],
        "config": {
            "llm_proxy_url": settings.hermes_llm_proxy_url,
            "mcp_server_url": settings.mcp_server_url,
            "n8n_webhook_base_url": settings.n8n_webhook_base_url,
            "db_pool_size": settings.db_pool_size,
            "tool_max_iterations": settings.tool_executor_max_iterations,
        },
    }


# Inclure les routers API
app.include_router(conversations_router)
app.include_router(agents_router)
app.include_router(settings_routerapp.include_router(tools_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.hermes_core_port)