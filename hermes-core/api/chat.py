"""
hermes-core/api/chat.py — Endpoint SSE chat avec boucle ReAct.

Routes :
  POST /api/chat/stream — SSE streaming (Master Prompt §11)
"""

import logging
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from orchestrator import execute_chat_stream

logger = logging.getLogger("hermes.core.api.chat")

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatStreamRequest(BaseModel):
    messages: List[Dict[str, str]] = Field(..., description="Historique conversation")
    model: Optional[str] = None
    conversation_id: Optional[int] = None
    agent_id: Optional[int] = None
    agent_name: Optional[str] = None
    tools_schema: Optional[List[Dict[str, Any]]] = None
    user_id: str = "default"


@router.post("/stream")
async def chat_stream(payload: ChatStreamRequest, request: Request):
    """
    SSE streaming du chat Hermes avec boucle ReAct (tool calls + approvals).

    Events émis (cf. useChatStream.ts côté UI) :
      - delta           : chunk texte du LLM
      - reasoning       : raisonnement exposé
      - tool_call       : LLM demande un outil
      - tool_result     : résultat d'outil
      - tool_calls_detected : nécessite approbation humaine (approval_id fourni)
      - done            : fin du stream
      - error           : erreur durant le stream
    """
    http_client = request.app.state.http

    async def event_generator():
        try:
            async for sse_event in execute_chat_stream(
                http_client=http_client,
                messages=payload.messages,
                model=payload.model or "",
                agent_id=payload.agent_id,
                conversation_id=payload.conversation_id,
                user_id=payload.user_id,
                tools_schema=payload.tools_schema,
            ):
                # Flush immédiat (critique pour SSE)
                yield sse_event
        except Exception as e:
            logger.exception("Chat stream error")
            yield f"data: {{\"type\":\"error\",\"message\":\"{e}\"}}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )