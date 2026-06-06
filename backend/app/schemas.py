from __future__ import annotations

from pydantic import BaseModel, Field
from typing import List, Optional, Literal


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserCreate(BaseModel):
    username: str = Field(min_length=2, max_length=80)
    password: str = Field(min_length=4, max_length=200)
    role: Literal["admin", "user"] = "user"
    permissions: List[str] = []
    is_active: bool = True


class UserUpdate(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    role: Optional[Literal["admin", "user"]] = None
    permissions: Optional[List[str]] = None
    is_active: Optional[bool] = None


class SearchRequest(BaseModel):
    format: Literal["step", "pdf", "dxf", "obj", "doc", "xls", "ppt", "md", "txt", "html"]
    codes: List[str]
    folder_path: Optional[str] = None


class FolderPresetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    path: str = Field(min_length=1, max_length=1000)


class OpenLogRequest(BaseModel):
    file_id: int
    format: Literal["step", "pdf", "dxf", "obj", "doc", "xls", "ppt", "md", "txt", "html"]
