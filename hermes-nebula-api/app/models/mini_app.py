from sqlalchemy import String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel


class MiniApp(BaseModel):
    __tablename__ = "mini_apps"

    workspace_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    type: Mapped[str] = mapped_column(String(100), default="custom")
    html_content: Mapped[str | None] = mapped_column(Text)
    config_json: Mapped[dict | None] = mapped_column(JSONB)
    created_by: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    workspace = relationship("Workspace", back_populates="mini_apps")
