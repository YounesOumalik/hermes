from sqlalchemy import String, Text, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel
import enum


class JobStatus(str, enum.Enum):
    active = "active"
    paused = "paused"
    completed = "completed"


class JobRunStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    success = "success"
    failed = "failed"


class Job(BaseModel):
    __tablename__ = "jobs"

    workspace_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    agent_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    cron_expression: Mapped[str] = mapped_column(String(100))
    next_run_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(30), default=JobStatus.active)
    created_by: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    workspace = relationship("Workspace", back_populates="jobs")
    agent = relationship("Agent", back_populates="jobs")
    runs: Mapped[list["JobRun"]] = relationship("JobRun", back_populates="job", cascade="all, delete-orphan")


class JobRun(BaseModel):
    __tablename__ = "job_runs"

    job_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    started_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(30), default=JobRunStatus.pending)
    result_message_id: Mapped[str | None] = mapped_column(UUID(as_uuid=True))
    error: Mapped[str | None] = mapped_column(Text)

    job = relationship("Job", back_populates="runs")
