import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.audit import UserQuota
from app.models.model_config import ModelConfig, ModelProvider

router = APIRouter(prefix="/models", tags=["models"])


class ModelConfigResponse(BaseModel):
    id: uuid.UUID
    provider: str
    model_name: str
    display_name: str
    context_window: int
    input_price_per_1m: Optional[float]
    output_price_per_1m: Optional[float]
    capabilities: List[str]
    is_default: bool
    enabled: bool

    class Config:
        from_attributes = True


@router.get("", response_model=List[ModelConfigResponse])
async def list_available_models(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(ModelConfig).where(ModelConfig.enabled == True).order_by(ModelConfig.provider.asc())
    result = await db.execute(stmt)
    configs = result.scalars().all()

    # Si aucun modèle configuré, initialiser les modèles par défaut
    if not configs:
        default_configs = [
            ModelConfig(
                provider=ModelProvider.minimax.value,
                model_name="abab6.5-chat",
                display_name="MiniMax Abab 6.5",
                context_window=8192,
                input_price_per_1m=0.20,
                output_price_per_1m=0.20,
                capabilities=["text", "tools"],
                is_default=True
            ),
            ModelConfig(
                provider=ModelProvider.opencode_zen.value,
                model_name="opencode-zen-base",
                display_name="OpenCode Zen",
                context_window=32768,
                input_price_per_1m=0.10,
                output_price_per_1m=0.10,
                capabilities=["text", "vision", "tools"],
                is_default=False
            )
        ]
        for c in default_configs:
            db.add(c)
        await db.commit()

        stmt = select(ModelConfig).where(ModelConfig.enabled == True).order_by(ModelConfig.provider.asc())
        result = await db.execute(stmt)
        configs = result.scalars().all()

    # Filtrer par rapport aux quotas de l'utilisateur (si non superadmin)
    if current_user.is_superadmin:
        return configs

    # Récupérer les quotas de l'utilisateur
    stmt_quota = select(UserQuota).where(UserQuota.user_id == current_user.id)
    res_quota = await db.execute(stmt_quota)
    quota = res_quota.scalar_one_or_none()

    if not quota:
        return []  # Aucun quota configuré = aucun modèle accessible

    allowed_model_ids = quota.allowed_models or []
    
    # Retourner uniquement les modèles autorisés dans le quota
    filtered_configs = [c for c in configs if str(c.id) in allowed_model_ids]
    return filtered_configs
