from __future__ import annotations

import base64
import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

from .config import ACCESS_TOKEN_EXPIRE_MINUTES, ALGORITHM, SECRET_KEY
from .db import get_conn, json_loads, row_to_dict, utc_now

# Use stdlib PBKDF2 instead of passlib/bcrypt.
# This avoids the passlib + bcrypt 5.x crash:
# "ValueError: password cannot be longer than 72 bytes".
PBKDF2_ITERATIONS = 310_000
security = HTTPBearer(auto_error=False)


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _unb64(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def get_password_hash(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${_b64(salt)}${_b64(digest)}"


def verify_password(plain_password: str, password_hash: str) -> bool:
    if password_hash.startswith("pbkdf2_sha256$"):
        try:
            _, iter_text, salt_text, digest_text = password_hash.split("$", 3)
            iterations = int(iter_text)
            salt = _unb64(salt_text)
            expected = _unb64(digest_text)
            actual = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, iterations)
            return hmac.compare_digest(actual, expected)
        except Exception:
            return False

    # Optional legacy support for old databases created with passlib bcrypt.
    # Import lazily so the app can start even when passlib/bcrypt is not installed.
    if password_hash.startswith(("$2a$", "$2b$", "$2y$")):
        try:
            from passlib.context import CryptContext  # type: ignore

            return CryptContext(schemes=["bcrypt"], deprecated="auto").verify(plain_password, password_hash)
        except Exception:
            return False

    return False


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        user = row_to_dict(row)
    if user:
        user["permissions"] = json_loads(user.get("permissions_json"), [])
    return user


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        user = row_to_dict(row)
    if user:
        user["permissions"] = json_loads(user.get("permissions_json"), [])
    return user


def public_user(user: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": user["id"],
        "username": user["username"],
        "role": user["role"],
        "permissions": user.get("permissions") or json_loads(user.get("permissions_json"), []),
        "is_active": bool(user["is_active"]),
        "last_login_at": user.get("last_login_at"),
    }


async def current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    access_token: Optional[str] = Query(default=None),
) -> Dict[str, Any]:
    token = access_token
    if credentials and credentials.scheme.lower() == "bearer":
        token = credentials.credentials
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub = payload.get("sub")
        if sub is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        user_id = int(sub)
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")
    user = get_user_by_id(user_id)
    if not user or not user.get("is_active"):
        raise HTTPException(status_code=401, detail="Inactive or missing user")
    return user


def require_permission(permission: str):
    def dependency(user: Dict[str, Any] = Depends(current_user)) -> Dict[str, Any]:
        permissions = user.get("permissions") or json_loads(user.get("permissions_json"), [])
        if user.get("role") == "admin" or permission in permissions:
            return user
        raise HTTPException(status_code=403, detail=f"Missing permission: {permission}")

    return dependency


def ensure_admin_user(username: str, password: str, permissions: list[str]) -> None:
    from .db import json_dumps

    with get_conn() as conn:
        row = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        if row:
            return
        now = utc_now()
        conn.execute(
            """
            INSERT INTO users (username, password_hash, role, permissions_json, is_active, created_at, updated_at)
            VALUES (?, ?, 'admin', ?, 1, ?, ?)
            """,
            (username, get_password_hash(password), json_dumps(permissions), now, now),
        )
