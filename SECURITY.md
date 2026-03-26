# Security Notes

This repository contains a mix of hardened runtime paths, integration helpers, and older prototype code. Do not assume the whole repo meets a uniform security bar.

## Current Posture

- The maintained runtime and test surface currently pass:
  - `ruff check .`
  - `mypy src/oracle orchestrator.py`
  - `pytest -q`
- Some modules remain intentionally lower-trust or prototype-grade. `AGENTS.md` is the preload source of truth for subsystem maturity.
- The formal hostile-review findings live in [security_best_practices_report.md](/home/donovan/Projects/replit/security_best_practices_report.md).

## High-Level Guidance

- Treat `src/oracle/agent_system.py` and `orchestrator.py` as the primary hardened spine.
- Treat `gui/`, `src/oracle/workflow_engine.py`, and older operational scripts as higher-risk review targets.
- Do not use placeholder secrets, default broker credentials, or broad CORS settings outside isolated local development.
- Prefer JSON-safe serialization, parameterized SQL, explicit subprocess argument lists, and fail-closed auth checks.

## Security Checks

Recommended local checks:

```bash
ruff check .
mypy src/oracle orchestrator.py
pytest -q
python3 scripts/validate_env.py
python3 scripts/validate_production.py
```

Targeted hostile grep:

```bash
rg -n "shell=True|pickle\\.|eval\\(|yaml\\.load\\(|SECRET_KEY|demo-api-key|cors_allowed_origins=\\\"\\*\\\"|innerHTML\\s*=|marked\\.parse\\(" . --glob '!venv/**' --glob '!.venv/**'
```

## Secret Handling

- Keep runtime secrets in `.env` or your deployment secret manager, not in tracked files.
- Generate strong random values for:
  - `ORACLE_API_KEY`
  - `WEBHOOK_API_KEY`
  - `SECRET_KEY`
  - `RABBITMQ_DEFAULT_PASS`
  - `POSTGRES_PASSWORD`
- The checked-in `.env.example` is intentionally non-functional for secrets and should be filled in before use.

## Reporting

If you are doing a review or remediation pass:

1. Start with `AGENTS.md` and the hostile findings report.
2. Re-verify after every owned change.
3. Separate fixed issues from unresolved findings that sit outside your edit scope.
