from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit import UserQuota
from app.models.model_config import ModelConfig
import uuid


async def can_use_model(db: AsyncSession, user_id: uuid.UUID, model_config_id: uuid.UUID) -> bool:
    """Vérifie si l'utilisateur a le droit d'utiliser ce modèle."""
    stmt = select(UserQuota).where(UserQuota.user_id == user_id)
    result = await db.execute(stmt)
    quota = result.scalar_one_or_none()

    if quota is None:
        return False  # Pas de quota = pas d'accès

    allowed = quota.allowed_models or []
    return str(model_config_id) in allowed


async def can_use_tool(db: AsyncSession, user_id: uuid.UUID, tool_id: uuid.UUID) -> bool:
    """Vérifie si l'utilisateur a le droit d'utiliser cet outil."""
    stmt = select(UserQuota).where(UserQuota.user_id == user_id)
    result = await db.execute(stmt)
    quota = result.scalar_one_or_none()

    if quota is None:
        return False

    allowed = quota.allowed_tools or []
    return str(tool_id) in allowed


async def check_token_budget(db: AsyncSession, user_id: uuid.UUID, tokens_needed: int) -> bool:
    """Vérifie si l'utilisateur a encore du budget tokens."""
    stmt = select(UserQuota).where(UserQuota.user_id == user_id)
    result = await db.execute(stmt)
    quota = result.scalar_one_or_none()

    if quota is None:
        return False

    remaining = quota.max_monthly_llm_tokens - quota.used_monthly_llm_tokens
    return remaining >= tokens_needed


async def deduct_tokens(db: AsyncSession, user_id: uuid.UUID, tokens_used: int):
    """Déduit les tokens utilisés du quota."""
    stmt = select(UserQuota).where(UserQuota.user_id == user_id)
    result = await db.execute(stmt)
    quota = result.scalar_one_or_none()

    if quota:
        quota.used_monthly_llm_tokens += tokens_used
        await db.commit()
