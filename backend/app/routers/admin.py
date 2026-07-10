from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..auth import generate_api_key, get_password_hash, public_user, require_permission
from ..config import (
    ADMIN_PERMISSIONS,
    DEFAULT_USER_PERMISSIONS,
    FILE_ROOTS,
    LDAP_BIND_DN_TEMPLATE,
    LDAP_GROUP_PERMISSIONS_MAP,
    LDAP_URL,
    LDAP_USER_SEARCH_BASE,
    LDAP_USER_SEARCH_FILTER,
    LDAP_USE_SSL,
)
from ..db import get_conn, json_dumps, json_loads, row_to_dict, rows_to_dicts, utc_now
from ..file_index import reindex_files
from ..schemas import ApiKeyCreate, LdapTestRequest, UserCreate, UserUpdate

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


# ── v0.4: LDAP Test ─────────────────────────────────────────────────────────


@router.post("/ldap-test")
async def ldap_test(payload: LdapTestRequest, admin=Depends(require_permission("manage_users"))):
    """Test LDAP connectivity. Returns bind status, found users/groups, mapped perms."""
    url = payload.url or LDAP_URL or ""
    if not url:
        return {"ok": False, "error": "LDAP URL is not configured. Set QUICKPEEK_LDAP_URL."}

    try:
        import ldap3
        from ldap3.core.exceptions import LDAPBindError, LDAPSocketOpenError, LDAPStartTLSConnectError

        use_ssl = LDAP_USE_SSL
        server = ldap3.Server(url, use_ssl=use_ssl, get_info=ldap3.ALL)

        bind_dn = payload.bind_dn or LDAP_BIND_DN_TEMPLATE.format(username=payload.username or "test")
        bind_password = payload.bind_password or "test"
        search_base = payload.search_base or LDAP_USER_SEARCH_BASE
        search_filter = payload.search_filter or LDAP_USER_SEARCH_FILTER

        bind_conn = ldap3.Connection(
            server, user=bind_dn, password=bind_password, auto_bind=True, receive_timeout=5
        )
        server_info = str(server.info) if server.info else "connected"

        user_info = None
        mapped_permissions = None

        if payload.username and payload.password:
            search_filter_filled = search_filter.format(username=payload.username)
            bind_conn.search(
                search_base,
                search_filter_filled,
                attributes=["sAMAccountName", "mail", "displayName", "memberOf"],
            )
            if bind_conn.entries:
                entry = bind_conn.entries[0]
                groups = [str(g) for g in entry.get("memberOf", [])] if hasattr(entry, "memberOf") else []
                user_info = {
                    "username": str(entry.get("sAMAccountName", payload.username)),
                    "email": str(entry.get("mail", "")),
                    "display_name": str(entry.get("displayName", payload.username)),
                    "dn": str(entry.entry_dn),
                    "groups": groups,
                }
                mapped_permissions = []
                for g in groups:
                    extra = LDAP_GROUP_PERMISSIONS_MAP.get(g, [])
                    if isinstance(extra, list):
                        mapped_permissions.extend(extra)

        bind_conn.unbind()
        return {
            "ok": True,
            "server_info": server_info,
            "user_info": user_info,
            "mapped_permissions": mapped_permissions,
        }

    except LDAPBindError:
        return {"ok": False, "error": "LDAP bind failed — incorrect credentials or DN template"}
    except LDAPSocketOpenError:
        return {"ok": False, "error": f"Cannot reach LDAP server at {url}"}
    except LDAPStartTLSConnectError as e:
        return {"ok": False, "error": f"TLS connection failed: {e}"}
    except ImportError:
        return {"ok": False, "error": "ldap3 package is not installed. Run: pip install ldap3"}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


# ── v0.4: API Key CRUD ──────────────────────────────────────────────────────


@router.get("/api-keys")
def list_api_keys(admin=Depends(require_permission("manage_users"))):
    """List all API keys (without full key hashes)."""
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT ak.id, ak.name, ak.prefix, ak.user_id, u.username,
                   ak.scopes_json, ak.expires_at, ak.last_used_at, ak.created_at, ak.revoked_at
            FROM api_keys ak
            LEFT JOIN users u ON u.id = ak.user_id
            ORDER BY ak.id
            """
        ).fetchall()
    keys = []
    for r in rows_to_dicts(rows):
        r["scopes"] = json_loads(r.pop("scopes_json", "[]"), [])
        keys.append(r)
    return {"keys": keys}


@router.post("/api-keys")
def create_api_key(payload: ApiKeyCreate, admin=Depends(require_permission("manage_users"))):
    """Create a new API key. The full key is returned only once."""
    # Verify target user exists
    with get_conn() as conn:
        target = conn.execute("SELECT id FROM users WHERE id = ?", (payload.user_id,)).fetchone()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    raw_key, prefix, key_hash = generate_api_key()
    scopes_json = json_dumps(payload.scopes)
    now = utc_now()

    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO api_keys (name, prefix, key_hash, user_id, scopes_json, expires_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (payload.name.strip(), prefix, key_hash, payload.user_id, scopes_json, payload.expires_at, now),
        )
        key_id = cur.lastrowid
        row = conn.execute(
            """
            SELECT ak.id, ak.name, ak.prefix, ak.user_id, u.username,
                   ak.scopes_json, ak.expires_at, ak.last_used_at, ak.created_at, ak.revoked_at
            FROM api_keys ak
            LEFT JOIN users u ON u.id = ak.user_id
            WHERE ak.id = ?
            """,
            (key_id,),
        ).fetchone()

    key_dict = dict(row)
    key_dict["scopes"] = json_loads(key_dict.pop("scopes_json", "[]"), [])

    return {
        "key": key_dict,
        "full_key": raw_key,
    }


@router.delete("/api-keys/{key_id}")
def revoke_api_key(key_id: int, admin=Depends(require_permission("manage_users"))):
    """Revoke an API key (soft-delete by setting revoked_at)."""
    now = utc_now()
    with get_conn() as conn:
        cur = conn.execute(
            "UPDATE api_keys SET revoked_at = ? WHERE id = ? AND revoked_at IS NULL",
            (now, key_id),
        )
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="API key not found or already revoked")
    return {"ok": True}
