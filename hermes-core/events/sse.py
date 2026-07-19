"""
hermes-core/events/sse.py — Event Bus SSE (Master Prompt §65).

Endpoints :
  GET /api/events/stream?conversation_id? — SSE entrant pour la UI

Implémentation MVP : in-memory asyncio.Queue per connection.
Pas de persistance events (éphémères). Suffisant pour live activity UI.

Events émis :
  - task.created / started / progress / completed / failed
  - tool.started / completed
  - approval.required / resolved
  - agent.status.changed
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any, Set

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

logger = logging.getLogger("hermes.core.events")

router = APIRouter(prefix="/api/events", tags=["events"])

# Set de queues actives (one per SSE connection)
_active_queues: Set[asyncio.Queue] = set()
_event_history: list = []  # Ring buffer simple (50 derniers events)
_MAX_HISTORY = 50


async def publish_event(event_type: str, payload: Dict[str, Any]) -> None:
    """
    Publie un event à tous les clients SSE connectés.

    Utilisé par executor, dispatchers, etc.
    """
    event = {
        "type": event_type,
        "id": len(_event_history) + 1,
        "timestamp": datetime.utcnow().isoformat(),
        "payload": payload,
    }

    _event_history.append(event)
    if len(_event_history) > _MAX_HISTORY:
        _event_history.pop(0)

    # Fan-out non-bloquant
    for q in list(_active_queues):
        try:
            q.put_nowait(event)
        except asyncio.QueueFull:
            logger.warning("Event queue full, dropping for subscriber")


@router.get("/stream")
async def events_stream(
    request: Request,
    conversation_id: Optional[int] = None,
    replay: bool = True,
):
    """
    SSE stream des events.

    query params :
      - conversation_id : filtre (MVP : on envoie tout, le client filtre côté UI)
      - replay : si True, renvoie l'historique récent au connect
    """
    queue: asyncio.Queue = asyncio.Queue(maxsize=200)
    _active_queues.add(queue)

    async def event_generator():
        try:
            # Replay de l'historique récent
            if replay:
                for ev in _event_history[-20:]:
                    yield _format_sse(ev)

            # Stream live
            while True:
                if await request.is_disconnected():
                    break
                try:
                    ev = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield _format_sse(ev)
                except asyncio.TimeoutError:
                    # Heartbeat pour keep-alive
                    yield ": heartbeat\n\n"
        finally:
            _active_queues.discard(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


def _format_sse(ev: Dict[str, Any]) -> str:
    import json
    return f"data: {json.dumps(ev, default=str)}\n\n"


@router.get("/history")
async def events_history(limit: int = 20):
    """Renvoie l'historique récent (pour init UI)."""
    return {"events": _event_history[-limit:]}