from sqlalchemy import String, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel
import uuid


class User(BaseModel):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    username: Mapped[str | None] = mapped_column(String(100), unique=True, index=True)
    avatar_url: Mapped[str | None] = mapped_column(Text)
    timezone: Mapped[str] = mapped_column(String(50), default="UTC")
    google_id: Mapped[str | None] = mapped_column(String(200), unique=True, index=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_superadmin: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    quotas: Mapped["UserQuota | None"] = relationship(
        "UserQuota", back_populates="user", uselist=False, cascade="all, delete-orphan",
        foreign_keys="[UserQuota.user_id]"
    )
    workspaces_owned: Mapped[list["Workspace"]] = relationship(
        "Workspace", back_populates="owner", foreign_keys="[Workspace.owner_id]"
    )
    memberships: Mapped[list["WorkspaceMember"]] = relationship(
        "WorkspaceMember", back_populates="user", cascade="all, delete-orphan"
    )
    agents: Mapped[list["Agent"]] = relationship("Agent", back_populates="created_by_user")
    conversations: Mapped[list["Conversation"]] = relationship("Conversation", back_populates="user")
