"""
hermes-core/api/runs.py — Tasks / Runs (Master Prompt §20-21).

Routes :
  GET    /api/runs              — liste filtrée par status / conversation_id / limit
  GET    /api/runs/{id}         — détail avec tool_calls + approvals
  POST   /api/runs/{id}/cancel  — cancel un run en cours
"""

import logging
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db.session import get_db
from db.models import Run, ToolCall, Approval

logger = logging.getLogger("hermes.core.api.runs")

router = APIRouter(prefix="/api/runs", tags=["runs"])


class ToolCallOut(BaseModel):
    id: int
    tool_name: str
    args: dict
    result: Optional[dict] = None
    requires_approval: bool
    approved_at: Optional[datetime] = None
    executed_at: Optional[datetime] = None
    status: str

    class Config:
        from_attributes = True


class ApprovalOut(BaseModel):
    id: int
    tool_call_id: int
    status: str
    decided_by: Optional[str] = None
    decided_at: Optional[datetime] = None
    modified_args: Optional[dict] = None
    created_at: datetime

    class Config:
        from_attributes = True


class RunOut(BaseModel):
    id: int
    conversation_id: int
    agent_name: Optional[str]
    status: str
    title: Optional[str]
    input: Optional[str]
    output: Optional[str]
    progress: int
    started_at: datetime
    finished_at: Optional[datetime] = None
    error: Optional[str] = None

    class Config:
        from_attributes = True


class RunDetail(RunOut):
    tool_calls: List[ToolCallOut] = []
    approvals: List[ApprovalOut] = []


@router.get("", response_model=List[RunOut])
async def list_runs(
    status: Optional[str] = None,
    conversation_id: Optional[int] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """Liste des runs filtrés."""
    stmt = select(Run).order_by(desc(Run.started_at)).limit(limit)
    if status:
        stmt = stmt.where(Run.status == status)
    if conversation_id:
        stmt = stmt.where(Run.conversation_id == conversation_id)
    result = await db.execute(stmt)
    return list(result.scalars())


@router.get("/{run_id}", response_model=RunDetail)
async def get_run(run_id: int, db: AsyncSession = Depends(get_db)):
    """Détail d'un run avec tool_calls et approvals."""
    stmt = (
        select(Run)
        .where(Run.id == run_id)
        .options(
            selectinload(Run.tool_calls).selectinload(ToolCall.approvals),
        )
    )
    result = await db.execute(stmt)
    run = result.scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=404, detail="Run introuvable")

    return RunDetail(
        id=run.id,
        conversation_id=run.conversation_id,
        agent_name=run.agent_name,
        status=run.status,
        title=run.title,
        input=run.input,
        output=run.output,
        progress=run.progress,
        started_at=run.started_at,
        finished_at=run.finished_at,
        error=run.error,
        tool_calls=[
            ToolCallOut(
                id=tc.id,
                tool_name=tc.tool_name,
                args=tc.args or {},
                result=tc.result,
                requires_approval=tc.requires_approval,
                approved_at=tc.approved_at,
                executed_at=tc.executed_at,
                status=tc.status,
            )
            for tc in run.tool_calls
        ],
        approvals=[
            ApprovalOut(
                id=tc.approvals[0].id,
                tool_call_id=tc.id,
                status=tc.approvals[0].status,
                decided_by=tc.approvals[0].decided_by,
                decided_at=tc.approvals[0].decided_at,
                modified_args=tc.approvals[0].modified_args,
                created_at=tc.approvals[0].created_at,
            )
            for tc in run.tool_calls
            if tc.approvals
        ],
    )


@router.post("/{run_id}/cancel")
async def cancel_run(run_id: int, db: AsyncSession = Depends(get_db)):
    """Annule un run en cours."""
    run = await db.get(Run, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run introuvable")
    if run.status not in ("running", "waiting_approval", "queued"):
        raise HTTPException(
            status_code=400,
            detail=f"Run déjà {run.status}, impossible d'annuler",
        )

    run.status = "cancelled"
    run.finished_at = datetime.utcnow()
    await db.commit()
    return {"status": "cancelled", "run_id": run_id}