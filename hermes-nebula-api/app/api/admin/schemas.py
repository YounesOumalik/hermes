from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from datetime import datetime
import uuid


class UserQuotaUpdate(BaseModel):
    max_disk_bytes: int = Field(..., description="Max disk space in bytes")
    max_monthly_llm_tokens: int = Field(..., description="Max monthly LLM tokens budget")
    allowed_models: List[str] = Field(default_list=[], description="Array of model config UUID strings")
    allowed_tools: List[str] = Field(default_list=[], description="Array of tool UUID strings")
    notes_admin: Optional[str] = None


class UserQuotaResponse(BaseModel):
    user_id: uuid.UUID
    max_disk_bytes: int
    used_disk_bytes: int
    max_monthly_llm_tokens: int
    used_monthly_llm_tokens: int
    allowed_models: List[str]
    allowed_tools: List[str]
    notes_admin: Optional[str]
    updated_at: datetime

    class Config:
        from_attributes = True


class AdminUserListItem(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str
    username: Optional[str]
    avatar_url: Optional[str]
    is_active: bool
    is_superadmin: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ApiKeyCreate(BaseModel):
    provider: str = Field(..., description="LLM provider name, e.g. minimax, opencode_zen, openai...")
    key_name: str = Field(..., description="Descriptive name for the API key")
    api_key: str = Field(..., description="Raw API key value to encrypt")
    base_url: Optional[str] = Field(None, description="Base API endpoint URL (optional)")


class ApiKeyResponse(BaseModel):
    id: uuid.UUID
    provider: str
    key_name: str
    base_url: Optional[str]
    is_active: bool
    added_by_user_id: uuid.UUID
    last_used_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class ApiKeyTestRequest(BaseModel):
    provider: str
    base_url: str
    api_key: str


class AuditLogResponse(BaseModel):
    id: uuid.UUID
    admin_user_id: uuid.UUID
    action: str
    target_user_id: Optional[uuid.UUID]
    details_json: Optional[dict]
    created_at: datetime

    class Config:
        from_attributes = True
