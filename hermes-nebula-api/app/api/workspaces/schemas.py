from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import uuid


class WorkspaceCreate(BaseModel):
    name: str = Field(..., max_length=200)
    logo_url: Optional[str] = None


class WorkspaceUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    logo_url: Optional[str] = None


class WorkspaceMemberAdd(BaseModel):
    email: str = Field(..., description="Email of the user to invite/add")
    role: str = Field("member", description="Role: admin, member")


class WorkspaceMemberResponse(BaseModel):
    user_id: uuid.UUID
    email: str
    display_name: str
    avatar_url: Optional[str]
    role: str

    class Config:
        from_attributes = True


class WorkspaceResponse(BaseModel):
    id: uuid.UUID
    name: str
    logo_url: Optional[str]
    owner_id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True
