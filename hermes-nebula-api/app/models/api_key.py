from sqlalchemy import String, Text, Boolean, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel


class ApiKey(BaseModel):
    __tablename__ = "api_keys"

    provider: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    key_name: Mapped[str] = mapped_column(String(300), nullable=False)
    encrypted_key: Mapped[str] = mapped_column(Text, nullable=False)
    base_url: Mapped[str | None] = mapped_column(String(1000))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    added_by_user_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    last_used_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True))

    added_by = relationship("User")
