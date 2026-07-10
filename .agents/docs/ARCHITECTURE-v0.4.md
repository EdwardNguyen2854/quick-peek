# Architecture — Quick Peek v0.4 "Enterprise" Release

> **Quick Peek v0.4** — Release: LDAP/SSO, Folder Permissions, Search History, File Tagging & Metadata, API Key Auth

---

## Table of Contents

1. [Architecture Decisions](#1-architecture-decisions)
2. [Answers to Open Questions](#2-answers-to-open-questions)
3. [System Diagram](#3-system-diagram)
4. [Database Schema](#4-database-schema)
5. [API Surface](#5-api-surface-exhaustive)
6. [Auth Flow Pseudocode](#6-auth-flow-pseudocode)
7. [Permission Composition](#7-permission-composition)
8. [Frontend Changes](#8-frontend-changes-high-level)
9. [Migration Plan](#9-migration-plan-ordered)
10. [Test Plan](#10-test-plan-concrete)
11. [PyInstaller Spec Changes](#11-pyinstaller-spec-changes)
12. [New Env Vars](#12-new-env-vars-exhaustive)
13. [Uncovered Risks](#13-uncovered-risks)

---

## 1. Architecture Decisions

### 1.1 LDAP Strategy

**Decision**: Use `ldap3` for bind-only authentication. Keep local PBKDF2 as break-glass admin fallback. No SAML, no OIDC.

**Rationale**:
- `ldap3==2.9.1` is pure-Python (no system DLLs), which is critical for the PyInstaller frozen .exe. SAML/OIDC would require either a system-level IdP agent or a heavy library like `python3-saml` that depends on `xmlsec1` system binaries — wrong for an air-gapped desktop tool.
- The codebase already uses PBKDF2 in `auth.py:33-36` (`get_password_hash`) and `auth.py:39-61` (`verify_password`). This serves as the local fallback when LDAP is unreachable or for the break-glass admin account.
- `config.py:44-45` already has `ADMIN_USERNAME`/`ADMIN_PASSWORD`. The LDAP flow will be a **new code path** inserted at `routers/auth.py:12-22` (`login` endpoint), attempted first if `QUICKPEEK_LDAP_URL` is set, falling through to local PBKDF2.
- Groups-to-permissions mapping is a configurable CSV via `QUICKPEEK_LDAP_GROUP_MAP` (e.g., `CN=QuickPeek-Admins,OU=Groups,DC=example,DC=com=manage_users,view_dashboard`).

**Auth flow priority**:
```
POST /api/auth/login
  ├─ IF QUICKPEEK_LDAP_URL is set → try LDAP bind
  │   ├─ Success → upsert user, return JWT
  │   ├─ LDAPBindError → 401 "Incorrect username or password"
  │   └─ LDAPSocketOpenError → 503 "LDAP server unavailable"
  └─ ELSE → try local PBKDF2 (existing behavior)
```

**Why not SAML/OIDC**: These protocols are designed for web SSO with redirects to an identity provider. In an air-gapped desktop tool with no browser redirect flow, they add complexity with no benefit. LDAP bind is a single round-trip to check credentials and read groups.

### 1.2 Folder Permission Model

**Decision**: ACL on path-prefix globs with explicit-deny > explicit-allow > default-allow for v0.4. Compose with format permissions: folder scope first (cheap deny), then format permission.

**Rationale**:
- The existing permission model in `peek.py:18-29` (`FORMAT_PERMISSION`) is format-level only. There is no path-based restriction. `raw_file()` at `peek.py:128-144` and `preview_file()` at `peek.py:147-191` use bare `current_user` with no further checks — a P0 security gap that v0.4 must fix.
- Folder scopes use path-prefix glob matching (e.g., `\\server\shared\Engineering\**`, `/mnt/cad/restricted/**`). Patterns are stored in `folder_scopes.pattern`.
- `folder_grants.principal_type` supports `user`, `group`, and `api_key` principal types. For v0.4, `group` and `api_key` are stored but only `user` and `api_key` are evaluated.
- Explicit-deny always wins. This allows "allow everything except this subfolder" patterns.
- Default-allow (configurable via `QUICKPEEK_FOLDER_DEFAULT_ALLOW`, default `True` for v0.4) means: if no scope matches a path, access is **allowed**. This is safe because format permission still gates the search. We flip to default-deny in v0.5 with a migration notice.

**Composition model**:
```
can_access_folder(user, full_path, "view"):
  1. Admin role → True (bypass)
  2. Check all folder_grants where principal matches user
  3. If any matching grant has effect='deny' → False
  4. If any matching grant has effect='allow' → True
  5. Return QUICKPEEK_FOLDER_DEFAULT_ALLOW (True in v0.4)
```

Then at search time in `peek.py:50-99` (`search()`), after format permission check (line 52), add a `can_access_folder()` filter on every result file's `full_path`. Similarly in `raw_file()` (line 129) and `preview_file()` (line 148).

### 1.3 Search History

**Decision**: Reuse `usage_logs` table (already records `action='search'` and `action='open_preview'` on lines 93-97 and 104-111). Add a small `recent_files` table driven by the existing `/api/usage/open` endpoint. Per-deploy TTL via `QUICKPEEK_HISTORY_RETENTION_DAYS` (default 90).

**Rationale**:
- `usage_logs` at `db.py:67-78` already has `user_id`, `action`, `details_json`, and `created_at`. The `details_json` column stores search codes (line 97: `json_dumps({"codes": cleaned[:200], "folder_path": folder_path})`). We can query this for recent searches without schema changes.
- `recent_files` table is new and lightweight — capped at 50 rows per user. It records `(user_id, file_id, last_opened_at, open_count)`. Updated on every `/api/usage/open` call.
- TTL is per-deploy, not per-user. A background cleanup in `init_db()` or a cron-style check on startup purges `usage_logs` and `recent_files` older than `QUICKPEEK_HISTORY_RETENTION_DAYS`.
- The frontend needs two new components: a "Recents" panel on `QuickPeekPage.tsx` and a "Recent Searches" dropdown/sidebar.

### 1.4 Tagging

**Decision**: M2M (`tags` + `file_tags` tables) for tags. Typed custom fields in `file_metadata` with `custom_json` escape hatch. Tags survive reindex by keying on `full_path` (not file ID).

**Rationale**:
- Tags are many-to-many: a file can have multiple tags, a tag can apply to many files. `tags` table stores `(id, name, scope, color)`. `file_tags` stores `(file_id, tag_id, applied_by, created_at)`.
- `file_metadata` is a 1:1 extension of `files`, keyed on `file_id`. It has typed columns (`project_code`, `revision`, `supplier`, `cost_center`) plus `custom_json TEXT DEFAULT '{}'` for any user-defined fields.
- Reindex in `file_index.py:47-63` (`reindex_files()`) deletes file rows for missing files (line 62). Since `file_tags` and `file_metadata` reference `files.id` via `PRAGMA foreign_keys=ON; ON DELETE CASCADE`, tag associations are automatically cleaned up when a file is removed from the index. When a file reappears (same `full_path`), it gets a new `files.id` — tags do not survive a delete+reappear cycle. That's acceptable: if a file disappears and reappears, it's effectively a new version.
- A future enhancement could preserve tags across reindex by storing them keyed on `full_path` in a separate mapping table, but that introduces sync complexity not warranted for v0.4.

### 1.5 API Keys

**Decision**: `X-API-Key` header authentication. First 8 characters (`qpk_` prefix + random hex) stored plain for UI display. Full key SHA-256 hashed for storage. Scopes are JSON array that acts as intersection with the issuing user's permissions. Admin-only creation.

**Rationale**:
- API keys allow external tools (scripts, CI pipelines, integrations) to search and preview without interactive login. The `current_user` dependency in `auth.py:100-121` will be modified to try JWT first, then API key.
- The `qpk_` prefix makes API keys easily identifiable in logs and UI. The plaintext prefix (first 8 chars) is stored in the `api_keys` table for display purposes only.
- Full key hashed with `sha256(key.encode()).hexdigest()` — using stdlib `hashlib`, no extra dependencies. PBKDF2 is not needed here because API keys are high-entropy random strings (32 bytes > 256 bits).
- Scopes are stored as a JSON array in `scopes_json`. When authenticating via API key, the code constructs a "synthetic user" dict whose permissions are the **intersection** of the API key's scopes and the issuing user's permissions. This prevents scope escalation.
- Admin-only creation (gated by `manage_users` permission) prevents lateral movement. Self-service is v0.5.
- `api_keys.revoked_at` enables soft-revocation. The verification logic checks `revoked_at IS NULL AND (expires_at IS NULL OR expires_at > now)`.

---

## 2. Answers to Open Questions

### 2.1 Default-Allow for Folder Scopes

**Decision**: Yes, default-allow for v0.4.

**One paragraph**: Default-allow means "if no folder scope matches a path, access is granted." This is safe because format permission (`FORMAT_PERMISSION` in `peek.py:18-29`) still gates every search. An admin who configures folder scopes must explicitly create deny rules to restrict access. We ship with `QUICKPEEK_FOLDER_DEFAULT_ALLOW=True` and document that v0.5 will flip the default to `False`. A startup warning log is emitted when default-allow is enabled.

### 2.2 Per-Deploy History TTL

**Decision**: Per-deploy, not per-user.

**One paragraph**: A single `QUICKPEEK_HISTORY_RETENTION_DAYS` env var (default 90) controls retention for all users. Per-user TTL would require a new UI (user settings page), per-user configuration storage, and additional query complexity — none of which justifies the benefit for v0.4. The cleanup runs in `init_db()` on every boot: `DELETE FROM usage_logs WHERE created_at < datetime('now', ?)` and `DELETE FROM recent_files WHERE last_opened_at < datetime('now', ?)` using the configured days.

### 2.3 Admin-Only API Key Creation

**Decision**: Yes, admin-only for v0.4.

**One paragraph**: Only users with `manage_users` permission can create, list, or revoke API keys. Self-service key generation (for users to create their own keys with a subset of their own permissions) is explicitly deferred to v0.5. This avoids the complexity of scope-confined key creation UI and permission intersection logic that could introduce escalation bugs.

### 2.4 Ship "Test LDAP Connection" Button

**Decision**: Yes, ship it.

**One paragraph**: A 30-line endpoint (`POST /api/admin/ldap-test`) that accepts the same LDAP env var configuration plus optional override credentials, performs an LDAP bind, and returns `{"ok": true}` or `{"ok": false, "error": "..."}`. This single endpoint saves countless support tickets from administrators who misconfigure LDAP URLs, base DNs, or group filters. The frontend shows it as a button in AdminPage.tsx with a green/red indicator.

### 2.5 FTS5: One-Boot Full Rebuild

**Decision**: Acceptable for v0.4.

**One paragraph**: FTS5 full-text search requires a one-time index rebuild on boot. For file counts under 100,000 files, SQLite builds the FTS index in under 2 seconds. We add an `fts5_files` virtual table and populate it via `INSERT INTO fts5_files(rowid, filename, full_path) SELECT id, filename, full_path FROM files` on startup after `reindex_files()` completes. We use `PRAGMA schema_version` comparison to only rebuild if the schema changed. For the target audience (engineering CAD files, typically 5,000–50,000 files), this is acceptable.

---

## 3. System Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Client (Browser / curl / external tool)                                │
│                                                                         │
│  Authorization: Bearer <JWT>     OR     X-API-Key: qpk_<key>           │
│  OR  ?access_token=<JWT>  (legacy fallback)                             │
└───────────────────────────┬─────────────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                    FastAPI Middleware + Dependency Chain                 │
│                                                                          │
│  current_user(request) → tries JWT decode → tries API key verify → 401  │
│       │                                                                  │
│       ├─ JWT path:                                                       │
│       │   decode_jwt(token) → get_user_by_id(payload["sub"]) → user     │
│       │                                                                  │
│       └─ API key path:                                                   │
│           token.startswith("qpk_") → sha256 compare → load key row      │
│           → build synthetic user (intersected permissions)               │
│                                                                          │
└──────────────────────────┬───────────────────────────────────────────────┘
                           │
                           ▼
POST /api/auth/login ──────┼────── LDAP bind flow (if configured)          │
                           │       └─ fall through to local PBKDF2         │
                           │
POST /api/peek/search  ────┼────── require_permission("use_quick_peek")   │
                           │         └─ FORMAT_PERMISSION[format] check   │
                           │            └─ can_access_folder() check      │
                           │               └─ search_index() with tag     │
                           │                  filter → results             │
                           │
GET /api/files/{id}/raw ───┼────── current_user → can_access_folder()     │
                           │         → require_permission("download_files")│
                           │            → FileResponse (download)          │
                           │
GET /api/files/{id}/preview ──┼─── current_user → can_access_folder()     │
                              │      → ensure_preview() → FileResponse    │
                              │
POST /api/admin/ldap-test ────┼─── require_permission("manage_users")     │
                              │      → ldap3.Connection(auto_bind)        │
                              │
┌──────────────────────────────────────────────────────────────────────────┐
│  Backend Services                                                        │
│                                                                          │
│  ┌──────────┐  ┌──────────────┐  ┌────────────┐  ┌───────────────────┐  │
│  │ auth.py  │  │ rbac.py      │  │ file_index │  │ preview.py        │  │
│  │ JWT/PBKDF│  │ can_access_  │  │ .py        │  │ ensure_preview()  │  │
│  │ LDAP bind│  │ folder()     │  │ search_    │  │ file_key()        │  │
│  │ API key  │  │              │  │ index()    │  │                   │  │
│  └──────────┘  └──────────────┘  └────────────┘  └───────────────────┘  │
│       │               │               │                    │            │
│       ▼               ▼               ▼                    ▼            │
│  ┌─────────────────────────────────────────────────────────────────┐     │
│  │  SQLite Database (quickpeek.sqlite3)                            │     │
│  │  tables: users, files, usage_logs, folder_presets,             │     │
│  │          api_keys, folder_scopes, folder_grants,               │     │
│  │          tags, file_tags, file_metadata, recent_files,         │     │
│  │          tag_audit_log, folder_schemas, fts5_files             │     │
│  └─────────────────────────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────────────────────────┘
```

**Request flow for a search with all v0.4 features enabled:**

```
Client → POST /api/peek/search
  headers: Authorization: Bearer <JWT>
  1. current_user() → decode JWT → load user from DB → user dict
  2. require_permission("use_quick_peek") → check user.permissions
  3. FORMAT_PERMISSION[format] check → user has view_step, etc.
  4. search_index(format, codes, root_path) → SQL query → file rows
  5. For each file row:
     a. can_access_folder(user, file.full_path, "view") → folder ACL check
     b. apply tag_filter (if provided in request body)
  6. Filtered results → _file_payload() → preview metadata
  7. Log search to usage_logs (existing behavior, db.py:93-97)
  8. Update recent_files (new, for "recents" panel)
  9. Return results
```

---

## 4. Database Schema

All new tables and column additions. Uses SQLite syntax. `ALTER TABLE ADD COLUMN` must be wrapped in try/except for idempotency. Execute inside `init_db()` at `db.py:38-94`.

### 4.1 Existing `users` Table — New Columns

```sql
-- Applied via ALTER TABLE ADD COLUMN in try/except after the CREATE TABLE block
ALTER TABLE users ADD COLUMN auth_source TEXT DEFAULT 'local';
ALTER TABLE users ADD COLUMN ldap_dn TEXT;
ALTER TABLE users ADD COLUMN email TEXT;
ALTER TABLE users ADD COLUMN display_name TEXT;
ALTER TABLE users ADD COLUMN last_synced_at TEXT;
```

### 4.2 `api_keys` Table

```sql
CREATE TABLE IF NOT EXISTS api_keys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    prefix TEXT NOT NULL,                         -- first 8 chars for UI display
    key_hash TEXT NOT NULL,                       -- sha256 of full key
    user_id INTEGER NOT NULL REFERENCES users(id),
    scopes_json TEXT NOT NULL DEFAULT '["use_quick_peek"]',
    expires_at TEXT,                              -- ISO datetime or NULL for no expiry
    last_used_at TEXT,
    created_at TEXT NOT NULL,
    revoked_at TEXT,                              -- NULL = active, set = revoked
    UNIQUE(prefix)
);
CREATE INDEX IF NOT EXISTS idx_api_keys_key_hash ON api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_user ON api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_active ON api_keys(revoked_at) WHERE revoked_at IS NULL;
```

### 4.3 `folder_scopes` Table

```sql
CREATE TABLE IF NOT EXISTS folder_scopes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern TEXT NOT NULL,                        -- path prefix glob: /data/cad/**, \\server\share\restricted\**
    description TEXT,
    created_at TEXT NOT NULL
);
```

### 4.4 `folder_grants` Table

```sql
CREATE TABLE IF NOT EXISTS folder_grants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scope_id INTEGER NOT NULL REFERENCES folder_scopes(id) ON DELETE CASCADE,
    principal_type TEXT NOT NULL CHECK(principal_type IN ('user','group','api_key')),
    principal_id TEXT NOT NULL,                   -- user id, group DN, or api_key id as TEXT
    permission TEXT NOT NULL DEFAULT 'view' CHECK(permission IN ('view','download','index')),
    effect TEXT NOT NULL CHECK(effect IN ('allow','deny')),
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_folder_grants_scope ON folder_grants(scope_id);
CREATE INDEX IF NOT EXISTS idx_folder_grants_principal ON folder_grants(principal_type, principal_id);
```

### 4.5 `tags` Table

```sql
CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    scope TEXT NOT NULL DEFAULT 'shared',         -- 'shared' (global) or 'user' (private)
    color TEXT DEFAULT '#6b7280',                 -- hex color for UI display
    created_at TEXT NOT NULL,
    UNIQUE(name, scope)
);
CREATE INDEX IF NOT EXISTS idx_tags_name ON tags(name COLLATE NOCASE);
```

### 4.6 `file_tags` Table (M2M)

```sql
CREATE TABLE IF NOT EXISTS file_tags (
    file_id INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    applied_by INTEGER REFERENCES users(id),
    created_at TEXT NOT NULL,
    PRIMARY KEY (file_id, tag_id)
);
CREATE INDEX IF NOT EXISTS idx_file_tags_tag ON file_tags(tag_id);
```

### 4.7 `file_metadata` Table

```sql
CREATE TABLE IF NOT EXISTS file_metadata (
    file_id INTEGER PRIMARY KEY REFERENCES files(id) ON DELETE CASCADE,
    project_code TEXT,
    revision TEXT,
    supplier TEXT,
    cost_center TEXT,
    custom_json TEXT NOT NULL DEFAULT '{}',
    updated_at TEXT NOT NULL,
    updated_by INTEGER REFERENCES users(id)
);
```

### 4.8 `recent_files` Table

```sql
CREATE TABLE IF NOT EXISTS recent_files (
    user_id INTEGER NOT NULL REFERENCES users(id),
    file_id INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    last_opened_at TEXT NOT NULL,
    open_count INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (user_id, file_id)
);
CREATE INDEX IF NOT EXISTS idx_recent_files_user_time ON recent_files(user_id, last_opened_at DESC);
```

### 4.9 `tag_audit_log` Table

```sql
CREATE TABLE IF NOT EXISTS tag_audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL REFERENCES files(id),
    tag_id INTEGER NOT NULL REFERENCES tags(id),
    action TEXT NOT NULL CHECK(action IN ('add','remove')),
    user_id INTEGER REFERENCES users(id),
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tag_audit_file ON tag_audit_log(file_id);
```

### 4.10 `folder_schemas` Table

```sql
CREATE TABLE IF NOT EXISTS folder_schemas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path_prefix TEXT NOT NULL,                    -- pattern matched against full_path
    required_fields_json TEXT NOT NULL DEFAULT '[]',
    created_by INTEGER REFERENCES users(id),
    created_at TEXT NOT NULL
);
```

### 4.11 FTS5 Virtual Table

```sql
-- Requires PRAGMA foreign_keys=OFF temporarily; FTS5 tables don't support FK.
-- Created in init_db() AFTER regular tables.
CREATE VIRTUAL TABLE IF NOT EXISTS fts5_files USING fts5(
    filename,
    full_path,
    content='files',
    content_rowid='id',
    tokenize='porter unicode61'
);
```

### 4.12 Backup/Rebuild of FTS5 Index

```python
# In init_db() or a dedicated init_fts5() function, after reindex_files():
def rebuild_fts5():
    with get_conn() as conn:
        conn.executescript("""
            INSERT OR REPLACE INTO fts5_files(rowid, filename, full_path)
            SELECT id, filename, full_path FROM files;
        """)
```

---

## 5. API Surface (Exhaustive)

### 5.1 Modified Auth Endpoint

#### `POST /api/auth/login` — Modified

**Purpose**: Try LDAP bind first (if configured), fall through to local PBKDF2.  
**Current location**: `routers/auth.py:12-22`  
**Permission gate**: None (public).  
**Request body**: `LoginRequest { username: string, password: string }` (unchanged from `schemas.py:7-9`).  
**Response body**: `TokenResponse { access_token: string, token_type: "bearer", user: User }` (unchanged).  
**Changes**: Insert LDAP bind logic before line 14. If LDAP succeeds, upsert user with `auth_source='ldap'`, `ldap_dn` set, `last_synced_at` set. If LDAP fails with bind error, return 401. If LDAP socket error, return 503. Otherwise fall through to existing `get_user_by_username` + `verify_password` on line 14-16.

**Error additions**:
- `401` — `"LDAP: Incorrect username or password"` vs `"Incorrect username or password"` (distinct for frontend)
- `503` — `"LDAP server is not reachable. Contact your administrator."`

### 5.2 New Auth Admin Endpoints

#### `POST /api/admin/ldap-test`

**Purpose**: Test LDAP connectivity without restarting the app.  
**Permission gate**: `require_permission("manage_users")`.  
**Request body**:
```json
{
  "url": "ldap://dc01.example.com:389",
  "bind_dn": "CN=svc-quickpeek,CN=Users,DC=example,DC=com",
  "bind_password": "secret",
  "search_base": "DC=example,DC=com",
  "search_filter": "(sAMAccountName={username})"
}
```
All fields optional — defaults read from env vars `QUICKPEEK_LDAP_*`.  
**Response body**: `{ "ok": true, "server_info": "..." }` or `{ "ok": false, "error": "..." }`.  
**Implementation**: 30-line function in `routers/admin.py`.

#### `GET /api/admin/ldap-config`

**Purpose**: Return masked LDAP config (show URLs, show search base, mask passwords).  
**Permission gate**: `require_permission("manage_users")`.  
**Response body**:
```json
{
  "url": "ldap://dc01.example.com:389",
  "bind_dn": "CN=svc-quickpeek,...",
  "search_base": "DC=example,DC=com",
  "search_filter": "(sAMAccountName={username})",
  "group_map": "CN=QuickPeek-Admins,...=manage_users,view_dashboard"
}
```

### 5.3 Search History & Recents (New Router: `routers/me.py`)

#### `GET /api/me/recents`

**Purpose**: Return recently opened files for the current user.  
**Permission gate**: `current_user` (authenticated).  
**Query params**: `limit` (int, default 20, max 50).  
**Response body**:
```json
{
  "files": [
    {
      "file_id": 123,
      "filename": "part-123.stp",
      "extension": ".stp",
      "full_path": "\\\\server\\cad\\part-123.stp",
      "last_opened_at": "2026-06-05T14:30:00",
      "open_count": 5
    }
  ]
}
```
**Implementation**: `SELECT f.id, f.filename, f.extension, f.full_path, rf.last_opened_at, rf.open_count FROM recent_files rf JOIN files f ON f.id = rf.file_id WHERE rf.user_id = ? ORDER BY rf.last_opened_at DESC LIMIT ?`.

#### `GET /api/me/recent-searches`

**Purpose**: Return past search queries for the current user.  
**Permission gate**: `current_user`.  
**Query params**: `limit` (int, default 10, max 50).  
**Response body**:
```json
{
  "searches": [
    {
      "query": "1827009605",
      "format": "step",
      "codes_count": 3,
      "files_found": 5,
      "created_at": "2026-06-05T14:30:00"
    }
  ]
}
```
**Implementation**: `SELECT details_json, format, codes_count, files_found, created_at FROM usage_logs WHERE user_id = ? AND action = 'search' ORDER BY created_at DESC LIMIT ?`. Extract codes from `details_json`.

#### `DELETE /api/me/history`

**Purpose**: Clear all search history and recents for the current user.  
**Permission gate**: `current_user`.  
**Response body**: `{ "ok": true }`.  
**Implementation**: `DELETE FROM usage_logs WHERE user_id = ?` + `DELETE FROM recent_files WHERE user_id = ?`.

### 5.4 Folder Permissions (New Admin Endpoints)

#### `GET /api/admin/folder-scopes`

**Purpose**: List all folder scopes.  
**Permission gate**: `require_permission("manage_users")`.  
**Response body**: `{ "scopes": [ { id, pattern, description, created_at }, ... ] }`.

#### `POST /api/admin/folder-scopes`

**Purpose**: Create a folder scope.  
**Permission gate**: `require_permission("manage_users")`.  
**Request body**: `{ "pattern": "/data/cad/**", "description": "Engineering CAD files" }`.  
**Response body**: `{ "scope": { id, pattern, description, created_at } }`.

#### `DELETE /api/admin/folder-scopes/{id}`

**Purpose**: Delete a folder scope (cascades to its grants).  
**Permission gate**: `require_permission("manage_users")`.  
**Response body**: `{ "ok": true }`.

#### `GET /api/admin/folder-grants`

**Purpose**: List all folder grants.  
**Permission gate**: `require_permission("manage_users")`.  
**Query params**: `scope_id` (optional, filter by scope).  
**Response body**: `{ "grants": [ { id, scope_id, pattern, principal_type, principal_id, permission, effect, created_at }, ... ] }`.

#### `POST /api/admin/folder-grants`

**Purpose**: Create a folder grant.  
**Permission gate**: `require_permission("manage_users")`.  
**Request body**:
```json
{
  "scope_id": 1,
  "principal_type": "user",
  "principal_id": "5",
  "permission": "view",
  "effect": "allow"
}
```
**Response body**: `{ "grant": { id, scope_id, principal_type, principal_id, permission, effect, created_at } }`.

#### `DELETE /api/admin/folder-grants/{id}`

**Purpose**: Delete a folder grant.  
**Permission gate**: `require_permission("manage_users")`.  
**Response body**: `{ "ok": true }`.

#### `POST /api/admin/simulate`

**Purpose**: Simulate effective permissions for a user+path.  
**Permission gate**: `require_permission("manage_users")`.  
**Request body**: `{ "path": "/data/cad/restricted/secret.stp", "user_id": 5 }`.  
**Response body**:
```json
{
  "path": "/data/cad/restricted/secret.stp",
  "effective": {
    "view": "deny",
    "download": "deny",
    "index": "allow"
  },
  "matched_rules": [
    { "scope_id": 1, "pattern": "/data/cad/restricted/**", "effect": "deny", "permission": ["view","download"] }
  ]
}
```

### 5.5 API Keys (New Admin Endpoints)

#### `GET /api/admin/api-keys`

**Purpose**: List all API keys (without full key hashes — only prefix + name).  
**Permission gate**: `require_permission("manage_users")`.  
**Response body**:
```json
{
  "keys": [
    { "id": 1, "name": "CI pipeline", "prefix": "qpk_a1b2c3d4", "user_id": 1, "username": "admin",
      "scopes": ["use_quick_peek", "view_step"], "expires_at": "2027-01-01T00:00:00",
      "last_used_at": "2026-06-05T12:00:00", "created_at": "2026-06-01T00:00:00",
      "revoked_at": null }
  ]
}
```

#### `POST /api/admin/api-keys`

**Purpose**: Create a new API key. The full key is returned only once.  
**Permission gate**: `require_permission("manage_users")`.  
**Request body**:
```json
{
  "name": "CI pipeline",
  "user_id": 1,
  "scopes": ["use_quick_peek", "view_step"],
  "expires_at": "2027-01-01T00:00:00"
}
```
**Response body**:
```json
{
  "key": { "id": 1, "name": "CI pipeline", "prefix": "qpk_a1b2c3d4", ... },
  "full_key": "qpk_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f"
}
```
**Implementation**: Generate 32 random bytes → encode as hex → prefix `qpk_` → store first 8 chars as `prefix` → store `sha256(full_key.encode()).hexdigest()` as `key_hash`.

#### `DELETE /api/admin/api-keys/{id}`

**Purpose**: Revoke an API key (soft-delete by setting `revoked_at`).  
**Permission gate**: `require_permission("manage_users")`.  
**Response body**: `{ "ok": true }`.

Or if idempotent: `DELETE` actually sets `revoked_at = now` — does not remove row.

### 5.6 Tags & Metadata (New Endpoints)

#### `GET /api/files/{file_id}/tags`

**Purpose**: Return tags applied to a file.  
**Permission gate**: `current_user`.  
**Response body**:
```json
{
  "tags": [
    { "id": 1, "name": "critical", "scope": "shared", "color": "#ef4444" }
  ]
}
```

#### `PUT /api/files/{file_id}/tags`

**Purpose**: Set tags on a file (replaces all tags).  
**Permission gate**: `current_user`.  
**Request body**: `{ "tags": ["critical", "wip"] }`.  
**Response body**: `{ "tags": [ { id, name, ... }, ... ] }`.  
**Implementation**: `DELETE FROM file_tags WHERE file_id = ?` → find-or-create each tag → `INSERT INTO file_tags`. Log to `tag_audit_log`.

#### `GET /api/files/{file_id}/metadata`

**Purpose**: Return custom metadata for a file.  
**Permission gate**: `current_user`.  
**Response body**:
```json
{
  "metadata": {
    "project_code": "AVT-2026-001",
    "revision": "C",
    "supplier": "Bosch Rexroth",
    "cost_center": "CC-4200",
    "custom_json": { "drawing_number": "DWG-001", "material": "AL6061" },
    "updated_at": "2026-06-05T14:30:00",
    "updated_by": 1
  }
}
```
If no metadata row exists for the file, return `{ "metadata": null }`.

#### `PUT /api/files/{file_id}/metadata`

**Purpose**: Upsert custom metadata for a file.  
**Permission gate**: `current_user`.  
**Request body**:
```json
{
  "project_code": "AVT-2026-001",
  "revision": "D",
  "supplier": "Bosch Rexroth",
  "cost_center": "CC-4200",
  "custom_json": { "drawing_number": "DWG-001", "material": "AL6061" }
}
```
All fields optional. `custom_json` must be a valid JSON object.  
**Response body**: `{ "metadata": { ... } }`.  
**Implementation**: `INSERT INTO file_metadata (file_id, ...) VALUES (?, ...) ON CONFLICT(file_id) DO UPDATE SET ...`.

#### `GET /api/tags`

**Purpose**: Autocomplete/search tags by name.  
**Permission gate**: `current_user`.  
**Query params**: `q` (string, min 1 char).  
**Response body**:
```json
{
  "tags": [
    { "id": 1, "name": "critical", "scope": "shared", "color": "#ef4444" }
  ]
}
```
**Implementation**: `SELECT * FROM tags WHERE name LIKE ? ORDER BY name LIMIT 20`.

#### `POST /api/admin/folder-schemas`

**Purpose**: Define required metadata fields for a path prefix.  
**Permission gate**: `require_permission("manage_users")`.  
**Request body**: `{ "path_prefix": "/data/cad/engineering/**", "required_fields": ["project_code", "revision"] }`.  
**Response body**: `{ "schema": { id, path_prefix, required_fields, ... } }`.

### 5.7 Modified Search Endpoint

#### `POST /api/peek/search` — Modified

**Current location**: `routers/peek.py:49-99`.  
**Permission gate**: Remains `require_permission("use_quick_peek")` (line 50).  
**Additions**:
- **Request body**: Add `tag_filter: Optional[List[str]] = None` to `SearchRequest` in `schemas.py:34-37`.
- **Folder scope filtering**: After line 77 (`indexed_results = search_index(...)`), filter results through `can_access_folder(user, match["full_path"], "view")`.
- **Tag filtering**: If `tag_filter` is provided, filter results to only files that have ALL specified tags: `SELECT file_id FROM file_tags WHERE tag_id IN (SELECT id FROM tags WHERE name IN (?)) GROUP BY file_id HAVING COUNT(DISTINCT tag_id) = ?`.
- **Response**: Add `"tags": [...]` and `"metadata": {...}` to each `FileItem` returned in `_file_payload()`.

**Modified `_file_payload()`** (at `peek.py:32-46`): Append `tags` and `metadata` fields from new tables.

### 5.8 Modified Raw/Preview Endpoints (P0 Fix)

#### `GET /api/files/{file_id}/raw` — Modified

**Current location**: `routers/peek.py:128-144`.  
**Current gap**: Only checks `current_user` (line 129). **No format permission check, no folder scope check, no download permission check.** This means any authenticated user can download any file.  
**v0.4 fix**: Add:
1. `require_permission("download_files")` check — add `routers/peek.py:129` before the function body.
2. `can_access_folder(user, path, "download")` check after line 133 (`item = row_to_dict(row)`).
3. Format permission check: `require_permission(FORMAT_PERMISSION[format])` — infer format from file extension.

#### `GET /api/files/{file_id}/preview` — Modified

**Current location**: `routers/peek.py:147-191`.  
**Current gap**: Only checks `current_user` (line 148). **No folder scope check.**  
**v0.4 fix**: Add `can_access_folder(user, path, "view")` check after the file row is fetched (line 152).

---

## 6. Auth Flow Pseudocode

### 6.1 New `current_user` Dependency (Modified `auth.py:100-121`)

```python
async def current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    access_token: Optional[str] = Query(default=None),
) -> Dict[str, Any]:
    # Extract token from header (Bearer) or query param (legacy)
    token = access_token
    if credentials and credentials.scheme.lower() == "bearer":
        token = credentials.credentials

    # Try X-API-Key header (v0.4 addition)
    if not token:
        token = request.headers.get("X-API-Key")

    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    # ── Try JWT path (existing behavior) ──
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub = payload.get("sub")
        if sub is not None:
            user_id = int(sub)
            user = get_user_by_id(user_id)
            if user and user.get("is_active"):
                return user
    except (JWTError, ValueError):
        pass  # Not a valid JWT — try API key

    # ── Try API key path (v0.4) ──
    if token.startswith("qpk_"):
        key = _verify_api_key(token)  # sha256 comparison
        if key and key.revoked_at is None:
            if key.expires_at and key.expires_at < datetime.now(timezone.utc):
                raise HTTPException(status_code=401, detail="API key expired")
            key.last_used_at = utc_now()  # update asynchronously
            return _build_api_key_user(key)  # synthetic user with intersected perms

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication")
```

### 6.2 API Key Verification Functions (New in `auth.py`)

```python
import hashlib

def _hash_api_key(raw_key: str) -> str:
    """Return lowercase hex sha256 digest of an API key."""
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def _verify_api_key(raw_key: str) -> Optional[Dict[str, Any]]:
    """Lookup an API key by its full hash. Returns the key row or None."""
    key_hash = _hash_api_key(raw_key)
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM api_keys WHERE key_hash = ? AND revoked_at IS NULL",
            (key_hash,),
        ).fetchone()
    if row is None:
        return None
    key = row_to_dict(row)
    key["scopes"] = json_loads(key.get("scopes_json"), [])
    return key


def _build_api_key_user(key: Dict[str, Any]) -> Dict[str, Any]:
    """Build a synthetic user dict from an API key."""
    issuing_user = get_user_by_id(key["user_id"])
    if not issuing_user:
        raise HTTPException(status_code=401, detail="Issuing user not found")
    # Intersect API key scopes with issuing user's permissions
    perms = [s for s in key["scopes"] if s in (issuing_user.get("permissions") or [])]
    return {
        "id": -key["id"],  # negative id to distinguish from real users
        "username": f"api_key:{key['name']}",
        "role": "user",
        "permissions": perms,
        "is_active": True,
        "auth_source": "api_key",
        "api_key_id": key["id"],
    }
```

### 6.3 LDAP Login Flow (Modified `routers/auth.py:12-22`)

```python
from ..config import (
    QUICKPEEK_LDAP_URL, QUICKPEEK_LDAP_BIND_DN, QUICKPEEK_LDAP_BIND_PASSWORD,
    QUICKPEEK_LDAP_SEARCH_BASE, QUICKPEEK_LDAP_SEARCH_FILTER,
    QUICKPEEK_LDAP_GROUP_MAP,
)

@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest):
    # ── LDAP path (v0.4 addition) ──
    if QUICKPEEK_LDAP_URL:
        return _ldap_login(payload)

    # ── Local PBKDF2 path (existing) ──
    return _local_login(payload)


def _ldap_login(payload: LoginRequest) -> dict:
    import ldap3
    from ldap3.core.exceptions import LDAPBindError, LDAPSocketOpenError

    # 1. Build user DN from search
    server = ldap3.Server(QUICKPEEK_LDAP_URL, get_info=ldap3.ALL)
    user_dn_template = QUICKPEEK_LDAP_BIND_DN or ""

    try:
        # First, bind with service account to search for user
        conn = ldap3.Connection(server, user=QUICKPEEK_LDAP_BIND_DN,
                                password=QUICKPEEK_LDAP_BIND_PASSWORD, auto_bind=True)
        search_filter = QUICKPEEK_LDAP_SEARCH_FILTER.replace("{username}", payload.username)
        conn.search(QUICKPEEK_LDAP_SEARCH_BASE, search_filter, attributes=['memberOf', 'mail', 'displayName', 'dn'])
        if len(conn.entries) == 0:
            raise HTTPException(status_code=401, detail="LDAP: Incorrect username or password")
        entry = conn.entries[0]
        user_dn = str(entry.entry_dn)
        conn.unbind()

        # 2. Verify user credentials
        user_conn = ldap3.Connection(server, user=user_dn, password=payload.password, auto_bind=True)

        # 3. Extract groups
        groups = []
        if 'memberOf' in entry:
            groups = [str(g) for g in entry.memberOf]

        # 4. Map groups to permissions
        perms = _map_ldap_groups_to_permissions(groups)

        # 5. Upsert user
        now = utc_now()
        email = str(getattr(entry, 'mail', ''))
        display_name = str(getattr(entry, 'displayName', payload.username))
        with get_conn() as conn:
            existing = conn.execute("SELECT id FROM users WHERE username = ?", (payload.username,)).fetchone()
            if existing:
                conn.execute("""
                    UPDATE users SET ldap_dn=?, email=?, display_name=?, permissions_json=?,
                        auth_source='ldap', last_synced_at=?, updated_at=?
                    WHERE id=?
                """, (user_dn, email, display_name, json_dumps(perms), now, now, existing["id"]))
                user_id = existing["id"]
            else:
                cur = conn.execute("""
                    INSERT INTO users (username, password_hash, role, permissions_json, is_active,
                        auth_source, ldap_dn, email, display_name, last_synced_at, created_at, updated_at)
                    VALUES (?, '', 'user', ?, 1, 'ldap', ?, ?, ?, ?, ?, ?)
                """, (payload.username, json_dumps(perms), user_dn, email, display_name, now, now, now))
                user_id = cur.lastrowid

        user = get_user_by_id(user_id)
        token = create_access_token({"sub": str(user["id"])})
        return {"access_token": token, "token_type": "bearer", "user": public_user(user)}

    except LDAPBindError:
        raise HTTPException(status_code=401, detail="LDAP: Incorrect username or password")
    except LDAPSocketOpenError:
        raise HTTPException(status_code=503, detail="LDAP server is not reachable. Contact your administrator.")
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"LDAP error: {str(exc)}")


def _map_ldap_groups_to_permissions(groups: list[str]) -> list[str]:
    """Map LDAP groups to Quick Peek permissions using QUICKPEEK_LDAP_GROUP_MAP."""
    from ..config import QUICKPEEK_LDAP_GROUP_MAP, DEFAULT_USER_PERMISSIONS
    if not QUICKPEEK_LDAP_GROUP_MAP:
        return DEFAULT_USER_PERMISSIONS[:]
    perms = set()
    for mapping in QUICKPEEK_LDAP_GROUP_MAP.split(","):
        mapping = mapping.strip()
        if "=" not in mapping:
            continue
        group_dn, perm_list = mapping.split("=", 1)
        if group_dn.strip() in groups:
            for p in perm_list.split(";"):
                perms.add(p.strip())
    return list(perms) if perms else DEFAULT_USER_PERMISSIONS[:]
```

### 6.4 Local Login Fallback (Existing, Unchanged)

```python
def _local_login(payload: LoginRequest) -> dict:
    user = get_user_by_username(payload.username)
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    if not user.get("is_active"):
        raise HTTPException(status_code=403, detail="User is disabled")
    with get_conn() as conn:
        conn.execute("UPDATE users SET last_login_at = ? WHERE id = ?", (utc_now(), user["id"]))
    token = create_access_token({"sub": str(user["id"])})
    return {"access_token": token, "token_type": "bearer", "user": public_user(user)}
```

---

## 7. Permission Composition

### 7.1 `can_access_folder()` — New function in `rbac.py`

```python
# backend/app/rbac.py
from __future__ import annotations

import fnmatch
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import QUICKPEEK_FOLDER_DEFAULT_ALLOW
from .db import get_conn, row_to_dict, rows_to_dicts


def _normalize_path(full_path: str) -> str:
    """Normalize a file path for pattern matching: lowercase, forward slashes."""
    path = str(Path(full_path).resolve())
    if os.name == "nt":
        path = path.replace("\\", "/").lower()
    return path


def _get_folder_grants_for_principal(principal_type: str, principal_id: str) -> List[Dict[str, Any]]:
    """Fetch all folder grants matching a principal (user or api_key)."""
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT fg.*, fs.pattern
            FROM folder_grants fg
            JOIN folder_scopes fs ON fs.id = fg.scope_id
            WHERE fg.principal_type = ? AND fg.principal_id = ?
            """,
            (principal_type, principal_id),
        ).fetchall()
    return rows_to_dicts(rows)


def _pattern_matches(pattern: str, normalized_path: str) -> bool:
    """Check if a path matches a glob pattern (case-insensitive on Windows)."""
    pattern = pattern.replace("\\", "/")
    # Handle ** for recursive matching
    if "**" in pattern:
        # Split on ** and check prefix/suffix
        parts = pattern.split("**")
        if normalized_path.startswith(_normalize_path(parts[0])) and normalized_path.endswith(_normalize_path(parts[-1])):
            return True
    return fnmatch.fnmatch(normalized_path, _normalize_path(pattern)) or \
           normalized_path.startswith(_normalize_path(pattern.rstrip("*")))


def can_access_folder(
    user: Dict[str, Any],
    full_path: str,
    permission: str = "view",
) -> bool:
    """
    Check if a user can access a file at full_path with the given permission.
    Admin role bypasses all folder checks.

    Composition:
      1. Admin → True
      2. Deny rules (evaluated first, deny wins)
      3. Allow rules
      4. Default (QUICKPEEK_FOLDER_DEFAULT_ALLOW)
    """
    # 1. Admin bypass
    if user.get("role") == "admin":
        return True

    # Synthetic API key users are never admin
    normalized = _normalize_path(full_path)

    # 2. Determine principal type and ID
    if user.get("auth_source") == "api_key":
        principal_type = "api_key"
        principal_id = str(user["api_key_id"])
    else:
        principal_type = "user"
        principal_id = str(user["id"])

    # 3. Fetch matching grants
    grants = _get_folder_grants_for_principal(principal_type, principal_id)

    # 4. Check deny rules first
    for g in grants:
        if g["effect"] == "deny" and g["permission"] == permission:
            if _pattern_matches(g["pattern"], normalized):
                return False

    # 5. Check allow rules
    for g in grants:
        if g["effect"] == "allow" and g["permission"] == permission:
            if _pattern_matches(g["pattern"], normalized):
                return True

    # 6. Default
    return QUICKPEEK_FOLDER_DEFAULT_ALLOW
```

### 7.2 Usage in `raw_file()` — P0 Fix

Insert after file row is fetched at `peek.py:131-132`:

```python
@router.get("/files/{file_id}/raw")
def raw_file(file_id: int, user=Depends(current_user)):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM files WHERE id = ?", (file_id,)).fetchone()
    item = row_to_dict(row)
    if not item:
        raise HTTPException(status_code=404, detail="File not found")
    path = Path(item["full_path"])
    if not path.exists():
        raise HTTPException(status_code=404, detail="File missing on disk")

    # v0.4: folder scope + download permission check (P0 fix)
    from ..rbac import can_access_folder
    if not can_access_folder(user, item["full_path"], "download"):
        raise HTTPException(status_code=403, detail="Folder scope denies download access")
    # Check download_files permission
    if user.get("role") != "admin" and "download_files" not in (user.get("permissions") or []):
        raise HTTPException(status_code=403, detail="Missing permission: download_files")

    return FileResponse(path, ...)
```

### 7.3 Integration with Search Results

In `routers/peek.py:search()`, after line 75 (`indexed_results = search_index(...)`) and before `_file_payload()` on line 81:

```python
from ..rbac import can_access_folder

# v0.4: Filter by folder scope
filtered_results = []
for item in indexed_results:
    filtered_matches = []
    for m in item["matches"]:
        # Folder scope check
        if not can_access_folder(user, m["full_path"], "view"):
            continue
        # Tag filter (if provided)
        if payload.tag_filter:
            # Check file has ALL requested tags
            with get_conn() as conn:
                matched = conn.execute("""
                    SELECT COUNT(*) FROM file_tags ft
                    JOIN tags t ON t.id = ft.tag_id
                    WHERE ft.file_id = ? AND t.name IN ({})
                """.format(",".join("?" for _ in payload.tag_filter)),
                    [m["id"]] + payload.tag_filter
                ).fetchone()[0]
            if matched < len(payload.tag_filter):
                continue
        filtered_matches.append(m)
    if filtered_matches:
        item["matches"] = filtered_matches
        filtered_results.append(item)
indexed_results = filtered_results
```

---

## 8. Frontend Changes (High-Level)

### 8.1 `types.ts` — New Types

Add to `frontend/src/types.ts`:

```typescript
// API Key
export type ApiKey = {
  id: number;
  name: string;
  prefix: string;
  user_id: number;
  username: string;
  scopes: string[];
  expires_at: string | null;
  last_used_at: string | null;
  created_at: string;
  revoked_at: string | null;
};

// Folder Scope
export type FolderScope = {
  id: number;
  pattern: string;
  description: string;
  created_at: string;
};

// Folder Grant
export type FolderGrant = {
  id: number;
  scope_id: number;
  pattern: string;
  principal_type: 'user' | 'group' | 'api_key';
  principal_id: string;
  permission: 'view' | 'download' | 'index';
  effect: 'allow' | 'deny';
  created_at: string;
};

// Tag
export type Tag = {
  id: number;
  name: string;
  scope: 'shared' | 'user';
  color: string;
  created_at: string;
};

// File Metadata
export type FileMetadata = {
  project_code: string | null;
  revision: string | null;
  supplier: string | null;
  cost_center: string | null;
  custom_json: Record<string, unknown>;
  updated_at: string;
  updated_by: number;
};

// Recent File
export type RecentFile = {
  file_id: number;
  filename: string;
  extension: string;
  full_path: string;
  last_opened_at: string;
  open_count: number;
};

// Recent Search
export type RecentSearch = {
  query: string;
  format: string;
  codes_count: number;
  files_found: number;
  created_at: string;
};

// Extended FileItem for v0.4
export type FileItemV4 = FileItem & {
  tags: Tag[];
  metadata: FileMetadata | null;
};
```

### 8.2 `api.ts` — New API Methods

```typescript
// ── Recents & History ──
export async function getRecents(limit = 20) {
  return api<{ files: RecentFile[] }>(`/api/me/recents?limit=${limit}`);
}
export async function getRecentSearches(limit = 10) {
  return api<{ searches: RecentSearch[] }>(`/api/me/recent-searches?limit=${limit}`);
}
export async function clearHistory() {
  return api<{ ok: boolean }>('/api/me/history', { method: 'DELETE' });
}

// ── Tags & Metadata ──
export async function getFileTags(fileId: number) {
  return api<{ tags: Tag[] }>(`/api/files/${fileId}/tags`);
}
export async function setFileTags(fileId: number, tags: string[]) {
  return api<{ tags: Tag[] }>(`/api/files/${fileId}/tags`, {
    method: 'PUT', body: JSON.stringify({ tags })
  });
}
export async function getFileMetadata(fileId: number) {
  return api<{ metadata: FileMetadata | null }>(`/api/files/${fileId}/metadata`);
}
export async function setFileMetadata(fileId: number, metadata: Partial<FileMetadata>) {
  return api<{ metadata: FileMetadata }>(`/api/files/${fileId}/metadata`, {
    method: 'PUT', body: JSON.stringify(metadata)
  });
}
export async function searchTags(query: string) {
  return api<{ tags: Tag[] }>(`/api/tags?q=${encodeURIComponent(query)}`);
}

// ── API Keys ──
export async function listApiKeys() {
  return api<{ keys: ApiKey[] }>('/api/admin/api-keys');
}
export async function createApiKey(data: { name: string; user_id: number; scopes: string[]; expires_at?: string }) {
  return api<{ key: ApiKey; full_key: string }>('/api/admin/api-keys', {
    method: 'POST', body: JSON.stringify(data)
  });
}
export async function revokeApiKey(id: number) {
  return api<{ ok: boolean }>(`/api/admin/api-keys/${id}`, { method: 'DELETE' });
}

// ── Folder Scopes & Grants ──
export async function listFolderScopes() {
  return api<{ scopes: FolderScope[] }>('/api/admin/folder-scopes');
}
export async function createFolderScope(data: { pattern: string; description?: string }) {
  return api<{ scope: FolderScope }>('/api/admin/folder-scopes', {
    method: 'POST', body: JSON.stringify(data)
  });
}
export async function deleteFolderScope(id: number) {
  return api<{ ok: boolean }>(`/api/admin/folder-scopes/${id}`, { method: 'DELETE' });
}
export async function listFolderGrants(scopeId?: number) {
  const query = scopeId ? `?scope_id=${scopeId}` : '';
  return api<{ grants: FolderGrant[] }>(`/api/admin/folder-grants${query}`);
}
export async function createFolderGrant(data: Omit<FolderGrant, 'id' | 'created_at'>) {
  return api<{ grant: FolderGrant }>('/api/admin/folder-grants', {
    method: 'POST', body: JSON.stringify(data)
  });
}
export async function deleteFolderGrant(id: number) {
  return api<{ ok: boolean }>(`/api/admin/folder-grants/${id}`, { method: 'DELETE' });
}
export async function simulatePermission(path: string, userId: number) {
  return api<{ path: string; effective: Record<string, string>; matched_rules: unknown[] }>('/api/admin/simulate', {
    method: 'POST', body: JSON.stringify({ path, user_id: userId })
  });
}

// ── LDAP ──
export async function testLdapConnection(data?: { url?: string; bind_dn?: string; bind_password?: string }) {
  return api<{ ok: boolean; server_info?: string; error?: string }>('/api/admin/ldap-test', {
    method: 'POST', body: JSON.stringify(data || {})
  });
}
export async function getLdapConfig() {
  return api<Record<string, string>>('/api/admin/ldap-config');
}
```

### 8.3 `LoginPage.tsx` — LDAP Error Handling

Distinguish error messages from `current_user` in `frontend/src/pages/LoginPage.tsx`:

- `"LDAP: Incorrect username or password"` → Show "LDAP authentication failed" badge.
- `"LDAP server is not reachable"` → Show warning banner "LDAP server unreachable. Using local login." and allow local fallback.
- `"Incorrect username or password"` (no LDAP prefix) → Show generic "Invalid credentials".

```typescript
// In submit() error handler:
if (err.message.startsWith('LDAP:')) {
  setError(err.message.replace('LDAP: ', ''));  // Show "Incorrect username or password"
  setIsLdapError(true);
} else {
  setError(err.message);
}
```

### 8.4 `QuickPeekPage.tsx` — Recents Panel + Tag Filter Chips

**Recents panel**:
- Add a collapsible "Recents" section between folder presets and the search area.
- Each recent file shows filename, format icon, last-opened timestamp.
- Clicking a recent file pre-fills the format selector and code input, then triggers search.

**Tag filter chips**:
- When a search result is displayed, show a "Filter by tag" dropdown next to the code list.
- Chip-based selection: `+critical ×` style tags above results.
- Tag autocomplete from `GET /api/tags?q=...` when user types in the tag filter input.

**Tag picker in PreviewCard**:
- Each card shows existing tags as small colored badges.
- Clicking a card's tag area opens an inline tag editor (add/remove tags via `PUT /api/files/{id}/tags`).

**Empty state for "no folder access"**:
- When `can_access_folder()` denies everything visible to the user's role, show:
  "You don't have access to any files in this folder scope. Contact your administrator."

**Initial recents fetch on `useEffect`**:
```typescript
const [recents, setRecents] = useState<RecentFile[]>([]);
useEffect(() => {
  getRecents().then(r => setRecents(r.files)).catch(() => {});
}, []);
```

### 8.5 `AdminPage.tsx` — New Sub-Panels

Add tab navigation to AdminPage with the following panels:

1. **Users** (existing, unchanged)
2. **Folder Scopes** — Create/list/delete scopes with pattern input
3. **Folder Grants** — Create/list/delete grants with user/scope picker
4. **API Keys** — Create/list/revoke keys, with scope checkboxes
5. **LDAP Test** — Connection test button + config display
6. **Folder Schemas** — Define required metadata fields per path prefix
7. **Permission Simulator** — Enter path + user → show effective permissions

Each panel is a separate tab rendered when active:

```typescript
type AdminTab = 'users' | 'folder-scopes' | 'folder-grants' | 'api-keys' | 'ldap' | 'schemas' | 'simulate';
const [adminTab, setAdminTab] = useState<AdminTab>('users');
```

### 8.6 `ViewerModal.tsx` — Tag Editor + Tag Display

**Tag display**:
- In the header area (below filename), show file's tags as colored badges.

**Tag editor**:
- Add an "Edit tags" button in the modal actions bar.
- When clicked, show an inline tag editor: text input with autocomplete (`GET /api/tags?q=...`), chip display for added tags, and a save button that calls `PUT /api/files/{id}/tags`.
- Show metadata fields (project_code, revision, etc.) in a collapsible "Details" section.

### 8.7 `InfoPage.tsx` — Update Feature List

Add v0.4 features to the features list:
- "LDAP authentication support" — badge
- "Per-folder access control" — badge
- "File tagging & metadata" — badge
- "API key authentication for automation" — badge

### 8.8 `RoadmapPage.tsx` — Update v0.4 Status

Change `status: 'planned'` to `status: 'done'` for v0.4 in `frontend/src/pages/RoadmapPage.tsx:42-51`.

### 8.9 `ReleasesPage.tsx` — Update v0.4 Status

Change `status: 'planned'` to `status: 'done'` for v0.4 in `frontend/src/pages/ReleasesPage.tsx:48`. Update date to `'2026'`. Update items to match actual v0.4 features.

---

## 9. Migration Plan (Ordered, With Per-Task Owner)

### 9.1 Schema Migration — db.py

**Owner**: orion-dev  
**Location**: `backend/app/db.py`  
**Lines affected**: `db.py:38-94` (`init_db()` function).  
**Tasks**:
1. Add `PRAGMA foreign_keys=ON;` at top of `init_db()` (line 42 area).
2. Add all new `CREATE TABLE IF NOT EXISTS` statements after line 93.
3. Add all `ALTER TABLE users ADD COLUMN ...` statements wrapped in try/except.
4. Add FTS5 virtual table creation.
5. Add `rebuild_fts5()` call after `reindex_files()` in `main.py:29-35`.
6. Add history cleanup query: `DELETE FROM usage_logs WHERE created_at < datetime('now', ?)` with `QUICKPEEK_HISTORY_RETENTION_DAYS`.
7. **Estimate**: 2 hours.

### 9.2 Auth Refactor — auth.py + routers/auth.py

**Owner**: orion-dev  
**Locations**: `backend/app/auth.py`, `backend/app/routers/auth.py`.  
**Lines affected**: `auth.py:100-121` (current_user), `routers/auth.py:12-22` (login).  
**Tasks**:
1. Add `_hash_api_key()`, `_verify_api_key()`, `_build_api_key_user()` to `auth.py`.
2. Modify `current_user()` to try `X-API-Key` header after Bearer token.
3. Add `_ldap_login()` and `_map_ldap_groups_to_permissions()` to `routers/auth.py`.
4. Modify `login()` to route to LDAP path if `QUICKPEEK_LDAP_URL` is set.
5. Add `POST /api/admin/ldap-test` and `GET /api/admin/ldap-config` endpoints.
6. **Estimate**: 4 hours.

### 9.3 Folder Scoping — rbac.py + peek.py + folders.py

**Owner**: orion-dev  
**New file**: `backend/app/rbac.py`.  
**Lines affected**: `peek.py:49-99` (search), `peek.py:128-144` (raw_file), `peek.py:147-191` (preview_file), `folders.py:54-91` (browse).  
**Tasks**:
1. Create `rbac.py` with `can_access_folder()`, helper functions, glob matching.
2. Modify `search()` to filter results through `can_access_folder()`.
3. Modify `raw_file()` to add download permission check + folder scope check (P0 fix).
4. Modify `preview_file()` to add folder scope check (P0 fix).
5. Add admin CRUD endpoints for folder scopes and grants.
6. **Estimate**: 6 hours.

### 9.4 Search History — routers/me.py

**Owner**: orion-dev  
**New file**: `backend/app/routers/me.py`.  
**Tasks**:
1. Create `routers/me.py` with `GET /api/me/recents`, `GET /api/me/recent-searches`, `DELETE /api/me/history`.
2. Modify existing `/api/usage/open` endpoint (`peek.py:102-112`) to also upsert into `recent_files`.
3. Add router to `main.py:46` (`app.include_router(me.router)`).
4. **Estimate**: 2 hours.

### 9.5 Tagging — routers/metadata.py + file_index.py

**Owner**: orion-dev  
**New file**: `backend/app/routers/metadata.py`.  
**Lines affected**: `file_index.py:47-63` (reindex_files), `peek.py:32-46` (_file_payload).  
**Tasks**:
1. Create `routers/metadata.py` with tag CRUD and metadata CRUD endpoints.
2. Modify `_file_payload()` to append tags and metadata to every file result.
3. Add tag filtering support to `search()`.
4. No change to `reindex_files()` — cascading deletes handle cleanup.
5. Add `POST /api/admin/folder-schemas` endpoint.
6. **Estimate**: 4 hours.

### 9.6 API Keys — routers/admin.py

**Owner**: orion-dev  
**Location**: `backend/app/routers/admin.py`.  
**Lines affected**: `admin.py:101` (end of file — append new endpoints).  
**Tasks**:
1. Add API key CRUD endpoints to `routers/admin.py`.
2. Key generation: `os.urandom(32).hex()` → prefix `qpk_`.
3. Implement key hash storage and one-time return of full key.
4. **Estimate**: 2 hours.

### 9.7 Frontend — All UI Changes

**Owner**: lyra-designer (design) + orion-dev (implementation)  
**Files affected**: All frontend files listed in Section 8.  
**Tasks**:
1. Update `types.ts` with all new types.
2. Update `api.ts` with all new API methods.
3. Modify `LoginPage.tsx` for LDAP error differentiation.
4. Modify `QuickPeekPage.tsx` for recents panel + tag filter chips + tag picker.
5. Modify `AdminPage.tsx` for folder scopes/grants/API keys/LDAP/schemas/simulate tabs.
6. Modify `ViewerModal.tsx` for tag editor/display + metadata display.
7. Update `RoadmapPage.tsx` and `ReleasesPage.tsx` v0.4 status.
8. Update `InfoPage.tsx` features + specs list.
9. **Estimate**: 8 hours.

### 9.8 Tests

**Owner**: rigel-review  
**New directories**: `backend/tests/`.  
**Tasks**:
1. Set up pytest with `pytest-asyncio`, `httpx`, `pytest-httpx`.
2. Write `tests/test_auth.py` — 9 test cases (see Section 10).
3. Write `tests/test_search.py` — 4 test cases (see Section 10).
4. Write `tests/test_migration.py` — 2 test cases (see Section 10).
5. **Estimate**: 4 hours.

### 9.9 Docs/Release

**Owner**: atlas-docs  
**Files affected**: `frontend/src/version.ts`, `README.md`, `quick_peek.spec`.  
**Tasks**:
1. Update `version.ts`: set `VERSION = '0.4.0'`.
2. Update `README.md` with v0.4 feature list.
3. Update `quick_peek.spec` hiddenimports (Section 11).
4. Update `frontend/src/pages/RoadmapPage.tsx` — set v0.4 to done, add v0.5.
5. Update `frontend/src/pages/ReleasesPage.tsx` — set v0.4 to done.
6. **Estimate**: 1 hour.

---

## 10. Test Plan (Concrete)

### 10.1 Test Infrastructure

**Add to `backend/requirements.txt`**:
```
pytest>=8.0
pytest-asyncio>=0.24.0
httpx>=0.27.0
pytest-httpx>=0.30.0
```

**New directory**: `backend/tests/__init__.py` (empty) + `backend/tests/conftest.py`:

```python
# conftest.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

import pytest
from app.db import init_db, get_conn


@pytest.fixture(autouse=True)
def setup_db():
    """Fresh in-memory SQLite DB for every test."""
    import app.config as config
    import app.db as db_module
    # Override to in-memory
    original = config.DB_PATH
    config.DB_PATH = Path("/tmp/test_quickpeek_v0.4.sqlite3")
    if config.DB_PATH.exists():
        config.DB_PATH.unlink()
    init_db()
    yield
    config.DB_PATH.unlink(missing_ok=True)
    config.DB_PATH = original
```

### 10.2 `tests/test_auth.py` — 9 Test Cases

```python
"""
Auth test cases for v0.4.

Test matrix:
  1. local-good       — Valid local credentials → 200 + token
  2. local-bad        — Invalid local password → 401
  3. api-key-good     — Valid API key in X-API-Key header → 200 + user
  4. api-key-revoked  — Revoked API key → 401
  5. api-key-expired  — Expired API key → 401
  6. api-key-missing-scope — Key without 'use_quick_peek' → 403 on search
  7. ldap-bind-success  — Mock LDAP bind succeeds → 200 + token (need pytest-httpx or mock ldap3)
  8. ldap-bind-bad-creds — Mock LDAP bind fails → 401
  9. ldap-unavailable   — Mock LDAP socket error → 503
"""

# Case 1: local-good
async def test_local_login_good(client):
    resp = await client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()
    assert resp.json()["token_type"] == "bearer"

# Case 2: local-bad
async def test_local_login_bad(client):
    resp = await client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
    assert resp.status_code == 401

# Case 3: api-key-good
async def test_api_key_good(client, api_key_header):
    resp = await client.get("/api/auth/me", headers=api_key_header)
    assert resp.status_code == 200
    assert resp.json()["auth_source"] == "api_key"

# Case 4: api-key-revoked
async def test_api_key_revoked(client, revoked_api_key_header):
    resp = await client.get("/api/auth/me", headers=revoked_api_key_header)
    assert resp.status_code == 401

# Case 5: api-key-expired
async def test_api_key_expired(client, expired_api_key_header):
    resp = await client.get("/api/auth/me", headers=expired_api_key_header)
    assert resp.status_code == 401

# Case 6: api-key-missing-scope
async def test_api_key_missing_scope(client, limited_api_key_header):
    resp = await client.post("/api/peek/search", headers=limited_api_key_header,
                             json={"format": "step", "codes": ["test"]})
    assert resp.status_code == 403

# Case 7-9: LDAP (requires mocking ldap3.Connection)
async def test_ldap_bind_success(client, monkeypatch):
    # monkeypatch ldap3.Connection to auto_bind successfully
    # and return a mock entry with memberOf
    pass

async def test_ldap_bind_bad_creds(client, monkeypatch):
    # monkeypatch ldap3.Connection to raise LDAPBindError
    pass

async def test_ldap_unavailable(client, monkeypatch):
    # monkeypatch ldap3.Connection to raise LDAPSocketOpenError
    pass
```

### 10.3 `tests/test_search.py` — 4 Test Cases

```python
"""
Search test cases for v0.4.

Test matrix:
  1. tag-filter       — Search with tag_filter → only files with matching tags returned
  2. folder-allow     — User with explicit folder allow → file in allowed path returned
  3. folder-deny      — User with explicit folder deny → file in denied path excluded
  4. folder-default   — User with no folder grants → file included if default-allow=True
"""

# Case 1: tag-filter
async def test_search_tag_filter(client, auth_header, indexed_files_with_tags):
    resp = await client.post("/api/peek/search", headers=auth_header,
                             json={"format": "step", "codes": ["test"], "tag_filter": ["critical"]})
    assert resp.status_code == 200
    for result in resp.json()["results"]:
        for file_item in result["files"]:
            assert any(t["name"] == "critical" for t in file_item["tags"])

# Case 2: folder-allow
async def test_search_folder_allow(client, auth_header, indexed_files, folder_allow_grant):
    resp = await client.post("/api/peek/search", headers=auth_header,
                             json={"format": "step", "codes": ["allowed_file"]})
    assert resp.status_code == 200
    files = [f for r in resp.json()["results"] for f in r["files"]]
    assert len(files) > 0

# Case 3: folder-deny
async def test_search_folder_deny(client, auth_header, indexed_files, folder_deny_grant):
    resp = await client.post("/api/peek/search", headers=auth_header,
                             json={"format": "step", "codes": ["denied_file"]})
    assert resp.status_code == 200
    files = [f for r in resp.json()["results"] for f in r["files"]]
    assert len(files) == 0

# Case 4: folder-default (default-allow=True)
async def test_search_folder_default_allow(client, auth_header, indexed_files_without_grants):
    resp = await client.post("/api/peek/search", headers=auth_header,
                             json={"format": "step", "codes": ["ungranted_file"]})
    assert resp.status_code == 200
    files = [f for r in resp.json()["results"] for f in r["files"]]
    assert len(files) > 0  # Default-allow
```

### 10.4 `tests/test_migration.py` — 2 Test Cases

```python
"""
Migration test cases for v0.4.

Test matrix:
  1. fresh-boot      — Fresh DB on v0.4 → all tables created, no errors
  2. upgrade-v0.3    — Existing v0.3 DB → ALTER TABLE ADD COLUMN succeeds
"""

# Case 1: fresh-boot
async def test_fresh_boot():
    from app.main import create_app
    app = create_app()
    with get_conn() as conn:
        # Verify all v0.4 tables exist
        tables = [r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        for t in ["api_keys", "folder_scopes", "folder_grants", "tags", "file_tags", "file_metadata", "recent_files", "tag_audit_log", "folder_schemas"]:
            assert t in tables
        # Verify v0.3 tables still exist
        for t in ["users", "files", "usage_logs", "folder_presets"]:
            assert t in tables

# Case 2: upgrade-v0.3
async def test_upgrade_from_v03():
    # Create a v0.3 schema (without new tables/columns)
    from app.db import init_db
    # ... drop new tables, remove new columns
    # Re-run init_db → should add new tables and columns without error
    init_db()
```

---

## 11. PyInstaller Spec Changes

**File**: `quick_peek.spec` (at project root).

**Changes**:

1. Add to `hiddenimports` list (line 16-26 area):

```python
hiddenimports=[
    # ... existing imports ...
    # v0.4 additions:
    "ldap3", "ldap3.core", "ldap3.protocol", "ldap3.strategy", "ldap3.utils",
    "ldap3.core.exceptions", "ldap3.protocol.rfc4511",
]
```

2. No other changes needed — `ldap3` is pure Python and requires no system DLLs or binary hooks.

3. If FTS5 causes issues (unlikely since it's built into Python's sqlite3), add:
```python
# FTS5 is part of Python's sqlite3 module, no extra import needed.
```

---

## 12. New Env Vars (Exhaustive)

All handled in `backend/app/config.py` using the existing `_get()` pattern (line 16-17).

### 12.1 LDAP Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `QUICKPEEK_LDAP_URL` | `""` | LDAP server URL (e.g., `ldap://dc01.example.com:389`). Empty = local auth only. |
| `QUICKPEEK_LDAP_BIND_DN` | `""` | Service account DN for LDAP searches (e.g., `CN=svc-quickpeek,CN=Users,DC=example,DC=com`). |
| `QUICKPEEK_LDAP_BIND_PASSWORD` | `""` | Service account password. |
| `QUICKPEEK_LDAP_SEARCH_BASE` | `""` | Search base DN for user lookup (e.g., `DC=example,DC=com`). |
| `QUICKPEEK_LDAP_SEARCH_FILTER` | `"(sAMAccountName={username})"` | LDAP search filter. `{username}` is replaced with the login username. |
| `QUICKPEEK_LDAP_GROUP_MAP` | `""` | Comma-separated group-to-permission mappings. Format: `group_dn=perm1;perm2,group_dn2=perm3`. |
| `QUICKPEEK_LDAP_CACHE_TTL_MINUTES` | `"60"` | How long LDAP user attributes are cached before re-sync on login. |

### 12.2 Folder Scope Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `QUICKPEEK_FOLDER_DEFAULT_ALLOW` | `"true"` | Default access when no folder scope matches. `true` for v0.4, will default `false` in v0.5. |

### 12.3 History Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `QUICKPEEK_HISTORY_RETENTION_DAYS` | `"90"` | Days to retain search history and recent files. 0 = disable retention cleanup. |

### 12.4 Config.py Implementation

```python
# backend/app/config.py — additions after line 52

# ── LDAP ──
QUICKPEEK_LDAP_URL = _get("QUICKPEEK_LDAP_URL", "").strip()
QUICKPEEK_LDAP_BIND_DN = _get("QUICKPEEK_LDAP_BIND_DN", "").strip()
QUICKPEEK_LDAP_BIND_PASSWORD = _get("QUICKPEEK_LDAP_BIND_PASSWORD", "").strip()
QUICKPEEK_LDAP_SEARCH_BASE = _get("QUICKPEEK_LDAP_SEARCH_BASE", "").strip()
QUICKPEEK_LDAP_SEARCH_FILTER = _get("QUICKPEEK_LDAP_SEARCH_FILTER", "(sAMAccountName={username})").strip()
QUICKPEEK_LDAP_GROUP_MAP = _get("QUICKPEEK_LDAP_GROUP_MAP", "").strip()
QUICKPEEK_LDAP_CACHE_TTL_MINUTES = int(_get("QUICKPEEK_LDAP_CACHE_TTL_MINUTES", "60"))

# ── Folder Permissions ──
QUICKPEEK_FOLDER_DEFAULT_ALLOW = _get("QUICKPEEK_FOLDER_DEFAULT_ALLOW", "true").lower() == "true"

# ── History ──
QUICKPEEK_HISTORY_RETENTION_DAYS = int(_get("QUICKPEEK_HISTORY_RETENTION_DAYS", "90"))
```

---

## 13. Uncovered Risks

### 13.1 P0: `raw_file` and `preview_file` Use Bare `current_user` — No Permission Check

**Risk**: `routers/peek.py:129` and `routers/peek.py:148` use bare `current_user` without any format permission, folder scope, or download permission check. Any authenticated user can download any file, including those in restricted folders or formats they shouldn't have access to. This is a **P0 security hole** that existed in v0.3 and must be fixed in v0.4.

**Mitigation**: Add `require_permission("download_files")` to `raw_file()` and `can_access_folder(user, path, "download")` check. Similar for `preview_file()` with `can_access_folder(user, path, "view")`. Documented in Section 7.2.

**Owner**: orion-dev. **Priority**: **P0 — must ship with v0.4**.

### 13.2 Path Collision: `peek.py` Prefix Is `/api`, Not `/api/peek`

**Risk**: `routers/peek.py:16` declares `router = APIRouter(prefix="/api", tags=["peek"])`. This means all endpoints in the peek router are at `/api/...` not `/api/peek/...`. For example, `preview_file()` is at `/api/files/{file_id}/preview`. The `search()` endpoint is at `/api/peek/search` (because it's defined as `/peek/search` inside the `/api` prefix). This is confusing and creates path collision risk with the new `/api/tags`, `/api/files/{id}/tags`, `/api/files/{id}/metadata`, and `/api/admin/*` endpoints.

**Mitigation**: The new endpoints are placed in separate routers with correct prefixes (`/api/me`, `/api/tags`, `/api/admin`, `/api/files`). No existing path collides. But the inconsistent prefix (`/api` vs `/api/admin` vs `/api/me`) is a code smell. Refactoring `peek.py` prefix to `/api/peek` would break existing deployments. **Deferred to v0.5**.

**Owner**: orion-dev (awareness). **Priority**: Low. **Risk**: Existing endpoints remain broken at `/api/peek/search` style; new endpoints are clean.

### 13.3 `reindex_files()` Swallows All Exceptions

**Risk**: `main.py:31-35` wraps `reindex_files()` in a bare `try/except: pass`. Any error during indexing — including errors from the new FTS5 rebuild, or SQL constraint violations from new schema interactions — will be silently swallowed. The app starts but the index may be empty or corrupted.

**Mitigation**: Improve the exception handler to log the error (to stderr, since there's no logging yet). In `main.py:33-34`, change to:

```python
try:
    reindex_files()
except Exception as exc:
    import sys; print(f"[WARN] reindex_files() failed: {exc}", file=sys.stderr)
```

Added to the "uncovered risks" section as an awareness item.

**Owner**: orion-dev. **Priority**: Medium.

### 13.4 `admin.py` Reads All Users Without Pagination

**Risk**: `routers/admin.py:23-30` (`list_users`) fetches all users with `SELECT * FROM users ORDER BY id`. With LDAP integration, the number of users can grow to hundreds (all LDAP-authenticated users are upserted into the `users` table). This endpoint will become slow and memory-heavy.

**Mitigation**: For v0.4, add `LIMIT 500` and a warning comment. Defer proper pagination to v0.5. The frontend AdminPage already expects a list; adding pagination would require a UI overhaul.

**Owner**: orion-dev. **Priority**: Medium.

### 13.5 LDAP Group Mapping Is Conjunctive, Not Hierarchical

**Risk**: The `QUICKPEEK_LDAP_GROUP_MAP` env var is a flat CSV. If an organization has nested AD groups, members of a child group won't inherit permissions from the parent group. LDAP `memberOf` is a direct attribute — it doesn't include transitive (nested) group memberships by default.

**Mitigation**: Document that `memberOf` only returns direct group memberships. For nested groups, the LDAP admin must either (a) configure AD to return transitive memberships via `LDAP_MATCHING_RULE_IN_CHAIN`, or (b) expand `group_map` to include all relevant groups. The `ldap-test` endpoint can show which groups a test user resolves to, reducing confusion.

**Owner**: atlas-docs (documentation). **Priority**: Low.

### 13.6 API Key Scopes Are Intersection, Not Subset

**Risk**: The `_build_api_key_user()` function (Section 6.2) intersects API key scopes with the issuing user's permissions. If the issuing user's permissions are later **reduced**, existing API keys may grant scopes that the issuing user no longer has. This is intentional (revoking a key is a separate operation), but administrators may expect key scopes to auto-shrink when the issuing user's permissions shrink.

**Mitigation**: Document this behavior explicitly in the admin UI and in the release notes. The key verification code reads the issuing user's current permissions at authentication time, not at key creation time, so intersection is dynamic. If the issuing user loses `view_step`, the API key loses it too — no need to recreate keys.

**Owner**: atlas-docs. **Priority**: Low.

---

## Appendix A: Load Order of Changes in `main.py`

The `create_app()` function at `main.py:28-60` must be modified to reflect the new initialization order:

```python
def create_app() -> FastAPI:
    init_db()                                          # line 29 — unchanged
    ensure_admin_user(ADMIN_USERNAME, ADMIN_PASSWORD, ADMIN_PERMISSIONS)  # line 30 — unchanged
    try:
        reindex_files()                                # line 32 — unchanged
        rebuild_fts5()                                 # NEW: rebuild FTS5 index after reindex
    except Exception as exc:
        import sys; print(f"[WARN] reindex_files() failed: {exc}", file=sys.stderr)  # IMPROVED

    app = FastAPI(title="Quick Peek API", version="0.4.0")  # VERSION BUMP
    app.add_middleware(CORSMiddleware, ...)             # lines 38-44 — unchanged

    # Router registration — NEW routers added
    app.include_router(auth.router)                    # line 45
    from .routers import me as me_router               # NEW
    app.include_router(me_router)                      # NEW
    app.include_router(admin.router)                   # line 46
    app.include_router(peek.router)                    # line 47
    from .routers import metadata as metadata_router   # NEW
    app.include_router(metadata_router)                # NEW
    app.include_router(dashboard.router)               # line 48
    app.include_router(folders.router)                 # line 49

    @app.get("/api/health")                            # line 51
    def health():
        return {"ok": True, "name": "Quick Peek", "version": "0.4.0"}

    static_path = _resource_path("app/static")         # line 56
    if static_path.exists():
        app.mount("/", StaticFiles(directory=str(static_path), html=True), name="frontend")

    return app
```

## Appendix B: `routers/__init__.py` Updates

The `backend/app/routers/__init__.py` (currently empty) should export new routers:

```python
from . import auth
from . import admin
from . import peek
from . import dashboard
from . import folders
from . import me          # NEW
from . import metadata    # NEW
```

---

*End of Architecture Document — Quick Peek v0.4 "Enterprise"*
