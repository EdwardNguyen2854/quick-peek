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


# ── v0.4 / Phase 2: Auth & Admin schemas ────────────────────────────────────


class LdapTestRequest(BaseModel):
    url: Optional[str] = None
    bind_dn: Optional[str] = None
    bind_password: Optional[str] = None
    search_base: Optional[str] = None
    search_filter: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None


class LdapTestResponse(BaseModel):
    ok: bool
    server_info: Optional[str] = None
    error: Optional[str] = None
    user_info: Optional[dict] = None
    mapped_permissions: Optional[list] = None


class ApiKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    user_id: int
    scopes: List[str] = ["use_quick_peek"]
    expires_at: Optional[str] = None  # ISO datetime or null for no expiry


class ApiKeyResponse(BaseModel):
    id: int
    name: str
    prefix: str
    user_id: int
    username: Optional[str] = None
    scopes: List[str] = []
    expires_at: Optional[str] = None
    last_used_at: Optional[str] = None
    created_at: str
    revoked_at: Optional[str] = None


class ApiKeyCreateResponse(BaseModel):
    key: ApiKeyResponse
    full_key: str


class FolderScopeCreate(BaseModel):
    pattern: str = Field(min_length=1, max_length=2000)
    description: Optional[str] = None


class FolderGrantCreate(BaseModel):
    scope_id: int
    principal_type: str = Field(pattern=r"^(user|group|api_key)$")
    principal_id: str = Field(min_length=1, max_length=500)
    permission: str = Field(default="view", pattern=r"^(view|download|index)$")
    effect: str = Field(default="allow", pattern=r"^(allow|deny)$")
