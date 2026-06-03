from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..auth import get_password_hash, public_user, require_permission
from ..config import ADMIN_PERMISSIONS, DEFAULT_USER_PERMISSIONS, FILE_ROOTS
from ..db import get_conn, json_dumps, json_loads, row_to_dict, rows_to_dicts, utc_now
from ..file_index import reindex_files
from ..schemas import UserCreate, UserUpdate

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/permissions")
def permissions(user=Depends(require_permission("manage_users"))):
    return {
        "available_permissions": ADMIN_PERMISSIONS,
        "default_user_permissions": DEFAULT_USER_PERMISSIONS,
    }


@router.get("/users")
def list_users(user=Depends(require_permission("manage_users"))):
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM users ORDER BY id").fetchall()
    items = []
    for r in rows_to_dicts(rows):
        r["permissions"] = json_loads(r.get("permissions_json"), [])
        items.append(public_user(r))
    return {"users": items}


@router.post("/users")
def create_user(payload: UserCreate, user=Depends(require_permission("manage_users"))):
    now = utc_now()
    try:
        with get_conn() as conn:
            cur = conn.execute(
                """
                INSERT INTO users (username, password_hash, role, permissions_json, is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload.username.strip(),
                    get_password_hash(payload.password),
                    payload.role,
                    json_dumps(payload.permissions),
                    1 if payload.is_active else 0,
                    now,
                    now,
                ),
            )
            new_id = cur.lastrowid
            row = conn.execute("SELECT * FROM users WHERE id = ?", (new_id,)).fetchone()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    item = row_to_dict(row) or {}
    item["permissions"] = json_loads(item.get("permissions_json"), [])
    return public_user(item)


@router.put("/users/{user_id}")
def update_user(user_id: int, payload: UserUpdate, user=Depends(require_permission("manage_users"))):
    fields = []
    values = []
    if payload.username is not None:
        fields.append("username = ?"); values.append(payload.username.strip())
    if payload.password:
        fields.append("password_hash = ?"); values.append(get_password_hash(payload.password))
    if payload.role is not None:
        fields.append("role = ?"); values.append(payload.role)
    if payload.permissions is not None:
        fields.append("permissions_json = ?"); values.append(json_dumps(payload.permissions))
    if payload.is_active is not None:
        fields.append("is_active = ?"); values.append(1 if payload.is_active else 0)
    fields.append("updated_at = ?"); values.append(utc_now())
    if not fields:
        raise HTTPException(status_code=400, detail="No changes supplied")
    values.append(user_id)
    try:
        with get_conn() as conn:
            conn.execute(f"UPDATE users SET {', '.join(fields)} WHERE id = ?", values)
            row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if row is None:
        raise HTTPException(status_code=404, detail="User not found")
    item = row_to_dict(row) or {}
    item["permissions"] = json_loads(item.get("permissions_json"), [])
    return public_user(item)


@router.post("/reindex")
def reindex(user=Depends(require_permission("manage_users"))):
    result = reindex_files()
    return result


@router.get("/roots")
def roots(user=Depends(require_permission("manage_users"))):
    return {"roots": [str(r) for r in FILE_ROOTS]}
