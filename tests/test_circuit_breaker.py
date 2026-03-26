import sqlite3
from orchestrator import CircuitBreakerStore, CircuitBreakerState


class MockCircuitBreaker:
    def __init__(
        self,
        task_type: str,
        state: CircuitBreakerState,
        consecutive_failures: int,
        probe_successes: int,
        tripped_at: float | None = None,
        last_success_at: float | None = None,
    ):
        self.task_type = task_type
        self.state = state
        self.consecutive_failures = consecutive_failures
        self.probe_successes = probe_successes
        self.tripped_at = tripped_at
        self.last_success_at = last_success_at


def test_circuit_breaker_store_init(memory_db: sqlite3.Connection) -> None:
    _ = CircuitBreakerStore(memory_db)
    cur = memory_db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='circuit_breakers'")
    assert cur.fetchone() is not None


def test_circuit_breaker_save_and_load(memory_db: sqlite3.Connection) -> None:
    store = CircuitBreakerStore(memory_db)

    cb1 = MockCircuitBreaker(
        task_type="api_call",
        state=CircuitBreakerState.OPEN,
        consecutive_failures=5,
        probe_successes=0,
        tripped_at=100.0,
        last_success_at=95.0,
    )

    cb2 = MockCircuitBreaker(
        task_type="db_query",
        state=CircuitBreakerState.CLOSED,
        consecutive_failures=0,
        probe_successes=3,
    )

    store.save(cb1)
    store.save(cb2)

    loaded = store.load_all()

    assert len(loaded) == 2

    # Check loaded cb1
    assert loaded["api_call"].state == CircuitBreakerState.OPEN
    assert loaded["api_call"].consecutive_failures == 5
    assert loaded["api_call"].tripped_at == 100.0

    # Check loaded cb2
    assert loaded["db_query"].state == CircuitBreakerState.CLOSED
    assert loaded["db_query"].probe_successes == 3
    assert loaded["db_query"].tripped_at is None


def test_circuit_breaker_save_upsert(memory_db: sqlite3.Connection) -> None:
    store = CircuitBreakerStore(memory_db)

    cb = MockCircuitBreaker("api", CircuitBreakerState.CLOSED, 0, 0)
    store.save(cb)

    cb.state = CircuitBreakerState.OPEN
    cb.consecutive_failures = 10

    store.save(cb)
    loaded = store.load_all()
    assert loaded["api"].state == CircuitBreakerState.OPEN
    assert loaded["api"].consecutive_failures == 10
