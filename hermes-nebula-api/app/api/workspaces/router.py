import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember, MemberRole
from app.api.workspaces.schemas import (
    WorkspaceCreate, WorkspaceUpdate, WorkspaceMemberAdd, WorkspaceMemberResponse, WorkspaceResponse
)

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.get("", response_model=List[WorkspaceResponse])
async def list_workspaces(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Récupérer tous les workspaces où l'utilisateur est membre
    stmt = (
        select(Workspace)
        .join(WorkspaceMember, Workspace.id == WorkspaceMember.workspace_id)
        .where(WorkspaceMember.user_id == current_user.id)
        .order_by(Workspace.created_at.desc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    payload: WorkspaceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Créer le workspace
    workspace = Workspace(
        name=payload.name,
        logo_url=payload.logo_url,
        owner_id=current_user.id
    )
    db.add(workspace)
    await db.commit()
    await db.refresh(workspace)

    # Ajouter le créateur en tant que membre propriétaire
    member = WorkspaceMember(
        user_id=current_user.id,
        workspace_id=workspace.id,
        role=MemberRole.owner.value
    )
    db.add(member)
    await db.commit()

    return workspace


@router.get("/{id}", response_model=WorkspaceResponse)
async def get_workspace(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Vérifier l'appartenance
    stmt = select(WorkspaceMember).where(
        and_(WorkspaceMember.workspace_id == id, WorkspaceMember.user_id == current_user.id)
    )
    result = await db.execute(stmt)
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=403, detail="Workspace access denied")

    stmt_ws = select(Workspace).where(Workspace.id == id)
    result_ws = await db.execute(stmt_ws)
    workspace = result_ws.scalar_one_or_none()
    
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    return workspace


@router.patch("/{id}", response_model=WorkspaceResponse)
async def update_workspace(
    id: uuid.UUID,
    payload: WorkspaceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Seul l'admin ou le owner peut modifier
    stmt = select(WorkspaceMember).where(
        and_(WorkspaceMember.workspace_id == id, WorkspaceMember.user_id == current_user.id)
    )
    result = await db.execute(stmt)
    member = result.scalar_one_or_none()
    if not member or member.role not in [MemberRole.owner.value, MemberRole.admin.value]:
        raise HTTPException(status_code=403, detail="Workspace modification denied")

    stmt_ws = select(Workspace).where(Workspace.id == id)
    result_ws = await db.execute(stmt_ws)
    workspace = result_ws.scalar_one_or_none()

    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    if payload.name is not None:
        workspace.name = payload.name
    if payload.logo_url is not None:
        workspace.logo_url = payload.logo_url

    await db.commit()
    await db.refresh(workspace)
    return workspace


@router.delete("/{id}")
async def delete_workspace(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Seul le owner peut supprimer le workspace
    stmt = select(WorkspaceMember).where(
        and_(WorkspaceMember.workspace_id == id, WorkspaceMember.user_id == current_user.id)
    )
    result = await db.execute(stmt)
    member = result.scalar_one_or_none()
    if not member or member.role != MemberRole.owner.value:
        raise HTTPException(status_code=403, detail="Workspace deletion denied")

    stmt_ws = select(Workspace).where(Workspace.id == id)
    result_ws = await db.execute(stmt_ws)
    workspace = result_ws.scalar_one_or_none()

    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    await db.delete(workspace)
    await db.commit()
    return {"status": "success", "message": "Workspace deleted successfully"}


@router.get("/{id}/members", response_model=List[WorkspaceMemberResponse])
async def list_workspace_members(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Vérifier l'appartenance
    stmt_check = select(WorkspaceMember).where(
        and_(WorkspaceMember.workspace_id == id, WorkspaceMember.user_id == current_user.id)
    )
    res_check = await db.execute(stmt_check)
    if not res_check.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Workspace access denied")

    # Lister tous les membres
    stmt = (
        select(User.id.label("user_id"), User.email, User.display_name, User.avatar_url, WorkspaceMember.role)
        .join(WorkspaceMember, User.id == WorkspaceMember.user_id)
        .where(WorkspaceMember.workspace_id == id)
    )
    result = await db.execute(stmt)
    
    members = []
    for r in result:
        members.append({
            "user_id": r[0],
            "email": r[1],
            "display_name": r[2],
            "avatar_url": r[3],
            "role": r[4]
        })
    return members


@router.post("/{id}/members", response_model=WorkspaceMemberResponse)
async def add_workspace_member(
    id: uuid.UUID,
    payload: WorkspaceMemberAdd,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Seul l'admin ou le owner peut inviter
    stmt_check = select(WorkspaceMember).where(
        and_(WorkspaceMember.workspace_id == id, WorkspaceMember.user_id == current_user.id)
    )
    res_check = await db.execute(stmt_check)
    member_check = res_check.scalar_one_or_none()
    if not member_check or member_check.role not in [MemberRole.owner.value, MemberRole.admin.value]:
        raise HTTPException(status_code=403, detail="Workspace invite denied")

    # Vérifier si l'utilisateur à ajouter existe en base
    stmt_user = select(User).where(User.email == payload.email)
    res_user = await db.execute(stmt_user)
    user_to_add = res_user.scalar_one_or_none()

    if not user_to_add:
        raise HTTPException(status_code=404, detail="User not found. They must first sign up via Google.")

    # Vérifier s'il est déjà membre
    stmt_exist = select(WorkspaceMember).where(
        and_(WorkspaceMember.workspace_id == id, WorkspaceMember.user_id == user_to_add.id)
    )
    res_exist = await db.execute(stmt_exist)
    if res_exist.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="User is already a member of this workspace")

    # Ajouter le membre
    new_member = WorkspaceMember(
        user_id=user_to_add.id,
        workspace_id=id,
        role=payload.role
    )
    db.add(new_member)
    await db.commit()

    return {
        "user_id": user_to_add.id,
        "email": user_to_add.email,
        "display_name": user_to_add.display_name,
        "avatar_url": user_to_add.avatar_url,
        "role": payload.role
    }
