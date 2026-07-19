import uuid
import json
import asyncio
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.agent import Agent, AgentStatus
from app.models.message import Conversation, Message, MessageRole, Attachment
from app.models.workspace import WorkspaceMember
from app.api.chat.schemas import ConversationCreate, ConversationResponse, MessageSend, MessageResponse
from app.services.llm_router import stream_chat
from app.services.quota_checker import check_token_budget, deduct_tokens

router = APIRouter(tags=["chat"])


@router.get("/agents/{id}/conversations", response_model=List[ConversationResponse])
async def list_agent_conversations(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Récupérer l'agent
    stmt_agent = select(Agent).where(Agent.id == id)
    res_agent = await db.execute(stmt_agent)
    agent = res_agent.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Vérifier l'accès
    stmt_member = select(WorkspaceMember).where(
        and_(WorkspaceMember.workspace_id == agent.workspace_id, WorkspaceMember.user_id == current_user.id)
    )
    res_member = await db.execute(stmt_member)
    if not res_member.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Workspace access denied")

    # Lister les conversations de cet agent créées par l'utilisateur
    stmt = select(Conversation).where(
        and_(Conversation.agent_id == id, Conversation.user_id == current_user.id)
    ).order_by(Conversation.created_at.desc())
    
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/agents/{id}/conversations", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_agent_conversation(
    id: uuid.UUID,
    payload: ConversationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt_agent = select(Agent).where(Agent.id == id)
    res_agent = await db.execute(stmt_agent)
    agent = res_agent.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    stmt_member = select(WorkspaceMember).where(
        and_(WorkspaceMember.workspace_id == agent.workspace_id, WorkspaceMember.user_id == current_user.id)
    )
    res_member = await db.execute(stmt_member)
    if not res_member.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Workspace access denied")

    # Créer la conversation
    conversation = Conversation(
        agent_id=id,
        user_id=current_user.id,
        title=payload.title or f"Chat with {agent.name}"
    )
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)

    return conversation


@router.get("/conversations/{cid}/messages", response_model=List[MessageResponse])
async def get_conversation_messages(
    cid: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt_conv = select(Conversation).where(Conversation.id == cid)
    res_conv = await db.execute(stmt_conv)
    conv = res_conv.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if conv.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Conversation access denied")

    stmt_msg = select(Message).where(Message.conversation_id == cid).order_by(Message.created_at.asc())
    result_msg = await db.execute(stmt_msg)
    messages = result_msg.scalars().all()

    # Formater avec attachments
    res = []
    for msg in messages:
        stmt_att = select(Attachment).where(Attachment.message_id == msg.id)
        res_att = await db.execute(stmt_att)
        attachments = res_att.scalars().all()
        
        res.append({
            "id": msg.id,
            "conversation_id": msg.conversation_id,
            "role": msg.role,
            "content": msg.content,
            "metadata_json": msg.metadata_json,
            "tokens_used": msg.tokens_used,
            "created_at": msg.created_at,
            "attachments": attachments
        })

    return res


@router.post("/conversations/{cid}/messages")
async def send_message_and_stream_response(
    cid: uuid.UUID,
    payload: MessageSend,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Vérifier la conversation et l'accès
    stmt_conv = select(Conversation).where(Conversation.id == cid)
    res_conv = await db.execute(stmt_conv)
    conv = res_conv.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conv.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Conversation access denied")

    # 2. Récupérer l'agent
    stmt_agent = select(Agent).where(Agent.id == conv.agent_id)
    res_agent = await db.execute(stmt_agent)
    agent = res_agent.scalar_one_or_none()
    if not agent or agent.status != AgentStatus.active:
        raise HTTPException(status_code=400, detail="Agent is inactive or archived")

    # 3. Vérifier le budget jetons
    has_token_budget = await check_token_budget(db, current_user.id, tokens_needed=2000)
    if not has_token_budget and not current_user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Token budget exceeded. Contact your super admin to increase your monthly limit."
        )

    # 4. Enregistrer le message utilisateur
    user_msg = Message(
        conversation_id=cid,
        role=MessageRole.user,
        content=payload.content
    )
    db.add(user_msg)
    await db.commit()
    await db.refresh(user_msg)

    # Lier les attachments existants à ce message si nécessaire
    for att_id in payload.attachments:
        stmt_att = select(Attachment).where(
            and_(Attachment.id == att_id, Attachment.conversation_id == cid)
        )
        res_att = await db.execute(stmt_att)
        att = res_att.scalar_one_or_none()
        if att:
            att.message_id = user_msg.id
    
    await db.commit()

    # 5. Récupérer l'historique pour le LLM
    stmt_history = select(Message).where(Message.conversation_id == cid).order_by(Message.created_at.asc())
    res_history = await db.execute(stmt_history)
    history = res_history.scalars().all()

    llm_messages = [{"role": "system", "content": agent.system_prompt}]
    for msg in history:
        llm_messages.append({
            "role": msg.role.value if hasattr(msg.role, "value") else str(msg.role),
            "content": msg.content
        })

    # 6. Stream generator
    async def sse_generator():
        # Envoyer l'ID du message utilisateur créé
        yield {
            "event": "user_message",
            "data": json.dumps({"id": str(user_msg.id), "content": user_msg.content})
        }

        full_response = ""
        try:
            # Récupérer l'id du modèle associé
            model_id = str(agent.model_config_id) if agent.model_config_id else None
            
            async for chunk in stream_chat(
                model_config_id=model_id,
                messages=llm_messages,
                temperature=0.7
            ):
                if chunk == "[DONE]":
                    break
                full_response += chunk
                yield {
                    "event": "chunk",
                    "data": json.dumps({"text": chunk})
                }
                # Petit throttle pour le streaming
                await asyncio.sleep(0.01)
                
        except Exception as e:
            yield {
                "event": "error",
                "data": json.dumps({"detail": str(e)})
            }
            return

        # Enregistrer le message final de l'agent en base
        agent_msg = Message(
            conversation_id=cid,
            role=MessageRole.assistant,
            content=full_response
        )
        db.add(agent_msg)
        await db.commit()
        await db.refresh(agent_msg)

        # Déduire les tokens d'utilisation
        # Estimation à la louche : 1 token = 4 caractères
        total_tokens = int((len(payload.content) + len(full_response)) / 4)
        await deduct_tokens(db, current_user.id, total_tokens)

        yield {
            "event": "done",
            "data": json.dumps({
                "id": str(agent_msg.id),
                "content": agent_msg.content,
                "tokens_used": total_tokens
            })
        }

    return EventSourceResponse(sse_generator())
