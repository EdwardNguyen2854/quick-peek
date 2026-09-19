# Quick Peek v0.9.0 — Background Indexing and Preview Cache

## Highlights

- background startup indexing with live progress (phase, current folder, file count)
- per-root index health (ready / indexing / error) visible in the search panel
- legacy Office preview for `.doc`, `.xls`, `.ppt` files via `QUICKPEEK_LIBREOFFICE_CMD`
- bounded preview cache controlled by `QUICKPEEK_PREVIEW_CACHE_MAX_SIZE_MB` and `QUICKPEEK_PREVIEW_CACHE_MAX_AGE_DAYS`
- search remains non-blocking; startup no longer waits for indexing to complete

## Index lifecycle

Configured roots are indexed in a background thread at startup. The UI exposes per-root health and live progress without blocking the search panel. Manual Refresh re-indexes all roots or a selected folder.

## Compatibility

All v0.8 ranking contracts, deterministic match ordering, fuzzy suggestions, paste handling, and SQLite migration behaviour are preserved. Existing `files` rows are retained and enriched on the next refresh.

## Migration

No migration steps are required. Existing SQLite databases open as-is; existing rows are enriched on the next index refresh. New `QUICKPEEK_PREVIEW_CACHE_MAX_SIZE_MB` and `QUICKPEEK_PREVIEW_CACHE_MAX_AGE_DAYS` env vars default to `500` MB and `7` days if not set.

---

# Quick Peek v0.8.0 — Reliable Search

## Highlights

- deterministic engineering part-number ranking
- case/separator/extension normalization
- explicit revision parsing and revision-aware ordering
- common folder-state priority (released/current/supplier/WIP/archive)
- SQLite-only normal searches; no filesystem walk on Search
- explicit index status and Refresh
- All-formats search
- batch filters for Found / Multiple / Suggested / Missing
- inspectable alternative strong matches
- conservative fuzzy "Did you mean?" suggestions
- robust Excel/tab/comma/semicolon paste handling
- backward-compatible SQLite migration
- search regression tests and GitHub Actions CI

## Ranking contract

Strong matches are ordered by:

1. match exactness
2. folder priority
3. revision
4. modified time
5. deterministic filename tie-breakers

Fuzzy results are suggestions only and never replace a strong result.

## Migration

Existing `files` rows remain in place. v0.8 adds normalized search metadata and `index_state`; the next index refresh enriches existing rows.

## Compatibility

The no-login, local-first architecture remains unchanged. Existing STEP interaction, card sizing, document previews, raw downloads, and working-folder browsing remain part of the core workflow.
