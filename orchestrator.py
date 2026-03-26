"""
orchestrator.py — Single source of truth for task lifecycle, rate limiting,
scheduling, circuit breaking, and metrics.

Python 3.11+. No external dependencies.
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Mapping, MutableMapping, Protocol, Sequence, TypeVar, runtime_checkable

__all__ = [
    "AsyncTokenBucket",
    "CircuitBreaker",
    "CircuitBreakerState",
    "CircuitBreakerStore",
    "Dependency",
    "DependencyCondition",
    "InvalidDependencyError",
    "LoggerLike",
    "MetricSample",
    "MetricsRegistry",
    "MetricsRegistryLike",
    "MiddlewareChain",
    "MiddlewareContext",
    "PersistedCircuitBreaker",
    "PrometheusExporter",
    "QuiescenceLatch",
    "RateLimitError",
    "RecurringScheduler",
    "RecurringSpec",
    "Task",
    "TaskLike",
    "TaskStatus",
    "TaskStoreLike",
    "WorkflowController",
    "apply_priority_inheritance",
    "normalize_status",
    "wrap_with_circuit_breaker",
]

T = TypeVar("T")


# ---------------------------------------------------------------------------
# Task Status
# ---------------------------------------------------------------------------


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"
    DEAD_LETTER = "dead_letter"
    PAUSED = "paused"

    @property
    def is_terminal(self) -> bool:
        return self in (
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
            TaskStatus.TIMED_OUT,
            TaskStatus.DEAD_LETTER,
        )


def normalize_status(value: "TaskStatus | str") -> TaskStatus:
    """Coerce a string or enum to TaskStatus, raising ValueError for unknowns."""
    if isinstance(value, TaskStatus):
        return value
    try:
        return TaskStatus(str(value).strip().lower())
    except ValueError as err:
        raise ValueError(f"Unknown task status: {value!r}") from err


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------


class InvalidDependencyError(Exception):
    pass


class DependencyCondition(str, Enum):
    COMPLETED = "completed"
    FAILED = "failed"
    ANY = "any"


@dataclass
class Dependency:
    task_id: str
    on: DependencyCondition = DependencyCondition.COMPLETED

    @classmethod
    def coerce(cls, value: Any) -> "Dependency":
        if isinstance(value, cls):
            return value
        if isinstance(value, str):
            return cls(task_id=value)
        if isinstance(value, Mapping):
            if "task_id" not in value:
                raise InvalidDependencyError(f"Dependency dict missing 'task_id': {value!r}")
            on_raw = value.get("on", "completed")
            try:
                on = DependencyCondition(str(on_raw).lower())
            except ValueError as err:
                raise InvalidDependencyError(f"Unknown dependency condition: {on_raw!r}") from err
            return cls(task_id=value["task_id"], on=on)
        raise InvalidDependencyError(f"Cannot coerce {type(value).__name__!r} to Dependency") from None

    def is_satisfied_by(self, status: "TaskStatus | str") -> bool:
        s = normalize_status(status)
        if self.on == DependencyCondition.COMPLETED:
            return s == TaskStatus.COMPLETED
        if self.on == DependencyCondition.FAILED:
            return s in (TaskStatus.FAILED, TaskStatus.TIMED_OUT)
        if self.on == DependencyCondition.ANY:
            return s.is_terminal
        return False

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Dependency):
            return NotImplemented
        return self.task_id == other.task_id and self.on == other.on

    def __hash__(self) -> int:
        return hash((self.task_id, self.on))


# ---------------------------------------------------------------------------
# Concrete Task reference type (design §3.1 Option A)
# ---------------------------------------------------------------------------


@dataclass
class Task:
    """
    Concrete reference implementation of TaskLike.
    Use this in workers and tests; custom task types remain valid via the protocol.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: str = "generic"
    status: TaskStatus = TaskStatus.PENDING
    priority: int = 0
    payload: dict[str, Any] = field(default_factory=dict)
    dependencies: list[Dependency] = field(default_factory=list)
    workflow_id: str | None = None
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timeout_s: float = 60.0
    max_retries: int = 3
    retry_count: int = 0
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    completed_at: float | None = None
    error: str | None = None

    def mark_running(self) -> None:
        self.status = TaskStatus.RUNNING
        self.started_at = time.time()

    def mark_completed(self) -> None:
        self.status = TaskStatus.COMPLETED
        self.completed_at = time.time()

    def mark_failed(self, error: str) -> None:
        self.status = TaskStatus.FAILED
        self.completed_at = time.time()
        self.error = error

    def mark_dead_letter(self, error: str) -> None:
        self.status = TaskStatus.DEAD_LETTER
        self.completed_at = time.time()
        self.error = error

    def can_retry(self) -> bool:
        return self.retry_count < self.max_retries

    def next_retry_delay(self, base: float = 2.0) -> float:
        """Exponential backoff: base * 2^retry_count, capped at 60s."""
        return float(min(base * (2**self.retry_count), 60.0))


# ---------------------------------------------------------------------------
# Protocols
# ---------------------------------------------------------------------------


@runtime_checkable
class TaskLike(Protocol):
    id: str
    status: "TaskStatus | str"
    priority: int


@runtime_checkable
class LoggerLike(Protocol):
    def info(self, event: str, **fields: Any) -> None: ...
    def error(self, event: str, **fields: Any) -> None: ...
    def warning(self, event: str, **fields: Any) -> None: ...
    def debug(self, event: str, **fields: Any) -> None: ...


@runtime_checkable
class TaskStoreLike(Protocol):
    def upsert(self, task: Any) -> None: ...


# ---------------------------------------------------------------------------
# Result Store  (SQLite WAL, thread-safe)
# ---------------------------------------------------------------------------


class ResultStore:
    """
    SQLite-backed key/value store for task results.
    WAL mode enabled for concurrent read/write access.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS task_results (
                task_id   TEXT PRIMARY KEY,
                result_json TEXT NOT NULL,
                stored_at REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_task_results_stored_at
                ON task_results(stored_at);
        """)
        self._conn.commit()

    def store(self, task_id: str, result: dict[str, Any]) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO task_results (task_id, result_json, stored_at) VALUES (?, ?, ?)",
            (task_id, json.dumps(result), time.time()),
        )
        self._conn.commit()

    def get(self, task_id: str) -> dict[str, Any] | None:
        row = self._conn.execute("SELECT result_json FROM task_results WHERE task_id = ?", (task_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def get_many(self, task_ids: Sequence[str]) -> dict[str, dict[str, Any]]:
        if not task_ids:
            return {}
        task_ids_json = json.dumps(list(task_ids))
        rows = self._conn.execute(
            """
            SELECT task_id, result_json
            FROM task_results
            WHERE task_id IN (SELECT value FROM json_each(?))
            """,
            (task_ids_json,),
        ).fetchall()
        return {row[0]: json.loads(row[1]) for row in rows}

    def delete(self, task_id: str) -> None:
        self._conn.execute("DELETE FROM task_results WHERE task_id = ?", (task_id,))
        self._conn.commit()

    def inject_parent_results(self, task: Any) -> None:
        """Inject parent task results into task.payload['__results__']."""
        deps = getattr(task, "dependencies", [])
        if not deps:
            return
        parent_ids: list[str] = []
        for d in deps:
            if isinstance(d, str):
                parent_ids.append(d)
            elif isinstance(d, Dependency):
                parent_ids.append(d.task_id)
            elif isinstance(d, Mapping) and "task_id" in d:
                parent_ids.append(d["task_id"])
        if not parent_ids:
            return
        results = self.get_many(parent_ids)
        if results:
            if task.payload is None:
                task.payload = {}
            task.payload["__results__"] = results

    def purge_older_than(self, age_s: float) -> int:
        """Delete results older than age_s seconds. Returns rows deleted."""
        cutoff = time.time() - age_s
        cur = self._conn.execute("DELETE FROM task_results WHERE stored_at < ?", (cutoff,))
        self._conn.commit()
        return cur.rowcount


# ---------------------------------------------------------------------------
# Rate Limiting
# ---------------------------------------------------------------------------


class RateLimitError(Exception):
    pass


class AsyncTokenBucket:
    """
    Async token bucket for rate limiting.
    Thread-safe via asyncio.Lock. Refills continuously at `rate` tokens/sec.
    """

    def __init__(self, rate: float, capacity: float) -> None:
        self._rate = rate
        self._capacity = capacity
        self._tokens = capacity
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    def _refill(self) -> None:
        now = time.monotonic()
        self._tokens = min(self._capacity, self._tokens + (now - self._last_refill) * self._rate)
        self._last_refill = now

    async def try_consume(self, amount: float = 1.0) -> bool:
        async with self._lock:
            self._refill()
            if self._tokens >= amount:
                self._tokens -= amount
                return True
            return False

    async def acquire(self, amount: float = 1.0, timeout_s: float | None = None) -> None:
        """Block until `amount` tokens are available, or raise RateLimitError on timeout."""
        deadline = time.monotonic() + timeout_s if timeout_s is not None else None
        while True:
            async with self._lock:
                self._refill()
                if self._tokens >= amount:
                    self._tokens -= amount
                    return
                wait = (amount - self._tokens) / self._rate
            if deadline is not None and time.monotonic() + wait > deadline:
                raise RateLimitError(f"Rate limit timeout waiting for {amount} tokens")
            await asyncio.sleep(min(wait, 0.05))

    @property
    def available(self) -> float:
        """Current token count (approximate, not locked)."""
        now = time.monotonic()
        return min(self._capacity, self._tokens + (now - self._last_refill) * self._rate)


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------


@dataclass
class MiddlewareContext:
    task: Any
    phase: str  # "before" | "after" | "error"
    result: Any = None
    error: BaseException | None = None
    elapsed_s: float = 0.0


class MiddlewareChain:
    """
    Ordered chain of middleware functions called around task execution.
    fail_open=True (default): middleware errors are logged and swallowed.
    fail_open=False: middleware errors propagate and abort execution.
    """

    def __init__(self, log: Any = None, fail_open: bool = True) -> None:
        self._middlewares: list[Callable[[MiddlewareContext], Any]] = []
        self._log = log
        self._fail_open = fail_open

    def use(self, fn: Callable[[MiddlewareContext], Any]) -> None:
        self._middlewares.append(fn)

    async def _run(self, ctx: MiddlewareContext) -> None:
        for mw in self._middlewares:
            try:
                result = mw(ctx)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as exc:
                if not self._fail_open:
                    raise
                if self._log:
                    self._log.warning("middleware_error", phase=ctx.phase, error=str(exc))

    async def run_before(self, task: Any) -> None:
        await self._run(MiddlewareContext(task=task, phase="before"))

    async def run_after(self, task: Any, result: Any, elapsed_s: float) -> None:
        await self._run(MiddlewareContext(task=task, phase="after", result=result, elapsed_s=elapsed_s))

    async def run_error(self, task: Any, error: BaseException, elapsed_s: float) -> None:
        await self._run(MiddlewareContext(task=task, phase="error", error=error, elapsed_s=elapsed_s))


# ---------------------------------------------------------------------------
# Recurring Scheduler
# ---------------------------------------------------------------------------


@dataclass
class RecurringSpec:
    """Specification for a recurring task pattern."""

    prefix: str
    type: str
    interval_s: float
    payload: dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    max_instances: int = 1
    timeout_s: float = 60.0
    max_retries: int = 0
    # runtime state — not constructor args
    active_count: int = field(default=0, init=False)
    next_run_at_mono: float = field(default_factory=time.monotonic, init=False)
    paused: bool = field(default=False, init=False)
    _active_ids: set[str] = field(default_factory=set, init=False, repr=False)


class RecurringScheduler:
    """
    Drives recurring task submission based on RecurringSpec intervals.
    Call check_and_submit() on each orchestrator tick.
    """

    def __init__(self, submit_fn: Callable[..., Any], log: Any = None) -> None:
        self._submit = submit_fn
        self._log = log
        self._specs: dict[str, RecurringSpec] = {}

    def schedule(self, spec: RecurringSpec) -> None:
        self._specs[spec.prefix] = spec

    def unschedule(self, prefix: str) -> bool:
        return self._specs.pop(prefix, None) is not None

    def check_and_submit(self, active_tasks: Mapping[str, Any]) -> list[Any]:
        now = time.monotonic()
        submitted: list[Any] = []
        for spec in self._specs.values():
            if spec.paused or now < spec.next_run_at_mono:
                continue
            if spec.active_count >= spec.max_instances:
                continue
            task_id = f"{spec.prefix}_{int(now * 1000)}"
            task = self._submit(
                task_id,
                type=spec.type,
                payload=dict(spec.payload),
                priority=spec.priority,
                timeout_s=spec.timeout_s,
                max_retries=spec.max_retries,
            )
            spec.active_count += 1
            spec._active_ids.add(task_id)
            spec.next_run_at_mono = now + spec.interval_s
            submitted.append(task)
            if self._log:
                self._log.debug("recurring_submitted", task_id=task_id, prefix=spec.prefix)
        return submitted

    def mark_terminal(self, task_id: str) -> None:
        for spec in self._specs.values():
            if task_id in spec._active_ids:
                spec._active_ids.discard(task_id)
                spec.active_count = max(0, spec.active_count - 1)
                return

    def pause(self, prefix: str) -> bool:
        if prefix in self._specs:
            self._specs[prefix].paused = True
            return True
        return False

    def resume(self, prefix: str) -> bool:
        if prefix in self._specs:
            spec = self._specs[prefix]
            spec.paused = False
            spec.next_run_at_mono = time.monotonic() + spec.interval_s
            return True
        return False


# ---------------------------------------------------------------------------
# Workflow Controller
# ---------------------------------------------------------------------------


class WorkflowController:
    """
    Pause, resume, and cancel all tasks belonging to a workflow_id.
    Publishes events to an optional event bus on state transitions.
    """

    def __init__(
        self,
        tasks: MutableMapping[str, Any],
        store: TaskStoreLike,
        log: Any = None,
        bus: Any = None,
        cancel_running_task: Callable[[Any], Any] | None = None,
    ) -> None:
        self._tasks = tasks
        self._store = store
        self._log = log
        self._bus = bus
        self._cancel_running_task = cancel_running_task

    def _workflow_tasks(self, workflow_id: str) -> list[Any]:
        return [t for t in self._tasks.values() if getattr(t, "workflow_id", None) == workflow_id]

    async def pause_workflow(self, workflow_id: str) -> int:
        """Transition PENDING tasks → PAUSED. Returns count changed."""
        count = 0
        for task in self._workflow_tasks(workflow_id):
            if normalize_status(task.status) == TaskStatus.PENDING:
                task.status = TaskStatus.PAUSED
                self._store.upsert(task)
                count += 1
        if self._bus and count:
            await self._bus.publish("workflow.paused", {"workflow_id": workflow_id, "count": count})
        if self._log:
            self._log.info("workflow_paused", workflow_id=workflow_id, count=count)
        return count

    async def resume_workflow(self, workflow_id: str) -> int:
        """Transition PAUSED tasks → PENDING. Returns count changed."""
        count = 0
        for task in self._workflow_tasks(workflow_id):
            if normalize_status(task.status) == TaskStatus.PAUSED:
                task.status = TaskStatus.PENDING
                self._store.upsert(task)
                count += 1
        if self._log:
            self._log.info("workflow_resumed", workflow_id=workflow_id, count=count)
        return count

    async def cancel_workflow(self, workflow_id: str) -> int:
        """Cancel all non-terminal tasks in the workflow. Returns count changed."""
        count = 0
        for task in self._workflow_tasks(workflow_id):
            s = normalize_status(task.status)
            if s.is_terminal:
                continue
            if s == TaskStatus.RUNNING and self._cancel_running_task:
                result = self._cancel_running_task(task)
                if asyncio.iscoroutine(result):
                    await result
            task.status = TaskStatus.CANCELLED
            task.completed_at = time.time()
            self._store.upsert(task)
            count += 1
        if self._log:
            self._log.info("workflow_cancelled", workflow_id=workflow_id, count=count)
        return count


# ---------------------------------------------------------------------------
# Priority Inheritance
# ---------------------------------------------------------------------------


def apply_priority_inheritance(
    child_task: Any,
    tasks: Mapping[str, Any],
    store: TaskStoreLike,
) -> int:
    """
    Walk the dependency graph upward from child_task and raise the priority
    of any ancestor whose priority number is higher (lower urgency) than the child.
    Returns the number of tasks updated.
    """
    child_priority = child_task.priority
    updated = 0
    visited: set[str] = set()
    queue = list(getattr(child_task, "dependencies", []))

    while queue:
        dep_raw = queue.pop(0)
        try:
            dep = Dependency.coerce(dep_raw)
        except InvalidDependencyError:
            continue
        parent_id = dep.task_id
        if parent_id in visited:
            continue
        visited.add(parent_id)
        parent = tasks.get(parent_id)
        if parent is None:
            continue
        if parent.priority > child_priority:
            parent.priority = child_priority
            store.upsert(parent)
            updated += 1
        queue.extend(getattr(parent, "dependencies", []))

    return updated


# ---------------------------------------------------------------------------
# Circuit Breaker
# ---------------------------------------------------------------------------


class CircuitBreakerState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """
    In-memory circuit breaker: CLOSED → OPEN after failure_threshold failures,
    OPEN → HALF_OPEN after recovery_timeout_s, HALF_OPEN → CLOSED after
    success_threshold consecutive successes.
    """

    def __init__(
        self,
        task_type: str,
        failure_threshold: int = 5,
        recovery_timeout_s: float = 60.0,
        success_threshold: int = 2,
    ) -> None:
        self.task_type = task_type
        self._failure_threshold = failure_threshold
        self._recovery_timeout_s = recovery_timeout_s
        self._success_threshold = success_threshold
        self.state = CircuitBreakerState.CLOSED
        self.consecutive_failures = 0
        self.probe_successes = 0
        self.tripped_at: float | None = None
        self.last_success_at: float | None = None

    def should_attempt(self) -> bool:
        if self.state == CircuitBreakerState.CLOSED:
            return True
        if self.state == CircuitBreakerState.OPEN:
            if self.tripped_at is not None and time.time() - self.tripped_at >= self._recovery_timeout_s:
                self.state = CircuitBreakerState.HALF_OPEN
                self.probe_successes = 0
                return True
            return False
        return True  # HALF_OPEN — allow probe

    def record_success(self) -> None:
        self.last_success_at = time.time()
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.probe_successes += 1
            if self.probe_successes >= self._success_threshold:
                self.state = CircuitBreakerState.CLOSED
                self.consecutive_failures = 0
                self.probe_successes = 0
        elif self.state == CircuitBreakerState.CLOSED:
            self.consecutive_failures = 0

    def record_failure(self) -> None:
        self.consecutive_failures += 1
        if self.state in (CircuitBreakerState.CLOSED, CircuitBreakerState.HALF_OPEN):
            if self.consecutive_failures >= self._failure_threshold:
                self.state = CircuitBreakerState.OPEN
                self.tripped_at = time.time()


@dataclass
class PersistedCircuitBreaker:
    """Value object returned by CircuitBreakerStore.load_all()."""

    task_type: str
    state: CircuitBreakerState
    consecutive_failures: int
    probe_successes: int
    tripped_at: float | None
    last_success_at: float | None


class CircuitBreakerStore:
    """SQLite-backed persistence for CircuitBreaker state across restarts."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS circuit_breakers (
                task_type            TEXT PRIMARY KEY,
                state                TEXT NOT NULL,
                consecutive_failures INTEGER NOT NULL DEFAULT 0,
                probe_successes      INTEGER NOT NULL DEFAULT 0,
                tripped_at           REAL,
                last_success_at      REAL,
                updated_at           REAL NOT NULL DEFAULT 0
            )
        """)
        # Add updated_at to existing tables that predate this schema version
        try:
            self._conn.execute("ALTER TABLE circuit_breakers ADD COLUMN updated_at REAL NOT NULL DEFAULT 0")
        except sqlite3.OperationalError as err:
            if "duplicate column name" not in str(err).lower():
                raise
        self._conn.commit()

    def save(self, cb: Any) -> None:
        import time as _time

        self._conn.execute(
            """INSERT OR REPLACE INTO circuit_breakers
               (task_type, state, consecutive_failures, probe_successes, tripped_at, last_success_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                cb.task_type,
                cb.state.value if isinstance(cb.state, CircuitBreakerState) else cb.state,
                cb.consecutive_failures,
                cb.probe_successes,
                cb.tripped_at,
                cb.last_success_at,
                _time.time(),
            ),
        )
        self._conn.commit()

    def load_all(self) -> dict[str, PersistedCircuitBreaker]:
        rows = self._conn.execute(
            "SELECT task_type, state, consecutive_failures, probe_successes, tripped_at, last_success_at "
            "FROM circuit_breakers"
        ).fetchall()
        return {
            row[0]: PersistedCircuitBreaker(
                task_type=row[0],
                state=CircuitBreakerState(row[1]),
                consecutive_failures=row[2],
                probe_successes=row[3],
                tripped_at=row[4],
                last_success_at=row[5],
            )
            for row in rows
        }

    def restore_into(self, cb: CircuitBreaker) -> bool:
        """Restore persisted state into a live CircuitBreaker. Returns True if found."""
        stored = self.load_all().get(cb.task_type)
        if stored is None:
            return False
        cb.state = stored.state
        cb.consecutive_failures = stored.consecutive_failures
        cb.probe_successes = stored.probe_successes
        cb.tripped_at = stored.tripped_at
        cb.last_success_at = stored.last_success_at
        return True


async def wrap_with_circuit_breaker(
    cb: CircuitBreaker,
    fn: Callable[..., Any],
    *args: Any,
    store: CircuitBreakerStore | None = None,
    **kwargs: Any,
) -> Any:
    """
    Call fn(*args, **kwargs) guarded by the circuit breaker.
    Persists state to store after each call if provided.
    Raises RuntimeError if the circuit is OPEN.
    Re-raises the original exception on failure after recording it.
    """
    if not cb.should_attempt():
        raise RuntimeError(f"Circuit breaker OPEN for task_type={cb.task_type!r}")
    try:
        result = fn(*args, **kwargs)
        if asyncio.iscoroutine(result):
            result = await result
        cb.record_success()
        if store:
            store.save(cb)
        return result
    except Exception:
        cb.record_failure()
        if store:
            store.save(cb)
        raise


# ---------------------------------------------------------------------------
# Metrics Registry + Prometheus Exporter
# ---------------------------------------------------------------------------


@dataclass
class MetricSample:
    name: str
    labels: dict[str, str]
    value: float


class MetricsRegistryLike(Protocol):
    _counters: dict[str, float]
    _gauges: dict[Any, float]
    _hists: dict[str, list[float]]


class MetricsRegistry:
    """
    Concrete in-process metrics registry.
    Counters, gauges, and histograms keyed by name (with optional label strings).
    """

    def __init__(self) -> None:
        self._counters: dict[str, float] = {}
        self._gauges: dict[Any, float] = {}
        self._hists: dict[str, list[float]] = {}

    def inc(self, name: str, amount: float = 1.0, labels: dict[str, str] | None = None) -> None:
        key = _label_key(name, labels)
        self._counters[key] = self._counters.get(key, 0.0) + amount

    def set_gauge(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        key = _label_key(name, labels)
        self._gauges[key] = value

    def observe(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        key = _label_key(name, labels)
        self._hists.setdefault(key, []).append(value)

    # Convenience helpers for standardised orchestrator metric names
    def record_task_status(self, status: str, queue: str = "default") -> None:
        self.inc(f'orchestrator_task_status_{status}{{queue="{queue}"}}')

    def record_task_latency(self, elapsed_s: float, status: str = "completed") -> None:
        self.observe(f'orchestrator_task_latency_seconds{{status="{status}"}}', elapsed_s)

    def record_circuit_breaker(self, task_type: str, state: str) -> None:
        self.set_gauge(
            f'orchestrator_circuit_breaker_state{{task_type="{task_type}"}}', 1.0 if state == "open" else 0.0
        )


def _label_key(name: str, labels: dict[str, str] | None) -> str:
    if not labels:
        return name
    parts = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
    return f"{name}{{{parts}}}"


class PrometheusExporter:
    """Render a MetricsRegistryLike to Prometheus text exposition format."""

    _QUANTILES = (0.5, 0.9, 0.95, 0.99)

    def __init__(self, namespace: str = "") -> None:
        self._ns = namespace

    def _metric_name(self, name: str) -> str:
        return f"{self._ns}_{name}" if self._ns else name

    @staticmethod
    def _parse_labels(raw: str) -> tuple[str, str]:
        if "{" in raw:
            idx = raw.index("{")
            return raw[:idx], raw[idx:]
        return raw, ""

    @staticmethod
    def _parse_label_str(label_str: str) -> dict[str, str]:
        if not label_str:
            return {}
        result: dict[str, str] = {}
        for label_part in label_str.strip("{}").split(","):
            part = label_part.strip()
            if "=" in part:
                k, v = part.split("=", 1)
                result[k.strip()] = v.strip().strip('"')
        return result

    @staticmethod
    def _labels_from_tuple(labels_map: Mapping[str, str]) -> str:
        parts = ",".join(f'{k}="{v}"' for k, v in sorted(labels_map.items()))
        return "{" + parts + "}" if parts else ""

    def _quantile(self, values: list[float], q: float) -> float:
        if not values:
            return 0.0
        sv = sorted(values)
        idx = q * (len(sv) - 1)
        lo = int(idx)
        hi = lo + 1
        if hi >= len(sv):
            return sv[lo]
        return sv[lo] * (1 - (idx - lo)) + sv[hi] * (idx - lo)

    def export(self, registry: Any) -> str:
        lines: list[str] = []

        for raw_name, value in registry._counters.items():
            base, label_str = self._parse_labels(raw_name)
            full = self._metric_name(base) + "_total"
            lines.append(f"# TYPE {full} counter")
            lines.append(f"{full}{label_str} {float(value)}")

        gauge_groups: dict[str, list[tuple[str, float]]] = {}
        for raw_key, value in registry._gauges.items():
            if isinstance(raw_key, tuple):
                base, labels_map = raw_key
                label_str = self._labels_from_tuple(labels_map)
            else:
                base, label_str = self._parse_labels(raw_key)
            gauge_groups.setdefault(base, []).append((label_str, value))
        for base, entries in gauge_groups.items():
            full_base = self._metric_name(base)
            lines.append(f"# TYPE {full_base} gauge")
            for label_str, value in entries:
                lines.append(f"{full_base}{label_str} {float(value)}")

        for raw_name, values in registry._hists.items():
            base, label_str = self._parse_labels(raw_name)
            full_base = self._metric_name(base)
            lines.append(f"# TYPE {full_base} summary")
            existing = self._parse_label_str(label_str)
            for q in self._QUANTILES:
                all_labels = {"quantile": str(q), **existing}
                q_label = "{" + ",".join(f'{k}="{v}"' for k, v in all_labels.items()) + "}"
                lines.append(f"{full_base}{q_label} {self._quantile(values, q)}")
            lines.append(f"{full_base}_sum{label_str} {round(sum(values), 10)}")
            lines.append(f"{full_base}_count{label_str} {len(values)}")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Quiescence Latch
# ---------------------------------------------------------------------------


class QuiescenceLatch:
    """
    Returns True once all tasks have been terminal for a sustained window_s.
    Resets if any non-terminal task appears before the window expires.
    """

    def __init__(self, window_s: float = 1.0) -> None:
        self._window_s = window_s
        self._start: float | None = None

    def check(self, all_terminal: bool) -> bool:
        if not all_terminal:
            self._start = None
            return False
        now = time.monotonic()
        if self._start is None:
            self._start = now
            return False
        return (now - self._start) >= self._window_s

    def reset(self) -> None:
        self._start = None
