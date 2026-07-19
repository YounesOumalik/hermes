from sqlalchemy import String, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel
import enum


class CostTier(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"


class Tool(BaseModel):
    __tablename__ = "tools"

    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(200), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    icon_name: Mapped[str] = mapped_column(String(50), default="wrench")
    category: Mapped[str] = mapped_column(String(100), default="general")
    cost_tier: Mapped[str] = mapped_column(String(30), default=CostTier.low)
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=True)
    config_schema_json: Mapped[dict | None] = mapped_column(JSONB)
    enabled_globally: Mapped[bool] = mapped_column(Boolean, default=True)

    agent_bindings: Mapped[list["AgentTool"]] = relationship("AgentTool", back_populates="tool")
