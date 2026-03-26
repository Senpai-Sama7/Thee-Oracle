# Oracle Agent Platform - Codebase Intelligence Scaffold

This file is the primary preload context for AI coding agents working in `/home/donovan/Projects/replit`.
Use it as the source of truth before trusting `README.md`, marketing docs, or older architecture notes.

## Reality Check

- This workspace is a snapshot, not a live git checkout. `.git/` is absent.
- The repo contains both hardened runtime code and older prototype modules. Do not assume every `src/oracle/*.py` file follows the same quality bar.
- Verified on 2026-03-26:
  - `pytest -q` -> `125 passed, 2 warnings`
  - `mypy src/oracle orchestrator.py` -> clean
  - `ruff check .` -> clean
  - `python3 demo.py` -> successful smoke run
  - `python3 -m compileall src/oracle personal_agent email_worker interfaces gui skills orchestrator.py main.py demo.py` -> clean
  - `python3 -c "import gui.app"` -> clean, with graceful fallback if optional Flask security packages are absent
- `ruff check .` is clean because `pyproject.toml` excludes non-runtime comparison, audit, and validation scripts from the maintained lint target.
- The strictest, most production-like code is concentrated in:
  - `src/oracle/agent_system.py`
  - `src/oracle/model_router.py`
  - `src/oracle/tool_registry.py`
  - `src/oracle/skill_loader.py`
  - `src/oracle/mcp_client.py`
  - `src/oracle/mcp_registry.py`
  - `orchestrator.py`
- The weakest / partially prototype code is concentrated in:
  - `src/oracle/workflow_engine.py`
  - `src/oracle/plugin_system.py`
  - `src/oracle/integration_framework.py`
  - `src/oracle/agent_collaboration.py`
  - `src/oracle/code_generator.py`
  - parts of `src/oracle/agent_graph.py`

## Stage 1: Topology Map (Macro Layer)

### High-signal directories

```text
src/oracle/                Core runtime modules
orchestrator.py            Shared orchestration primitives used across subsystems
skills/                    Dynamic skill modules discovered at runtime
tests/                     Main automated test suite
personal_agent/            Separate FastAPI-style service using orchestrator primitives
email_worker/              RabbitMQ email consumer / SMTP sender
gui/                       Flask + Socket.IO web UI
interfaces/messaging/      Slack / Telegram / Discord adapters
config/                    Example model-chain and MCP server configs
infrastructure/            Docker Compose, Terraform, metrics helpers
docs/                      Project docs, roadmaps, older audit notes
data/                      SQLite databases and sample data
```

### Low-signal or mostly archival paths

Ignore these unless the task explicitly targets them:

- `archive/`
- `docs/archive/`
- `venv/`
- `.venv/`
- `.mypy_cache/`
- `.pytest_cache/`
- `__pycache__/`
- generated reports and image artifacts in the repo root

### Important root-level entry points

- `main.py`
  - Interactive production-style CLI wrapper around `OracleAgent`
  - Starts the standalone health check HTTP server on port `8080`
- `demo.py`
  - Credential-free tool and persistence smoke demo
- `src/oracle/main.py`
  - FastAPI webhook/chat service wrapping `OracleAgent`
- `personal_agent/main.py`
  - Separate service with its own rate limiting, circuit breakers, and persistence
- `gui/app.py`
  - Flask GUI backend

## Stage 2: Module Decomposition (Meso Layer)

### A. Core Oracle runtime

#### `src/oracle/agent_system.py`

Main stateful agent implementation.

- `OracleConfig` at line 85
  - Reads model, GCP, timeout, MCP, and skill settings from env
  - Important caveat: despite docs mentioning `ORACLE_PROJECT_ROOT`, the code currently hardcodes `project_root` to the repository root via `Path(__file__).parent.parent.parent.resolve()`
- `PersistenceLayer` at line 121
  - SQLite WAL storage for session history and task logs
- `HistorySerializer` at line 194
  - Preserves Gemini `thought_signature` bytes via Pydantic JSON serialization
- `ToolExecutor` at line 231
  - Built-in tool surface: `shell_execute`, `vision_capture`, `file_system_ops`, `http_fetch`
- `OracleAgent` at line 450
  - Direct Gemini client path
  - Optional ModelRouter path
  - Optional MCP and skill registry path
  - `backup_to_gcs()` at line 587
  - `_build_config()` at line 599
  - `run_async()` at line 774
  - `_dispatch()` at line 892
  - `run()` at line 940

#### `src/oracle/model_router.py`

Multi-provider LLM abstraction and failover layer.

- `GenerateConfig` at line 46
- `CostTracker` at line 196
- `GeminiAdapter` at line 429
- `OpenAIAdapter` at line 668
- `AnthropicAdapter` at line 863
- `OllamaAdapter` at line 1085
- `ModelRouter` at line 1306
- Factory functions:
  - `create_provider_from_config()` at line 1559
  - `create_router_from_config()` at line 1587

Important caveats:

- The router is optional. `OracleAgent` only uses it when `ORACLE_USE_MODEL_ROUTER=true`.
- Provider priority in `config/model_chain*.yaml` is not actually attached to adapter instances, so `priority` sorting is effectively inert.
- Env interpolation in `create_router_from_config()` only handles `${VAR}` literally. Example syntax like `${GCP_LOCATION:-us-central1}` is not truly expanded.

#### `orchestrator.py`

This is the cleanest shared systems module in the repo. It is not just support code; several other subsystems build on it.

- `TaskStatus` at line 57
- `Task` at line 150
- `ResultStore` at line 228
- `AsyncTokenBucket` at line 315
- `RecurringScheduler` at line 437
- `WorkflowController` at line 506
- `apply_priority_inheritance()` at line 580
- `CircuitBreaker` at line 628
- `CircuitBreakerStore` at line 694
- `MetricsRegistry` at line 817
- `PrometheusExporter` at line 860
- `QuiescenceLatch` at line 949

Use this file as the style reference for:

- type-annotated dataclasses
- explicit state transitions
- small focused abstractions
- SQLite WAL-backed persistence

### B. Tooling, MCP, and skill composition

#### `src/oracle/tool_registry.py`

Unified dispatch surface for built-in, MCP, and skill tools.

- `ToolRegistry` at line 28
- `initialize()` at line 139
- `get_function_declarations()` at line 212
- `dispatch()` at line 220

#### `src/oracle/skill_loader.py`

Dynamic discovery and validation for `skills/*.py`.

- `SkillToolDef` at line 22
- `SkillLoader` at line 71
- `load_all()` at line 93

Key behaviors:

- scans only `*.py` in the configured skills directory
- rejects non-callable handlers
- prefixes conflicting skill tool names with `skill_name__`
- attempts `setup()` and `teardown()` hooks
- includes permission hardening against world-writable skill files/directories

#### `src/oracle/mcp_client.py`

MCP transport manager.

- `MCPClient` at line 51
- `initialize()` at line 75
- `connect_all()` at line 195
- `call_tool()` at line 303

Key behaviors:

- supports `stdio` and `sse`
- auto-creates an example config if the configured MCP config file is missing
- tracks unavailable servers
- preserves stdio context managers keyed by server name to avoid collisions

#### `src/oracle/mcp_registry.py`

Schema translation layer from MCP tool definitions into Gemini function declarations.

- `MCPRegistry` at line 26
- `build_registry()` at line 47
- `dispatch()` at line 165

### C. Operational and auxiliary services

#### `src/oracle/health_check.py`

Standalone `HTTPServer`-based health/metrics/status service.

- `HealthCheckHandler` at line 22
- `/health` handler at line 53
- `/metrics` handler at line 81
- `/status` handler at line 89

#### `src/oracle/gcs_storage.py`

GCS upload/download/list/backup helper.

- `GCSStorageManager` at line 24

#### `src/oracle/knowledge_worker.py`

RabbitMQ consumer that calls Discovery Engine search.

- `load_env()` at line 11
- `start_worker()` at line 105

Notes:

- This file uses env-based RabbitMQ credentials correctly.
- It is separate from the email worker used by `personal_agent`.

#### `src/oracle/interface_adapter.py`

Channel-agnostic message bus and protocol types.

- `Attachment`, `InboundMessage`, `OutboundMessage`
- `InterfaceBus` at line 47

#### `interfaces/messaging/*.py`

Slack, Telegram, and Discord adapters that stream incremental model output using `StreamChunk`.

### D. Parallel subsystem: Personal Agent

This is a real subsystem, but it is distinct from `OracleAgent`.

#### `personal_agent/main.py`

- FastAPI app with `/health` and `/metrics`
- uses `ResultStore`, `CircuitBreaker`, `CircuitBreakerStore`, and `AsyncTokenBucket`
- defines its own `check_calendar` and `send_email` tool declarations

Important caveat:

- default `RABBITMQ_URL` includes a hardcoded local-dev credential string: `amqp://admin:oracle_pass_2026@localhost:5672/`

#### `email_worker/main.py`

- RabbitMQ consumer for queued email delivery via SMTP
- persists task state through `ResultStore`

Important caveat:

- also defaults `RABBITMQ_URL` to the same hardcoded local-dev credential string

### E. GUI subsystem

#### `gui/app.py`

- Flask + Socket.IO wrapper around `OracleAgent`
- security middleware via `flask_talisman`
- rate limiting via `flask_limiter`
- config mutation endpoint writes back into `.env`
- if `flask_talisman` or `flask_limiter` are missing, the module now falls back to no-op implementations so imports and basic routes still work

## Stage 3: Deep File Scan (Micro Layer)

### Runtime flows that matter

#### Direct OracleAgent flow

`main.py` -> `OracleAgent()` -> `OracleAgent.run()` -> Gemini `generate_content()` -> optional tool dispatch -> SQLite history save

This is the default path unless the async ModelRouter path is explicitly used.

#### Async OracleAgent flow

`OracleAgent.run_async()` only activates the multi-provider stack if:

- `MODEL_ROUTER_AVAILABLE` import succeeds
- `ORACLE_USE_MODEL_ROUTER=true`
- router config can actually instantiate providers

#### Tool dispatch flow

`OracleAgent._dispatch()` ->

- `ToolRegistry.dispatch()` when registry exists
- otherwise built-in `ToolExecutor` methods directly

#### MCP flow

`OracleAgent._init_tool_registry()` ->

- `MCPClient`
- `MCPRegistry`
- `SkillLoader`
- `ToolRegistry`

Important caveat:

- `_init_tool_registry()` calls `asyncio.run(...)` inside `OracleAgent.__init__`. That is acceptable in synchronous startup contexts but hostile inside an already-running event loop.

### Critical invariants

#### Conversation persistence

- session history stored in `data/oracle_core.db`
- serialized with JSON, not pickle
- intended to preserve Gemini thought signatures across resumed tool-using sessions

#### Tool response bundling

`OracleAgent.run()` consolidates all tool results from one model turn into a single `types.Content(role="tool", parts=[...])`.

This is correct for Gemini function-calling semantics. Do not refactor it into one content turn per tool call.

#### Filesystem sandbox

`ToolExecutor.file_system_ops()` uses:

- `(project_root / path).resolve()`
- `Path.is_relative_to(project_root)`

This is the main path traversal guard in the repo.

### Known mismatches between docs and code

- `README.md` and older docs overstate current production readiness.
- `pyproject.toml` targets Python `py311`, but the environment here is Python 3.13.
- `AGENTS.md` / `README.md` still overstate some subsystem maturity, but the maintained runtime path currently passes strict `mypy`.
- `ORACLE_PROJECT_ROOT` is documented but ignored by `OracleConfig`.
- `src/oracle/main.py` now correctly uses `agent.cfg.model_id` in `/health`.

### Known failing / fragile spots

#### `src/oracle/agent_graph.py`

- hardening tests now pass
- conditions are evaluated through a restricted AST-based path
- still treat this file as semi-hardened compared with `orchestrator.py` and `agent_system.py`

#### `src/oracle/workflow_engine.py`

Prototype module, not hardened:

- uses `subprocess.run(..., shell=True)`
- uses `requests.request(...)` synchronously
- uses raw `eval(condition, {}, context)`

Prefer `orchestrator.py` and `src/oracle/agent_graph.py` over this file when implementing workflow behavior.

#### Hardcoded local-dev credentials still present

- `personal_agent/main.py`
- `email_worker/main.py`
- several verification tests also contain the same local credential string

## Stage 4: Relationship & Dependency Graph

### Primary dependency graph

```text
main.py
  -> src/oracle/agent_system.py:OracleAgent
     -> PersistenceLayer
     -> ToolExecutor
     -> optional ToolRegistry
        -> SkillLoader
        -> MCPRegistry
           -> MCPClient
     -> optional ModelRouter
        -> GeminiAdapter / OpenAIAdapter / AnthropicAdapter / OllamaAdapter
     -> optional GCSStorageManager

src/oracle/main.py
  -> OracleAgent

gui/app.py
  -> OracleAgent

personal_agent/main.py
  -> orchestrator.ResultStore
  -> orchestrator.AsyncTokenBucket
  -> orchestrator.CircuitBreaker
  -> RabbitMQ
  -> email_worker/main.py

src/oracle/knowledge_worker.py
  -> RabbitMQ
  -> Discovery Engine API
```

### Conceptual entities

- Agent core: `OracleAgent`
- Tool execution layer: `ToolExecutor`, `ToolRegistry`
- Dynamic extension layer: `SkillLoader`, `MCPClient`, `MCPRegistry`
- Model abstraction layer: `ModelRouter` and provider adapters
- Persistence layer: `PersistenceLayer`, `ResultStore`, `CircuitBreakerStore`
- Observability layer: `HealthCheckHandler`, `MetricsRegistry`, `PrometheusExporter`
- Communication layer: `InterfaceBus`, messaging adapters, `A2AProtocol`

### Duplicate or overlapping concepts

Be explicit about which implementation you are editing:

- Workflow logic exists in both `orchestrator.py` and `src/oracle/workflow_engine.py`
- Agent/webhook services exist in both `src/oracle/main.py` and `personal_agent/main.py`
- Messaging / async worker behavior exists in both `src/oracle/knowledge_worker.py` and `email_worker/main.py`

## Stage 5: System Intelligence Report

### Architecture details

Use this mental model:

1. `OracleAgent` is the center of the main system.
2. `ToolExecutor` is the trusted built-in side-effect surface.
3. `ToolRegistry` is the extension composition layer.
4. `ModelRouter` is optional and not the default runtime path.
5. `orchestrator.py` is the shared systems toolkit used by nontrivial side subsystems.
6. Several other modules are sketches, integration shells, or partially hardened experiments.

### Coding conventions

Strongest conventions, as actually practiced in the better modules:

- dataclass-heavy modeling for state objects
- structured response envelopes like `{success: bool, ...}`
- SQLite WAL for persistence
- async at subsystem boundaries, sync in simple local helpers
- explicit environment-variable configuration
- narrow helper methods instead of giant utility classes

Conventions that are claimed in docs but not universal in code:

- full `mypy --strict` compliance
- uniformly hardened security posture
- no hardcoded local dev credentials

### Testing requirements

Before claiming a system-wide change is safe, prefer:

```bash
pytest -q
pytest tests/test_model_router.py -q
pytest tests/test_mcp_integration.py -q
pytest tests/test_hardening.py -q
mypy src/oracle orchestrator.py
```

Current observed status:

- `pytest -q` is green at `125 passed, 2 warnings`
- the 2 warnings are external deprecation warnings from `google._upb._message`
- `mypy src/oracle orchestrator.py` is green
- `ruff check .` is green after scoping non-runtime comparison/audit scripts out of the maintained lint target

If you touch:

- `src/oracle/agent_system.py`: rerun `tests/test_tool_execution_flow.py` and relevant persistence/hardening tests
- `src/oracle/model_router.py`: rerun `tests/test_model_router.py` and `tests/test_hardening.py`
- `src/oracle/skill_loader.py` or MCP code: rerun `tests/test_mcp_integration.py`
- `src/oracle/main.py`, `personal_agent/main.py`, or `gui/app.py`: rerun `tests/test_http_entrypoints.py`
- `orchestrator.py`: rerun the orchestration-focused tests:
  - `tests/test_core.py`
  - `tests/test_async.py`
  - `tests/test_workflow.py`
  - `tests/test_scheduler.py`
  - `tests/test_priority.py`
  - `tests/test_result_store.py`
  - `tests/test_circuit_breaker.py`
  - `tests/test_prometheus.py`
  - `tests/test_quiescence.py`

### Preferred tools and commands

Use fast local inspection first:

```bash
rg --files
rg -n "class OracleAgent|def run\\(" src/oracle/agent_system.py
rg -n "class ModelRouter|class GeminiAdapter" src/oracle/model_router.py
rg -n "class ResultStore|class CircuitBreaker" orchestrator.py
pytest -q
mypy src/oracle orchestrator.py
ruff check .
ruff format .
```

### Style guidelines for future edits

- Follow `orchestrator.py` style when introducing new shared abstractions.
- Follow `src/oracle/agent_system.py` style when changing agent runtime behavior.
- Prefer structured error returns over uncaught exceptions in tool surfaces.
- Avoid copying patterns from `src/oracle/workflow_engine.py`, `plugin_system.py`, or `integration_framework.py` unless you are explicitly refactoring those files.
- If you add a tool:
  - update declarations and dispatch consistently
  - keep the response envelope structured
  - think about persistence and observability, not just execution

### Semantic code analysis features

#### Best symbol search targets

- `OracleAgent`
- `ToolExecutor`
- `PersistenceLayer`
- `HistorySerializer`
- `ToolRegistry`
- `SkillLoader`
- `MCPClient`
- `MCPRegistry`
- `ModelRouter`
- `GeminiAdapter`
- `ResultStore`
- `CircuitBreaker`
- `WorkflowController`
- `HealthCheckHandler`

#### Useful search commands

```bash
rg -n "class OracleAgent|def run_async|def _dispatch|def run\\(" src/oracle/agent_system.py
rg -n "class GeminiAdapter|class OpenAIAdapter|class AnthropicAdapter|class ModelRouter" src/oracle/model_router.py
rg -n "class ToolRegistry|def dispatch" src/oracle/tool_registry.py
rg -n "class SkillLoader|def load_all" src/oracle/skill_loader.py
rg -n "class MCPClient|def call_tool" src/oracle/mcp_client.py
rg -n "class ResultStore|class CircuitBreaker|class WorkflowController" orchestrator.py
rg -n "shell=True|eval\\(|oracle_pass_2026" src/oracle personal_agent email_worker
```

#### Diagnostics to keep in mind

- If a task involves Gemini tool calling and session persistence, inspect `HistorySerializer` first.
- If a tool exists in docs but not at runtime, inspect `ToolRegistry.initialize()` and `SkillLoader.load_all()`.
- If model failover is not happening, verify `ORACLE_USE_MODEL_ROUTER`, router config loading, and actual provider instantiation.
- If workflow conditions misbehave, inspect `src/oracle/agent_graph.py` before touching `src/oracle/workflow_engine.py`.
- If a service wrapper breaks on startup or health checks, compare the wrapper's expected agent API against `OracleAgent` fields (`cfg`, not `config`).

## Practical Guidance For Future Agents

- Treat `src/oracle/agent_system.py` plus `orchestrator.py` as the architectural spine.
- Treat `model_router.py` as a real subsystem, but remember it is not the default execution path.
- Treat `personal_agent/` as a sibling subsystem, not just a thin wrapper.
- Treat docs in `docs/archive/` and older root markdown files as historical context, not current truth.
- When asked for a review, call out the split between hardened core code and prototype modules explicitly.
