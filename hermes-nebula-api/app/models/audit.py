from datetime import datetime
from sqlalchemy import String, Text, ForeignKey, BigInteger, Integer, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel


class AdminAuditLog(BaseModel):
    __tablename__ = "admin_audit_log"

    admin_user_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    target_user_id: Mapped[str | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    details_json: Mapped[dict | None] = mapped_column(JSONB)

    admin = relationship("User", foreign_keys=[admin_user_id])
    target_user = relationship("User", foreign_keys=[target_user_id])


class UserQuota(BaseModel):
    __tablename__ = "user_quotas"

    user_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    max_disk_bytes: Mapped[int] = mapped_column(BigInteger, default=1073741824)  # 1 GiB
    used_disk_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    max_monthly_llm_tokens: Mapped[int] = mapped_column(BigInteger, default=1000000)
    used_monthly_llm_tokens: Mapped[int] = mapped_column(BigInteger, default=0)
    quota_reset_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    allowed_models: Mapped[list] = mapped_column(JSONB, default=list)  # Array of model_config IDs
    allowed_tools: Mapped[list] = mapped_column(JSONB, default=list)  # Array of tool IDs
    notes_admin: Mapped[str | None] = mapped_column(Text)
    updated_by_admin_id: Mapped[str | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    user = relationship("User", back_populates="quotas", foreign_keys=[user_id])
    updated_by_admin = relationship("User", foreign_keys=[updated_by_admin_id])
