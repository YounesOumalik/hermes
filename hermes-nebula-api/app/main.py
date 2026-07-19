from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from app.config import get_settings
from app.database import engine
from app.models.base import Base

# Routers imports
from app.api.auth.router import router as auth_router
from app.api.admin.router import router as admin_router
from app.api.workspaces.router import router as workspaces_router
from app.api.agents.router import router as agents_router
from app.api.chat.router import router as chat_router
from app.api.jobs.router import router as jobs_router
from app.api.tools.router import router as tools_router
from app.api.models_api.router import router as models_router
from app.api.settings.router import router as settings_router
from app.api.files.router import router as files_router

settings = get_settings()

app = FastAPI(
    title="AgentAI API",
    description="Backend API for the AgentAI autonomous AI agent platform.",
    version="2.0.0",
    docs_url="/docs" if settings.hermes_env == "development" else None,
    redoc_url=None,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Géré par Caddy en prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session Middleware is REQUIRED for Authlib Google OAuth to store intermediate states
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.jwt_secret,
    max_age=3600  # 1 hour session window for oauth flow
)


@app.on_event("startup")
async def startup_event():
    # En développement, on crée les tables automatiquement
    if settings.hermes_env == "development":
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)


@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint for Docker container checks."""
    return {"status": "healthy", "environment": settings.hermes_env}


# Include Routers under the unified API prefix matching Caddy rules
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(workspaces_router)
app.include_router(agents_router)
app.include_router(chat_router)
app.include_router(jobs_router)
app.include_router(tools_router)
app.include_router(models_router)
app.include_router(settings_router)
app.include_router(files_router)
