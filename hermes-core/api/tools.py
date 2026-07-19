"""
hermes-core/api/tools.py — Tools registry (DB-backed).

Routes :
  GET  /api/tools               — liste
  POST /api/tools/refresh       — redécouvre les tools depuis MCP server
  GET  /api/tools/{name}        — détail d'un tool
"""

import logging
from typing import List

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from db.models import Tool
from config import settings
from .schemas import ToolOut

logger = logging.getLogger("hermes.core.api.tools")

router = APIRouter(prefix="/api/tools", tags=["tools"])


def _tool_to_out(t: Tool) -> ToolOut:
    return ToolOut(
        id=t.id,
        name=t.name,
        description=t.description,
        parameters=t.parameters or {},
        requires_approval=t.requires_approval,
        enabled=t.enabled,
        source=t.source,
    )


@router.get("", response_model=List[ToolOut])
async def list_tools(
    enabled_only: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """Liste tous les tools (DB-backed)."""
    stmt = select(Tool).order_by(Tool.source, Tool.name)
    if enabled_only:
        stmt = stmt.where(Tool.enabled == True)  # noqa: E712
    result = await db.execute(stmt)
    return [_tool_to_out(t) for t in result.scalars()]


@router.get("/{name}", response_model=ToolOut)
async def get_tool(name: str, db: AsyncSession = Depends(get_db)):
    """Détail d'un tool par son nom."""
    stmt = select(Tool).where(Tool.name == name)
    result = await db.execute(stmt)
    tool = result.scalar_one_or_none()
    if tool is None:
        raise HTTPException(status_code=404, detail=f"Tool '{name}' introuvable")
    return _tool_to_out(tool)


@router.post("/refresh")
async def refresh_tools(db: AsyncSession = Depends(get_db)):
    """Re-découvre les tools depuis MCP server + ajoute ceux manquants en DB.

    Crée 4 outils initiaux : n8n_webhook, mcp_filesystem, mcp_github, mcp_terminal.
    Idempotent : ne duplique pas si déjà présents.
    """
    INITIAL_TOOLS = [
        {
            "name": "n8n_webhook",
            "description": "Délègue une tâche à un workflow n8n via webhook",
            "parameters": {
                "type": "object",
                "properties": {
                    "webhook_path": {"type": "string"},
                    "method": {"type": "string", "enum": ["GET", "POST"], "default": "POST"},
                    "payload": {"type": "object"},
                },
                "required": ["webhook_path"],
            },
            "requires_approval": False,
            "source": "n8n",
        },
        {
            "name": "mcp_filesystem",
            "description": "Lit/écrit dans le système de fichiers via MCP",
            "parameters": {
                "type": "object",
                "properties": {
                    "operation": {"type": "string", "enum": ["read", "write", "list", "delete"]},
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                    "confirmed": {"type": "boolean", "default": False},
                },
                "required": ["operation", "path"],
            },
            "requires_approval": True,
            "source": "mcp",
        },
        {
            "name": "mcp_github",
            "description": "Opérations GitHub via MCP (list_repos, read_file, create_pr, search_code)",
            "parameters": {
                "type": "object",
                "properties": {
                    "operation": {"type": "string", "enum": ["list_repos", "read_file", "create_pr", "search_code"]},
                    "repo": {"type": "string"},
                    "path": {"type": "string"},
                    "branch": {"type": "string"},
                    "title": {"type": "string"},
                    "body": {"type": "string"},
                    "confirmed": {"type": "boolean", "default": False},
                },
                "required": ["operation"],
            },
            "requires_approval": True,
            "source": "mcp",
        },
        {
            "name": "mcp_terminal",
            "description": "Exécute des commandes terminal (ls, git, npm, python3, etc.) via MCP",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string"},
                    "args": {"type": "array", "items": {"type": "string"}},
                    "cwd": {"type": "string"},
                    "timeout_seconds": {"type": "integer", "minimum": 1, "maximum": 120},
                    "confirmed": {"type": "boolean", "default": False},
                },
                "required": ["command"],
            },
            "requires_approval": True,
            "source": "mcp",
        },
    ]

    added = []
    for tool_data in INITIAL_TOOLS:
        stmt = select(Tool).where(Tool.name == tool_data["name"])
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            continue

        tool = Tool(**tool_data)
        db.add(tool)
        added.append(tool_data["name"])

    await db.commit()

    return {"status": "ok", "added": added, "total_after": len(INITIAL_TOOLS)}