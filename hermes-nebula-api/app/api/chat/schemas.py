from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
import uuid


class ConversationCreate(BaseModel):
    agent_id: uuid.UUID
    title: Optional[str] = Field(None, max_length=500)


class ConversationResponse(BaseModel):
    id: uuid.UUID
    agent_id: uuid.UUID
    user_id: uuid.UUID
    title: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class MessageSend(BaseModel):
    content: str
    attachments: Optional[List[uuid.UUID]] = Field(default_factory=list, description="Array of attachment UUIDs already uploaded")


class AttachmentResponse(BaseModel):
    id: uuid.UUID
    type: str
    storage_path: str
    original_filename: str
    size_bytes: int
    mime_type: Optional[str]

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    role: str
    content: Optional[str]
    metadata_json: Optional[Dict]
    tokens_used: Optional[int]
    created_at: datetime
    attachments: Optional[List[AttachmentResponse]] = None

    class Config:
        from_attributes = True
