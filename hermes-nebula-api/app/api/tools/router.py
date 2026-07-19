import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.workspace import WorkspaceMember
from app.models.agent import Agent, AgentTool, ToolBindingStatus
from app.models.tool import Tool, CostTier

router = APIRouter(tags=["tools"])


class ToolBindingUpdate(BaseModel):
    status: str  # off, on_demand, always_on


class ToolResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    description: Optional[str]
    icon_name: str
    category: str
    cost_tier: str
    enabled_globally: bool

    class Config:
        from_attributes = True


class AgentToolBindingResponse(BaseModel):
    tool_id: uuid.UUID
    name: str
    slug: str
    description: Optional[str]
    icon_name: str
    status: str

    class Config:
        from_attributes = True


@router.get("/tools", response_model=List[ToolResponse])
async def list_global_tools(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(Tool).where(Tool.enabled_globally == True).order_by(Tool.category.asc())
    result = await db.execute(stmt)
    tools = result.scalars().all()

    # S'il n'y a aucun outil en base (premier démarrage), on en crée par défaut
    if not tools:
        default_tools = [
            Tool(name="Web Search", slug="web_search", description="Search the web for up-to-date information", icon_name="globe", category="search", cost_tier=CostTier.low.value),
            Tool(name="Web Scraping", slug="web_scraping", description="Scrape text content from a web page", icon_name="document-text", category="search", cost_tier=CostTier.low.value),
            Tool(name="Image Generation", slug="image_gen", description="Generate images from text descriptions", icon_name="photograph", category="media", cost_tier=CostTier.medium.value),
            Tool(name="Text To Speech", slug="tts", description="Convert text to natural sounding speech audio", icon_name="volume-up", category="media", cost_tier=CostTier.medium.value),
            Tool(name="Speech To Text", slug="transcription", description="Transcribe audio files to text transcriptions", icon_name="microphone", category="media", cost_tier=CostTier.low.value),
        ]
        for t in default_tools:
            db.add(t)
        await db.commit()
        
        stmt = select(Tool).where(Tool.enabled_globally == True).order_by(Tool.category.asc())
        result = await db.execute(stmt)
        tools = result.scalars().all()

    return tools


@router.get("/agents/{id}/tools", response_model=List[AgentToolBindingResponse])
async def list_agent_tools(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt_agent = select(Agent).where(Agent.id == id)
    res_agent = await db.execute(stmt_agent)
    agent = res_agent.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Vérifier l'appartenance au workspace de l'agent
    stmt_member = select(WorkspaceMember).where(
        and_(WorkspaceMember.workspace_id == agent.workspace_id, WorkspaceMember.user_id == current_user.id)
    )
    res_member = await db.execute(stmt_member)
    if not res_member.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Workspace access denied")

    # Charger tous les outils globaux
    stmt_tools = select(Tool).where(Tool.enabled_globally == True)
    res_tools = await db.execute(stmt_tools)
    tools = res_tools.scalars().all()

    # Charger les bindings existants pour cet agent
    stmt_bindings = select(AgentTool).where(AgentTool.agent_id == id)
    res_bindings = await db.execute(stmt_bindings)
    bindings = {b.tool_id: b.status for b in res_bindings.scalars().all()}

    # Fusionner
    res = []
    for t in tools:
        res.append({
            "tool_id": t.id,
            "name": t.name,
            "slug": t.slug,
            "description": t.description,
            "icon_name": t.icon_name,
            "status": bindings.get(t.id, ToolBindingStatus.off.value)
        })

    return res


@router.patch("/agents/{id}/tools/{tid}", response_model=AgentToolBindingResponse)
async def update_agent_tool_binding(
    id: uuid.UUID,
    tid: uuid.UUID,
    payload: ToolBindingUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt_agent = select(Agent).where(Agent.id == id)
    res_agent = await db.execute(stmt_agent)
    agent = res_agent.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Vérifier l'appartenance au workspace de l'agent
    stmt_member = select(WorkspaceMember).where(
        and_(WorkspaceMember.workspace_id == agent.workspace_id, WorkspaceMember.user_id == current_user.id)
    )
    res_member = await db.execute(stmt_member)
    if not res_member.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Workspace access denied")

    # Vérifier l'outil
    stmt_tool = select(Tool).where(and_(Tool.id == tid, Tool.enabled_globally == True))
    res_tool = await db.execute(stmt_tool)
    tool = res_tool.scalar_one_or_none()
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found or disabled globally")

    # Récupérer ou créer le binding
    stmt_binding = select(AgentTool).where(and_(AgentTool.agent_id == id, AgentTool.tool_id == tid))
    res_binding = await db.execute(stmt_binding)
    binding = res_binding.scalar_one_or_none()

    if payload.status == ToolBindingStatus.off.value:
        if binding:
            await db.delete(binding)
            await db.commit()
    else:
        if not binding:
            binding = AgentTool(
                agent_id=id,
                tool_id=tid,
                status=payload.status
            )
            db.add(binding)
        else:
            binding.status = payload.status
        await db.commit()

    return {
        "tool_id": tool.id,
        "name": tool.name,
        "slug": tool.slug,
        "description": tool.description,
        "icon_name": tool.icon_name,
        "status": payload.status
    }
