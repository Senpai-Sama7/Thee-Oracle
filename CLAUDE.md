# Oracle Agent Platform - Codebase Intelligence Scaffold

This file is preload context for AI coding agents working in `/home/donovan/Projects/replit`.
Use it as the code-grounded source of truth before trusting older docs, aspirational plans, or archived reports.

## Reality Check

- This is a real git checkout now; older notes claiming `.git/` is absent are stale.
- The repo is not uniform. It contains a hardened runtime path plus older prototype and research modules.
- Verified on 2026-03-26 from the repo root:
  - `pytest -q` -> `140 passed, 2 warnings`
  - `mypy src/oracle orchestrator.py` -> clean
  - `ruff check .` -> clean
- The two pytest warnings are external `google._upb._message` deprecation warnings, not repo failures.
- Highest-trust code paths are:
  - `src/oracle/agent_system.py`
  - `src/oracle/model_router.py`
  - `src/oracle/tool_registry.py`
  - `src/oracle/skill_loader.py`
  - `src/oracle/mcp_client.py`
  - `src/oracle/mcp_registry.py`
  - `orchestrator.py`
  - `gui/app.py`
- Lower-trust or more prototype-style modules are:
  - `src/oracle/workflow_engine.py`
  - `src/oracle/plugin_system.py`
  - `src/oracle/integration_framework.py`
  - `src/oracle/agent_collaboration.py`
  - `src/oracle/code_generator.py`
  - some graph/workflow code around `src/oracle/agent_graph.py`

## Stage 1: Topology Map (Macro Layer)

### Repo Shape

```text
src/oracle/                Core runtime, wrappers, adapters, storage, health, workflows
orchestrator.py            Shared orchestration primitives used by multiple subsystems
skills/                    Runtime-loaded skill modules
gui/                       Flask + Socket.IO web interface
personal_agent/            Separate FastAPI-based service and tool flow
email_worker/              RabbitMQ consumer that sends queued email via SMTP
interfaces/messaging/      Slack / Telegram / Discord adapters
tests/                     Maintained automated test suite
config/                    MCP and model-chain config examples
infrastructure/            Docker Compose, Terraform, storage helpers, monitoring support
docs/                      Mixed current docs and historical design material
data/                      SQLite databases and sample data
main.py                    Interactive CLI wrapper + health bootstrap
demo.py                    Credential-light smoke path
```

### Runtime Entry Points

- `main.py`
  - interactive CLI wrapper around `OracleAgent`
  - starts the standalone health server from `src/oracle/health_check.py`
- `demo.py`
  - smoke/demo path that exercises persistence and tools without full production setup
- `src/oracle/main.py`
  - FastAPI webhook/chat wrapper around `OracleAgent`
- `personal_agent/main.py`
  - separate FastAPI service with its own tool loop, rate limiter, and circuit breakers
- `email_worker/main.py`
  - RabbitMQ worker for async email delivery
- `gui/app.py`
  - Flask + Socket.IO frontend backend

### Trust Order For Navigation

1. Runtime code in `src/oracle/`, `orchestrator.py`, `gui/`, `personal_agent/`, `email_worker/`
2. Tests in `tests/`
3. Root docs: `README.md`, this file
4. Subsystem docs like `gui/README.md`
5. Historical docs in `docs/` and older audit artifacts

### Low-Signal Paths

Ignore unless the task explicitly targets them:

- `archive/`
- `docs/archive/`
- `venv/`, `.venv/`
- `.mypy_cache/`, `.pytest_cache/`, `__pycache__/`
- one-off comparison and audit scripts excluded by Ruff

## Stage 2: Module Decomposition (Meso Layer)

### A. Core Agent Runtime

#### `src/oracle/agent_system.py`

Primary runtime spine.

- `OracleConfig` at line 85
  - reads env config
  - resolves `ORACLE_PROJECT_ROOT`
  - resolves relative MCP, skills, and model-chain paths against `project_root`
- `PersistenceLayer` at line 133
  - SQLite WAL persistence for history and task logs
- `HistorySerializer` at line 206
  - uses Pydantic JSON-mode conversion instead of pickle
- `ToolExecutor` at line 243
  - built-in tools: `shell_execute`, `vision_capture`, `file_system_ops`, `http_fetch`
- `OracleAgent` at line 472
  - owns config, persistence, model client/router, MCP, skills, and the ReAct loop

Operational facts:

- `ToolExecutor.http_fetch()` rejects non-HTTP(S) URLs.
- file operations stay under `ORACLE_PROJECT_ROOT`.
- built-in shell execution uses `subprocess.run([...])` with `bash -c`, not `shell=True`.
- `OracleAgent` can run either direct Gemini or `ModelRouter` depending on env/config.

#### `src/oracle/model_router.py`

Multi-provider abstraction and failover layer.

- `GenerateConfig` at line 46
- `GeminiAdapter` at line 429
- `OpenAIAdapter` at line 668
- `AnthropicAdapter` at line 863
- `OllamaAdapter` at line 1085
- `ModelRouter` at line 1306
- `create_provider_from_config()` at line 1559
- `create_router_from_config()` at line 1587

Important behavior:

- router use is optional; `OracleAgent` only uses it when enabled
- tracks provider health, token usage, and estimated cost
- supports failover and streaming chunk normalization
- env interpolation in model-chain config is simple `${VAR}` replacement, not full shell-style expansion

### B. Tool and Capability Composition

#### `src/oracle/tool_registry.py`

Unified tool dispatch across built-ins, MCP, and skills.

- `ToolRegistry` at line 28
- aggregates schemas/declarations for Gemini-compatible tool calling
- central async `dispatch()` decides whether a call is built-in, MCP-backed, or skill-backed

#### `src/oracle/skill_loader.py`

Dynamic skill loader for `skills/*.py`.

- `SkillToolDef` at line 22
- `SkillLoader` at line 71

Behavior:

- scans configured skills dir for legacy Python modules and `SKILL.md` package skills
- expects a module-level `TOOLS` list
- package skills may be instruction-only and still participate in prompt-time selection
- validates callables and schema shape
- prefixes name collisions with `skill_name__...`
- supports optional `setup()` / `teardown()`
- refuses world-writable skill files/directories

#### `src/oracle/mcp_client.py`

Transport manager for configured MCP servers.

- `MCPClient` at line 51
- supports `stdio` and `sse`
- can create an example config when no config file exists
- tracks unavailable servers and stdio contexts by server key

#### `src/oracle/mcp_registry.py`

Registry/translation layer from MCP tool schema to model-facing declarations.

- `MCPRegistry` at line 26
- builds a merged registry and exposes async dispatch

### C. Orchestration and Shared Primitives

#### `orchestrator.py`

This is the cleanest shared systems module and the best reference for repo coding style.

- `TaskStatus` at line 57
- `Task` at line 150
- `ResultStore` at line 228
- `AsyncTokenBucket` at line 315
- `WorkflowController` at line 506
- `CircuitBreaker` at line 628
- `CircuitBreakerStore` at line 694
- `MetricsRegistry` at line 817
- `PrometheusExporter` at line 860
- `QuiescenceLatch` at line 949

This file is the actual source of truth for:

- task lifecycle
- WAL-backed result persistence
- circuit breaker state
- rate limiting
- metrics export

### D. Service Wrappers and Frontends

#### `src/oracle/main.py`

FastAPI wrapper around `OracleAgent`.

- endpoints: `POST /webhook`, `POST /chat`, `GET /health`
- optional API key protection via `WEBHOOK_API_KEY`
- bridges standard Google env vars into `OracleConfig`
- still has permissive CORS for localhost frontend dev origins only

#### `personal_agent/main.py`

Separate service; not just a thin alias for `OracleAgent`.

- uses `AsyncTokenBucket`, `CircuitBreaker`, `CircuitBreakerStore`, `ResultStore`
- exposes `POST /webhook`, `POST /chat`, `GET /health`, `GET /metrics`
- has its own tool declarations like `check_calendar` and `send_email`
- `send_email` now fails closed when `RABBITMQ_URL` is unset

#### `email_worker/main.py`

Background RabbitMQ SMTP sender.

- consumes `email_tasks`
- persists task state via `ResultStore`
- tracks retries and dead-letter behavior
- requires `RABBITMQ_URL`; no guessed local credentials remain

#### `gui/app.py`

Flask + Socket.IO frontend backend.

Key runtime traits:

- uses `AppState` instead of mutable module-global config/agent drift
- falls back gracefully if `flask_talisman` or `flask_limiter` are not installed
- applies baseline security headers even in fallback mode
- protects config/settings endpoints with `ORACLE_API_KEY`
- requires authenticated Socket.IO connections when `ORACLE_API_KEY` is set
- limits direct browser-triggered tools to:
  - `shell_execute`
  - `file_system_ops`
  - `http_fetch`
  - `vision_capture`
- defaults to same-origin Socket.IO unless `ORACLE_GUI_CORS_ORIGINS` is explicitly set
- defaults bind host to `127.0.0.1`

### E. Workflow / Prototype Layer

#### `src/oracle/agent_graph.py`

Graph/workflow execution model with node abstractions and a workflow engine.

Current important fact:

- workflow conditions no longer use raw `eval`; they use the shared restricted AST evaluator from `src/oracle/safe_expression.py`

#### `src/oracle/workflow_engine.py`

Simpler workflow/prototype engine.

Current important facts:

- also uses the restricted AST evaluator
- validates absolute HTTP(S) URLs for API actions
- still shells out for shell steps; treat as lower-trust operational code than `agent_system.py` and `orchestrator.py`

## Stage 3: Deep File Scan (Micro Layer)

### High-Signal Files To Read First

1. `src/oracle/agent_system.py`
2. `src/oracle/model_router.py`
3. `orchestrator.py`
4. `src/oracle/tool_registry.py`
5. `src/oracle/skill_loader.py`
6. `src/oracle/mcp_client.py`
7. `src/oracle/mcp_registry.py`
8. `gui/app.py`
9. `src/oracle/main.py`
10. `personal_agent/main.py`
11. `email_worker/main.py`
12. `tests/test_http_entrypoints.py`
13. `tests/test_hardening.py`
14. `tests/test_backend_security_guards.py`

### File-Level Intelligence

#### `src/oracle/agent_system.py`

What matters most:

- config resolution and path sandboxing
- `PersistenceLayer` SQLite schema and WAL mode
- `HistorySerializer` JSON-safe conversion path
- `ToolExecutor` security boundaries
- `OracleAgent.run_async()` and `OracleAgent.run()` loop behavior
- `_dispatch()` integration with `ToolRegistry`

Questions this file answers:

- where session history lives
- how tool calls are executed and normalized
- how GCS backup is triggered
- whether the model path is direct Gemini or router-backed

#### `src/oracle/model_router.py`

What matters most:

- provider protocol and normalized response types
- failover behavior
- streaming normalization through `StreamChunk`
- config loading and provider construction

Questions this file answers:

- how providers are selected and retried
- how token usage and cost are recorded
- where streaming behavior differs by vendor

#### `orchestrator.py`

What matters most:

- task state transitions
- retry semantics
- circuit breaker behavior
- persistence guarantees
- metrics shape

Questions this file answers:

- how async work is tracked
- how subsystems persist state consistently
- which primitives the personal-agent and worker flows reuse

#### `gui/app.py`

What matters most:

- auth gates
- CORS/origin behavior
- Socket.IO event handlers
- settings/config update flow
- fallback security headers and rate limiting

Questions this file answers:

- what the browser is allowed to trigger directly
- whether the GUI is safe to expose remotely by default
- how frontend state maps back to `OracleAgent`

#### `tests/test_http_entrypoints.py`

Most useful current black-box coverage map.

It validates:

- `src/oracle.main` webhook/chat/health
- `personal_agent.main` webhook/chat/health
- `gui.app` status, health, help, config, settings auth, and socket auth/tool guards

#### `tests/test_hardening.py`

Security regression suite for:

- restricted workflow condition evaluation
- knowledge worker env parsing
- model-router stream/failover behavior
- MCP stdio context collision protections

#### `tests/test_backend_security_guards.py`

Fast security regression suite for:

- `http_fetch` URL scheme restrictions
- API key enforcement in wrappers
- integration URL validation
- unsafe workflow eval blocking

### Supporting Files Worth Checking When Relevant

- `src/oracle/safe_expression.py`
  - shared restricted AST evaluator used by both workflow engines
- `src/oracle/health_check.py`
  - standalone monitoring endpoints
- `src/oracle/gcs_storage.py`
  - GCS persistence helper
- `interfaces/messaging/*.py`
  - channel adapters
- `.env.example`
  - current runtime variable map
- `pyproject.toml`
  - actual mypy, Ruff, and pytest settings

## Stage 4: Relationship & Dependency Graph

### Runtime Relationship Graph

```text
User / API / Browser
  -> main.py / src/oracle.main / personal_agent.main / gui.app
  -> OracleAgent (src/oracle/agent_system.py)
  -> ToolRegistry
     -> ToolExecutor built-ins
     -> MCPRegistry -> MCPClient -> external MCP servers
     -> SkillLoader -> skills/*.py handlers
  -> direct Gemini client OR ModelRouter
     -> Gemini / OpenAI / Anthropic / Ollama adapters
  -> PersistenceLayer (SQLite)
  -> optional GCSStorageManager
```

### Cross-Subsystem Graph

```text
orchestrator.py
  -> reused by personal_agent/main.py
  -> reused by email_worker/main.py
  -> conceptually overlaps with workflow logic in src/oracle/agent_graph.py

personal_agent/main.py
  -> publishes email tasks to RabbitMQ
  -> email_worker/main.py consumes those tasks
  -> both persist through ResultStore

gui/app.py
  -> wraps OracleAgent directly
  -> does not own separate orchestration primitives
  -> exposes browser-side trigger path into a tool allowlist
```

### Security Boundary Graph

```text
Browser
  -> gui/app.py routes + Socket.IO auth
  -> allowed direct tools only
  -> OracleAgent tool path

Webhook clients
  -> src/oracle.main or personal_agent.main
  -> optional API-key dependency
  -> OracleAgent or personal-agent flow

OracleAgent
  -> file sandbox at ORACLE_PROJECT_ROOT
  -> HTTP fetch limited to absolute HTTP(S)
  -> subprocess execution via ToolExecutor

RabbitMQ
  -> personal_agent publishes
  -> email_worker consumes
  -> credentials come from env only
```

### Semantic Coupling Notes

- `OracleAgent` is the center of the main runtime knowledge graph.
- `orchestrator.py` is the center of the async job/control-plane knowledge graph.
- `gui/app.py`, `src/oracle/main.py`, and `personal_agent/main.py` are wrapper surfaces, not the core reasoning engine.
- `safe_expression.py` is the shared security hinge between the two workflow engines.

## Stage 5: System Intelligence Report

### Architecture Details

- Primary pattern: layered service architecture with a hardened ReAct-style agent loop.
- Main control path: prompt/input -> model response -> tool dispatch -> tool results -> iterative continuation -> final response.
- Capability composition is modular:
  - built-in tools from `ToolExecutor`
  - external tools from MCP
- local tools from `skills/`
- prompt-time skill instructions from `SKILL.md` package skills
- The repo has parallel product surfaces:
  - `OracleAgent` runtime
  - `personal_agent` service flow
  - GUI browser wrapper
  - messaging adapters
  - background email worker
- `orchestrator.py` provides the strongest reusable control-plane abstractions in the repo.

### Coding Conventions

Follow what the maintained code already does:

- Python 3.11+ typing everywhere
- `from __future__ import annotations` in modern modules
- dataclasses for compact state containers
- explicit `dict[str, Any]` / `list[str]` style annotations
- structured results instead of raising through tool boundaries
- SQLite WAL for local persistence
- env-driven config, not checked-in secrets
- logging through module loggers, not print-heavy production paths

### Testing Requirements

Before trusting a runtime-affecting change, run:

```bash
pytest -q
ruff check .
mypy src/oracle orchestrator.py
```

Focused reruns:

```bash
pytest -q tests/test_http_entrypoints.py
pytest -q tests/test_hardening.py
pytest -q tests/test_backend_security_guards.py
```

Use targeted reruns when editing:

- `gui/app.py` -> `tests/test_http_entrypoints.py`
- `src/oracle/agent_system.py` -> `tests/test_backend_security_guards.py` plus core smoke tests
- `src/oracle/model_router.py` -> `tests/test_hardening.py`, `tests/test_model_router.py`
- `personal_agent/main.py` or `email_worker/main.py` -> `tests/test_http_entrypoints.py` and any worker-specific tests

### Preferred Tools / Commands

Repo-root commands:

```bash
pytest -q
ruff check .
mypy src/oracle orchestrator.py
python3 demo.py
python3 -m compileall src/oracle personal_agent email_worker interfaces gui skills orchestrator.py main.py demo.py
python3 -c "import gui.app; print('gui.app import ok')"
```

Search/navigation:

```bash
rg -n "class OracleAgent|class ToolExecutor|class ModelRouter|class SkillLoader" src/oracle orchestrator.py gui personal_agent email_worker
rg -n "def run_async|def _dispatch|def dispatch|def load_all|def call_tool" src/oracle orchestrator.py
rg --files src/oracle gui personal_agent email_worker tests
```

### Style Guidelines

- Prefer direct, narrow abstractions over meta-framework layers.
- Keep side effects at the edges: wrappers, workers, storage helpers, adapters.
- Preserve structured error envelopes on tool boundaries.
- Preserve path, URL, and auth validation that already exists.
- When touching security-sensitive wrappers, keep defaults fail-closed and loopback-bound unless explicitly configured otherwise.
- Use `orchestrator.py` and the hardened runtime modules as style references, not older prototype files.

### Semantic Code Analysis Features

#### Symbol Search Targets

High-value symbols:

- `OracleConfig`
- `PersistenceLayer`
- `HistorySerializer`
- `ToolExecutor`
- `OracleAgent`
- `ModelRouter`
- `GenerateConfig`
- `ToolRegistry`
- `SkillLoader`
- `MCPClient`
- `MCPRegistry`
- `WorkflowController`
- `CircuitBreaker`
- `ResultStore`
- `AsyncTokenBucket`
- `AppState`

#### Reference Hotspots

- tool dispatch flow:
  - `OracleAgent._dispatch()`
  - `ToolRegistry.dispatch()`
  - `MCPRegistry.dispatch()`
- model selection flow:
  - `OracleAgent` router setup
  - `create_router_from_config()`
  - adapter classes in `model_router.py`
- workflow safety flow:
  - `safe_expression.py`
  - `agent_graph.py`
  - `workflow_engine.py`
- GUI auth/tool flow:
  - `require_auth`
  - `socket_request_authorized`
  - Socket.IO `execute_tool` handler in `gui/app.py`

#### Definitions / Diagnostics Heuristics

When debugging:

- import/config failures:
  - inspect `.env`, `.env.example`, `OracleConfig`, and wrapper env bridging
- tool execution failures:
  - inspect `ToolExecutor` and `ToolRegistry`
- MCP issues:
  - inspect `MCPClient` config path resolution and unavailable-server state
- skill issues:
  - inspect `SkillLoader.load_all()` and skill file permissions
- GUI/API auth issues:
  - inspect `ORACLE_API_KEY`, `WEBHOOK_API_KEY`, `PERSONAL_AGENT_API_KEY`, and wrapper auth dependencies
- workflow condition issues:
  - inspect `safe_expression.py` before assuming a generic eval bug

## Common Questions, Answered From The Current Code

### Where is the main agent loop?

`OracleAgent` in `src/oracle/agent_system.py`.

### Where are sessions and task logs stored?

SQLite through `PersistenceLayer` in `src/oracle/agent_system.py` and `ResultStore` in `orchestrator.py`.

### How are external tools added?

Through MCP config plus `MCPClient`/`MCPRegistry`, or through Python skill modules in `skills/` loaded by `SkillLoader`.

### What is the best file to copy style from?

`orchestrator.py` for systems code, then `src/oracle/agent_system.py` and `gui/app.py` for current runtime boundaries.

### Which files are wrappers versus core logic?

Wrappers: `main.py`, `src/oracle/main.py`, `personal_agent/main.py`, `gui/app.py`.
Core logic: `src/oracle/agent_system.py`, `src/oracle/model_router.py`, `orchestrator.py`, `src/oracle/tool_registry.py`.

### Which docs are safe to trust?

This file, `README.md`, and `gui/README.md` first. Treat older `docs/` material as historical until cross-checked against code.
