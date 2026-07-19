"""
hermes-core/db/models.py — Modèles SQLAlchemy 2.x async.

10 tables :
  - Conversation, Message, Attachment
  - Agent, Run, ToolCall
  - Approval, UsageEvent
  - AuditEvent, Tool (registry)
"""

from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Index,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .session import Base


# ---------------------------------------------------------------------------
# Conversations & Messages
# ---------------------------------------------------------------------------
class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = {"schema": "hermes_core"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(128), nullable=False, default="default")
    title: Mapped[str] = mapped_column(String(256), nullable=False, default="Nouvelle conversation")
    agent_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    tool_names: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=list)
    context_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=128000)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    messages: Mapped[List["Message"]] = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.time"
    )

    __table_args__ = (
        Index("ix_conversations_user_updated", "user_id", "updated_at"),
        {"schema": "hermes_core"},
    )


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = {"schema": "hermes_core"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False)  # user | assistant | system | tool
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    reasoning_details: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON, nullable=True)
    time: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="messages")

    __table_args__ = (
        Index("ix_messages_conv_time", "conversation_id", "time"),
        {"schema": "hermes_core"},
    )


class Attachment(Base):
    __tablename__ = "attachments"
    __table_args__ = {"schema": "hermes_core"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    extracted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


# ---------------------------------------------------------------------------
# Agents
# ---------------------------------------------------------------------------
class Agent(Base):
    __tablename__ = "agents"
    __table_args__ = {"schema": "hermes_core"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False, default="")
    model: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    temperature: Mapped[float] = mapped_column(Integer, nullable=False, default=7)  # stored as int*10 to avoid float quirks ; decode as /10
    # Note: temperature 0.7 stored as 7. Will revisit if needed.
    max_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=2000)
    tools: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=list)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_preset: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )


# ---------------------------------------------------------------------------
# Runs (Tasks) & Tool Calls
# ---------------------------------------------------------------------------
class Run(Base):
    __tablename__ = "runs"
    __table_args__ = {"schema": "hermes_core"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    agent_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="running")
    # status: running | queued | waiting_approval | completed | failed | cancelled
    title: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    input: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    output: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # 0-100
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    tool_calls: Mapped[List["ToolCall"]] = relationship(
        "ToolCall", back_populates="run", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_runs_conv_status", "conversation_id", "status"),
        Index("ix_runs_status_started", "status", "started_at"),
        {"schema": "hermes_core"},
    )


class ToolCall(Base):
    __tablename__ = "tool_calls"
    __table_args__ = {"schema": "hermes_core"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"), nullable=False)
    tool_name: Mapped[str] = mapped_column(String(128), nullable=False)
    args: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    result: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    requires_approval: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    executed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    # status: pending | awaiting_approval | running | completed | failed | rejected
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    run: Mapped["Run"] = relationship("Run", back_populates="tool_calls")
    approvals: Mapped[List["Approval"]] = relationship(
        "Approval", back_populates="tool_call", cascade="all, delete-orphan"
    )


class Approval(Base):
    __tablename__ = "approvals"
    __table_args__ = {"schema": "hermes_core"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tool_call_id: Mapped[int] = mapped_column(
        ForeignKey("tool_calls.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    # status: pending | approved | rejected | modified
    decided_by: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    modified_args: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    tool_call: Mapped["ToolCall"] = relationship("ToolCall", back_populates="approvals")


# ---------------------------------------------------------------------------
# Usage & Audit
# ---------------------------------------------------------------------------
class UsageEvent(Base):
    """Compteur tokens / cost par appel LLM."""
    __tablename__ = "usage_events"
    __table_args__ = {"schema": "hermes_core"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[Optional[int]] = mapped_column(ForeignKey("runs.id", ondelete="SET NULL"), nullable=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_estimate: Mapped[float] = mapped_column(Integer, nullable=False, default=0)  # stored as cents*100
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


class AuditEvent(Base):
    """Log d'audit (Master Prompt §62)."""
    __tablename__ = "audit_events"
    __table_args__ = {"schema": "hermes_core"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(128), nullable=False, default="default")
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    target: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ok")
    ip: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    request_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_audit_user_time", "user_id", "timestamp"),
        {"schema": "hermes_core"},
    )


# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------
class Tool(Base):
    """Catalogue des outils disponibles (DB-backed, mcp + n8n + custom)."""
    __tablename__ = "tools"
    __table_args__ = {"schema": "hermes_core"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    parameters: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    requires_approval: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="manual")
    # source: mcp | n8n | manual
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)