from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import uuid


class AgentCreate(BaseModel):
    name: str = Field(..., max_length=200)
    description: Optional[str] = None
    avatar_color: str = Field("#58a6ff", max_length=7)
    system_prompt: str = Field("You are a helpful assistant.")
    model_config_id: Optional[uuid.UUID] = None
    tools: List[str] = Field(default_list=[], description="Array of tool UUIDs to bind")


class AgentUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    avatar_color: Optional[str] = Field(None, max_length=7)
    system_prompt: Optional[str] = None
    model_config_id: Optional[uuid.UUID] = None
    status: Optional[str] = None  # active, paused, archived
    tools: Optional[List[str]] = None


class AgentResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    description: Optional[str]
    avatar_color: str
    system_prompt: str
    model_config_id: Optional[uuid.UUID]
    status: str
    created_by: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True
