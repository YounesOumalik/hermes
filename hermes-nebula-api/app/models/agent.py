from sqlalchemy import String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel
import enum


class AgentStatus(str, enum.Enum):
    active = "active"
    paused = "paused"
    archived = "archived"


class ToolBindingStatus(str, enum.Enum):
    off = "off"
    on_demand = "on_demand"
    always_on = "always_on"


class Agent(BaseModel):
    __tablename__ = "agents"

    workspace_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    avatar_color: Mapped[str] = mapped_column(String(7), default="#58a6ff")
    system_prompt: Mapped[str] = mapped_column(Text, default="You are a helpful assistant.")
    model_config_id: Mapped[str | None] = mapped_column(UUID(as_uuid=True), ForeignKey("model_configs.id", ondelete="SET NULL"))
    status: Mapped[str] = mapped_column(String(30), default=AgentStatus.active)
    created_by: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Relationships
    workspace = relationship("Workspace", back_populates="agents")
    created_by_user = relationship("User", back_populates="agents")
    model_config = relationship("ModelConfig", foreign_keys=[model_config_id])
    conversations: Mapped[list["Conversation"]] = relationship("Conversation", back_populates="agent", cascade="all, delete-orphan")
    chapters: Mapped[list["Chapter"]] = relationship("Chapter", back_populates="agent", cascade="all, delete-orphan")
    memories: Mapped[list["Memory"]] = relationship("Memory", back_populates="agent", cascade="all, delete-orphan")
    jobs: Mapped[list["Job"]] = relationship("Job", back_populates="agent", cascade="all, delete-orphan")
    tool_bindings: Mapped[list["AgentTool"]] = relationship("AgentTool", back_populates="agent", cascade="all, delete-orphan")


class AgentTool(BaseModel):
    __tablename__ = "agent_tools"

    agent_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), primary_key=True)
    tool_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("tools.id", ondelete="CASCADE"), primary_key=True)
    status: Mapped[str] = mapped_column(String(30), default=ToolBindingStatus.off)

    agent = relationship("Agent", back_populates="tool_bindings")
    tool = relationship("Tool", back_populates="agent_bindings")
