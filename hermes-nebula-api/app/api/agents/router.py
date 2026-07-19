import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.workspace import WorkspaceMember
from app.models.agent import Agent, AgentTool, AgentStatus, ToolBindingStatus
from app.models.tool import Tool
from app.models.model_config import ModelConfig
from app.api.agents.schemas import AgentCreate, AgentUpdate, AgentResponse
from app.services.quota_checker import can_use_model, can_use_tool

router = APIRouter(tags=["agents"])


@router.get("/workspaces/{wid}/agents", response_model=List[AgentResponse])
async def list_workspace_agents(
    wid: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Vérifier l'appartenance au workspace
    stmt_member = select(WorkspaceMember).where(
        and_(WorkspaceMember.workspace_id == wid, WorkspaceMember.user_id == current_user.id)
    )
    res_member = await db.execute(stmt_member)
    if not res_member.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Workspace access denied")

    stmt = select(Agent).where(Agent.workspace_id == wid).order_by(Agent.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/workspaces/{wid}/agents", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    wid: uuid.UUID,
    payload: AgentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Vérifier l'appartenance au workspace
    stmt_member = select(WorkspaceMember).where(
        and_(WorkspaceMember.workspace_id == wid, WorkspaceMember.user_id == current_user.id)
    )
    res_member = await db.execute(stmt_member)
    if not res_member.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Workspace access denied")

    # Si un modèle est spécifié, vérifier le quota de l'utilisateur
    if payload.model_config_id:
        has_model_quota = await can_use_model(db, current_user.id, payload.model_config_id)
        if not has_model_quota and not current_user.is_superadmin:
            raise HTTPException(status_code=403, detail="You do not have quota/permission for this LLM model")

    # Créer l'agent
    agent = Agent(
        workspace_id=wid,
        name=payload.name,
        description=payload.description,
        avatar_color=payload.avatar_color,
        system_prompt=payload.system_prompt,
        model_config_id=payload.model_config_id,
        status=AgentStatus.active,
        created_by=current_user.id
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)

    # Lier les outils
    for tool_id_str in payload.tools:
        try:
            tool_uuid = uuid.UUID(tool_id_str)
        except ValueError:
            continue
            
        # Vérifier si l'utilisateur a l'autorisation pour cet outil
        has_tool_quota = await can_use_tool(db, current_user.id, tool_uuid)
        if not has_tool_quota and not current_user.is_superadmin:
            continue  # Ignorer les outils non autorisés

        # Lier l'outil à l'agent
        binding = AgentTool(
            agent_id=agent.id,
            tool_id=tool_uuid,
            status=ToolBindingStatus.on_demand
        )
        db.add(binding)
        
    await db.commit()
    return agent


@router.get("/agents/{id}", response_model=AgentResponse)
async def get_agent(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(Agent).where(Agent.id == id)
    result = await db.execute(stmt)
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Vérifier l'appartenance au workspace de l'agent
    stmt_member = select(WorkspaceMember).where(
        and_(WorkspaceMember.workspace_id == agent.workspace_id, WorkspaceMember.user_id == current_user.id)
    )
    res_member = await db.execute(stmt_member)
    if not res_member.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Workspace access denied")

    return agent


@router.patch("/agents/{id}", response_model=AgentResponse)
async def update_agent(
    id: uuid.UUID,
    payload: AgentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(Agent).where(Agent.id == id)
    result = await db.execute(stmt)
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Vérifier l'appartenance au workspace de l'agent
    stmt_member = select(WorkspaceMember).where(
        and_(WorkspaceMember.workspace_id == agent.workspace_id, WorkspaceMember.user_id == current_user.id)
    )
    res_member = await db.execute(stmt_member)
    if not res_member.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Workspace access denied")

    if payload.name is not None:
        agent.name = payload.name
    if payload.description is not None:
        agent.description = payload.description
    if payload.avatar_color is not None:
        agent.avatar_color = payload.avatar_color
    if payload.system_prompt is not None:
        agent.system_prompt = payload.system_prompt
    if payload.status is not None:
        agent.status = payload.status
        
    if payload.model_config_id is not None:
        # Vérifier le quota
        has_model_quota = await can_use_model(db, current_user.id, payload.model_config_id)
        if not has_model_quota and not current_user.is_superadmin:
            raise HTTPException(status_code=403, detail="You do not have quota/permission for this LLM model")
        agent.model_config_id = payload.model_config_id

    # Mettre à jour les liaisons d'outils
    if payload.tools is not None:
        # Supprimer les liaisons existantes
        await db.execute(delete(AgentTool).where(AgentTool.agent_id == agent.id))
        
        # Ajouter les nouvelles liaisons valides
        for tool_id_str in payload.tools:
            try:
                tool_uuid = uuid.UUID(tool_id_str)
            except ValueError:
                continue
                
            has_tool_quota = await can_use_tool(db, current_user.id, tool_uuid)
            if not has_tool_quota and not current_user.is_superadmin:
                continue

            binding = AgentTool(
                agent_id=agent.id,
                tool_id=tool_uuid,
                status=ToolBindingStatus.on_demand
            )
            db.add(binding)

    await db.commit()
    await db.refresh(agent)
    return agent


@router.delete("/agents/{id}")
async def delete_agent(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(Agent).where(Agent.id == id)
    result = await db.execute(stmt)
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Vérifier l'appartenance au workspace de l'agent
    stmt_member = select(WorkspaceMember).where(
        and_(WorkspaceMember.workspace_id == agent.workspace_id, WorkspaceMember.user_id == current_user.id)
    )
    res_member = await db.execute(stmt_member)
    if not res_member.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Workspace access denied")

    await db.delete(agent)
    await db.commit()
    return {"status": "success", "message": "Agent deleted successfully"}
