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
