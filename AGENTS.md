# Quick Peek — Agent Notes

## Product scope

Quick Peek is intentionally a small local engineering file-search and preview app.

Core workflow:
1. choose All files or a format
2. optionally choose an indexed working folder
3. paste codes / part numbers
4. search the SQLite index
5. review recommended matches, alternatives, suggestions, and missing codes
6. preview, open, or download

Do not reintroduce login, accounts, roles, permissions, admin pages, dashboards, roadmap pages, releases pages, API keys, LDAP, or usage analytics unless explicitly requested.

## Search invariants

- Search itself must not recursively scan the filesystem.
- Exact/normalized deterministic matches outrank fuzzy candidates.
- Fuzzy candidates are suggestions only.
- Preserve input order.
- Keep ranking logic in the backend.
- Explain recommendation reasons in the API/UI.
- Prefer released/current locations over archive/WIP according to explicit ranking rules.
- Existing SQLite databases must migrate in place.

## Repo structure

```
backend/
  app/
    main.py
    config.py
    db.py             SQLite schema + index state
    file_index.py     filesystem indexing + candidate retrieval
    search_engine.py  normalization, parsing, ranking, fuzzy suggestions
    preview.py
    dxf_preview.py
    routers/          peek, folders
  tests/              search + migration regression tests
frontend/
  src/pages/          QuickPeekPage only
  src/components/     preview + folder picker components
.github/workflows/    CI
scripts/              dev + Windows build scripts
```

## Development

Windows:
```bat
scripts\run_dev_windows.bat
```

macOS/Linux:
```bash
scripts/run_dev_mac_linux.sh
```

The Vite dev server proxies `/api` to `http://127.0.0.1:8000`.

## STEP preview

```
STEP B-rep → OpenCascade WebAssembly tessellation → Three.js
```

STEP previews are for quick visual inspection, not authoritative geometry validation.
