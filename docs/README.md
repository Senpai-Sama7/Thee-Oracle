# Documentation Index

This repository has a mix of current docs, design notes, and older aspirational material. Use the files below in this order when you need accurate guidance.

## Trust Order

1. [README.md](../README.md) for current setup, run modes, and verification commands
2. [AGENTS.md](../AGENTS.md) for the code-grounded architecture map and maintenance notes
3. [gui/README.md](../gui/README.md) for GUI-specific setup and behavior
4. Everything else in `docs/` as supporting or historical context

## Current Verified Baseline

- `pytest -q` -> `167 passed`
- `ruff check .` -> clean
- `mypy src/oracle orchestrator.py` -> clean
- `python3 demo.py` -> passes

## Current Runtime Surfaces

- `main.py`: interactive CLI wrapper plus health-check bootstrap
- `src/oracle/main.py`: FastAPI webhook/chat wrapper around `OracleAgent`
- `personal_agent/main.py`: separate FastAPI service with its own tool flow
- `email_worker/main.py`: RabbitMQ email consumer
- `gui/app.py` and `gui/launch.py`: Flask GUI backend and launcher

## Useful Docs In This Folder

- [ORACLE_PLATFORM_COMPREHENSIVE_GUIDE.md](./ORACLE_PLATFORM_COMPREHENSIVE_GUIDE.md)
  - broad platform overview
  - use for context, but verify claims against the code
- [TECHNICAL_IMPLEMENTATION_GUIDE.md](./TECHNICAL_IMPLEMENTATION_GUIDE.md)
  - implementation-oriented notes and commands
  - some sections describe earlier phases, not only the current runtime
- [api_reference.md](./api_reference.md)
  - API reference material for service-facing paths
- [plugin_development.md](./plugin_development.md)
  - plugin-specific design notes

## Historical / Aspirational Material

These are still useful, but they are not the source of truth for current behavior:

- `ORACLE_50_*`
- `enterprise_features.md`
- phased implementation summaries
- roadmap and task-tracker documents

If one of these files conflicts with the code, trust the code, then update the doc that misled you.
