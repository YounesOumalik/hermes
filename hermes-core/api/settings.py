"""
hermes-core/api/settings.py — Settings UI endpoints.

Routes :
  GET  /api/settings/status         — agrège status des providers (minimax, telegram, github, mcp)
  POST /api/settings/update         — update keys (persiste dans DB)
  POST /api/settings/test/minimax   — ping minimax API
"""

import logging
import os
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db, async_session
from config import settings as app_settings
from .schemas import SettingsStatus, SettingsUpdate

logger = logging.getLogger("hermes.core.api.settings")

router = APIRouter(prefix="/api/settings", tags=["settings"])

SETTINGS_PERSIST_FILE = "/data/hermes.env"


def _read_env_file() -> dict:
    """Lit le fichier .env persistant (fallback compat avec ancien daemon)."""
    if not os.path.exists(SETTINGS_PERSIST_FILE):
        return {}
    env = {}
    with open(SETTINGS_PERSIST_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def _write_env_file(env: dict) -> None:
    """Écrit le fichier .env persistant."""
    os.makedirs(os.path.dirname(SETTINGS_PERSIST_FILE), exist_ok=True)
    with open(SETTINGS_PERSIST_FILE, "w") as f:
        for k, v in env.items():
            f.write(f"{k}={v}\n")
    os.chmod(SETTINGS_PERSIST_FILE, 0o600)


@router.get("/status", response_model=SettingsStatus)
async def settings_status():
    """Agrège le status des providers (toujours booléen, jamais les valeurs)."""
    persisted = _read_env_file()

    # MCP ready ? Ping rapide
    mcp_ready = False
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(f"{app_settings.mcp_server_url}/health")
            mcp_ready = r.status_code == 200
    except Exception:
        pass

    return SettingsStatus(
        minimax_configured=bool(persisted.get("MINIMAX_API_KEY")),
        telegram_configured=bool(persisted.get("TELEGRAM_BOT_TOKEN")),
        github_configured=bool(persisted.get("GITHUB_TOKEN")),
        model="MiniMax-M2.7",  # Le llm-proxy résout la liste via /v1/models
        mcp_ready=mcp_ready,
    )


@router.post("/update")
async def update_settings(payload: SettingsUpdate):
    """Update des clés API (persiste dans fichier + DB ready pour restart)."""
    env = _read_env_file()

    if payload.minimax_api_key:
        env["MINIMAX_API_KEY"] = payload.minimax_api_key
    if payload.telegram_bot_token:
        env["TELEGRAM_BOT_TOKEN"] = payload.telegram_bot_token
    if payload.github_token:
        env["GITHUB_TOKEN"] = payload.github_token

    _write_env_file(env)

    updated = [
        k for k, v in [
            ("minimax", bool(payload.minimax_api_key)),
            ("telegram", bool(payload.telegram_bot_token)),
            ("github", bool(payload.github_token)),
        ] if v
    ]

    return {
        "status": "ok",
        "updated": updated,
        "message": "Clés sauvegardées. Redémarrer hermes-llm-proxy pour qu'elles prennent effet.",
    }


@router.post("/test/minimax")
async def test_minimax():
    """Teste la clé Minimax via l'API /models."""
    api_key = app_settings.minimax_api_key or _read_env_file().get("MINIMAX_API_KEY")
    if not api_key:
        raise HTTPException(status_code=400, detail="Clé Minimax non configurée")

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(
                "https://api.minimax.chat/v1/models",
                headers={"Authorization": f"Bearer {api_key}"},
            )
        return {
            "status": "ok",
            "code": r.status_code,
            "reachable": r.status_code == 200,
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erreur Minimax: {e}")