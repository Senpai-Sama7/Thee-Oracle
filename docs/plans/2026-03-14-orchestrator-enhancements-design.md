## Orchestrator Enhancements – Architecture & Design (2026-03-14)

### 1. Goals and Constraints

- **Primary goals**
  - Make the orchestrator core (`orchestrator.py`) the single source of truth for task lifecycle, rate limiting, scheduling, circuit breaking, and metrics.
  - Cleanly integrate the orchestrator with:
    - The **personal agent service** (`personal_agent/main.py`) that fronts Vertex AI.
    - The **RabbitMQ-based async pipeline** (`rabbitmq_demo` and email worker).
  - Maintain **strict typing** (Python 3.11+), good async hygiene, and observability (Prometheus-compatible).
- **Constraints**
  - Keep SQLite as the default local store; allow migration to external stores later.
  - Avoid breaking existing public APIs exported via `__all__` in `orchestrator.py`.
  - Keep the personal agent FastAPI app simple enough to deploy as a single service.

---

### 2. Current Architecture (High Level)

- **Core library – `orchestrator.py`**
  - Provides:
    - Typed dependencies: `Dependency`, `DependencyCondition`, `normalize_status`.
    - Result persistence: `ResultStore` (SQLite, WAL mode, thread-safe).
    - Rate limiting: `AsyncTokenBucket`.
    - Middleware: `MiddlewareContext`, `MiddlewareChain`.
    - Recurring tasks: `RecurringSpec`, `RecurringScheduler`.
    - Workflow control: `WorkflowController`, `apply_priority_inheritance`.
    - Circuit breaker persistence: `CircuitBreakerStore`, `PersistedCircuitBreaker`, `CircuitBreakerState`.
    - Metrics export: `PrometheusExporter`, `MetricSample`, `MetricsRegistryLike`.
    - Quiescence detection: `QuiescenceLatch`.
- **Personal agent – `personal_agent/main.py`**
  - FastAPI app exposing `/webhook`.
  - Calls Vertex AI Gemini 2.5 Flash with tools `check_calendar` and `send_email`.
  - Uses `ResultStore` and `CircuitBreakerStore` directly for simple persistence but does not yet use higher-level orchestration primitives (scheduling, workflows).
  - Sends emails by publishing to RabbitMQ with basic resiliency (now with retries and bounded timeouts).
- **RabbitMQ demo – `rabbitmq_demo`**
  - Simple publisher / consumer scripts used as examples.
  - Not yet wired into the orchestrator’s state model or metrics.

---

### 3. Orchestrator Core Enhancements

#### 3.1 Task Model & State Management

- **Option A (Recommended):** Keep `TaskLike` as a protocol and define a small concrete `Task` dataclass in a separate module (e.g., `task.py`) used by default executors and tests.
  - **Pros:** Backward compatible, existing callers that define their own task types remain valid. Easier to spin up reference implementations.
  - **Cons:** Adds one more type to the public surface.
- **Option B:** Replace `TaskLike` with a concrete `Task` class everywhere.
  - **Pros:** Simpler to reason about in a single project.
  - **Cons:** Breaking for users that already rely on custom task implementations and the protocol flexibility.
- **Decision:** **Option A** – introduce a concrete `Task` reference type without breaking the protocol, keeping the orchestrator library flexible but easier to adopt.

#### 3.2 Integrated Circuit-Breaker Orchestration

- **Option A (Recommended):** Provide a small helper API in `orchestrator.py`, e.g., `wrap_with_circuit_breaker(task_type, store, fn)` that:
  - Consults `CircuitBreakerStore` and `CircuitBreakerState`.
  - Applies open/half-open/closed logic with `probe_successes` thresholds.
  - Updates the store via `save` after each call.
- **Option B:** Leave circuit-breaking fully up to higher layers (e.g., FastAPI) using the persistence layer only.
- **Decision:** **Option A** – add a helper wrapper so services like the personal agent can easily guard external calls (Gemini, RabbitMQ, HTTP APIs) using consistent logic.

#### 3.3 Observability and Metrics

- **Planned improvements**
  - Standardize metric name prefixes for:
    - Task lifecycle: `orchestrator_task_status_*`, `orchestrator_task_latency_*`.
    - Rate limiter: `orchestrator_rate_limit_tokens`, `orchestrator_rate_limit_wait_seconds`.
    - Circuit breakers: `orchestrator_circuit_breaker_state`, `orchestrator_circuit_breaker_tripped_total`.
  - Provide helper functions that accept a `MetricsRegistryLike` and record events (instead of direct registry mutations sprinkled across the codebase).

---

### 4. Personal Agent Service Design

#### 4.1 Role of the Personal Agent

- Act as the **API surface** for conversational agents (Dialogflow CX / Agent Builder).
- Delegate:
  - LLM calls (Gemini 2.5 Flash) wrapped with:
    - Rate limiting via `AsyncTokenBucket`.
    - Circuit breaking via the helper based on `CircuitBreakerStore`.
  - Async side effects (e.g., emails) to RabbitMQ workers.
- Persist:
  - User interaction metadata (inputs, tags, image presence) via `ResultStore`.
  - Circuit breaker state via `CircuitBreakerStore`.

#### 4.2 Enhanced Webhook Flow

- **Request handling**
  - Parse standard fields (`text`, `sessionInfo`, `fulfillmentInfo.tag`, optional `image_base64`).
  - Normalize user/session IDs into trace IDs compatible with orchestrator logging and metrics.
- **LLM invocation**
  - Use an `AsyncTokenBucket` instance to guard per-service request rate.
  - Wrap `model.generate_content` in a circuit-breaker helper (per `task_type="gemini_generate"`).
  - On failure:
    - Distinguish between logical errors (bad input) and upstream issues (timeouts, 5xx).
    - Return user-safe error messages while logging full details.
- **Tool execution**
  - Treat each tool call (e.g., `send_email`) as a logical task with a `workflow_id` bound to the session.
  - Publish to RabbitMQ and record the task submission in `ResultStore` or a small task ledger table for tracking.

---

### 5. RabbitMQ / Async Pipeline Design

#### 5.1 Email Worker Role

- Dedicated worker service (or module) that:
  - Consumes from `RABBITMQ_QUEUE`.
  - Parses messages into typed commands: `{"type": "email", "to": ..., "subject": ..., "body": ...}`.
  - Sends emails via SMTP or an external provider API.
  - Reports outcomes:
    - Success: store result or metadata in `ResultStore`.
    - Failure: retry with backoff; on final failure, send to a dead-letter queue and/or mark the task as failed in orchestrator state.

#### 5.2 Orchestrator Integration

- **Option A (Recommended):** Treat each message as a task within the orchestrator domain model:
  - Use a `Task` instance with:
    - `id` = queue message ID.
    - `type` = `"send_email"`.
    - `workflow_id` = user session or conversation ID.
  - The worker updates task status (`COMPLETED` / `FAILED` / `DEAD_LETTER`) and persists via a small `TaskStoreLike` implementation.
- **Option B:** Keep RabbitMQ processing completely decoupled from orchestrator task concepts.
- **Decision:** **Option A** – makes workflows and email side effects observable and controllable (e.g., via `WorkflowController`).

---

### 6. Testing & Verification Strategy

- **Core orchestrator**
  - Extend existing tests to cover:
    - New `Task` reference type (if introduced).
    - Circuit-breaker helper wrapper behavior across CLOSED/OPEN/HALF_OPEN transitions.
    - Metrics helper functions producing `PrometheusExporter`-compatible output.
- **Personal agent**
  - FastAPI tests using `TestClient`:
    - Happy path with plain text.
    - With `image_base64` attachments.
    - Tool invocation path (`send_email`, `check_calendar`) including RabbitMQ publish stubbing.
    - Circuit-breaker degradation path (Gemini temporarily “down”).
- **RabbitMQ worker**
  - Unit tests around:
    - Message parsing and validation.
    - Retry / backoff logic.
    - Integration with `ResultStore` / `TaskStoreLike`.
  - Optional integration tests with a real or in-memory RabbitMQ instance.

This design keeps the orchestrator core as a reusable library while cleanly tying the personal agent and RabbitMQ worker into its concepts for state, resiliency, and observability.

