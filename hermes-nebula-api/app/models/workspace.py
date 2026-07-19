from sqlalchemy import String, Text, ForeignKey, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel, Base
import enum


class MemberRole(str, enum.Enum):
    owner = "owner"
    admin = "admin"
    member = "member"


class Workspace(BaseModel):
    __tablename__ = "workspaces"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    logo_url: Mapped[str | None] = mapped_column(Text)
    owner_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Relationships
    owner = relationship("User", back_populates="workspaces_owned", foreign_keys=[owner_id])
    members: Mapped[list["WorkspaceMember"]] = relationship(
        "WorkspaceMember", back_populates="workspace", cascade="all, delete-orphan"
    )
    agents: Mapped[list["Agent"]] = relationship("Agent", back_populates="workspace", cascade="all, delete-orphan")
    jobs: Mapped[list["Job"]] = relationship("Job", back_populates="workspace", cascade="all, delete-orphan")
    memories: Mapped[list["Memory"]] = relationship("Memory", back_populates="workspace", cascade="all, delete-orphan")
    documents: Mapped[list["Document"]] = relationship("Document", back_populates="workspace", cascade="all, delete-orphan")
    mini_apps: Mapped[list["MiniApp"]] = relationship("MiniApp", back_populates="workspace", cascade="all, delete-orphan")
    integrations: Mapped[list["Integration"]] = relationship("Integration", back_populates="workspace", cascade="all, delete-orphan")
    secrets: Mapped[list["Secret"]] = relationship("Secret", back_populates="workspace", cascade="all, delete-orphan")


class WorkspaceMember(Base):
    """Table d'association many-to-many entre User et Workspace avec un champ `role`.

    Clé primaire composite (user_id, workspace_id) — pas de colonne `id` séparée.
    N'hérite PAS de BaseModel (qui ajouterait `id`, `created_at`, `updated_at`).
    """

    __tablename__ = "workspace_members"

    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    workspace_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), primary_key=True
    )
    role: Mapped[str] = mapped_column(String(20), default=MemberRole.member.value, nullable=False)
    joined_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="memberships")
    workspace = relationship("Workspace", back_populates="members")
