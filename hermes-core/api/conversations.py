"""
hermes-core/api/conversations.py — CRUD conversations + messages + attachments.

Routes :
  GET    /api/conversations                    — liste (user_id, limit, agent_name?)
  POST   /api/conversations                    — create
  GET    /api/conversations/{id}              — détail avec messages
  PUT    /api/conversations/{id}              — update title/agent/model/tools
  DELETE /api/conversations/{id}              — delete (cascade messages + attachments)
  POST   /api/conversations/{id}/messages     — append message
  POST   /api/conversations/{id}/attachments  — multipart upload (file)
  DELETE /api/conversations/{id}/attachments/{att_id}  — delete file + row
"""

import logging
import os
import uuid
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db.session import get_db, settings
from db.models import Conversation, Message, Attachment
from .schemas import (
    ConversationCreate,
    ConversationUpdate,
    ConversationOut,
    ConversationDetail,
    MessageCreate,
    MessageOut,
    AttachmentOut,
)

logger = logging.getLogger("hermes.core.api.conversations")

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


def _conv_to_out(c: Conversation) -> ConversationOut:
    return ConversationOut(
        id=c.id,
        user_id=c.user_id,
        title=c.title,
        agent_name=c.agent_name,
        model=c.model,
        tool_names=c.tool_names or [],
        context_tokens=c.context_tokens,
        created_at=c.created_at,
        updated_at=c.updated_at,
    )


@router.get("", response_model=List[ConversationOut])
async def list_conversations(
    user_id: str = "default",
    limit: int = 50,
    agent_name: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Liste les conversations (par user_id, plus récentes d'abord)."""
    stmt = (
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .order_by(desc(Conversation.updated_at))
        .limit(limit)
    )
    if agent_name:
        stmt = stmt.where(Conversation.agent_name == agent_name)
    result = await db.execute(stmt)
    return [_conv_to_out(c) for c in result.scalars()]


@router.post("", response_model=ConversationOut, status_code=201)
async def create_conversation(
    payload: ConversationCreate,
    user_id: str = "default",
    db: AsyncSession = Depends(get_db),
):
    """Crée une conversation vide."""
    conv = Conversation(
        user_id=user_id,
        title=payload.title,
        agent_name=payload.agent_name,
        model=payload.model,
        tool_names=payload.tool_names,
        context_tokens=payload.context_tokens,
    )
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    return _conv_to_out(conv)


@router.get("/{conv_id}", response_model=ConversationDetail)
async def get_conversation(
    conv_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Détail d'une conversation (avec ses messages)."""
    stmt = (
        select(Conversation)
        .where(Conversation.id == conv_id)
        .options(selectinload(Conversation.messages))
    )
    result = await db.execute(stmt)
    conv = result.scalar_one_or_none()
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation introuvable")

    return ConversationDetail(
        id=conv.id,
        user_id=conv.user_id,
        title=conv.title,
        agent_name=conv.agent_name,
        model=conv.model,
        tool_names=conv.tool_names or [],
        context_tokens=conv.context_tokens,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        messages=[
            MessageOut(
                id=m.id,
                role=m.role,
                content=m.content,
                reasoning_details=m.reasoning_details,
                time=m.time,
            )
            for m in conv.messages
        ],
    )


@router.put("/{conv_id}", response_model=ConversationOut)
async def update_conversation(
    conv_id: int,
    payload: ConversationUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update conversation (title, agent_name, model, tool_names, context_tokens)."""
    conv = await db.get(Conversation, conv_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation introuvable")

    if payload.title is not None:
        conv.title = payload.title
    if payload.agent_name is not None:
        conv.agent_name = payload.agent_name
    if payload.model is not None:
        conv.model = payload.model
    if payload.tool_names is not None:
        conv.tool_names = payload.tool_names
    if payload.context_tokens is not None:
        conv.context_tokens = payload.context_tokens

    await db.commit()
    await db.refresh(conv)
    return _conv_to_out(conv)


@router.delete("/{conv_id}", status_code=204)
async def delete_conversation(
    conv_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Supprime une conversation (cascade messages + attachments)."""
    conv = await db.get(Conversation, conv_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation introuvable")

    # Supprimer les fichiers attachments associés
    stmt = select(Attachment).where(Attachment.conversation_id == conv_id)
    result = await db.execute(stmt)
    for att in result.scalars():
        try:
            os.remove(att.storage_path)
        except FileNotFoundError:
            pass

    await db.delete(conv)
    await db.commit()
    return None


@router.post("/{conv_id}/messages", response_model=MessageOut, status_code=201)
async def append_message(
    conv_id: int,
    payload: MessageCreate,
    db: AsyncSession = Depends(get_db),
):
    """Append un message à la conversation."""
    conv = await db.get(Conversation, conv_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation introuvable")

    msg = Message(
        conversation_id=conv_id,
        role=payload.role,
        content=payload.content,
        reasoning_details=payload.reasoning_details,
    )
    db.add(msg)

    # Mettre à jour updated_at de la conversation
    from datetime import datetime
    conv.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(msg)

    return MessageOut(
        id=msg.id,
        role=msg.role,
        content=msg.content,
        reasoning_details=msg.reasoning_details,
        time=msg.time,
    )


@router.post("/{conv_id}/attachments", response_model=AttachmentOut, status_code=201)
async def upload_attachment(
    conv_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload un fichier attaché à la conversation (multipart)."""
    conv = await db.get(Conversation, conv_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation introuvable")

    # Créer le répertoire de stockage si nécessaire
    storage_dir = os.path.join(settings.attachments_dir, str(conv_id))
    os.makedirs(storage_dir, exist_ok=True)

    # Générer un nom de fichier unique
    file_ext = os.path.splitext(file.filename)[1] if file.filename else ""
    storage_filename = f"{uuid.uuid4()}{file_ext}"
    storage_path = os.path.join(storage_dir, storage_filename)

    # Écrire le fichier
    content = await file.read()
    with open(storage_path, "wb") as f:
        f.write(content)

    # Créer la ligne DB
    att = Attachment(
        conversation_id=conv_id,
        filename=file.filename or storage_filename,
        mime_type=file.content_type or "application/octet-stream",
        size=len(content),
        storage_path=storage_path,
    )
    db.add(att)
    await db.commit()
    await db.refresh(att)

    return AttachmentOut(
        id=att.id,
        filename=att.filename,
        mime_type=att.mime_type,
        size=att.size,
        extracted=att.extracted,
        created_at=att.created_at,
    )


@router.delete("/{conv_id}/attachments/{att_id}", status_code=204)
async def delete_attachment(
    conv_id: int,
    att_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Supprime un attachment (fichier + ligne DB)."""
    att = await db.get(Attachment, att_id)
    if att is None or att.conversation_id != conv_id:
        raise HTTPException(status_code=404, detail="Attachment introuvable")

    try:
        os.remove(att.storage_path)
    except FileNotFoundError:
        pass

    await db.delete(att)
    await db.commit()
    return None