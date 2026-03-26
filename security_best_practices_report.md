# Security Best Practices Report

Date: 2026-03-26

Scope:

- Full-repo hostile pattern scan for exploitable security issues and operational drift.
- Remediation limited to owned files:
  - `infrastructure/**`
  - `scripts/**`
  - `.env.example`
  - `SECURITY.md`

Method:

- Static hostile grep for dangerous execution, deserialization, permissive network policy, weak/default secrets, and trust-boundary drift.
- Targeted source inspection of runtime entrypoints, GUI surface, infrastructure, and helper scripts.
- Post-fix verification using repo linters plus owned-surface smoke tests.

## Prioritized Findings

### 1. High: Unsafe state deserialization path in legacy infrastructure helper was remediated

Status: fixed in owned scope

Evidence:

- `infrastructure/oracle_storage.py:24-26`
- `infrastructure/oracle_storage.py:73-80`

Details:

- The persistence helper now stores Gemini history as JSON-safe model payloads and restores with `types.Content.model_validate(...)`.
- This removes the unsafe-deserialization class that exists when persisted state is loaded with `pickle.loads(...)`.

Impact:

- Unsafe pickle deserialization is equivalent to arbitrary code execution if an attacker can influence stored bytes.

Remediation:

- Replaced object pickling with JSON serialization and schema validation.
- Added legacy-schema migration support for `history_json`.

### 2. Medium: Shell-string execution in production validation was remediated

Status: fixed in owned scope

Evidence:

- `scripts/validate_production.py:5-6`
- `scripts/validate_production.py:37-57`
- `scripts/validate_production.py:87-116`

Details:

- The validator now uses explicit subprocess argument lists and controlled working-directory execution.
- It no longer depends on shell-string command construction.

Impact:

- Shell-string execution expands command-injection risk if user-controlled values ever reach the validator path.

Remediation:

- Replaced shell invocation with `subprocess.run(args, ...)`.
- Moved simple checks to direct file inspection where possible.

### 3. Medium: Insecure example/default secrets in ops configuration were remediated

Status: fixed in owned scope

Evidence:

- `.env.example:31-33`
- `.env.example:39-41`
- `.env.example:54-56`
- `infrastructure/docker-compose.yml:7-9`
- `infrastructure/docker-compose.yml:21-24`

Details:

- The tracked example env previously encouraged placeholder or default-style credentials for API and broker access.
- The Compose file now fails fast if `RABBITMQ_DEFAULT_PASS` or `POSTGRES_PASSWORD` are missing instead of silently using `change-me`.

Impact:

- Default or predictable credentials frequently survive into shared dev, staging, or even production deployments.

Remediation:

- Removed the checked-in GUI API key placeholder value.
- Replaced RabbitMQ guest-style examples with dedicated placeholder credentials.
- Required explicit secret provisioning in Compose.

### 4. Medium: Public Cloud Run invoker was enabled by default in Terraform and is now opt-in

Status: fixed in owned scope

Evidence:

- `infrastructure/deploy.tf:35-39`
- `infrastructure/deploy.tf:107-114`

Details:

- Terraform now defaults `allow_public_invoker` to `false`.
- Internet-wide unauthenticated invocation of the webhook is no longer the default deployment posture.

Impact:

- Public invoker on an internet-facing service increases exposure to brute force, probing, and auth-bypass fallout if a key leaks.

Remediation:

- Made public access explicit and opt-in.

### 5. High: GUI WebSocket surface still allows wildcard cross-origin access

Status: remediated

Evidence:

- `gui/app.py`
- `tests/test_http_entrypoints.py`

Details:

- Socket.IO now defaults to same-origin browser access.
- Cross-origin browser access requires an explicit `ORACLE_GUI_CORS_ORIGINS` allowlist.
- Wildcard `*` is ignored unless `ORACLE_GUI_ALLOW_ANY_ORIGIN=true` is also set.

Impact:

- Broad browser-origin trust increases the chance of cross-origin abuse against authenticated browser sessions and widens the attack surface for event endpoints.

Recommended fix:

- Completed: restricted allowed origins to an explicit environment-driven allowlist.

### 6. Medium: GUI security headers and rate limiting fail open when optional packages are missing

Status: remediated in owned surface

Evidence:

- `gui/app.py`
- `tests/test_http_entrypoints.py`

Details:

- Baseline browser security headers are now applied directly in `after_request`, even if `flask_talisman` is missing.
- The GUI now uses an in-process fallback rate limiter when `flask_limiter` is absent.

Impact:

- Production deployments can lose security headers and rate limiting without a hard failure, leaving operators with a false sense of coverage.

Recommended fix:

- Completed: direct security headers and fallback rate limiting prevent a silent fail-open path.

### 7. Medium: GUI HTTPS enforcement is miswired

Status: remediated

Evidence:

- `gui/app.py`

Details:

- The parsed HTTPS flag is now persisted into `app.config["FORCE_HTTPS"]` before middleware initialization.
- `SESSION_COOKIE_SECURE` and Talisman redirect enforcement now use the same parsed flag.

Impact:

- Operators can reasonably believe HTTPS redirect enforcement is active when it is not.

Recommended fix:

- Completed: HTTPS settings are now wired through a shared parsed flag.

### 8. Low: Verification helpers still carry weak placeholder secret defaults

Status: remediated

Evidence:

- `tests/verify_oracle_simple.py:14`
- `tests/verify_oracle_simple.py:18`
- `tests/verify_oracle_integration.py:16`
- `tests/verify_oracle_integration.py:20`
- `tests/test_query.py:10`
- `tests/verify_oracle_fixed.py`

Details:

- Verification helpers now use empty defaults and fail fast when required secrets are unset.

Impact:

- This is mostly operational drift, but it normalizes weak secret handling and can leak into copied deployment snippets.

Recommended fix:

- Completed: replaced placeholder defaults with explicit failure paths.

## Notes

- The current GUI markdown path is sanitizing parsed markdown with DOMPurify:
  - `gui/templates/index.html:12`
  - `gui/static/js/app.js:1042-1043`
- `src/oracle/main.py` currently enforces API-key checks on `/webhook` and `/chat`; this was reviewed and is not an active auth gap in the current snapshot.

## Owned-Surface Changes Applied

- Replaced legacy pickle-backed persistence with JSON-safe serialization in `infrastructure/oracle_storage.py`.
- Removed shell-string execution from `scripts/validate_production.py`.
- Removed insecure/default secret examples from `.env.example`.
- Required explicit broker/database passwords in `infrastructure/docker-compose.yml`.
- Made public Cloud Run invocation opt-in in `infrastructure/deploy.tf`.
- Rewrote `SECURITY.md` to reflect the actual repo posture and point to this report.
