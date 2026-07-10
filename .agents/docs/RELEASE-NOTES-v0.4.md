# Release Notes — Quick Peek v0.4 "Enterprise"

> **Version**: 0.4.0  
> **Release date**: 2026-06-06  
> **Previous release**: v0.3 "Document Preview"  
> **Audience**: End users, IT administrators

---

## 1. Release Summary

Quick Peek v0.4 "Enterprise" is the next major release following v0.3 Document Preview, bringing LDAP/SSO authentication, per-folder permission scoping, search history and recent files, file tagging with custom metadata, and API key authentication for external tools. v0.4 transforms Quick Peek from a single-user preview tool into a multi-user enterprise platform that integrates with Windows Active Directory, enforces folder-level access control, and supports automation via CI pipelines and scripts. Every new feature is opt-in — existing v0.3 deployments upgrade without configuration changes.

---

## 2. What's New

### 2.1 LDAP/SSO Authentication

**Why this matters**: Users can now log in with their Windows domain credentials instead of maintaining a separate Quick Peek password. Groups are auto-mapped to permissions, and the break-glass local admin account always works.

**How it works (end users)**:
When LDAP is configured, the login page shows "Sign in with LDAP" as the primary option. Enter your corporate username and password — Quick Peek binds to your Active Directory, reads your group memberships, and assigns permissions based on the group map configured by your IT admin. If your groups grant admin permissions, you get full access. If they grant only `use_quick_peek` and `view_step`, you can search STEP files but nothing else.

If the LDAP server is unreachable (e.g., you're on a disconnected laptop), a warning banner appears and you can fall back to your local admin account. The local admin (`QUICKPEEK_ADMIN_USERNAME` / `QUICKPEEK_ADMIN_PASSWORD`) always works regardless of LDAP status — this is the break-glass account.

**How to configure it (IT admins)**:
Set `QUICKPEEK_LDAP_URL` to your domain controller (e.g., `ldap://dc01.example.com:389`). Provide a service account via `QUICKPEEK_LDAP_BIND_DN` and `QUICKPEEK_LDAP_BIND_PASSWORD` for user search. Set `QUICKPEEK_LDAP_SEARCH_BASE` (e.g., `DC=example,DC=com`) and `QUICKPEEK_LDAP_SEARCH_FILTER` (default `(sAMAccountName={username})`). Map groups to permissions via `QUICKPEEK_LDAP_GROUP_MAP` as a CSV of `group_dn=perm1;perm2` pairs. Users are auto-provisioned on first login. No LDAP config means local-only auth (v0.3 behavior).

**Screenshot reference**: See [DESIGN-v0.4.md §A — Modified Login Page](DESIGN-v0.4.md#a-modified-login-page).

---

### 2.2 Per-Folder Permission Scoping

**Why this matters**: Grant read/download access to specific folder paths. Contractors see only their project. Engineering sees everything. Finance sees nothing in CAD folders.

**How it works (end users)**:
Your IT admin defines folder scopes — glob patterns like `\\server\cad\engineering\**` or `/mnt/data/restricted/**` — and assigns you allow or deny rules on each scope. When you search, results are filtered to only files you're allowed to view. If you click a file you're not allowed to download, you get a clear "Folder scope denies download access" message. Admins see everything regardless of scopes.

The FolderPicker modal shows green/red access dots next to each folder so you know at a glance which directories are accessible.

**How to configure it (IT admins)**:
Navigate to Admin UI → Folder Scopes tab. Create scopes with path-prefix glob patterns (e.g., `\\server\cad\engineering\**`). Then go to Folder Grants to assign `allow` or `deny` for `view` / `download` / `index` permissions per user or API key. Use the Permission Simulator tab to test effective permissions for any user on any path.

Set `QUICKPEEK_FOLDER_DEFAULT_ALLOW=True` (default) to preserve existing v0.3 behavior where un-scoped paths are accessible. Set to `False` to restrict all paths by default — only explicitly allowed paths are visible. **v0.5 will flip the default to `False`**.

**Screenshot reference**: See [DESIGN-v0.4.md §E — AdminPage 7 New Tabs](DESIGN-v0.4.md#e-adminpage-7-new-tabs).

---

### 2.3 Search History & Recent Files

**Why this matters**: Pick up where you left off. The "Recent files" panel saves you retyping codes you searched yesterday.

**How it works (end users)**:
The main search page now has a collapsible "Recent files" panel between the folder selector and the code input. It shows your recently previewed files (up to 20), each with filename, format badge, and relative timestamp ("2h ago", "yesterday"). Click any recent file to auto-fill the format and code and trigger a search. Use the "Clear" link to wipe your history.

The code input textarea also has a "Recent searches" dropdown that appears when you focus the textarea while it's empty. Click a past search to re-run it. Your history is kept for 90 days by default and is visible only to you.

**How to configure it (IT admins)**:
Set `QUICKPEEK_HISTORY_RETENTION_DAYS` (default `90`) to control how long search history and recent files are retained. Set to `0` to disable retention cleanup (not recommended). The cleanup runs automatically on every server boot. Users can clear their own history via the "Clear" button in the recents panel.

**Screenshot reference**: See [DESIGN-v0.4.md §B — QuickPeekPage Recents Panel + Tag Filters](DESIGN-v0.4.md#b-quickpeekpage-recents-panel--tag-filters).

---

### 2.4 File Tagging & Custom Metadata

**Why this matters**: Organize files beyond folder structure. Add tags like `weldment` or `for-review` and filter search results by them. Attach structured metadata like project code and revision.

**How it works (end users)**:
Each file can have tags (many-to-many) — small colored pills displayed on the PreviewCard and in the ViewerModal header. Click a file's tags area to open the tag editor: type to search existing tags or create new ones, add/remove with a click. Tags are saved immediately.

Search results can be filtered by tag: a "Filter by tag" bar below the code input lets you add tag filters like `critical` or `wip`, and results are narrowed to files that have ALL selected tags.

Files also have a structured metadata section in the ViewerModal: project code, revision, supplier, cost center, plus a custom JSON field for any additional data. Admins can define folder schemas that require specific metadata fields for files in certain paths.

**How to configure it (IT admins)**:
No configuration needed — tagging works out of the box. Tags are shared (visible to all users) by default. Use the Admin UI → Folder Schemas tab to define required metadata fields per path prefix (e.g., require `project_code` and `revision` for files under `/data/cad/engineering/**`). The tag system uses a proper M2M schema with `tags` and `file_tags` tables — tags survive reindex as long as the file isn't deleted and recreated.

**Screenshot reference**: See [DESIGN-v0.4.md §D — File Tagging UI](DESIGN-v0.4.md#d-file-tagging-ui) and [§B.5 — Tag Filter Chips](DESIGN-v0.4.md#b5-tag-filter-chips).

---

### 2.5 API Key Auth for External Tools

**Why this matters**: Scripts, CI pipelines, and integrations can search and preview files without interactive login. Long-lived keys with scoped permissions, revocable at any time.

**How it works (end users)**:
Admins create API keys via Admin UI → API Keys tab. Each key has a name, an owner (the user whose permissions it inherits), an optional expiry date, and a set of scopes (permissions). On creation, the full key is shown once — copy it immediately. API keys start with the prefix `qpk_` (e.g., `qpk_a1b2c3d4e5f6...`) and are sent via the `X-API-Key` header:

```bash
curl -H "X-API-Key: qpk_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p" \
  "http://quickpeek:8000/api/peek/search" \
  -H "Content-Type: application/json" \
  -d '{"format":"step","codes":["1827009605"]}'
```

Keys are authenticated via SHA-256 hash (stored, not raw), and scopes are dynamically intersected with the issuing user's current permissions — if the user loses `view_step`, the API key loses it too. Revoke a key anytime; revocation is immediate.

**How to configure it (IT admins)**:
Navigate to Admin UI → API Keys tab. Click "Create API key", fill in the name, select the owner user, set scopes (checkboxes for each permission), and optionally set an expiry date. The full key is displayed exactly once — store it securely. Keys can be revoked via the table's "Revoke" button. Only users with `manage_users` permission can create/revoke keys.

**Screenshot reference**: See [DESIGN-v0.4.md §E.5 — API Keys Tab](DESIGN-v0.4.md#e5-tab-api-keys).

---

## 3. Breaking Changes

**No breaking changes in v0.4.** All new features are opt-in via environment variables. Existing v0.3 deployments upgrade without any configuration changes.

### Configuration Notes

| Setting | Default | What to know |
|---------|---------|-------------|
| `QUICKPEEK_FOLDER_DEFAULT_ALLOW` | `True` | Preserves existing behavior. Set to `False` to enforce folder scoping for non-admins. v0.5 will flip this default. |
| `QUICKPEEK_HISTORY_RETENTION_DAYS` | `90` | New cleanup runs on boot. Set to `0` to disable. |
| LDAP settings | All empty | No LDAP = local-only auth (unchanged from v0.3). |

### P0 Security Fixes

The following endpoints were unguarded in v0.3 and are now secured in v0.4:

- **`GET /api/files/{id}/raw`** — now requires `download_files` permission AND folder scope check
- **`GET /api/files/{id}/preview`** — now requires folder scope check (`view` permission)

These are fixes for existing vulnerabilities, not breaking changes — any deployment relying on unguarded access was unknowingly exposed.

---

## 4. Upgrade Guide (for IT Admins)

Upgrading from v0.3 to v0.4 is a drop-in replacement. Follow these steps:

### Step 1: Back up your database

```bash
cp data/quickpeek.sqlite3 data/quickpeek.sqlite3.v0.3.backup
```

The database is at `QUICKPEEK_DB_PATH` (default: `data/quickpeek.sqlite3` relative to the `backend/` working directory).

### Step 2: Download v0.4

Replace your existing `QuickPeek.exe` (or Python source) with the v0.4 build. On Windows, download the new `dist/QuickPeek/` folder.

### Step 3: Run the application

Start the new .exe (or `uvicorn app.main:app`). On first boot, `init_db()` runs automatically:

- New tables are created (`api_keys`, `folder_scopes`, `folder_grants`, `tags`, `file_tags`, `file_metadata`, `recent_files`, `tag_audit_log`, `folder_schemas`, `fts5_files`)
- New columns are added to `users` (`auth_source`, `ldap_dn`, `email`, `display_name`, `last_synced_at`)
- FTS5 full-text search index is rebuilt
- History cleanup runs (deletes records older than `QUICKPEEK_HISTORY_RETENTION_DAYS`)

All operations are idempotent — they use `CREATE TABLE IF NOT EXISTS` and try/except `ALTER TABLE ADD COLUMN`.

### Step 4: Verify local admin login

Log in with your existing `QUICKPEEK_ADMIN_USERNAME` / `QUICKPEEK_ADMIN_PASSWORD` credentials. The local auth path is unchanged.

### Step 5: (Optional) Configure LDAP

Create or edit your `.env` file (or set environment variables):

```bash
QUICKPEEK_LDAP_URL=ldap://dc01.example.com:389
QUICKPEEK_LDAP_BIND_DN=CN=svc-quickpeek,CN=Users,DC=example,DC=com
QUICKPEEK_LDAP_BIND_PASSWORD=your-service-password
QUICKPEEK_LDAP_SEARCH_BASE=DC=example,DC=com
QUICKPEEK_LDAP_SEARCH_FILTER=(sAMAccountName={username})
QUICKPEEK_LDAP_GROUP_MAP=CN=QuickPeek-Admins,OU=Groups,...=manage_users;view_dashboard,CN=QuickPeek-Users,OU=Groups,...=use_quick_peek;view_step;view_pdf
QUICKPEEK_LDAP_CACHE_TTL_MINUTES=60
```

Use the Admin UI → LDAP Test tab to verify connectivity before rolling out to users.

### Step 6: (Optional) Configure API keys

Navigate to Admin UI → API Keys tab. Create keys for CI pipelines, backup scripts, or integrations. Each key returns a full key exactly once — copy it immediately.

### Step 7: (Optional) Configure folder scopes

Navigate to Admin UI → Folder Scopes to define path-pattern boundaries, then Folder Grants to assign allow/deny rules to users. Use the Permission Simulator to verify effective permissions before enabling.

---

## 5. New Environment Variables

All new variables are optional. Defaults preserve v0.3 behavior.

### LDAP Authentication

| Variable | Default | Description |
|----------|---------|-------------|
| `QUICKPEEK_LDAP_URL` | `""` | LDAP server URL (e.g., `ldap://dc01.example.com:389`). Empty = local auth only. |
| `QUICKPEEK_LDAP_BIND_DN` | `""` | Service account DN for LDAP user search. |
| `QUICKPEEK_LDAP_BIND_PASSWORD` | `""` | Service account password. |
| `QUICKPEEK_LDAP_SEARCH_BASE` | `""` | Search base DN for user lookup. |
| `QUICKPEEK_LDAP_SEARCH_FILTER` | `"(sAMAccountName={username})"` | LDAP search filter. `{username}` is replaced with the login name at runtime. |
| `QUICKPEEK_LDAP_GROUP_MAP` | `""` | CSV of group-to-permission mappings. Format: `group_dn=perm1;perm2,group_dn2=perm3`. |
| `QUICKPEEK_LDAP_CACHE_TTL_MINUTES` | `"60"` | How long LDAP user attributes (groups, email, display name) are cached before re-sync on next login. |

### Folder Permissions

| Variable | Default | Description |
|----------|---------|-------------|
| `QUICKPEEK_FOLDER_DEFAULT_ALLOW` | `"true"` | Default access when no folder scope matches a path. `true` for v0.4; will default `false` in v0.5. |

### Search History

| Variable | Default | Description |
|----------|---------|-------------|
| `QUICKPEEK_HISTORY_RETENTION_DAYS` | `"90"` | Days to retain search history and recent files. `0` = disable retention cleanup. |

---

## 6. New Dependencies

### Python (backend)

| Package | Version | Purpose |
|---------|---------|---------|
| `ldap3` | `2.9.1` | Pure-Python LDAP client for Active Directory integration. No system DLLs required — critical for PyInstaller frozen exe. |
| `python-jose[cryptography]` | upgraded to `3.5.0` | JWT handling. Upgrade includes CVE fixes. |

The `ldap3` library is pure Python — it installs via `pip` on any platform with no system-level dependencies. It is fully compatible with PyInstaller (added to `hiddenimports` in `quick_peek.spec`).

### Python (test, optional)

| Package | Version | Purpose |
|---------|---------|---------|
| `pytest` | `>=8.0` | Test framework. |
| `pytest-asyncio` | `>=0.24.0` | Async test support. |
| `httpx` | `>=0.27.0` | HTTP test client. |
| `pytest-httpx` | `>=0.30.0` | HTTP request mocking. |

### Frontend

No new npm dependencies. All UI additions use existing libraries (lucide-react for icons) and vanilla CSS.

---

## 7. Contributors / Team

This release was a coordinated effort across all project agents:

| Agent | Role | Contributions |
|-------|------|---------------|
| **Astra** | Design / UX | User flows, interaction design, error state specifications |
| **Atlas** | Documentation / Knowledge | Release notes, architecture docs, decision log, env var reference |
| **Lyra** | Design / Frontend | Visual design system, CSS tokens, AdminPage wireframes, tag editor UI |
| **Orion** | Backend / Implementation | All backend code: LDAP flow, RBAC module, API keys, tagging, search history, schema migrations |
| **Rigel** | Review / Quality | Test plan, test cases, code review, P0 security audit of raw/preview endpoints |
| **Sirius** | DevEx / Build | PyInstaller spec updates, build pipeline, FTS5 integration, Python 3.9 compatibility |
| **Solis** | Security / Auth | Authentication architecture, JWT/API key dispatch, permission composition model |

**Orchestrated by**: **Zenith** — release planning, task tracking, risk management, milestone delivery.

---

## 8. Known Issues

### LDAP / Authentication

- **LDAP is bind-only**. SAML and OIDC are not supported — these protocols require browser redirect flows that don't fit Quick Peek's air-gapped desktop use case. SAML/OIDC integration is a future release consideration.
- **Nested AD groups are not resolved transitively** by default. `memberOf` returns only direct group memberships. If your organization uses nested groups, configure AD to return transitive memberships via `LDAP_MATCHING_RULE_IN_CHAIN`, or add all relevant groups to `QUICKPEEK_LDAP_GROUP_MAP`.
- **Rate limiter state is in-memory** and resets on server restart. Rate limiting uses an in-memory counter that clears when the process restarts.

### Search / Indexing

- **FTS5 full-text search** requires Python's SQLite to be compiled with FTS5 support. Python 3.10+ includes this by default. If your Python build lacks FTS5, the virtual table creation will fail silently and full-text search will not be available (standard `LIKE` search still works).
- **Tags do not survive a file delete+reappear cycle**. If a file is deleted from disk and reindexed, then reappears at the same path, it receives a new `files.id` and any previously applied tags are lost. This is an acceptable trade-off for v0.4; a future release may preserve tags across reindex by keying on `full_path`.

### Metadata / Schemas

- **File tagging does not include a curated tag vocabulary** — users can create any tag name freely. A controlled vocabulary with tag suggestions and synonyms is planned for v0.5.
- **Folder schemas** define required metadata fields per path prefix but do not enforce them — missing required fields are not blocked. Enforcement is deferred to v0.5.

### Admin / UI

- **User listing in Admin UI has no pagination** — deployments with hundreds of LDAP users may see slow page loads on the Users tab. A `LIMIT 500` guard is in place. Proper pagination is deferred to v0.5.
- **FolderPickerModal access dots** require backend support per-item — if the backend doesn't yet return `accessible` on each folder item, the dots are hidden. Support was added to `GET /api/folders/browse` but may need verification.

### API Keys

- **API key scopes are dynamic intersection with the issuing user's current permissions** — if the issuing user loses a permission, all their API keys lose it too. This is intentional (no need to recreate keys when permissions change), but may surprise admins who expect key scopes to be snapshotted at creation time.

---

*For detailed architecture and implementation guidance, see [ARCHITECTURE-v0.4.md](ARCHITECTURE-v0.4.md). For design specifications and wireframes, see [DESIGN-v0.4.md](DESIGN-v0.4.md).*
