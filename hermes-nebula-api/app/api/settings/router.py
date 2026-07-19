import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.notification import NotificationChannel, NotificationRule

router = APIRouter(prefix="/settings", tags=["settings"])


class ProfileUpdate(BaseModel):
    display_name: Optional[str] = Field(None, max_length=200)
    username: Optional[str] = Field(None, max_length=100)
    timezone: Optional[str] = Field(None, max_length=50)


class NotificationChannelResponse(BaseModel):
    id: uuid.UUID
    type: str
    is_connected: bool
    config_json: Optional[dict]

    class Config:
        from_attributes = True


class NotificationChannelUpdate(BaseModel):
    config_json: dict
    is_connected: bool


@router.patch("/profile")
async def update_profile(
    payload: ProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if payload.display_name is not None:
        current_user.display_name = payload.display_name
        
    if payload.username is not None:
        # Vérifier l'unicité du username
        stmt = select(User).where(and_(User.username == payload.username, User.id != current_user.id))
        res = await db.execute(stmt)
        if res.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Username is already taken")
        current_user.username = payload.username
        
    if payload.timezone is not None:
        current_user.timezone = payload.timezone

    await db.commit()
    return {
        "status": "success",
        "user": {
            "id": str(current_user.id),
            "display_name": current_user.display_name,
            "username": current_user.username,
            "timezone": current_user.timezone
        }
    }


@router.get("/notifications/channels", response_model=List[NotificationChannelResponse])
async def list_notification_channels(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(NotificationChannel).where(NotificationChannel.user_id == current_user.id)
    result = await db.execute(stmt)
    channels = result.scalars().all()

    # Si aucun channel, on initialise les types standard
    if not channels:
        types = ["email", "push", "slack", "discord", "telegram"]
        for t in types:
            db.add(NotificationChannel(user_id=current_user.id, type=t, is_connected=False))
        await db.commit()
        
        stmt = select(NotificationChannel).where(NotificationChannel.user_id == current_user.id)
        result = await db.execute(stmt)
        channels = result.scalars().all()

    return channels


@router.patch("/notifications/channels/{id}", response_model=NotificationChannelResponse)
async def update_notification_channel(
    id: uuid.UUID,
    payload: NotificationChannelUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(NotificationChannel).where(
        and_(NotificationChannel.id == id, NotificationChannel.user_id == current_user.id)
    )
    result = await db.execute(stmt)
    channel = result.scalar_one_or_none()

    if not channel:
        raise HTTPException(status_code=404, detail="Notification channel not found")

    channel.config_json = payload.config_json
    channel.is_connected = payload.is_connected
    await db.commit()
    await db.refresh(channel)

    return channel
