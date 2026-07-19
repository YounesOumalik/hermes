import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.api.deps import get_current_superadmin
from app.models.user import User
from app.models.audit import UserQuota, AdminAuditLog
from app.models.api_key import ApiKey
from app.api.admin.schemas import (
    UserQuotaUpdate, UserQuotaResponse, AdminUserListItem,
    ApiKeyCreate, ApiKeyResponse, ApiKeyTestRequest, AuditLogResponse
)
from app.services.encryption import encrypt
from app.services.llm_router import test_api_key

router = APIRouter(prefix="/admin", tags=["admin"])


async def log_admin_action(
    db: AsyncSession,
    admin_id: uuid.UUID,
    action: str,
    target_user_id: uuid.UUID | None = None,
    details: dict | None = None
):
    audit = AdminAuditLog(
        admin_user_id=admin_id,
        action=action,
        target_user_id=target_user_id,
        details_json=details
    )
    db.add(audit)
    await db.commit()


@router.get("/stats")
async def get_admin_stats(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_superadmin)
):
    # Nombre d'utilisateurs total, actifs, en attente
    total_users_res = await db.execute(select(func.count(User.id)))
    total_users = total_users_res.scalar() or 0

    active_users_res = await db.execute(select(func.count(User.id)).where(User.is_active == True))
    active_users = active_users_res.scalar() or 0

    pending_users = total_users - active_users

    # Espace disque consommé sur le quota global
    disk_usage_res = await db.execute(select(func.sum(UserQuota.used_disk_bytes)))
    total_disk_used = disk_usage_res.scalar() or 0

    # Total des clés API configurées
    api_keys_res = await db.execute(select(func.count(ApiKey.id)))
    total_api_keys = api_keys_res.scalar() or 0

    return {
        "total_users": total_users,
        "active_users": active_users,
        "pending_users": pending_users,
        "total_disk_used_bytes": total_disk_used,
        "total_api_keys": total_api_keys,
    }


@router.get("/users", response_model=List[AdminUserListItem])
async def list_users(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_superadmin)
):
    stmt = select(User).order_by(User.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


@router.patch("/users/{id}/approve")
async def approve_user(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_superadmin)
):
    stmt = select(User).where(User.id == id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = True
    
    # Créer le quota par défaut si absent
    quota_stmt = select(UserQuota).where(UserQuota.user_id == id)
    quota_res = await db.execute(quota_stmt)
    quota = quota_res.scalar_one_or_none()
    
    if not quota:
        quota = UserQuota(
            user_id=id,
            max_disk_bytes=1073741824,  # 1 GiB par défaut
            max_monthly_llm_tokens=1000000,
            allowed_models=[],
            allowed_tools=[]
        )
        db.add(quota)

    await db.commit()
    await log_admin_action(db, admin.id, "approve_user", target_user_id=id)

    return {"status": "success", "message": "User approved successfully"}


@router.patch("/users/{id}/disable")
async def disable_user(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_superadmin)
):
    if id == admin.id:
        raise HTTPException(status_code=400, detail="You cannot disable your own admin account")

    stmt = select(User).where(User.id == id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = False
    await db.commit()
    await log_admin_action(db, admin.id, "disable_user", target_user_id=id)

    return {"status": "success", "message": "User disabled successfully"}


@router.get("/users/{id}/quota", response_model=UserQuotaResponse)
async def get_user_quota(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_superadmin)
):
    stmt = select(UserQuota).where(UserQuota.user_id == id)
    result = await db.execute(stmt)
    quota = result.scalar_one_or_none()

    if not quota:
        raise HTTPException(status_code=404, detail="Quota not configured for this user")

    return quota


@router.patch("/users/{id}/quota", response_model=UserQuotaResponse)
async def update_user_quota(
    id: uuid.UUID,
    payload: UserQuotaUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_superadmin)
):
    stmt = select(UserQuota).where(UserQuota.user_id == id)
    result = await db.execute(stmt)
    quota = result.scalar_one_or_none()

    if not quota:
        raise HTTPException(status_code=404, detail="Quota record not found")

    quota.max_disk_bytes = payload.max_disk_bytes
    quota.max_monthly_llm_tokens = payload.max_monthly_llm_tokens
    quota.allowed_models = payload.allowed_models
    quota.allowed_tools = payload.allowed_tools
    quota.notes_admin = payload.notes_admin
    quota.updated_by_admin_id = admin.id

    await db.commit()
    await db.refresh(quota)

    await log_admin_action(
        db, 
        admin.id, 
        "update_quota", 
        target_user_id=id, 
        details={
            "max_disk_bytes": payload.max_disk_bytes,
            "max_monthly_llm_tokens": payload.max_monthly_llm_tokens,
            "allowed_models": payload.allowed_models,
            "allowed_tools": payload.allowed_tools
        }
    )

    return quota


@router.get("/api-keys", response_model=List[ApiKeyResponse])
async def list_global_api_keys(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_superadmin)
):
    stmt = select(ApiKey).order_by(ApiKey.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/api-keys", response_model=ApiKeyResponse)
async def add_global_api_key(
    payload: ApiKeyCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_superadmin)
):
    # Chiffrer la clé API avant de la stocker
    encrypted = encrypt(payload.api_key)

    api_key_obj = ApiKey(
        provider=payload.provider.lower(),
        key_name=payload.key_name,
        encrypted_key=encrypted,
        base_url=payload.base_url,
        is_active=True,
        added_by_user_id=admin.id
    )
    db.add(api_key_obj)
    await db.commit()
    await db.refresh(api_key_obj)

    await log_admin_action(db, admin.id, "add_api_key", details={"provider": payload.provider, "key_name": payload.key_name})

    return api_key_obj


@router.delete("/api-keys/{id}")
async def delete_global_api_key(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_superadmin)
):
    stmt = select(ApiKey).where(ApiKey.id == id)
    result = await db.execute(stmt)
    key_obj = result.scalar_one_or_none()

    if not key_obj:
        raise HTTPException(status_code=404, detail="API Key not found")

    await db.delete(key_obj)
    await db.commit()

    await log_admin_action(db, admin.id, "delete_api_key", details={"provider": key_obj.provider, "key_name": key_obj.key_name})

    return {"status": "success", "message": "API key deleted successfully"}


@router.post("/api-keys/test")
async def test_key_connectivity(
    payload: ApiKeyTestRequest,
    admin: User = Depends(get_current_superadmin)
):
    # Appeler le endpoint /v1/models du provider pour valider la clé
    test_res = await test_api_key(payload.provider, payload.base_url, payload.api_key)
    if not test_res.get("success"):
        raise HTTPException(status_code=400, detail=f"Connectivity test failed: {test_res.get('error')}")
    return test_res


@router.get("/audit-log", response_model=List[AuditLogResponse])
async def get_admin_audit_logs(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_superadmin)
):
    stmt = select(AdminAuditLog).order_by(AdminAuditLog.created_at.desc()).limit(100)
    result = await db.execute(stmt)
    return result.scalars().all()
