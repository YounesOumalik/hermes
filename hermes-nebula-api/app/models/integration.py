from sqlalchemy import String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel
import enum


class IntegrationStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"


class Integration(BaseModel):
    __tablename__ = "integrations"

    workspace_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    type: Mapped[str] = mapped_column(String(100), nullable=False)  # custom_toolkit, connected_app
    config_json: Mapped[dict | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(30), default=IntegrationStatus.inactive)

    workspace = relationship("Workspace", back_populates="integrations")


class Secret(BaseModel):
    __tablename__ = "secrets"

    workspace_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    key_name: Mapped[str] = mapped_column(String(300), nullable=False)
    encrypted_value: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    workspace = relationship("Workspace", back_populates="secrets")
