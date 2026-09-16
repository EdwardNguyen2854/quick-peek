# Decisions

## Keep the app single-purpose

Quick Peek is a local engineering utility, not an account platform. The UI is a single Quick Peek screen and the backend exposes only search/preview/folder endpoints.

## No authentication layer

Login, accounts, permissions, LDAP, API keys, admin controls, and dashboard analytics were removed to reduce setup and dependency complexity.

## Automatic indexing

Configured roots are indexed at startup and refreshed for default-root searches. A selected working folder is indexed when searched, so a manual admin reindex action is unnecessary.

## Same-origin API in development and builds

Vite runs on port 5173 and proxies `/api` to the backend on port 8000. Production/bundled builds use the same relative `/api` URLs.

## Python 3.14

Use FastAPI/Pydantic versions that support Python 3.14. Backend startup must stop if dependency installation fails and must run uvicorn through the project venv.
