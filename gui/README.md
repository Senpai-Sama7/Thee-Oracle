# Oracle Agent GUI

The GUI is a Flask + Socket.IO wrapper around `OracleAgent`. It provides a browser chat surface, health/status endpoints, and a small settings API.

## Current Behavior

- `gui/launch.py` and `gui/app.py` now use the same port setting: `ORACLE_GUI_PORT`, default `5001`
- the default GUI bind host is `127.0.0.1`; set `ORACLE_GUI_HOST` explicitly if you need remote access
- the GUI imports cleanly even when `flask_talisman` or `flask_limiter` are not installed
- if those optional packages are missing, the app logs warnings and falls back to no-op wrappers, but still applies baseline browser security headers directly
- protected config endpoints use `ORACLE_API_KEY`
- authenticated Socket.IO clients are required when `ORACLE_API_KEY` is set
- direct browser-triggered tool execution is limited to the GUI tool set: `shell_execute`, `file_system_ops`, `http_fetch`, and `vision_capture`
- Socket.IO cross-origin access is same-origin by default; set `ORACLE_GUI_CORS_ORIGINS` only when you intentionally need cross-origin browser access

## Launch

From the project root:

```bash
python3 gui/launch.py
```

Or run the app directly:

```bash
ORACLE_GUI_HOST=127.0.0.1 ORACLE_GUI_PORT=5001 python3 gui/app.py
```

Default URL:

```text
http://127.0.0.1:5001
```

## Environment

Relevant variables:

- `ORACLE_GUI_PORT`
- `ORACLE_GUI_HOST`
- `ORACLE_API_KEY`
- `SECRET_KEY`
- `ORACLE_GUI_CORS_ORIGINS`
- `ORACLE_MODEL_ID`
- `GCP_PROJECT_ID`
- `GCP_LOCATION`
- `ORACLE_PROJECT_ROOT`
- `ORACLE_MAX_TURNS`
- `ORACLE_SHELL_TIMEOUT`
- `ORACLE_HTTP_TIMEOUT`

The GUI reads `.env` if present and reinitializes the wrapped `OracleAgent` after config updates.
Protected settings reads/writes and Socket.IO actions require `ORACLE_API_KEY`.
Wildcard Socket.IO CORS is ignored unless `ORACLE_GUI_ALLOW_ANY_ORIGIN=true` is also set.

## Verified Endpoints

These routes are covered by `tests/test_http_entrypoints.py`:

- `GET /api/status`
- `GET /api/health`
- `GET /api/help/features`
- `GET /api/config` with `X-API-Key`
- authenticated Socket.IO connect with `auth.apiKey`

Additional routes in `gui/app.py` include:

- `GET /api/settings`
- `GET /api/settings/export`
- `POST /api/settings/reset`

## Notes

- Conversation and backup behavior depend on the wrapped `OracleAgent`
- file operations still inherit the `ORACLE_PROJECT_ROOT` sandbox
- if GCP credentials are missing, the GUI can still start, but model-backed chat paths will not work
- assistant markdown is sanitized in the browser before insertion into the DOM
