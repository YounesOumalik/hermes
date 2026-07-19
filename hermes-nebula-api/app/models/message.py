from datetime import datetime
from sqlalchemy import String, Text, ForeignKey, Integer, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel
import enum


class MessageRole(str, enum.Enum):
    user = "user"
    assistant = "assistant"
    system = "system"
    tool = "tool"


class Conversation(BaseModel):
    __tablename__ = "conversations"

    agent_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str | None] = mapped_column(String(500))
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    agent = relationship("Agent", back_populates="conversations")
    user = relationship("User", back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    chapters: Mapped[list["Chapter"]] = relationship("Chapter", back_populates="conversation", cascade="all, delete-orphan")
    attachments: Mapped[list["Attachment"]] = relationship("Attachment", back_populates="conversation", cascade="all, delete-orphan")


class Message(BaseModel):
    __tablename__ = "messages"

    conversation_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String(30), nullable=False)
    content: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB)
    tokens_used: Mapped[int | None] = mapped_column(Integer)

    conversation = relationship("Conversation", back_populates="messages")


class ChapterStatus(str, enum.Enum):
    live = "live"
    closed = "closed"


class Chapter(BaseModel):
    __tablename__ = "chapters"

    conversation_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    agent_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[list | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(30), default=ChapterStatus.live)
    start_message_id: Mapped[str | None] = mapped_column(UUID(as_uuid=True))

    conversation = relationship("Conversation", back_populates="chapters")
    agent = relationship("Agent", back_populates="chapters")


class AttachmentType(str, enum.Enum):
    image = "image"
    video = "video"
    file = "file"
    audio = "audio"


class Attachment(BaseModel):
    __tablename__ = "attachments"

    message_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"), nullable=False)
    conversation_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    type: Mapped[str] = mapped_column(String(30), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(200))

    message = relationship("Message")
    conversation = relationship("Conversation", back_populates="attachments")
