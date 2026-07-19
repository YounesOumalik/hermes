"""
hermes-core/api/schemas.py — Schémas Pydantic pour les routes API.

Réutilisés par les routers conversations/agents/settings/tools.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Conversations
# ---------------------------------------------------------------------------
class ConversationCreate(BaseModel):
    title: str = Field(default="Nouvelle conversation", max_length=256)
    agent_name: Optional[str] = None
    model: Optional[str] = None
    tool_names: List[str] = Field(default_factory=list)
    context_tokens: int = Field(default=128000, ge=1024, le=2000000)


class ConversationUpdate(BaseModel):
    title: Optional[str] = None
    agent_name: Optional[str] = None
    model: Optional[str] = None
    tool_names: Optional[List[str]] = None
    context_tokens: Optional[int] = None


class MessageCreate(BaseModel):
    role: str = Field(..., description="user | assistant | system | tool")
    content: str = Field(..., description="Contenu du message")
    reasoning_details: Optional[List[Dict[str, Any]]] = None


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    reasoning_details: Optional[List[Dict[str, Any]]] = None
    time: datetime

    class Config:
        from_attributes = True


class AttachmentOut(BaseModel):
    id: int
    filename: str
    mime_type: str
    size: int
    extracted: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationOut(BaseModel):
    id: int
    user_id: str
    title: str
    agent_name: Optional[str]
    model: Optional[str]
    tool_names: List[str]
    context_tokens: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConversationDetail(ConversationOut):
    messages: List[MessageOut] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Agents
# ---------------------------------------------------------------------------
class AgentCreate(BaseModel):
    name: str = Field(..., max_length=128)
    description: Optional[str] = None
    system_prompt: str = Field(default="")
    model: Optional[str] = None
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2000, ge=256, le=16000)
    tools: List[str] = Field(default_factory=list)
    enabled: bool = True


class AgentUpdate(AgentCreate):
    pass


class AgentOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    system_prompt: str
    model: Optional[str]
    temperature: float
    max_tokens: int
    tools: List[str]
    enabled: bool
    is_preset: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
class SettingsStatus(BaseModel):
    minimax_configured: bool
    telegram_configured: bool
    github_configured: bool
    model: str
    mcp_ready: bool


class SettingsUpdate(BaseModel):
    minimax_api_key: Optional[str] = None
    telegram_bot_token: Optional[str] = None
    github_token: Optional[str] = None


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------
class ToolOut(BaseModel):
    id: int
    name: str
    description: str
    parameters: Dict[str, Any]
    requires_approval: bool
    enabled: bool
    source: str

    class Config:
        from_attributes = True


class ToolCallRequest(BaseModel):
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)