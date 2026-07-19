"""
hermes-core/api/approvals.py — Approval system (Master Prompt §22).

Routes :
  GET  /api/approvals                       — liste (filtre status, agent)
  POST /api/approvals/{id}/resolve          — approve / reject / modify
"""

import logging
from datetime import datetime
from typing import Optional, List

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from db.models import Approval, ToolCall, Run
from config import settings

logger = logging.getLogger("hermes.core.api.approvals")

router = APIRouter(prefix="/api/approvals", tags=["approvals"])


class ApprovalResolve(BaseModel):
    decision: str  # "approve" | "reject" | "modify"
    decided_by: str = "default"
    modified_args: Optional[dict] = None


class ApprovalOut(BaseModel):
    id: int
    tool_call_id: int
    tool_name: Optional[str] = None
    args: Optional[dict] = None
    status: str
    decided_by: Optional[str] = None
    decided_at: Optional[datetime] = None
    modified_args: Optional[dict] = None
    created_at: datetime
    run_id: Optional[int] = None

    class Config:
        from_attributes = True


@router.get("", response_model=List[ApprovalOut])
async def list_approvals(
    status: Optional[str] = "pending",
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """Liste des approvals (filtre par status)."""
    stmt = (
        select(Approval, ToolCall, Run)
        .join(ToolCall, Approval.tool_call_id == ToolCall.id)
        .join(Run, ToolCall.run_id == Run.id)
        .order_by(desc(Approval.created_at))
        .limit(limit)
    )
    if status:
        stmt = stmt.where(Approval.status == status)
    result = await db.execute(stmt)
    rows = result.all()

    out = []
    for approval, tool_call, run in rows:
        out.append(ApprovalOut(
            id=approval.id,
            tool_call_id=approval.tool_call_id,
            tool_name=tool_call.tool_name,
            args=tool_call.args,
            status=approval.status,
            decided_by=approval.decided_by,
            decided_at=approval.decided_at,
            modified_args=approval.modified_args,
            created_at=approval.created_at,
            run_id=run.id,
        ))
    return out


@router.post("/{approval_id}/resolve")
async def resolve_approval(
    approval_id: int,
    payload: ApprovalResolve,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Résout une approval : approve / reject / modify.

    Si approve :
      - Marque l'approval comme approved
      - Re-dispatch le tool call avec confirmed=true
      - Marque le ToolCall comme completed/failed
    Si reject :
      - Marque l'approval + ToolCall comme rejected
    Si modify :
      - Update modified_args
      - Puis approve avec les nouveaux args
    """
    approval = await db.get(Approval, approval_id)
    if approval is None:
        raise HTTPException(status_code=404, detail="Approval introuvable")
    if approval.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Approval déjà {approval.status}",
        )

    tool_call = await db.get(ToolCall, approval.tool_call_id)
    if tool_call is None:
        raise HTTPException(status_code=404, detail="ToolCall introuvable")

    decision = payload.decision.lower()
    if decision not in ("approve", "reject", "modify"):
        raise HTTPException(status_code=400, detail=f"Décision invalide: {decision}")

    http_client = request.app.state.http

    # Reject → juste marquer
    if decision == "reject":
        approval.status = "rejected"
        approval.decided_by = payload.decided_by
        approval.decided_at = datetime.utcnow()
        tool_call.status = "rejected"
        await db.commit()
        return {"status": "rejected", "approval_id": approval_id}

    # Modify → update args, puis approve
    final_args = payload.modified_args or tool_call.args or {}
    if decision == "modify" and payload.modified_args:
        approval.modified_args = payload.modified_args

    # Approve (ou modify après update args) → re-dispatch avec confirmed=true
    from tools.dispatcher import route_tool_call
    result = await route_tool_call(
        tool_call.tool_name,
        final_args,
        http_client,
        confirmed=True,  # Bypass approval gate
    )

    approval.status = "approved" if result.success else "failed"
    approval.decided_by = payload.decided_by
    approval.decided_at = datetime.utcnow()

    tool_call.status = "completed" if result.success else "failed"
    tool_call.approved_at = datetime.utcnow()
    tool_call.executed_at = datetime.utcnow()
    tool_call.result = result.to_dict()

    await db.commit()

    return {
        "status": approval.status,
        "approval_id": approval_id,
        "tool_call_id": tool_call.id,
        "result": result.to_dict(),
    }