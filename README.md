# Oracle Agent Platform

Oracle Agent is a Python AI orchestration workspace centered on a hardened `OracleAgent` ReAct loop, plus sibling services for webhook handling, a personal-agent flow, a RabbitMQ-backed email worker, and a Flask GUI.

This repository is not uniformly polished. The maintained runtime path is solid and currently verified, but the tree also contains older prototype modules and historical docs. Use this README, [AGENTS.md](./AGENTS.md), and [gui/README.md](./gui/README.md) as the current entry points.

## Current Status

- `pytest -q` -> `167 passed`
- `ruff check .` -> clean
- `mypy src/oracle orchestrator.py` -> clean under the repo's strict mypy config
- `python3 demo.py` -> passes
- `python3 -m compileall src/oracle personal_agent email_worker interfaces gui skills orchestrator.py main.py demo.py` -> passes

## What Is Here

```text
src/oracle/                Core OracleAgent runtime, router, MCP, skills, health check
orchestrator.py            Shared task, persistence, circuit-breaker, metrics primitives
main.py                    Interactive CLI wrapper plus health-check bootstrap
demo.py                    Credential-light smoke demo for tools and persistence
src/oracle/main.py         FastAPI webhook/chat wrapper around OracleAgent
personal_agent/main.py     Separate FastAPI service with its own tool flow
email_worker/main.py       RabbitMQ consumer that sends queued email via SMTP
gui/                       Flask + Socket.IO web UI
skills/                    Dynamic skill modules
tests/                     Maintained automated test suite
docs/                      Mixed current and historical documentation
```

## Skill Architecture

The repo now supports two skill formats:

- legacy flat Python skills in `skills/*.py`
- Claude-style package skills in `skills/<skill-name>/SKILL.md`

Package skills can be instruction-only or tool-backed. When a request comes in, Oracle discovers the skill catalog, scores skills against the prompt using name/description/triggers, and injects the top matching `SKILL.md` instructions into the system prompt. If a package also has `skill.py` or `__init__.py`, its `TOOLS` are loaded into the existing `ToolRegistry` path alongside built-ins and MCP tools.

See [skills/README.md](./skills/README.md) for the on-disk format and [skills/code-review-guidance/SKILL.md](./skills/code-review-guidance/SKILL.md) for a package-style example.

## Quick Start

### 1. Configure the environment

Create a `.env` file from [.env.example](./.env.example) and set the variables for the components you plan to run.

Important notes:

- `ORACLE_PROJECT_ROOT` is now honored by `OracleConfig` and defines the file sandbox root.
- `ORACLE_DB_PATH` overrides the SQLite path; on Vercel the agent now defaults to `/tmp/oracle_core.db`.
- `GCP_PROJECT_ID` is required for live Gemini/Vertex AI calls.
- `RABBITMQ_URL` is required for `personal_agent` and `email_worker`; those paths now fail closed if it is missing.
- `requirements.txt` now provides a root runtime dependency set suitable for the Flask/Vercel deployment path.

### 2. Run the component you need

Demo mode:

```bash
python3 demo.py
```

Interactive CLI:

```bash
python3 main.py
```

Oracle FastAPI webhook wrapper:

```bash
python3 -m uvicorn src.oracle.main:app --host 0.0.0.0 --port 8000
```

Personal-agent service:

```bash
python3 -m uvicorn personal_agent.main:app --host 0.0.0.0 --port 8001
```

Email worker:

```bash
python3 email_worker/main.py
```

GUI:

```bash
python3 gui/launch.py
```

The GUI defaults to `http://127.0.0.1:5001` and can be moved with `ORACLE_GUI_HOST` / `ORACLE_GUI_PORT`.

## Vercel Deployment

This repo now includes a Vercel-compatible Flask entrypoint and routing config:

- [app.py](./app.py): WSGI entrypoint that boots the GUI runtime
- [vercel.json](./vercel.json): catch-all rewrite to the Flask app plus bundle exclusions
- [requirements.txt](./requirements.txt): Python runtime dependencies for the deployed function

Deployment notes:

- On Vercel, the GUI automatically switches to an HTTP fallback transport because Vercel Functions do not expose a Socket.IO/WebSocket server path.
- The serverless runtime now stores SQLite state in `/tmp/oracle_core.db` by default unless `ORACLE_DB_PATH` is set.
- The deployed filesystem is still effectively read-only except for `/tmp`, so file-writing tools should be treated accordingly.

Recommended Vercel environment variables:

- `GCP_PROJECT_ID`
- `GCP_LOCATION`
- `ORACLE_MODEL_ID`
- `ORACLE_API_KEY`
- `SECRET_KEY`
- `ORACLE_DB_PATH` if you want a custom writable path under `/tmp`

## Verification Commands

```bash
pytest -q
ruff check .
mypy src/oracle orchestrator.py
python3 demo.py
python3 -m compileall src/oracle personal_agent email_worker interfaces gui skills orchestrator.py main.py demo.py
```

Focused reruns:

```bash
pytest -q tests/test_http_entrypoints.py
pytest -q tests/test_runtime_config.py
pytest -q tests/test_tool_execution_flow.py
```

## Architecture Notes

The strongest code paths are:

- [src/oracle/agent_system.py](./src/oracle/agent_system.py)
- [src/oracle/model_router.py](./src/oracle/model_router.py)
- [src/oracle/tool_registry.py](./src/oracle/tool_registry.py)
- [src/oracle/skill_loader.py](./src/oracle/skill_loader.py)
- [src/oracle/mcp_client.py](./src/oracle/mcp_client.py)
- [orchestrator.py](./orchestrator.py)

Areas that still behave more like prototypes than hardened runtime code:

- `src/oracle/workflow_engine.py`
- `src/oracle/plugin_system.py`
- `src/oracle/integration_framework.py`
- `src/oracle/agent_collaboration.py`
- `src/oracle/code_generator.py`
- parts of `src/oracle/agent_graph.py`

## Security and Runtime Contracts

- File operations are sandboxed to `ORACLE_PROJECT_ROOT`.
- Built-in shell execution uses `["bash", "-c", cmd]`, not `shell=True`.
- Session history is stored as JSON-safe data in SQLite, not with `pickle`.
- `personal_agent/main.py` and `email_worker/main.py` no longer embed RabbitMQ credentials.
- `gui/app.py` works even without `flask_talisman` or `flask_limiter`; it logs warnings and falls back to no-op wrappers.

## Documentation Map

- [AGENTS.md](./AGENTS.md): code-grounded architecture and maintenance guide
- [docs/README.md](./docs/README.md): documentation index and trust order
- [gui/README.md](./gui/README.md): GUI-specific setup and API notes

Many older files in `docs/` describe earlier implementation plans or aspirational features. Cross-check them against the code before relying on them for changes.
