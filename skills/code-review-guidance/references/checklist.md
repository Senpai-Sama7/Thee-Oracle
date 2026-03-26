# Code Review Checklist

Use this checklist when a task calls for a full review or hostile audit.

## Runtime Boundaries

- Verify auth defaults are fail-closed when keys are configured.
- Verify loopback or same-origin defaults on browser-facing services.
- Verify file and URL validation is still in place.
- Verify subprocess execution does not regress to `shell=True`.

## Tooling Boundaries

- Check `ToolExecutor`, `ToolRegistry`, and any wrapper allowlists.
- Check skill- or MCP-loaded tools for naming collisions and unexpected exposure.
- Check prompt-time instruction paths for stale or misleading context.

## Persistence and Messaging

- Check SQLite paths, WAL mode, and JSON-safe serialization.
- Check RabbitMQ and SMTP code for missing env validation or credential fallbacks.
- Check worker retry / dead-letter behavior after code changes.

## Tests

- Prefer targeted reruns first, then `pytest -q` for final proof.
- Update or add regression tests for every confirmed defect.
