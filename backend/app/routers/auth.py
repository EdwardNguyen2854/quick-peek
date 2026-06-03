from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..auth import create_access_token, current_user, get_user_by_username, public_user, verify_password
from ..db import get_conn, utc_now
from ..schemas import LoginRequest, TokenResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest):
    user = get_user_by_username(payload.username)
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    if not user.get("is_active"):
        raise HTTPException(status_code=403, detail="User is disabled")
    with get_conn() as conn:
        conn.execute("UPDATE users SET last_login_at = ? WHERE id = ?", (utc_now(), user["id"]))
    token = create_access_token({"sub": str(user["id"])})
    return {"access_token": token, "token_type": "bearer", "user": public_user(user)}


@router.get("/me")
def me(user=Depends(current_user)):
    return public_user(user)
