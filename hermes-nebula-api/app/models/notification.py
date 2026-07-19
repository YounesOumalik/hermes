from sqlalchemy import String, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel


class NotificationChannel(BaseModel):
    __tablename__ = "notification_channels"

    user_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)  # email, push, slack, discord, telegram
    config_json: Mapped[dict | None] = mapped_column(JSONB)
    is_connected: Mapped[bool] = mapped_column(Boolean, default=False)

    user = relationship("User")


class NotificationRule(BaseModel):
    __tablename__ = "notification_rules"

    user_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    workspace_id: Mapped[str | None] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"))
    event_type: Mapped[str] = mapped_column(String(200), nullable=False)
    channel_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("notification_channels.id"), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
