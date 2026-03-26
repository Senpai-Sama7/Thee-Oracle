# Oracle Agent Abilities

This file is a lightweight companion to [AGENTS.md](./AGENTS.md), not a separate source of truth.

## Use These Files In Order

1. [README.md](./README.md) for current setup and run commands
2. [AGENTS.md](./AGENTS.md) for the detailed codebase intelligence map
3. [gui/README.md](./gui/README.md) for GUI-specific behavior

## Current Verified Snapshot

- `pytest -q` -> `167 passed`
- `ruff check .` -> clean
- `mypy src/oracle orchestrator.py` -> clean

## Practical Summary

- `main.py` is the interactive CLI wrapper around `OracleAgent`
- `src/oracle/main.py` is the FastAPI webhook/chat wrapper
- `personal_agent/main.py` is a separate FastAPI subsystem with its own tool flow
- `email_worker/main.py` consumes queued email tasks from RabbitMQ
- `gui/app.py` and `gui/launch.py` provide the Flask GUI on `ORACLE_GUI_PORT` or `5001`

For architecture, module boundaries, testing guidance, and caveats, use [AGENTS.md](./AGENTS.md).
