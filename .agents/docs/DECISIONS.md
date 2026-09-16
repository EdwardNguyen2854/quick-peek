# Decisions

## Keep the app single-purpose

Quick Peek is a local engineering utility, not an account platform. The UI remains one focused lookup/preview workspace.

## No authentication layer

Login, accounts, permissions, LDAP, API keys, admin controls, and dashboard analytics stay out of scope.

## Index search, do not scan on Search

Configured roots are indexed at startup. A selected working folder is indexed when explicitly selected/refreshed. Pressing Search queries SQLite only, so search latency is separated from filesystem/network-share latency.

## Deterministic search over opaque AI ranking

Part-number lookup uses normalization, filename parsing, exact/token/prefix/substring rules, folder priority, revision metadata, and deterministic tie-breakers. No LLM or embedding ranking is used.

## Conservative fuzzy matching

Fuzzy matching runs only when no strong deterministic candidate exists. It produces "Did you mean?" suggestions and never marks the suggestion as Found or automatically opens it.

## Ranking precedence

Match exactness outranks folder classification; folder classification outranks revision; revision outranks modified time. This prevents a newer archive/backup or fuzzy filename from silently displacing a cleaner current exact match.

## Folder classification

Common path terms classify files approximately as released/current/supplier/WIP/archive. Classification influences ranking but does not hide files.

## Backward-compatible SQLite migration

The existing `files` table is altered in place to add search metadata. Existing rows are retained and enriched by the next index refresh.

## Same-origin API

Vite proxies relative `/api` requests to the backend in development. Production/bundled builds use the same relative URLs.

## Browser-side STEP tessellation

STEP files are imported with OpenCascade WebAssembly in the browser and rendered with Three.js. No FreeCAD converter is required.
