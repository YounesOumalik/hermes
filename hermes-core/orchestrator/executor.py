"""
hermes-core/orchestrator/executor.py — ReAct loop principal.

Implémente le flux Master Prompt §19 :
  User → Intent Analysis → Task Planning → Agent Selection →
  Tool Selection → Execution → Validation → Response

Pour le MVP, on simplifie :
  - Reçoit POST /api/chat/stream avec messages + agent_id? + conversation_id?
  - Charge l'agent (system_prompt injecté en messages[0])
  - Crée un Run en DB (status=running)
  - Stream vers hermes-llm-proxy via SSE
  - À chaque chunk : yield SSE "delta" ou "reasoning"
  - Si tool_calls : yield "tool_call", dispatch, yield "tool_result",
    réinjecter dans messages, re-stream LLM (max 5 itérations)
  - Si requires_confirmation : yield "tool_calls_detected" avec approval_id,
    stopper la boucle (l'UI devra approve via /api/approvals/{id}/resolve)
  - Fin : yield "done", persiste messages, Run.status=completed
  - Erreur : yield "error", Run.status=failed
"""

import json
import logging
from datetime import datetime
from typing import AsyncIterator, List, Dict, Any, Optional

import httpx
from sqlalchemy import select

from config import settings
from db.session import async_session
from db.models import (
    Conversation,
    Message,
    Agent,
    Run,
    ToolCall,
    Approval,
)
from tools.dispatcher import route_tool_call, ToolCallResult

logger = logging.getLogger("hermes.core.executor")


SSE_EVENTS = {
    "delta": "Contenu texte incrémental du LLM",
    "reasoning": "Raisonnement du LLM (si exposé)",
    "tool_call": "Le LLM demande un tool call",
    "tool_result": "Résultat du tool call exécuté",
    "tool_calls_detected": "Tool call nécessite une approbation humaine",
    "done": "Stream terminé avec succès",
    "error": "Erreur durant le stream",
}


async def execute_chat_stream(
    http_client: httpx.AsyncClient,
    messages: List[Dict[str, str]],
    model: str,
    agent_id: Optional[int] = None,
    conversation_id: Optional[int] = None,
    user_id: str = "default",
    tools_schema: Optional[List[Dict[str, Any]]] = None,
) -> AsyncIterator[str]:
    """
    Exécute un chat SSE avec boucle ReAct.

    Yields des SSE events au format:
      data: {"type": "delta", "content": "..."}\\n\\n
      data: {"type": "tool_call", "tool_name": "...", "args": {...}}\\n\\n
      data: {"type": "done", "run_id": N, "message_id": N}\\n\\n
    """
    run_id: Optional[int] = None
    agent_name: Optional[str] = None
    system_prompt: Optional[str] = None

    # 1. Charger l'agent si spécifié
    if agent_id:
        async with async_session() as db:
            stmt = select(Agent).where(Agent.id == agent_id)
            result = await db.execute(stmt)
            agent = result.scalar_one_or_none()
            if agent:
                system_prompt = agent.system_prompt
                agent_name = agent.name
                if not model and agent.model:
                    model = agent.model

    # 2. Injecter system_prompt en messages[0] si pas déjà présent
    working_messages = list(messages)
    if system_prompt and (not working_messages or working_messages[0].get("role") != "system"):
        working_messages.insert(0, {"role": "system", "content": system_prompt})

    # 3. Charger la conversation et créer le Run
    if conversation_id:
        async with async_session() as db:
            conv = await db.get(Conversation, conversation_id)
            if conv:
                run = Run(
                    conversation_id=conversation_id,
                    agent_name=agent_name,
                    status="running",
                    title=f"Chat with {agent_name or 'Hermes'}",
                    input=working_messages[-1].get("content", "")[:500] if working_messages else "",
                )
                db.add(run)
                await db.commit()
                await db.refresh(run)
                run_id = run.id

    # 4. Boucle ReAct (max N itérations)
    full_content = ""
    reasoning_acc = []
    max_iterations = settings.tool_executor_max_iterations

    try:
        for iteration in range(max_iterations):
            # Stream LLM
            req_payload = {
                "model": model,
                "messages": working_messages,
                "stream": True,
                "temperature": 0.7,
                "max_tokens": 4000,
            }
            if tools_schema:
                req_payload["tools"] = tools_schema

            try:
                resp = await http_client.post(
                    f"{settings.hermes_llm_proxy_url}/v1/chat/completions",
                    json=req_payload,
                    headers={"Authorization": f"Bearer {settings.hermes_llm_proxy_token}"},
                    timeout=httpx.Timeout(120.0, connect=10.0),
                )
                resp.raise_for_status()
            except httpx.HTTPStatusError as e:
                err_msg = f"LLM proxy HTTP {e.response.status_code}: {e.response.text[:200]}"
                yield _sse("error", {"message": err_msg, "run_id": run_id})
                await _finalize_run(run_id, "failed", error=err_msg)
                return
            except Exception as e:
                err_msg = f"LLM proxy error: {e}"
                yield _sse("error", {"message": err_msg, "run_id": run_id})
                await _finalize_run(run_id, "failed", error=err_msg)
                return

            # Parse SSE stream
            tool_calls_detected: List[Dict[str, Any]] = []
            finish_reason = None

            async for chunk in _iter_sse_chunks(resp):
                chunk_type = chunk.get("type")

                if chunk_type == "delta":
                    delta = chunk.get("content", "")
                    full_content += delta
                    yield _sse("delta", {"content": delta})

                elif chunk_type == "reasoning":
                    reasoning_acc.append(chunk.get("content", ""))
                    yield _sse("reasoning", {"content": chunk.get("content", "")})

                elif chunk_type == "tool_calls":
                    tool_calls_detected = chunk.get("tool_calls", [])

                elif chunk_type == "done":
                    finish_reason = chunk.get("finish_reason", "stop")

            # Si pas de tool calls → fin de boucle
            if not tool_calls_detected:
                break

            # Traiter les tool calls
            tool_messages: List[Dict[str, str]] = []
            approval_ids: List[int] = []

            for tc in tool_calls_detected:
                tool_name = tc.get("function", {}).get("name", "") or tc.get("name", "")
                tool_args_raw = tc.get("function", {}).get("arguments", "{}") or tc.get("arguments", "{}")
                tool_call_id = tc.get("id", f"call_{iteration}_{len(tool_messages)}")

                try:
                    tool_args = json.loads(tool_args_raw) if isinstance(tool_args_raw, str) else tool_args_raw
                except json.JSONDecodeError:
                    tool_args = {}

                # Yield tool_call event
                yield _sse("tool_call", {
                    "id": tool_call_id,
                    "name": tool_name,
                    "args": tool_args,
                })

                # Dispatch
                result = await route_tool_call(tool_name, tool_args, http_client)

                # Persist ToolCall
                tool_call_db_id = await _save_tool_call(
                    run_id=run_id,
                    tool_name=tool_name,
                    args=tool_args,
                    result=result.to_dict() if result.data else None,
                    requires_approval=result.requires_approval,
                    status=("awaiting_approval" if result.requires_approval else
                            "completed" if result.success else "failed"),
                )

                # Cas 1 : requires_approval → yield tool_calls_detected + stopper
                if result.requires_approval:
                    approval_id = await _create_approval(tool_call_db_id, tool_args)
                    approval_ids.append(approval_id)
                    yield _sse("tool_calls_detected", {
                        "id": tool_call_id,
                        "approval_id": approval_id,
                        "tool_name": tool_name,
                        "args": tool_args,
                        "message": "Tool call nécessite approbation humaine",
                    })
                    # Stocker pour le message tool de la prochaine itération
                    tool_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "name": tool_name,
                        "content": json.dumps({
                            "requires_approval": True,
                            "approval_id": approval_id,
                            "message": "Cette action nécessite une approbation.",
                        }),
                    })
                    continue

                # Cas 2 : succès ou échec
                yield _sse("tool_result", {
                    "id": tool_call_id,
                    "tool_name": tool_name,
                    "success": result.success,
                    "result": result.data if result.success else None,
                    "error": result.error,
                })

                # Tool message pour la prochaine itération
                tool_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "name": tool_name,
                    "content": json.dumps(result.data if result.success else {"error": result.error}),
                })

            # Si on a des approvals pending, on stoppe la boucle (l'UI doit approve)
            if approval_ids:
                # Yield done avec indication
                yield _sse("done", {
                    "run_id": run_id,
                    "approval_ids": approval_ids,
                    "waiting_for_approval": True,
                })
                await _finalize_run(run_id, "waiting_approval")
                return

            # Réinjecter tool calls dans messages + tool responses
            # (format OpenAI : tool_calls dans le message assistant)
            working_messages.append({
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": tc.get("id", f"call_{iteration}_{i}"),
                        "type": "function",
                        "function": {
                            "name": tc.get("function", {}).get("name", "") or tc.get("name", ""),
                            "arguments": json.dumps(tc.get("function", {}).get("arguments", "{}") or tc.get("arguments", "{}")),
                        },
                    }
                    for i, tc in enumerate(tool_calls_detected)
                ],
            })
            working_messages.extend(tool_messages)

        # 5. Stream terminé : persister messages et finaliser le run
        async with async_session() as db:
            # Persister message assistant
            if conversation_id and full_content:
                msg = Message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=full_content,
                    reasoning_details=reasoning_acc if reasoning_acc else None,
                )
                db.add(msg)
                # Mettre à jour updated_at conversation
                conv = await db.get(Conversation, conversation_id)
                if conv:
                    conv.updated_at = datetime.utcnow()
                await db.commit()
                await db.refresh(msg)
                message_id = msg.id
            else:
                message_id = None

        yield _sse("done", {"run_id": run_id, "message_id": message_id})
        await _finalize_run(run_id, "completed", output=full_content)

    except Exception as e:
        logger.exception("Executor error")
        yield _sse("error", {"message": str(e), "run_id": run_id})
        await _finalize_run(run_id, "failed", error=str(e))


def _sse(event_type: str, data: Dict[str, Any]) -> str:
    """Formate un event SSE."""
    payload = {"type": event_type, **data}
    return f"data: {json.dumps(payload, default=str)}\n\n"


async def _iter_sse_chunks(resp: httpx.Response) -> AsyncIterator[Dict[str, Any]]:
    """
    Itère les chunks SSE du LLM proxy et les parse en dicts unifiés.

    Convertit le format OpenAI en notre format unifié:
      {"type": "delta", "content": "..."} | "reasoning" | "tool_calls" | "done"
    """
    accumulated_tool_calls: Dict[int, Dict[str, Any]] = {}
    finish_reason = None

    async for line in resp.aiter_lines():
        if not line or not line.startswith("data: "):
            continue
        data_str = line[6:].strip()
        if data_str == "[DONE]":
            break
        try:
            chunk = json.loads(data_str)
        except json.JSONDecodeError:
            continue

        if not chunk.get("choices"):
            continue
        choice = chunk["choices"][0]
        delta = choice.get("delta", {})
        finish_reason = choice.get("finish_reason") or finish_reason

        # Content
        if "content" in delta and delta["content"]:
            yield {"type": "delta", "content": delta["content"]}

        # Reasoning (si exposé par le provider)
        if "reasoning_content" in delta and delta["reasoning_content"]:
            yield {"type": "reasoning", "content": delta["reasoning_content"]}

        # Tool calls (accumulation OpenAI stream format)
        if "tool_calls" in delta:
            for tc_delta in delta["tool_calls"]:
                idx = tc_delta.get("index", 0)
                if idx not in accumulated_tool_calls:
                    accumulated_tool_calls[idx] = {
                        "id": tc_delta.get("id", f"call_{idx}"),
                        "type": "function",
                        "function": {"name": "", "arguments": ""},
                    }
                if "id" in tc_delta:
                    accumulated_tool_calls[idx]["id"] = tc_delta["id"]
                if "function" in tc_delta:
                    fn = tc_delta["function"]
                    if "name" in fn:
                        accumulated_tool_calls[idx]["function"]["name"] = fn["name"]
                    if "arguments" in fn:
                        accumulated_tool_calls[idx]["function"]["arguments"] += fn["arguments"]

    # Yield tool_calls à la fin (après accumulation)
    if accumulated_tool_calls:
        yield {
            "type": "tool_calls",
            "tool_calls": [accumulated_tool_calls[i] for i in sorted(accumulated_tool_calls.keys())],
        }

    yield {"type": "done", "finish_reason": finish_reason}


async def _save_tool_call(
    run_id: Optional[int],
    tool_name: str,
    args: Dict[str, Any],
    result: Optional[Dict[str, Any]],
    requires_approval: bool,
    status: str,
) -> int:
    """Persiste un ToolCall en DB, retourne son ID."""
    if not run_id:
        return 0
    async with async_session() as db:
        tc = ToolCall(
            run_id=run_id,
            tool_name=tool_name,
            args=args,
            result=result,
            requires_approval=requires_approval,
            executed_at=datetime.utcnow() if not requires_approval else None,
            status=status,
        )
        db.add(tc)
        await db.commit()
        await db.refresh(tc)
        return tc.id


async def _create_approval(tool_call_id: int, args: Dict[str, Any]) -> int:
    """Crée une Approval row pour un tool call sensible."""
    async with async_session() as db:
        approval = Approval(
            tool_call_id=tool_call_id,
            status="pending",
        )
        db.add(approval)
        await db.commit()
        await db.refresh(approval)
        return approval.id


async def _finalize_run(
    run_id: Optional[int],
    status: str,
    output: Optional[str] = None,
    error: Optional[str] = None,
) -> None:
    """Met à jour le Run final."""
    if not run_id:
        return
    async with async_session() as db:
        run = await db.get(Run, run_id)
        if run:
            run.status = status
            if output is not None:
                run.output = output
            if error is not None:
                run.error = error
            if status in ("completed", "failed", "waiting_approval", "cancelled"):
                run.finished_at = datetime.utcnow()
                if run.started_at:
                    duration = (run.finished_at - run.started_at).total_seconds()
                    # Optionnel : stocker duration
            await db.commit()