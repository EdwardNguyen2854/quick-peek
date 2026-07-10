# Design — Quick Peek v0.4 "Enterprise" Release

> **Status**: Final  
> **Audience**: Implementation team (orion-dev + rigel-review)  
> **Version**: 0.4.0  
> **Date**: 2026-06-06

---

## Table of Contents

1. [Screen A: Modified Login Page (LDAP/SSO)](#a-modified-login-page)
2. [Screen B: QuickPeekPage — Recents Panel + Tag Filter](#b-quickpeekpage-recents-panel--tag-filters)
3. [Screen C: Folder Access Empty State](#c-folder-access-empty-state)
4. [Screen D: File Tagging UI (PreviewCard + ViewerModal)](#d-file-tagging-ui)
5. [Screen E: AdminPage — 7 New Tabs](#e-adminpage-7-new-tabs)
6. [Screen F: Dashboard Page Updates](#f-dashboard-page-updates)
7. [Screen G: FolderPickerModal Permission Awareness](#g-folderpickermodal-permission-awareness)
8. [Interaction Design](#8-interaction-design)
9. [Visual Design Tokens](#9-visual-design-tokens)
10. [Responsive / Mobile Considerations](#10-responsive--mobile-considerations)
11. [Accessibility Notes](#11-accessibility-notes)
12. [Design Principles for This Release](#12-design-principles-for-this-release)
13. [Appendix: CSS Additions to global.css](#13-appendix-css-additions)

---

## A. Modified Login Page

### A.1 Current State (v0.3)

The existing login page is a centered card with brand, two inputs (username/password pre-filled with `admin`/`admin123`), a sign-in button, and a error box. No distinction between auth sources.

### A.2 v0.4 Design

**Layout** — If `QUICKPEEK_LDAP_URL` is set on the backend, the login card shows "Log in with LDAP" as the primary path. A small "Use local account" link below reveals the local login form. If LDAP is not configured, the UI stays identical to v0.3 (local-only).

**Login card — LDAP mode** (backend has `QUICKPEEK_LDAP_URL` set):

```
┌─────────────────────────────────────────────────┐
│  ┌───────┐                                       │
│  │  QP   │  Quick Peek                           │
│  │       │  STEP · PDF · DXF                     │
│  └───────┘                                       │
│                                                   │
│  Sign in                                         │
│  Fast preview for many CAD files at once.         │
│                                                   │
│  ┌─────────────────────────────────────────────┐ │
│  │ Log in with LDAP                            │ │
│  │ (Corporate credentials)                     │ │
│  └─────────────────────────────────────────────┘ │
│                                                   │
│  ┌─────────────────────────────────────────────┐ │
│  │ Username                                    │ │
│  │ ┌─────────────────────────────────────────┐ │ │
│  │ │                                         │ │ │
│  │ └─────────────────────────────────────────┘ │ │
│  │ Password                                    │ │
│  │ ┌─────────────────────────────────────────┐ │ │
│  │ │                                         │ │ │
│  │ └─────────────────────────────────────────┘ │ │
│  │                                             │ │
│  │ ┌─────────────────────────────────────────┐ │ │
│  │ │          Sign in with LDAP              │ │ │
│  │ └─────────────────────────────────────────┘ │ │
│  └─────────────────────────────────────────────┘ │
│                                                   │
│  ─── or ───                                       │
│  <a>Use a local account instead</a>               │
│                                                   │
│  ⚠ LDAP server unreachable — using local login    │
│  (shown only on LDAP connection failure)           │
└─────────────────────────────────────────────────┘
```

**Login card — Local mode** (when user clicked "Use a local account instead"):

```
┌─────────────────────────────────────────────────┐
│  ...same brand...                                │
│                                                   │
│  Sign in (local)                                 │
│                                                   │
│  ┌─────────────────────────────────────────────┐ │
│  │ Username                                    │ │
│  │ ┌─────────────────────────────────────────┐ │ │
│  │ │ admin                                   │ │ │
│  │ └─────────────────────────────────────────┘ │ │
│  │ Password                                    │ │
│  │ ┌─────────────────────────────────────────┐ │ │
│  │ │ ••••••••                               │ │ │
│  │ └─────────────────────────────────────────┘ │ │
│  │                                             │ │
│  │ ┌─────────────────────────────────────────┐ │ │
│  │ │              Sign in                    │ │ │
│  │ └─────────────────────────────────────────┘ │ │
│  └─────────────────────────────────────────────┘ │
│                                                   │
│  ← Back to LDAP login                            │
└─────────────────────────────────────────────────┘
```

### A.3 Error States

Three distinct error states, each rendered differently:

| Scenario | HTTP Code | Error `detail` | UI Treatment |
|----------|-----------|----------------|--------------|
| LDAP bind fails (bad creds) | 401 | `"LDAP: Incorrect username or password"` | Red `error-box` below inputs: "Incorrect username or password" + a subtle "LDAP authentication failed" hint |
| LDAP server unreachable | 503 | `"LDAP server is not reachable. Contact your administrator."` | Yellow warning banner at top of card: "⚠ LDAP server is not reachable. You can still log in with a local account." (Then auto-show the local login form) |
| Too many attempts | 429 | `"Too many attempts — try again in 60 seconds"` | Red `error-box` with lock icon + countdown timer (optional — backend sends `Retry-After` header, frontend shows seconds remaining) |
| Local login failure | 401 | `"Incorrect username or password"` | Red `error-box`: "Incorrect username or password" (generic, no LDAP prefix) |

### A.4 User Flow

1. User visits login page.
2. If LDAP is configured:
   a. User sees "Log in with LDAP" section as default.
   b. User types corporate credentials and clicks "Sign in with LDAP".
   c. On success → JWT stored, redirect to main app.
   d. On 401 LDAP bind fail → show "Incorrect username or password" in error box. Keep LDAP form visible.
   e. On 503 LDAP unreachable → show warning banner at top + auto-reveal local login form. User can type local admin creds.
   f. On 429 → show error with retry countdown.
3. If LDAP is not configured:
   a. User sees the existing local login form (identical to v0.3).
   b. Type credentials, submit → JWT stored, redirect.

### A.5 Component Tree — LoginPage.tsx

```
LoginPage (props: { onLogin: (user: User) => void })
├── useState: ldapAvailable (boolean, from GET /api/auth/ldap-config or backend env hint)
├── useState: showLocal (boolean — toggles between LDAP and local forms)
├── useState: username, password
├── useState: error (string), ldapError (boolean), ldapUnreachable (boolean)
├── useState: busy (boolean)
│
├── div.login-page
│   ├── div.supergraphic
│   └── form.login-card
│       ├── Brand header (QP logo + name)
│       ├── h1: "Sign in" (or "Sign in (local)" when showLocal)
│       ├── p.muted: tagline
│       │
│       ├── [if ldapUnreachable] → div.warning-box
│       │   "⚠ LDAP server is not reachable. You can still log in with a local account."
│       │
│       ├── [if !showLocal && ldapAvailable] → LDAP form:
│       │   ├── label: Username → input
│       │   ├── label: Password → input[type=password]
│       │   ├── [if error && ldapError] → div.error-box
│       │   │   error message + small hint "LDAP authentication failed"
│       │   ├── button.primary: "Sign in with LDAP"
│       │   └── p.hint with <a onClick={() => setShowLocal(true)}>
│       │       "Use a local account instead"
│       │
│       ├── [if showLocal || !ldapAvailable] → Local form:
│       │   ├── label: Username → input (pre-filled "admin")
│       │   ├── label: Password → input[type=password] (pre-filled "admin123")
│       │   ├── [if error && !ldapError] → div.error-box
│       │   │   error message
│       │   ├── button.primary: "Sign in"
│       │   └── [if ldapAvailable] → p.hint with <a onClick={() => setShowLocal(false)}>
│       │       "← Back to LDAP login"
│       │
│       └── [if !ldapAvailable] → p.hint
│           "Default admin is admin / admin123. Change this after first run."
```

### A.6 API Integration Points

- `POST /api/auth/login` — existing endpoint, body unchanged `{ username, password }`
- Error differentiation via `err.message` prefix `"LDAP:"` or `"Incorrect username or password"`
- No separate `GET /api/auth/ldap-config` call needed on login page — the backend returns 503 or 401 with distinct messages; the frontend infers LDAP availability from error types
- However, for UX: call `GET /api/admin/ldap-config` (if user has token) or add a lightweight `GET /api/auth/methods` endpoint that returns `{ "methods": ["ldap", "local"] }`. **Decision**: Use a simple heuristics approach — if the backend returns a 503 with "LDAP server is not reachable", set `ldapUnreachable = true` and `showLocal = true`. No separate endpoint needed for v0.4.

---

## B. QuickPeekPage — Recents Panel + Tag Filters

### B.1 Current State (v0.3)

The page has: format selector chips → folder panel (working folder + presets) → input grid (code textarea + search help) → results grid. No recents, no tag filtering.

### B.2 v0.4 Layout — Recents Panel

A new **collapsible "Recent files" panel** sits between the folder presets section and the code input grid. It is visually separated from the working folder panel above it by a subtle divider.

```
┌─────────────────────────────────────────────────────┐
│ [STEP] [PDF] [DXF] [OBJ] ... format chips            │
│                                                       │
│ ┌─ Working folder ─────────────────────────────────┐ │
│ │  ... (unchanged)                                  │ │
│ └──────────────────────────────────────────────────┘ │
│                                                       │
│ ┌─ Recent files ─── [▼ collapse] ─────────────────┐  │
│ │  [icon] part-456.stp          .STP  2h ago      │  │
│ │  [icon] assembly-v3.pdf       .PDF  yesterday    │  │
│ │  [icon] bracket-final.dxf     .DXF  Jun 3        │  │
│ │  [icon] housing-v2.obj        .OBJ  Jun 1        │  │
│ │  [icon] spec-sheet.xlsx       .XLS  May 28       │  │
│ │                                                   │ │
│ │  < Clear history >              (bottom right)    │ │
│ └──────────────────────────────────────────────────┘ │
│                                                       │
│ ┌─ Code input ───────────────┬─ Search help ───────┐ │
│ │  (textarea)                 │  (stats + button)    │ │
│ │                             │                      │ │
│ │  ┌── Filter by tag ──────┐ │                      │ │
│ │  │ [critical ×] [wip ×] │ │                      │ │
│ │  │ + Add tag...          │ │                      │ │
│ │  └───────────────────────┘ │                      │ │
│ └─────────────────────────────┴──────────────────────┘ │
│                                                       │
│ ┌─ Results grid ─────────────────────────────────────┐│
│ │  [PreviewCard] [PreviewCard] [PreviewCard]          ││
│ └────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────┘
```

### B.3 Recents Panel — Detailed Spec

**Position**: Between folder panel (`.folder-panel`) and the `.input-grid`. Wrapped in a `<section className="panel recents-panel">`.

**Header row**: Left side shows "Recent files" in bold, right side has a collapse toggle (▼/▲) and a "Clear" link button.

**List items** — each is a clickable row:
```
<button className="recents-item" onClick={() => applyRecent(file)}>
  <FileIcon size={16} />          // icon based on extension
  <span className="recents-name">{file.filename}</span>
  <span className="recents-badge">{file.extension.replace('.','').toUpperCase()}</span>
  <span className="recents-time">{relativeTime(file.last_opened_at)}</span>
</button>
```

- **FileIcon**: Use lucide-react `FileText` for docs, `FileImage` for images, `File` for generic.
- **Format badge**: Small `.badge` style pill with format extension (`.STP`, `.PDF`, etc.).
- **Timestamp**: Relative time using a helper function:
  - < 1 min: "just now"
  - < 1 hour: "Xm ago"
  - < 24 hours: "Xh ago"
  - < 7 days: "X days ago"
  - < 30 days: "X weeks ago"
  - Otherwise: short date "Jun 3"

**Click behavior**: Calls `applyRecent(recentFile)`:
1. Sets `format` to the format that matches `recentFile.extension`.
2. Sets `codesText` to the filename's code (extracted from filename by removing extension and common prefixes).
3. Automatically triggers `runSearch()`.

**Empty state** (no recents):
```
┌─ Recent files ──────────────────────────────────────┐
│  <FolderOpen icon> No recent files. Start searching! │
└──────────────────────────────────────────────────────┘
```

**Clear history**: Button/link at bottom right of the panel body. Calls `DELETE /api/me/history`, refreshes list.

**Loading state**: Show 3 skeleton placeholder rows (grey shimmer animation).

### B.4 Recent Searches Dropdown

A typeahead dropdown attached to the **code textarea** — when the textarea is focused and empty, show a dropdown of recent search queries below it.

```
┌─ Code list ────────────────────────────────────────────┐
│ ┌─────────────────────────────────────────────────────┐│
│ │ 1827009605                                          ││
│ │ 573419                                               ││
│ │                                                      ││
│ │ ┌─ Recent searches ────────────────────────────────┐││
│ │ │ 🔍 1827009605, 573419, SAMPLE    STEP · 5 files │││
│ │ │ 🔍 938472, 18273                STEP · 2 files  │││
│ │ │ 🔍 PN-44921                     PDF · 1 file    │││
│ │ └─────────────────────────────────────────────────┘││
│ └─────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────┘
```

- Max 10 recent searches shown.
- Each entry shows: search icon + codes preview (truncated at 50 chars) + format + file count.
- Click fills the textarea and triggers search.
- Dropdown dismisses on textarea input, Escape, or click outside.

### B.5 Tag Filter Chips

When search results are displayed, a **"Filter by tag"** section appears between the code textarea and the search help panel (or inline with the results controls).

```
┌─ Filter by tag ───────────────────────────────────────┐
│  [critical ×] [wip ×] [urgent ×]                      │
│  ┌─ search/filter tags ─────────────────────────┐     │
│  │ + Add tag filter...                          │     │
│  └──────────────────────────────────────────────┘     │
└───────────────────────────────────────────────────────┘
```

**Behavior**:
- Tag filter chips appear when user has selected tags to filter by.
- Clicking a chip's `×` removes that tag filter and re-runs search.
- The "+ Add tag filter" input shows autocomplete suggestions from `GET /api/tags?q=...` when user types 3+ characters.
- When tags are actively filtering, the search results grid gets a subtle overlay note: "Filtering by 2 tag(s)".
- Tag filter state is stored as `selectedTagFilters: string[]` in QuickPeekPage.
- On tag filter change, re-run the existing search with the new `tag_filter` parameter in the search API call.

### B.6 States Summary for Recents Panel

| State | Visual |
|-------|--------|
| **Loading** | 3 skeleton placeholder rows (`.recents-skeleton`) |
| **Empty** | "No recent files. Start searching!" with FolderOpen icon |
| **Populated** | Up to 20 recent file rows, each with icon + name + format badge + time |
| **Error** | Error box "Couldn't load recent files" + retry link |
| **Collapsed** | Only the header row visible; panel body hidden |

### B.7 Component Tree — QuickPeekPage Changes

```
QuickPeekPage (props: { user: User })
├── [existing] format row
├── [existing] folder panel
│
├── [NEW] section.panel.recents-panel
│   ├── div.recents-header
│   │   ├── strong "Recent files"
│   │   ├── button.secondary.small "Clear" (calls clearHistory)
│   │   └── button.collapse-toggle
│   ├── [if collapsed] nothing
│   ├── [if loading] 3 × div.recents-skeleton
│   ├── [if empty] div.recents-empty
│   ├── [if populated] div.recents-list
│   │   └── button.recents-item × N
│   └── [if error] div.error-box
│
├── [MODIFIED] input-grid
│   ├── [MODIFIED] code-input-label
│   │   ├── textarea (existing)
│   │   └── [NEW] div.recent-searches-dropdown (positioned absolute below textarea)
│   │       └── button.recent-search-item × N
│   └── search-help (existing, unchanged)
│
├── [NEW] div.tag-filter-bar (shown when results.length > 0)
│   ├── span "Filter by tag:"
│   ├── [for each selectedTag] div.tag-filter-chip
│   │   ├── span: tag name
│   │   └── button × (removes tag)
│   └── div.tag-filter-input
│       └── input (with autocomplete dropdown)
│
├── [existing] results-grid
│   └── [MODIFIED] PreviewCard (now receives tags data)
│
└── [existing] ViewerModal (now receives tags data)
```

---

## C. Folder Access Empty State

### C.1 When It Appears

The folder-access empty state appears in two scenarios:

1. **Search returns 0 results AFTER folder permission filtering** — the format buttons are enabled, but after running a search, every file in the results was filtered out by `can_access_folder()`.
2. **User opens a root folder in FolderPickerModal that they have no access to**.

### C.2 Full-Page Empty State (Search Page)

When a search completes and all results were filtered by folder permissions:

```
┌──────────────────────────────────────────────────────┐
│                                                        │
│                       🔒                               │
│                                                        │
│      You don't have access to any files                │
│      in this folder scope.                             │
│                                                        │
│  The files exist on the server but your account        │
│  doesn't have permission to view them.                 │
│                                                        │
│  Contact your administrator to request access.         │
│                                                        │
│  ┌────────────────────────────────────────┐            │
│  │        ← Change folder / reset         │            │
│  └────────────────────────────────────────┘            │
│                                                        │
└──────────────────────────────────────────────────────┘
```

**Layout**: Centered content replacing the results grid entirely. The format buttons and code input remain visible and interactive (the user can change folder and re-search).

**Lock icon**: A large `<Lock>` from lucide-react, 48×48, color `var(--muted)`.

**Detection**: The frontend detects this by checking: `results.length === 0 && noError && searchAttempted`. No separate API needed — the search endpoint already returns empty results when folder scope denies everything.

### C.3 FolderPickerModal — Permission Indicators

Individual folder items in the FolderPickerModal show a colored dot indicating access:

```
<button className="folder-item" onClick={...} title={...}>
  <Folder size={17} />
  <span>{item.name}</span>
  <em>{item.path}</em>
  <span className="access-dot access-allowed" title="You have access" />   ← green dot
</button>

<button className="folder-item folder-denied" onClick={...} title={...}>
  <Folder size={17} />
  <span>{item.name}</span>
  <em>{item.path}</em>
  <span className="access-dot access-denied" title="No access" />          ← red dot
</button>
```

**Access dot colors**:
- Green (`#22c55e`): User has view access
- Red (`#ef4444`): User does NOT have view access (denied or no allow rule)
- Amber (`#f59e0b`): Unknown / no grant exists (if default-allow is on, this is green; if off, this is red)

**Implementation**: The backend `GET /api/folders/browse` endpoint is modified to return `accessible: boolean` on each `FolderItem`. The frontend renders the dot based on `item.accessible`.

If the backend doesn't yet support this per-item flag (deferred), the frontend can skip the dots for v0.4 and only show the empty state on search.

---

## D. File Tagging UI

### D.1 PreviewCard — Tag Display

Each PreviewCard shows up to 3 tags as small colored pills below the filename in the footer area. Tags are rendered inline, not as a separate section.

```
┌─ PreviewCard ──────────────────────────────────────┐
│ header: code + status icon                          │
│                                                     │
│ preview frame (image/placeholder)                   │
│                                                     │
│ footer:                                             │
│   filename: part-456.stp                            │
│   1.2 MB · SVG                                     │
│                                                     │
│   [critical] [wip] [+2 more]  ← NEW tag pills      │
└─────────────────────────────────────────────────────┘
```

**Specs**:
- Tag pills are small (`.tag-pill`), font-size 11px, padding 2px 8px, border-radius 8px.
- Each pill's background color is `tag.color` with 15% opacity of that color. Text color is `tag.color` at full opacity (darkened if pastel).
- Max 3 pills shown. If more than 3 tags, show "+N more" as a muted pill.
- The tag pills are appended to the `file-meta` div, after the size line.

**Tag pill CSS** (to be added to global.css):
```css
.tag-pill {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 8px;
  font-size: 11px;
  font-weight: 500;
  line-height: 1.4;
  margin-right: 4px;
  margin-top: 4px;
}
.tag-pill-more {
  background: var(--soft);
  color: var(--muted);
  border: 1px solid var(--line);
}
```

### D.2 ViewerModal — Tag Editor + Metadata Section

The ViewerModal gets a new collapsible bottom section with two parts: **Tags** and **Details (metadata)**.

**Layout** — The modal changes from a single viewport to a flex layout:

```
┌─ ViewerModal ─────────────────────────────────────────┐
│ header (existing): code · FORMAT                      │
│   filename                              [Download] [X]│
│   [critical] [wip] [urgent]  ← tag pills (clickable) │
│                                                        │
│ ┌─ viewer body ─────────────────────────────────────┐ │
│ │  (existing — renders format-specific viewer)       │ │
│ └───────────────────────────────────────────────────┘ │
│                                                        │
│ ┌── Tags & Details ── [▲ collapse] ─────────────────┐ │
│ │                                                     │ │
│ │  ┌─ Tags ────────────────────────────────────────┐ │ │
│ │  │  [critical ×] [wip ×] [urgent ×]              │ │ │
│ │  │  ┌─ Add tag ───────────────────────────────┐  │ │ │
│ │  │  │ [tag name]  ▼                           │  │ │ │
│ │  │  │  critical     (shared)                  │  │ │ │
│ │  │  │  wip          (shared)                  │  │ │ │
│ │  │  │  urgent       (shared)                  │  │ │ │
│ │  │  └─────────────────────────────────────────┘  │ │ │
│ │  │  < Create tag "custom" >                      │ │ │
│ │  └───────────────────────────────────────────────┘ │ │
│ │                                                     │ │
│ │  ┌─ Details ─────────────────────────────────────┐ │ │
│ │  │  Project code:  AVT-2026-001                  │ │ │
│ │  │  Revision:       C                            │ │ │
│ │  │  Supplier:       Bosch Rexroth                │ │ │
│ │  │  Cost center:    CC-4200                      │ │ │
│ │  │  Custom JSON:    { "material": "AL6061" }     │ │ │
│ │  │  (Edit)                                       │ │ │
│ │  └───────────────────────────────────────────────┘ │ │
│ └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

**Tag editor interaction**:
1. Current tags appear as colored chips with `×` to remove.
2. The text input has autocomplete: after 3+ characters, call `GET /api/tags?q=...` and show a dropdown of matching tags.
3. Pressing Enter or comma adds the typed text as a tag (creates it if it doesn't exist).
4. The autocomplete dropdown shows max 10 results. Each shows name + scope badge.
5. If the typed text doesn't match any existing tag, show "Create tag 'text'" at the bottom of the dropdown.
6. "Save" is implicit — calling `PUT /api/files/{id}/tags` with the current tag list on every add/remove action. No separate save button needed. Use a debounce (500ms) to batch rapid changes.

**Metadata section**:
- Read-only by default. Shows structured fields (project_code, revision, supplier, cost_center) and custom_json.
- An "Edit" button toggles inline editing for structured fields (inputs) and a textarea for custom_json.
- Save button calls `PUT /api/files/{id}/metadata`.
- If no metadata exists (`response.metadata === null`), show "No metadata set" and an "Add metadata" button.

**Collapse behavior**: The Tags & Details section is collapsible. Default: expanded. The collapse state is stored in a ref (no persistence needed).

### D.3 Component Tree — ViewerModal Changes

```
ViewerModal (props: { code, format, file, onClose })
├── [existing] header
│   ├── [MODIFIED] p.eyebrow — unchanged
│   ├── [MODIFIED] h2 — unchanged
│   └── [NEW] div.tag-pills-inline
│       └── span.tag-pill × N (max 3 shown, clickable)
│           onClick → scroll to tag editor section
│
├── [existing] viewer-body
│   └── ... (unchanged)
│
├── [NEW] div.viewer-bottom-section
│   ├── div.viewer-section-header
│   │   ├── span "Tags & Details"
│   │   └── button collapse toggle
│   └── div.viewer-section-body (collapsible)
│       ├── div.tags-section
│       │   ├── div.current-tags
│       │   │   └── span.tag-pill × N (all tags, each with × button)
│       │   ├── div.tag-input-wrapper (relative positioned for dropdown)
│       │   │   ├── input (placeholder "Add tag...", onInput → debounced search)
│       │   │   └── div.tag-autocomplete-dropdown (absolute positioned)
│       │   │       ├── button.tag-autocomplete-item × N (existing tags)
│       │   │       └── button.tag-autocomplete-item.create (if no match)
│       │   └── [if busy] small spinner
│       │
│       ├── div.section-divider
│       │
│       └── div.metadata-section
│           ├── [if !metadata || !editing] display mode
│           │   ├── p "Project code: AVT-2026-001" (or "—" if null)
│           │   ├── p "Revision: C"
│           │   ├── p "Supplier: Bosch Rexroth"
│           │   ├── p "Cost center: CC-4200"
│           │   └── p "Custom: { ... }"
│           ├── [if editing] edit mode
│           │   ├── input for each field
│           │   ├── textarea for custom_json
│           │   └── button.primary "Save metadata"
│           ├── [if !editing && metadata] button.secondary "Edit"
│           └── [if !metadata] p "No metadata set" + button "Add metadata"
```

---

## E. AdminPage — 7 New Tabs

### E.1 Overview Layout

The Admin page is redesigned with a horizontal tab bar at the top. The existing "User management" + "Reindex" functionality becomes the first tab ("Users"). Six new tabs are added.

```
┌─ Admin ──────────────────────────────────────────────┐
│                                                       │
│  [Users] [Folder Scopes] [Folder Grants] [API Keys]   │
│  [LDAP Test] [Folder Schemas] [Simulate]              │
│  ─────────────────────────────────────────────────    │
│                                                       │
│  ┌─ Active Tab Content ────────────────────────────┐ │
│  │                                                   │ │
│  │  (varies by tab — see below)                     │ │
│  │                                                   │ │
│  └───────────────────────────────────────────────────┘ │
│                                                       │
└─────────────────────────────────────────────────────────┘
```

**Tab bar styling**:
- Horizontal flex container, no wrapping (overflow-x: auto on small screens).
- Each tab is a `<button>` with `.admin-tab` class.
- Active tab has `.admin-tab-active` class — blue underline (`border-bottom: 3px solid #2563eb`), bold text.
- Inactive tabs: `color: var(--muted)`, hover → `color: var(--text)`.
- Tab bar has a bottom border (`border-bottom: 1px solid var(--line)`).

**Type**:
```typescript
type AdminTab = 'users' | 'folder-scopes' | 'folder-grants' | 'api-keys' | 'ldap' | 'schemas' | 'simulate';
const [adminTab, setAdminTab] = useState<AdminTab>('users');
```

**State management**: Each tab's content is its own component (or section rendered conditionally). Data fetching happens per-tab on tab switch.

---

### E.2 Tab: Users (Existing, Modified)

**Changes from v0.3**:
- Keep the existing user table + create user form.
- Add a new column: "Auth source" showing `local` or `ldap` + LDAP DN tooltip.
- Keep reindex button in the toolbar.
- No other changes — this tab stays mostly as-is.

**Auth source column**:
```html
<td>
  <span class="auth-source-badge">
    {user.auth_source || 'local'}
  </span>
  {user.ldap_dn && <span class="muted-block" title={user.ldap_dn}>LDAP</span>}
</td>
```

Auth source badge colors:
- `local` → gray (`.badge-planned` style)
- `ldap` → blue (`.badge-progress` style)

---

### E.3 Tab: Folder Scopes

**Purpose**: Define path-prefix glob patterns that describe folder boundaries for permission scoping.

**Layout**:
```
┌─ Folder Scopes ──────────────────────────────────────┐
│                                                        │
│  ┌─ Add scope ───────────────────────────────────────┐│
│  │  Pattern: ┌───────────────────────────────────┐   ││
│  │           │ /data/cad/**                       │   ││
│  │           └───────────────────────────────────┘   ││
│  │  Description: ┌──────────────────────────────┐   ││
│  │               │ Engineering CAD files        │   ││
│  │               └──────────────────────────────┘   ││
│  │  [Add scope]                                     ││
│  │  ℹ Pattern supports ** and * globs. Paths are     ││
│  │    normalized to forward slashes automatically.   ││
│  └──────────────────────────────────────────────────┘│
│                                                        │
│  ┌─ Scopes table ────────────────────────────────────┐│
│  │  Pattern                    │ Desc           │    ││
│  │  ───────────────────────────────────────────────── ││
│  │  /data/cad/**               │ Engineering    │ [×]││
│  │  /data/cad/restricted/**    │ Restricted     │ [×]││
│  │  \\server\shared\public/**  │ Public share    │ [×]││
│  └──────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
```

**Add form**: Inline, above the table. Pattern input with helper text below. Submit button.

**Table columns**: Pattern, Description, Created, Actions (delete button).

**Actions**: Delete button (trash icon). Confirmation dialog before delete: "Delete scope '{pattern}'? This will also delete all grants associated with this scope."

**Pattern normalization helper text**: "Patterns use glob syntax. `**` matches any number of subdirectories. Paths are normalized to forward slashes. Example: `\\server\share\**` becomes `//server/share/**`."

---

### E.4 Tab: Folder Grants

**Purpose**: Assign allow/deny permissions on folder scopes to users/groups/API keys.

**Layout**:
```
┌─ Folder Grants ──────────────────────────────────────┐
│                                                        │
│  ┌─ Add grant ───────────────────────────────────────┐│
│  │  Scope: ┌─ Select scope ───────────────────────┐  ││
│  │         │ /data/cad/** (Engineering)           ▼│  ││
│  │         └────────────────────────────────────────┘  ││
│  │  -OR- type path: ┌────────────────────────────┐    ││
│  │                  │ /data/manufacturing/**     │    ││
│  │                  └────────────────────────────┘    ││
│  │                                                    ││
│  │  Principal type: ● User ○ Group ○ API Key          ││
│  │  Principal: ┌─ Select user ────────────────────┐   ││
│  │             │ jane.doe                        ▼│   ││
│  │             └──────────────────────────────────┘   ││
│  │                                                    ││
│  │  Permission: ● View ○ Download ○ Index             ││
│  │  Effect:     ● Allow ○ Deny                        ││
│  │                                                    ││
│  │  [Add grant]                                       ││
│  └──────────────────────────────────────────────────┘│
│                                                        │
│  ┌─ Grants table ────────────────────────────────────┐│
│  │  Scope Pattern            │ Principal   │ Perm    ││
│  │  ──────────────────────────────────────────────────││
│  │  /data/cad/**             │ jane.doe    │ view ✓  ││
│  │  /data/cad/restricted/**  │ jane.doe    │ view ✗  ││
│  └──────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
```

**Form elements**:
1. **Scope**: Dropdown of existing scopes + "Custom path" option. If "Custom path" selected, show a text input for path pattern.
2. **Principal type**: Radio buttons: User, Group, API Key.
3. **Principal**: Autocomplete input that searches users (for `user` type) or shows groups (for `group` type). For v0.4, just a simple select dropdown of all users (fetched from `GET /api/admin/users`). Group support is stored but UI is simplified — just a text input for group DN.
4. **Permission**: Radio buttons: View, Download, Index.
5. **Effect**: Radio buttons: Allow, Deny.

**Table columns**: Scope Pattern, Principal, Permission, Effect, Created, Actions.

**Effect rendering in table**:
- Allow: green checkmark ✓ with `color: #16a34a`
- Deny: red cross ✗ with `color: #dc2626`

---

### E.5 Tab: API Keys

**Purpose**: Create, list, and revoke API keys for external tool integration.

**Layout**:
```
┌─ API Keys ──────────────────────────────────────────┐
│                                                        │
│  ┌──── API Key Created! ──── ⚠ ────────────────────┐  │
│  │  Your API key has been created.                   │  │
│  │  This is the only time you'll see the full key.   │  │
│  │                                                    │  │
│  │  qpk_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p             │  │
│  │                                                    │  │
│  │  [Copy to clipboard] [Close]                       │  │
│  └──────────────────────────────────────────────────┘  │
│                                                        │
│  ┌─ Create API key ──────────────────────────────────┐│
│  │  Name: ┌────────────────────────────────────┐     ││
│  │         │ CI pipeline                        │     ││
│  │         └────────────────────────────────────┘     ││
│  │  Owner: ┌─ Select user ───────────────────────┐   ││
│  │         │ admin (you)                        ▼│   ││
│  │         └────────────────────────────────────┘   ││
│  │  Expires: ┌────────────────────────────────┐     ││
│  │           │ 2027-01-01                     │     ││
│  │           └────────────────────────────────┘     ││
│  │  Scopes:                                         ││
│  │  ☑ use_quick_peek    ☑ view_step    ☐ view_pdf   ││
│  │  ☐ view_dxf          ☐ view_obj      ☐ view_doc  ││
│  │  ☐ download_files                                ││
│  │                                                    ││
│  │  [Create API key]                                  ││
│  └──────────────────────────────────────────────────┘│
│                                                        │
│  ┌─ API Keys table ──────────────────────────────────┐│
│  │  Name        │ Prefix          │ Owner  │ Expires ││
│  │  ──────────────────────────────────────────────────││
│  │  CI pipeline │ qpk_a1b2c3d4    │ admin  │ 2027... ││
│  │  Backup tool │ qpk_f9e8d7c6    │ jane   │ Never   ││
│  └──────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
```

**Create form**: Name input, Owner dropdown (users list), Expiry date input (date picker or `<input type="date">`), Scope checkboxes. Submit button.

**Scope checkboxes**: All available permissions listed. Pre-checked: `use_quick_peek`, `view_step`, `view_pdf`, `view_dxf`, `view_obj`. Admin-only scopes (`manage_users`, `view_dashboard`) are shown but unchecked and have a tooltip "Admin-only scope".

**Post-creation modal**: A separate modal (not inline) shows the full key once. It has:
- A large monospace text field with the key: `qpk_a1b2c3d4...`
- "Copy to clipboard" button (calls `navigator.clipboard.writeText(fullKey)`)
- Warning text: "Store this key securely. It will not be shown again."
- "Close" button (dismisses the modal).
- The modal cannot be dismissed by clicking outside or pressing Escape until the user clicks "Copy to clipboard" first (to force conscious copying).

**Table columns**: Name, Prefix (first 8 chars + "…"), Owner, Scopes (as a comma-separated list), Expires, Last Used, Status (Active/Revoked), Actions.

**Actions column**: "Revoke" button (calls `DELETE /api/admin/api-keys/${id}`). Click opens a confirmation: "Revoke API key '{name}'? This cannot be undone." After revoke, the row's status changes to "Revoked" and the revoke button is replaced with a disabled "Revoked" badge.

---

### E.6 Tab: LDAP Test

**Purpose**: Test LDAP connectivity and group mapping without restarting the server.

**Layout**:
```
┌─ LDAP Test ─────────────────────────────────────────┐
│                                                        │
│  ┌─ Connection settings ────────────────────────────┐│
│  │  URL:   ┌──────────────────────────────────────┐  ││
│  │         │ ldap://dc01.example.com:389          │  ││
│  │         └──────────────────────────────────────┘  ││
│  │  Bind DN: ┌────────────────────────────────────┐  ││
│  │           │ CN=svc-quickpeek,CN=Users,...      │  ││
│  │           └────────────────────────────────────┘  ││
│  │  Password: ┌────────────────────────────────────┐  ││
│  │           │ •••••••••••••••••                  │  ││
│  │           └────────────────────────────────────┘  ││
│  │  Search base: ┌────────────────────────────────┐  ││
│  │               │ DC=example,DC=com              │  ││
│  │               └────────────────────────────────┘  ││
│  │  Search filter: ┌──────────────────────────────┐  ││
│  │                 │ (sAMAccountName={username})   │  ││
│  │                 └──────────────────────────────┘  ││
│  │  Test user: ┌────────────────────────────────┐   ││
│  │             │ jane.doe                       │   ││
│  │             └────────────────────────────────┘   ││
│  │                                                    ││
│  │  [Test Connection] (primary button)                ││
│  └──────────────────────────────────────────────────┘│
│                                                        │
│  ┌─ Result panel ────────────────────────────────────┐│
│  │  [●] Connection successful!                        ││
│  │  Server info: LDAP v3, dc01.example.com:389        ││
│  │                                                    ││
│  │  Bind: ✓ Success                                   ││
│  │  Search: ✓ Found 1 user(s)                         ││
│  │    → jane.doe (Jane Doe)                           ││
│  │    → DN: CN=Jane Doe,CN=Users,...                  ││
│  │    → Groups:                                        ││
│  │       CN=QuickPeek-Admins,OU=Groups,...            ││
│  │       CN=Engineering,OU=Groups,...                 ││
│  │    → Mapped permissions:                           ││
│  │       manage_users, view_dashboard, use_quick_peek ││
│  └──────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
```

**Form fields**: All fields are pre-filled from env vars (fetched from `GET /api/admin/ldap-config`). Password field shows `••••••••` (masked, length indicates something is stored). The admin can override any field for testing.

**Test user field**: Optional — if filled, the test performs a user search and shows group membership + mapped permissions. If empty, only tests server connectivity and bind.

**Result panel**: Appears after test completes.
- Green indicator: Connection successful.
- Red indicator: Connection failed with error message.
- Detailed breakdown: Bind status, search results, group membership, mapped permissions.

**Loading state**: Button shows spinner "Testing..." while request is in flight. Result panel shows "Testing..." with shimmer.

---

### E.7 Tab: Folder Schemas

**Purpose**: Define required metadata fields for files in specific folder paths.

**Layout**:
```
┌─ Folder Schemas ─────────────────────────────────────┐
│                                                        │
│  ┌─ Add schema ──────────────────────────────────────┐│
│  │  Path prefix: ┌───────────────────────────────┐   ││
│  │               │ /data/cad/engineering/**      │   ││
│  │               └───────────────────────────────┘   ││
│  │                                                    ││
│  │  Required fields:                                  ││
│  │  ┌─ Key ───────────────────┐ ┌─ Value hint ────┐  ││
│  │  │ project_code            │ │ e.g. AVT-2026    │  ││
│  │  └─────────────────────────┘ └──────────────────┘  ││
│  │  ┌─ Key ───────────────────┐ ┌─ Value hint ────┐  ││
│  │  │ revision                │ │ e.g. A, B, C     │  ││
│  │  └─────────────────────────┘ └──────────────────┘  ││
│  │  [+ Add field]                                     ││
│  │                                                    ││
│  │  [Add schema]                                      ││
│  └──────────────────────────────────────────────────┘│
│                                                        │
│  ┌─ Schemas table ───────────────────────────────────┐│
│  │  Path Prefix                     │ Required Fields ││
│  │  ──────────────────────────────────────────────────││
│  │  /data/cad/engineering/**        │ project_code    ││
│  │                                  │ revision        ││
│  │  /data/manufacturing/**          │ supplier        ││
│  └──────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
```

**Key-value pair editor**: Dynamic list where each row has two inputs: "Key" (text) and "Value hint" (text, optional). An "+ Add field" button appends a new row. Each row has an `×` button to remove it.

**Table**: Shows path prefix and a list of required field keys in a readable format. Delete button per row.

---

### E.8 Tab: Simulate

**Purpose**: Debug tool for admins to check effective permissions for any user on any path.

**Layout**:
```
┌─ Permission Simulator ───────────────────────────────┐
│                                                        │
│  ┌─ Simulate ────────────────────────────────────────┐│
│  │  User: ┌─ Select user ───────────────────────┐   ││
│  │         │ jane.doe                           ▼│   ││
│  │         └────────────────────────────────────┘   ││
│  │  Path: ┌────────────────────────────────────┐    ││
│  │         │ /data/cad/restricted/secret.stp   │    ││
│  │         └────────────────────────────────────┘   ││
│  │                                                    ││
│  │  [Check permissions]                               ││
│  └──────────────────────────────────────────────────┘│
│                                                        │
│  ┌─ Result ──────────────────────────────────────────┐│
│  │  Path: /data/cad/restricted/secret.stp             ││
│  │  User: jane.doe (ID: 5)                            ││
│  │                                                    ││
│  │  Permission   │ Effect    │ Matched Rule           ││
│  │  ────────────────────────────────────────────────── ││
│  │  View         │ ❌ Deny   │ Scope #2: restricted   ││
│  │  Download     │ ❌ Deny   │ Scope #2: restricted   ││
│  │  Index        │ ✅ Allow  │ Default allow          ││
│  └──────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
```

**Form**: User dropdown (autocomplete from users list) + Path input (text, placeholder for full path).

**Results table**: Three rows (View, Download, Index), each showing:
- Permission name
- Effect: green check with "Allow" or red cross with "Deny"
- Matched rule: Which scope+grant produced this effect, or "Default allow"/"Default deny"

**No-match state**: If the path doesn't match any scope, show "No folder scopes match this path. Default rule applies."

---

### E.9 Component Tree — AdminPage

```
AdminPage
├── useState: adminTab (AdminTab)
├── [existing] load users + permissions
│
├── div.admin-tab-bar
│   ├── button.admin-tab × 7 (one per tab)
│   └── (active tab underlined)
│
├── [if adminTab === 'users'] section
│   ├── [existing] admin-toolbar (create user form + reindex)
│   ├── [existing] table-wrap
│   │   └── [MODIFIED] UserRow (now shows auth_source column)
│   └── [existing] message
│
├── [if adminTab === 'folder-scopes'] section
│   ├── FolderScopesPanel
│   │   ├── addScope form (pattern + description + button)
│   │   └── scopesTable (pattern, description, created, delete)
│
├── [if adminTab === 'folder-grants'] section
│   ├── FolderGrantsPanel
│   │   ├── addGrant form (scope dropdown/path, principal type, principal select, permission radio, effect radio, button)
│   │   └── grantsTable (scope, principal, permission, effect, created, delete)
│
├── [if adminTab === 'api-keys'] section
│   ├── ApiKeysPanel
│   │   ├── createKey form (name, owner, expiry, scopes checkboxes, button)
│   │   ├── keyCreatedModal (full key display + copy button)
│   │   └── keysTable (name, prefix, owner, scopes, expires, lastUsed, status, revoke)
│
├── [if adminTab === 'ldap'] section
│   └── LdapTestPanel
│       ├── ldapConfigForm (url, bindDN, password, searchBase, searchFilter, testUser)
│       ├── testResult (success/fail indicator + details)
│       └── [if busy] loading state
│
├── [if adminTab === 'schemas'] section
│   └── FolderSchemasPanel
│       ├── addSchema form (pathPrefix + key-value pair editor)
│       └── schemasTable (pathPrefix, requiredFields, delete)
│
└── [if adminTab === 'simulate'] section
    └── SimulatePanel
        ├── simulateForm (user select + path input + button)
        └── resultTable (permission × 3 rows + matched rules)
```

---

## F. Dashboard Page Updates

### F.1 New KPIs

Add two additional KPI cards to the existing grid (which currently has 4: Searches, Files found, Opened previews, Hours saved):

```
┌─ New Dashboard KPIs ────────────────────────────────────┐
│ Added after the existing 4 KPI cards:                    │
│                                                          │
│ ┌──────────────┐ ┌──────────────────┐                    │
│ │  👥           │ │  🔑              │                    │
│ │  Users        │ │  API keys active │                    │
│ │  42           │ │  3               │                    │
│ │  LDAP: 38     │ │  Last 24h: 47    │                    │
│ │  Local: 4     │ │  requests        │                    │
│ └──────────────┘ └──────────────────┘                    │
└──────────────────────────────────────────────────────────┘
```

**Users card**:
- Icon: `UserRound` from lucide (or a custom double-user icon)
- Total user count
- Sub-line: "LDAP: 38 · Local: 4"

**API key usage card**:
- Icon: `Key` from lucide
- Total active API keys
- Sub-line: "Last 24h: 47 requests"

### F.2 API Changes Needed

Dashboard needs new endpoint properties:
- `total_users`, `ldap_users`, `local_users` in the dashboard summary
- `active_api_keys`, `api_key_requests_24h` in the dashboard summary

Or create a new endpoint `GET /api/dashboard/enterprise` that returns these v0.4-specific metrics.

---

## G. FolderPickerModal Permission Awareness

### G.1 Modified Item Rendering

Each folder item in the list renders an additional access indicator:

```
<button className="folder-item" onClick={() => load(item.path)} title={item.path}>
  <Folder size={17} />
  <span>{item.name}</span>
  <em>{item.path}</em>
  <span className={`access-dot ${item.accessible ? 'access-allowed' : 'access-denied'}`} />
</button>
```

### G.2 Access Dot CSS

```css
.access-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
  margin-left: auto;
}
.access-allowed {
  background: #22c55e;
  box-shadow: 0 0 0 2px rgba(34, 197, 94, 0.2);
}
.access-denied {
  background: #ef4444;
  box-shadow: 0 0 0 2px rgba(239, 68, 68, 0.2);
}
```

### G.3 Denied Folder Interaction

If a folder has `accessible: false`:
- The folder item is rendered (visible) but clicking it shows a tooltip/alert: "You don't have access to this folder."
- The item has a `.folder-denied` class that reduces opacity slightly.

---

## 8. Interaction Design

### 8.1 Tag Autocomplete

| Step | Action | Behavior |
|------|--------|----------|
| 1 | User starts typing in tag input field | After 3+ characters, trigger debounced API call (300ms debounce) to `GET /api/tags?q={query}` |
| 2 | API returns matching tags | Show dropdown below input with max 10 results. Each result shows: tag name + color dot + scope badge |
| 3 | User clicks a suggestion | Tag is added to the selected tags list, input clears, dropdown closes |
| 4 | User presses Enter with text | If text matches an existing tag → add it. If no match → create new tag with that name |
| 5 | User presses comma | Same as Enter — acts as delimiter |
| 6 | User clicks outside | Dropdown closes |
| 7 | User presses Escape | Dropdown closes |

### 8.2 Recents Panel Interaction

| Action | Behavior |
|--------|----------|
| Click recent file | Sets format + fills code textarea + triggers search automatically |
| Click "Clear" button | Opens confirmation: "Clear all recent files and search history?" with OK/Cancel |
| Click collapse toggle | Panel body collapses/expands. State stored in `localStorage('quickpeek_recents_collapsed')` |
| Hover recent file row | Background changes to `var(--soft)` |
| Right-click recent file | No context menu (deferred to v0.5) |

### 8.3 API Key Creation Flow

```
User fills form → "Create API Key" → POST /api/admin/api-keys
  → Success: Show modal with full key
    → User must click "Copy to clipboard" before modal can close
    → After copy, close button becomes active
    → User closes modal → list refreshes
  → Error: Show error inline in form
```

**Force-copy** implementation:
```typescript
const [keyCopied, setKeyCopied] = useState(false);
// In the modal footer:
<button onClick={() => { navigator.clipboard.writeText(fullKey); setKeyCopied(true); }}>
  {keyCopied ? '✓ Copied!' : 'Copy to clipboard'}
</button>
<button onClick={onClose} disabled={!keyCopied}>
  Close
</button>
```

### 8.4 Search History Dropdown

| Action | Behavior |
|--------|----------|
| Focus textarea (empty) | Fetch recent searches from `GET /api/me/recent-searches` and show dropdown |
| Type in textarea | Dropdown hides (user is typing a new search) |
| Click on a recent search item | Fill textarea with the query codes, set format, trigger search |
| Click outside | Dropdown closes |
| Press Escape | Dropdown closes |

### 8.5 Admin Tab Navigation — Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+1` | Switch to Users tab |
| `Ctrl+2` | Switch to Folder Scopes tab |
| `Ctrl+3` | Switch to Folder Grants tab |
| `Ctrl+4` | Switch to API Keys tab |
| `Ctrl+5` | Switch to LDAP Test tab |
| `Ctrl+6` | Switch to Folder Schemas tab |
| `Ctrl+7` | Switch to Simulate tab |

Implementation: `useEffect` with `keydown` listener on the admin page.

---

## 9. Visual Design Tokens

### 9.1 New CSS Variables

Add to `:root` in `global.css`:

```css
:root {
  /* ── Tag colors (8 distinct colors for taxonomy types) ── */
  --tag-red: #ef4444;
  --tag-orange: #f97316;
  --tag-amber: #f59e0b;
  --tag-green: #22c55e;
  --tag-teal: #14b8a6;
  --tag-blue: #3b82f6;
  --tag-purple: #a855f7;
  --tag-pink: #ec4899;
  --tag-gray: #6b7280;

  /* ── Permission indicators ── */
  --allow-color: #16a34a;
  --deny-color: #dc2626;
  --unknown-color: #f59e0b;

  /* ── LDAP / Auth source ── */
  --ldap-badge-bg: #eff6ff;
  --ldap-badge-color: #1d4ed8;
  --local-badge-bg: var(--soft);
  --local-badge-color: var(--muted);

  /* ── Admin tabs ── */
  --admin-tab-active: #2563eb;
  --admin-tab-hover: #1e40af;
}
```

### 9.2 Tag Color Application

Each tag has a `color` property from the database (hex). The tag pill renders:
- Background: `tag.color` at 15% opacity (use `background: ${color}26` where 26 = 15% in hex)
- Text color: `tag.color` (full opacity)
- Border: `tag.color` at 30% opacity

Implementation in React:
```typescript
function TagPill({ tag, onRemove }: { tag: Tag; onRemove?: () => void }) {
  const bg = tag.color + '26';  // 15% opacity
  const border = tag.color + '4D'; // 30% opacity
  return (
    <span className="tag-pill" style={{ background: bg, color: tag.color, borderColor: border }}>
      {tag.name}
      {onRemove && <button onClick={onRemove} style={{ marginLeft: 4 }}>×</button>}
    </span>
  );
}
```

### 9.3 Permission Badge

Used in FolderPickerModal and Simulate results:
```css
.permission-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
}
.permission-badge.allow { background: #dcfce7; color: #15803d; }
.permission-badge.deny { background: #fee2e2; color: #991b1b; }
.permission-badge.unknown { background: #fef3c7; color: #92400e; }
```

### 9.4 Admin Tab Styling

```css
.admin-tab-bar {
  display: flex;
  gap: 4px;
  border-bottom: 1px solid var(--line);
  margin-bottom: 24px;
  overflow-x: auto;
  flex-shrink: 0;
}
.admin-tab {
  padding: 12px 20px;
  border: 0;
  background: transparent;
  color: var(--muted);
  font-size: 14px;
  font-weight: 500;
  white-space: nowrap;
  cursor: pointer;
  border-bottom: 3px solid transparent;
  margin-bottom: -1px;
  transition: color 0.15s, border-color 0.15s;
}
.admin-tab:hover { color: var(--text); }
.admin-tab-active {
  color: var(--text);
  font-weight: 600;
  border-bottom-color: var(--admin-tab-active);
}
```

### 9.5 Error State Illustrations

Icon choices for empty/error states (all from lucide-react):

| State | Icon | Size | Color |
|-------|------|------|-------|
| No folder access | `Lock` | 48px | `var(--muted)` |
| LDAP unreachable | `AlertTriangle` | 20px | `#d97706` (amber) |
| No recents | `FolderOpen` | 32px | `var(--muted-2)` |
| No search results | `FileX` | 48px | `var(--muted)` |
| API key copy required | `AlertTriangle` | 18px | `#d97706` |

### 9.6 Skeleton Loading Placeholder

For the recents panel loading state:
```css
@keyframes shimmer {
  0% { background-position: -200px 0; }
  100% { background-position: calc(200px + 100%) 0; }
}
.recents-skeleton {
  height: 36px;
  border-radius: 8px;
  background: linear-gradient(90deg, var(--soft) 25%, var(--line) 50%, var(--soft) 75%);
  background-size: 200px 100%;
  animation: shimmer 1.5s infinite linear;
  margin-bottom: 8px;
}
```

---

## 10. Responsive / Mobile Considerations

### 10.1 Desktop-First (Primary)

The app targets engineering workstations with 1920×1080 or 2560×1440 displays. All new components are designed for these resolutions first.

### 10.2 Admin Tab Breakpoint

Below **900px** width, the admin tab bar switches from horizontal to a vertical accordion or stacked layout:

```css
@media (max-width: 900px) {
  .admin-tab-bar {
    flex-direction: column;
    border-bottom: 0;
    gap: 2px;
  }
  .admin-tab {
    border-bottom: 0;
    border-left: 3px solid transparent;
    margin-bottom: 0;
    padding: 10px 16px;
  }
  .admin-tab-active {
    border-left-color: var(--admin-tab-active);
    background: var(--soft);
  }
}
```

### 10.3 Tag Picker Minimum Width

The tag editor in ViewerModal must remain usable at **1366×768** (common corporate monitor minimum). Ensure:
- The tag input + chips area does not exceed 100% of the modal width
- Tags wrap to multiple rows if needed
- The autocomplete dropdown is at least 220px wide and doesn't overflow the modal

### 10.4 Recents Panel on Narrow Screens

Below 1100px, the recents panel truncates filenames more aggressively and reduces the number of visible items from 20 to 10:

```css
@media (max-width: 1100px) {
  .recents-item .recents-name {
    max-width: 150px;
  }
  .recents-list {
    max-height: 300px;
    overflow-y: auto;
  }
}
```

---

## 11. Accessibility Notes

### 11.1 Tag Color Is Not the Only Indicator

Every tag pill includes:
- The tag name as text (always visible)
- Color is decorative only — not relied upon for meaning
- If a tag is used for filtering, there is a visible checkmark or "filtering" label

### 11.2 Error State Announcer

Error messages use `aria-live="polite"` so screen readers announce them:

```html
<div className="error-box" role="alert" aria-live="assertive">
  {error}
</div>
```

For LDAP-specific states, use `aria-live="polite"` with a descriptive message:
```html
<div className="warning-box" role="status" aria-live="polite">
  ⚠ LDAP server is not reachable. You can still log in with a local account.
</div>
```

### 11.3 Tab Navigation Order

The logical tab order on QuickPeekPage (using the browser's natural DOM order):

```
1. Format selection chips (STEP, PDF, DXF...)
2. Working folder input + Browse button
3. Recent files panel (if present)
4. Code list textarea
5. Search help + Search button
6. Results grid cards
```

The recents panel sits **between** folder selection and code input in the DOM, following the visual order.

### 11.4 Focus Indicators

All new interactive elements (tag chips, recents items, admin tab buttons, autocomplete items) must have visible focus outlines. Use the existing `:focus-visible` pattern:

```css
button:focus-visible, input:focus-visible, select:focus-visible {
  outline: 2px solid #2563eb;
  outline-offset: 2px;
}
```

### 11.5 Keyboard Navigation

| Component | Keyboard Behavior |
|-----------|-------------------|
| Tag autocomplete dropdown | Arrow keys navigate items, Enter selects, Escape closes |
| Recents panel | Arrow keys navigate items (when panel is focused), Enter triggers search |
| Admin tab bar | Arrow keys switch tabs, Home/End go to first/last |
| API key copy modal | Tab order: Copy button → Close button. Close disabled until Copy clicked |
| Tag filter chips | Tab to chip → Delete/Backspace removes it (when focused) |

### 11.6 Color Contrast

All new text meets WCAG AA:
- Tag pill text uses `tag.color` at full opacity — ensure minimum 4.5:1 contrast against white background
- Access dots (green/red) are 8px and decorative only — no information is conveyed solely by the dot
- Warning banners have sufficient contrast: amber `#d97706` on light background with dark text

---

## 12. Design Principles for This Release

### 12.1 Progressive Enhancement

All new v0.4 features are **opt-in**. If the backend doesn't have LDAP configured, the login page looks identical to v0.3. If no tags exist, the tag UI doesn't show. If no recents exist, the recents panel shows the empty state. The v0.3 experience is a subset of v0.4.

### 12.2 Clear Error Communication

Every auth failure has a distinct visual treatment so the user knows what action to take:

| Error | What the user should do |
|-------|------------------------|
| "Incorrect username or password" | Check credentials and try again |
| "LDAP server is not reachable" | Contact IT, or use local admin account |
| "Too many attempts" | Wait for the timer, or contact admin for unlock |
| "You don't have access to this folder" | Contact admin to request folder access |

### 12.3 Admin Power Tools

The admin UI prioritizes efficiency:
- Inline forms (no modal dialogs for CRUD except for destructive actions and API key reveal)
- Keyboard shortcuts for tab switching
- Tab stays in memory (data is loaded per-tab but switching is instant)
- Form validation happens inline (red border on empty required fields)
- Success/error messages appear inline, not as toasts that disappear

### 12.4 Information Density

Engineering users work with many files. The UI prioritizes:
- Compact tag display (small pills, max 3 visible)
- Compact recents (single-line items with icon + name + badge + time)
- Efficient admin tables with inline actions
- Results grid density controls (column count + card height) already exist and are unchanged

---

## 13. Appendix: CSS Additions

All new CSS classes to be added to `frontend/src/styles/global.css`:

```css
/* ── Recents Panel ── */
.recents-panel { padding: 18px 20px; }
.recents-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.recents-header strong { font-size: 15px; }
.recents-list { display: grid; gap: 4px; }
.recents-item {
  display: grid;
  grid-template-columns: 28px 1fr auto auto;
  gap: 10px;
  align-items: center;
  padding: 8px 10px;
  border: 0;
  background: transparent;
  border-radius: 8px;
  text-align: left;
  cursor: pointer;
  width: 100%;
}
.recents-item:hover { background: var(--soft); }
.recents-name { font-size: 13px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.recents-badge {
  font-size: 10px; font-weight: 600; text-transform: uppercase;
  background: var(--soft); padding: 2px 6px; border-radius: 6px; color: var(--muted);
}
.recents-time { font-size: 12px; color: var(--muted-2); white-space: nowrap; }
.recents-empty { color: var(--muted); font-size: 13px; padding: 16px 0; display: flex; gap: 8px; align-items: center; }
.recents-skeleton { height: 36px; border-radius: 8px; background: var(--soft); margin-bottom: 4px; }

/* ── Recent Searches Dropdown ── */
.recent-searches-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  z-index: 30;
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 12px;
  box-shadow: var(--shadow);
  max-height: 280px;
  overflow-y: auto;
  margin-top: 4px;
}
.recent-search-item {
  display: flex;
  gap: 10px;
  align-items: center;
  padding: 10px 12px;
  border: 0;
  background: transparent;
  width: 100%;
  text-align: left;
  cursor: pointer;
  font-size: 13px;
}
.recent-search-item:hover { background: var(--soft); }
.recent-search-query { font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.recent-search-meta { color: var(--muted); font-size: 11px; white-space: nowrap; }

/* ── Tag Filter Bar ── */
.tag-filter-bar {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
  padding: 8px 0;
}
.tag-filter-bar > span { color: var(--muted); font-size: 13px; }
.tag-filter-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 500;
  background: var(--soft);
  border: 1px solid var(--line);
}
.tag-filter-chip button { border: 0; background: none; padding: 0; color: var(--muted); cursor: pointer; font-size: 14px; line-height: 1; }
.tag-filter-input { position: relative; }
.tag-filter-input input {
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  border: 1px solid var(--line);
  width: 140px;
}

/* ── Tag Pills (PreviewCard + ViewerModal) ── */
.tag-pills { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 4px; }
.tag-pill {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 2px 8px;
  border-radius: 8px;
  font-size: 11px;
  font-weight: 500;
  line-height: 1.4;
  border: 1px solid transparent;
}
.tag-pill button {
  border: 0; background: none; padding: 0;
  font-size: 13px; line-height: 1; cursor: pointer; opacity: 0.6;
}
.tag-pill button:hover { opacity: 1; }
.tag-pill-more { background: var(--soft); color: var(--muted); border-color: var(--line); }

/* ── ViewerModal Tags & Metadata Section ── */
.viewer-bottom-section { border-top: 1px solid var(--line); }
.viewer-section-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 12px 20px; cursor: pointer; user-select: none;
}
.viewer-section-header:hover { background: var(--soft); }
.viewer-section-body { padding: 0 20px 16px; }
.tags-section { margin-bottom: 16px; }
.current-tags { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 10px; }
.tag-input-wrapper { position: relative; }
.tag-input-wrapper input {
  width: 100%; padding: 8px 12px; border-radius: 10px;
  border: 1px solid var(--line); font-size: 13px;
}
.tag-autocomplete-dropdown {
  position: absolute; top: 100%; left: 0; right: 0; z-index: 30;
  background: #fff; border: 1px solid var(--line); border-radius: 10px;
  box-shadow: var(--shadow); max-height: 200px; overflow-y: auto; margin-top: 4px;
}
.tag-autocomplete-item {
  display: flex; gap: 8px; align-items: center;
  padding: 8px 12px; border: 0; background: transparent;
  width: 100%; text-align: left; cursor: pointer; font-size: 13px;
}
.tag-autocomplete-item:hover { background: var(--soft); }
.tag-autocomplete-item.create { color: var(--muted); font-style: italic; }
.section-divider { height: 1px; background: var(--line); margin: 12px 0; }
.metadata-section { font-size: 13px; }
.metadata-section p { margin: 4px 0; color: var(--text); }
.metadata-section .muted { color: var(--muted); }

/* ── Admin Tab Bar ── */
.admin-tab-bar {
  display: flex; gap: 4px; border-bottom: 1px solid var(--line);
  margin-bottom: 24px; overflow-x: auto; flex-shrink: 0;
}
.admin-tab {
  padding: 12px 20px; border: 0; background: transparent;
  color: var(--muted); font-size: 14px; font-weight: 500;
  white-space: nowrap; cursor: pointer;
  border-bottom: 3px solid transparent; margin-bottom: -1px;
  transition: color 0.15s, border-color 0.15s;
}
.admin-tab:hover { color: var(--text); }
.admin-tab-active {
  color: var(--text); font-weight: 600;
  border-bottom-color: #2563eb;
}

/* ── Folder Access Dots ── */
.access-dot {
  width: 8px; height: 8px; border-radius: 50%;
  flex-shrink: 0; margin-left: auto;
}
.access-allowed { background: #22c55e; box-shadow: 0 0 0 2px rgba(34,197,94,0.2); }
.access-denied { background: #ef4444; box-shadow: 0 0 0 2px rgba(239,68,68,0.2); }
.folder-denied { opacity: 0.55; }

/* ── Permission Badge ── */
.permission-badge {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 2px 8px; border-radius: 999px; font-size: 11px; font-weight: 600;
}
.permission-badge.allow { background: #dcfce7; color: #15803d; }
.permission-badge.deny { background: #fee2e2; color: #991b1b; }
.permission-badge.unknown { background: #fef3c7; color: #92400e; }

/* ── Auth Source Badge ── */
.auth-source-badge {
  display: inline-block;
  padding: 2px 8px; border-radius: 999px; font-size: 11px; font-weight: 500;
}
.auth-source-badge.ldap { background: #eff6ff; color: #1d4ed8; }
.auth-source-badge.local { background: var(--soft); color: var(--muted); }

/* ── API Key Created Modal ── */
.key-reveal-modal {
  width: min(520px, 90vw); background: #fff; border-radius: 20px;
  padding: 28px; box-shadow: 0 30px 80px rgba(0,0,0,0.25);
  display: grid; gap: 16px;
}
.key-reveal-modal .warning-icon { color: #d97706; }
.key-reveal-modal .full-key {
  font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace;
  font-size: 14px; padding: 14px; background: var(--soft);
  border: 1px solid var(--line); border-radius: 12px;
  word-break: break-all; user-select: all;
}
.key-reveal-modal .key-actions { display: flex; gap: 10px; justify-content: flex-end; }

/* ── LDAP Test Result ── */
.ldap-result { padding: 16px; border-radius: 14px; border: 1px solid var(--line); }
.ldap-result.success { border-color: #bbf7d0; background: #f0fdf4; }
.ldap-result.failure { border-color: #fecaca; background: #fef2f2; }
.ldap-result h4 { margin: 0 0 10px; font-size: 14px; }
.ldap-result .detail-row { display: flex; gap: 8px; font-size: 13px; padding: 2px 0; }
.ldap-result .detail-label { color: var(--muted); min-width: 100px; }
.ldap-result pre { font-size: 12px; background: var(--soft); padding: 8px; border-radius: 8px; margin: 8px 0 0; }

/* ── Key-Value Pair Editor (Folder Schemas) ── */
.kv-pair { display: flex; gap: 8px; align-items: center; margin-bottom: 6px; }
.kv-pair input { flex: 1; }
.kv-pair button { flex-shrink: 0; }

/* ── Warning Box (LDAP unreachable) ── */
.warning-box {
  padding: 12px 14px; border-radius: 12px;
  border: 1px solid #fde68a; background: #fffbeb;
  color: #92400e; font-size: 13px; display: flex; gap: 8px; align-items: flex-start;
}

/* ── Responsive: admin tabs stack below 900px ── */
@media (max-width: 900px) {
  .admin-tab-bar {
    flex-direction: column;
    border-bottom: 0;
    gap: 2px;
  }
  .admin-tab {
    border-bottom: 0;
    border-left: 3px solid transparent;
    margin-bottom: 0;
    padding: 10px 16px;
  }
  .admin-tab-active {
    border-left-color: #2563eb;
    background: var(--soft);
  }
}

/* ── Responsive: recents panel truncation below 1100px ── */
@media (max-width: 1100px) {
  .recents-item { grid-template-columns: 28px 1fr auto; }
  .recents-badge { display: none; }
  .recents-list { max-height: 300px; overflow-y: auto; }
}
```

---

*End of Design Document — Quick Peek v0.4 "Enterprise"*
