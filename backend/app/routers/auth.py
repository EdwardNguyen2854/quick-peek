from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..auth import create_access_token, current_user, get_user_by_id, get_user_by_username, public_user, verify_password
from ..config import (
    LDAP_BIND_DN_TEMPLATE,
    LDAP_GROUP_PERMISSIONS_MAP,
    LDAP_URL,
    LDAP_USER_SEARCH_BASE,
    LDAP_USER_SEARCH_FILTER,
    LDAP_USE_SSL,
    DEFAULT_USER_PERMISSIONS,
)
from ..db import get_conn, json_dumps, utc_now
from ..schemas import LoginRequest, TokenResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest):
    username = payload.username.strip().lower()

    # ── Try LDAP if configured (v0.4) ──
    if LDAP_URL:
        return _ldap_login(username, payload.password)

    # ── Local PBKDF2 (existing behavior) ──
    user = get_user_by_username(username)
    if not user or not verify_password(payload.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    if not user.get("is_active"):
        raise HTTPException(status_code=403, detail="User is disabled")
    with get_conn() as conn:
        conn.execute("UPDATE users SET last_login_at = ? WHERE id = ?", (utc_now(), user["id"]))
    token = create_access_token({"sub": str(user["id"]), "username": username})
    return {"access_token": token, "token_type": "bearer", "user": public_user(user)}


def _ldap_login(username: str, password: str) -> dict:
    """Try LDAP bind authentication. Raises HTTPException on failure."""
    import ldap3
    from ldap3.core.exceptions import LDAPBindError, LDAPSocketOpenError, LDAPStartTLSConnectError

    server = ldap3.Server(LDAP_URL, use_ssl=LDAP_USE_SSL, get_info=ldap3.ALL)
    bind_dn = LDAP_BIND_DN_TEMPLATE.format(username=username)

    try:
        conn = ldap3.Connection(server, user=bind_dn, password=password, auto_bind=True, receive_timeout=5)
    except LDAPBindError:
        raise HTTPException(status_code=401, detail="LDAP: Incorrect username or password")
    except (LDAPSocketOpenError, LDAPStartTLSConnectError) as e:
        raise HTTPException(status_code=503, detail=f"LDAP server is not reachable. Contact your administrator. ({e})")
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"LDAP error: {exc}")

    try:
        search_filter = LDAP_USER_SEARCH_FILTER.format(username=username)
        conn.search(
            LDAP_USER_SEARCH_BASE,
            search_filter,
            attributes=["sAMAccountName", "mail", "displayName", "memberOf", "objectGUID"],
        )
        if not conn.entries:
            # Bind succeeded but user not found in search — still return user info
            ldap_user = {
                "username": username,
                "email": "",
                "display_name": username,
                "ldap_dn": bind_dn,
                "groups": [],
            }
        else:
            entry = conn.entries[0]
            groups = [str(g) for g in entry.get("memberOf", [])] if hasattr(entry, "memberOf") else []
            ldap_user = {
                "username": str(entry.get("sAMAccountName", username)),
                "email": str(entry.get("mail", "")),
                "display_name": str(entry.get("displayName", username)),
                "ldap_dn": str(entry.entry_dn),
                "groups": groups,
            }
    finally:
        conn.unbind()

    # Map groups to permissions
    perms = _map_ldap_groups_to_permissions(ldap_user.get("groups", []))

    # Upsert user from LDAP
    user = _upsert_ldap_user(username, ldap_user, perms)

    token = create_access_token({"sub": str(user["id"]), "username": username})
    return {"access_token": token, "token_type": "bearer", "user": public_user(user)}


def _upsert_ldap_user(username: str, ldap_user: dict, permissions: list) -> dict:
    """Create or update a user record from LDAP attributes."""
    now = utc_now()
    with get_conn() as conn:
        existing = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        if existing:
            conn.execute(
                """
                UPDATE users
                SET ldap_dn=?, email=?, display_name=?, permissions_json=?,
                    auth_source='ldap', last_synced_at=?, updated_at=?
                WHERE id=?
                """,
                (
                    ldap_user.get("ldap_dn", ""),
                    ldap_user.get("email", ""),
                    ldap_user.get("display_name", username),
                    json_dumps(permissions),
                    now,
                    now,
                    existing["id"],
                ),
            )
            user_id = existing["id"]
        else:
            cur = conn.execute(
                """
                INSERT INTO users (username, password_hash, role, permissions_json, is_active,
                    auth_source, ldap_dn, email, display_name, last_synced_at, created_at, updated_at)
                VALUES (?, '', 'user', ?, 1, 'ldap', ?, ?, ?, ?, ?, ?)
                """,
                (
                    username,
                    json_dumps(permissions),
                    ldap_user.get("ldap_dn", ""),
                    ldap_user.get("email", ""),
                    ldap_user.get("display_name", username),
                    now,
                    now,
                    now,
                ),
            )
            user_id = cur.lastrowid

    return get_user_by_id(user_id) or {}


def _map_ldap_groups_to_permissions(groups: list) -> list:
    """Map LDAP group DNs to Quick Peek permissions."""
    mapping = LDAP_GROUP_PERMISSIONS_MAP
    if not mapping:
        return list(DEFAULT_USER_PERMISSIONS)
    perms = set()
    for group_dn in groups:
        extra = mapping.get(group_dn, [])
        if isinstance(extra, list):
            perms.update(extra)
    if not perms:
        return list(DEFAULT_USER_PERMISSIONS)
    return sorted(perms)


@router.get("/me")
def me(user=Depends(current_user)):
    return public_user(user)
