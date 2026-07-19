import uuid
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.workspace import WorkspaceMember
from app.models.job import Job, JobRun, JobStatus, JobRunStatus
from app.models.agent import Agent

router = APIRouter(tags=["jobs"])


class JobCreate(BaseModel):
    agent_id: uuid.UUID
    name: str = Field(..., max_length=300)
    prompt: str
    cron_expression: str = Field(..., max_length=100)


class JobUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=300)
    prompt: Optional[str] = None
    cron_expression: Optional[str] = Field(None, max_length=100)
    status: Optional[str] = None  # active, paused


class JobResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    agent_id: uuid.UUID
    name: str
    prompt: str
    cron_expression: str
    next_run_at: Optional[datetime]
    status: str
    created_by: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True


class JobRunResponse(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    status: str
    result_message_id: Optional[uuid.UUID]
    error: Optional[str]

    class Config:
        from_attributes = True


@router.get("/workspaces/{wid}/jobs", response_model=List[JobResponse])
async def list_workspace_jobs(
    wid: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt_member = select(WorkspaceMember).where(
        and_(WorkspaceMember.workspace_id == wid, WorkspaceMember.user_id == current_user.id)
    )
    res_member = await db.execute(stmt_member)
    if not res_member.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Workspace access denied")

    stmt = select(Job).where(Job.workspace_id == wid).order_by(Job.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/workspaces/{wid}/jobs", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    wid: uuid.UUID,
    payload: JobCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt_member = select(WorkspaceMember).where(
        and_(WorkspaceMember.workspace_id == wid, WorkspaceMember.user_id == current_user.id)
    )
    res_member = await db.execute(stmt_member)
    if not res_member.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Workspace access denied")

    # Vérifier l'agent
    stmt_agent = select(Agent).where(Agent.id == payload.agent_id)
    res_agent = await db.execute(stmt_agent)
    agent = res_agent.scalar_one_or_none()
    if not agent or agent.workspace_id != wid:
        raise HTTPException(status_code=400, detail="Invalid agent configuration for this workspace")

    # Créer le job
    job = Job(
        workspace_id=wid,
        agent_id=payload.agent_id,
        name=payload.name,
        prompt=payload.prompt,
        cron_expression=payload.cron_expression,
        status=JobStatus.active,
        created_by=current_user.id
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Celery Beat synchronisera périodiquement la planification basée sur les cron_expressions
    return job


@router.get("/jobs/{id}", response_model=JobResponse)
async def get_job(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(Job).where(Job.id == id)
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    stmt_member = select(WorkspaceMember).where(
        and_(WorkspaceMember.workspace_id == job.workspace_id, WorkspaceMember.user_id == current_user.id)
    )
    res_member = await db.execute(stmt_member)
    if not res_member.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Workspace access denied")

    return job


@router.patch("/jobs/{id}", response_model=JobResponse)
async def update_job(
    id: uuid.UUID,
    payload: JobUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(Job).where(Job.id == id)
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    stmt_member = select(WorkspaceMember).where(
        and_(WorkspaceMember.workspace_id == job.workspace_id, WorkspaceMember.user_id == current_user.id)
    )
    res_member = await db.execute(stmt_member)
    if not res_member.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Workspace access denied")

    if payload.name is not None:
        job.name = payload.name
    if payload.prompt is not None:
        job.prompt = payload.prompt
    if payload.cron_expression is not None:
        job.cron_expression = payload.cron_expression
    if payload.status is not None:
        job.status = payload.status

    await db.commit()
    await db.refresh(job)
    return job


@router.delete("/jobs/{id}")
async def delete_job(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(Job).where(Job.id == id)
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    stmt_member = select(WorkspaceMember).where(
        and_(WorkspaceMember.workspace_id == job.workspace_id, WorkspaceMember.user_id == current_user.id)
    )
    res_member = await db.execute(stmt_member)
    if not res_member.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Workspace access denied")

    await db.delete(job)
    await db.commit()
    return {"status": "success", "message": "Job deleted successfully"}


@router.get("/jobs/{id}/runs", response_model=List[JobRunResponse])
async def list_job_runs(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt_job = select(Job).where(Job.id == id)
    res_job = await db.execute(stmt_job)
    job = res_job.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    stmt_member = select(WorkspaceMember).where(
        and_(WorkspaceMember.workspace_id == job.workspace_id, WorkspaceMember.user_id == current_user.id)
    )
    res_member = await db.execute(stmt_member)
    if not res_member.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Workspace access denied")

    stmt_runs = select(JobRun).where(JobRun.job_id == id).order_by(JobRun.started_at.desc())
    result = await db.execute(stmt_runs)
    return result.scalars().all()


@router.post("/jobs/{id}/run-now")
async def trigger_job_now(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt_job = select(Job).where(Job.id == id)
    res_job = await db.execute(stmt_job)
    job = res_job.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    stmt_member = select(WorkspaceMember).where(
        and_(WorkspaceMember.workspace_id == job.workspace_id, WorkspaceMember.user_id == current_user.id)
    )
    res_member = await db.execute(stmt_member)
    if not res_member.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Workspace access denied")

    # Lancer le job via Celery en tâche de fond de suite
    from app.workers.tasks import run_scheduled_job_task
    # trigger async task execution
    task_res = run_scheduled_job_task.delay(str(job.id))
    
    return {"status": "success", "message": "Job execution triggered", "task_id": task_res.id}
