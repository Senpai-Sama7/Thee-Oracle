import sqlite3
import pytest
from typing import Any, Mapping, MutableMapping, Sequence, Optional, Iterator
from orchestrator import TaskStatus, Dependency


class MockLogger:
    def info(self, event: str, **fields: Any) -> None:
        pass

    def error(self, event: str, **fields: Any) -> None:
        pass

    def warning(self, event: str, **fields: Any) -> None:
        pass

    def debug(self, event: str, **fields: Any) -> None:
        pass

    def exception(self, event: str, **fields: Any) -> None:
        pass


class MockEventBus:
    def __init__(self) -> None:
        self.events: list[tuple[str, Any]] = []

    async def publish(self, topic: str, payload: Mapping[str, Any]) -> None:
        self.events.append((topic, payload))


class MockTask:
    def __init__(
        self,
        id: str,
        status: TaskStatus | str = TaskStatus.PENDING,
        dependencies: Sequence[Dependency | str | Mapping[str, Any]] = (),
        payload: MutableMapping[str, Any] | None = None,
        priority: int = 0,
        workflow_id: Optional[str] = None,
        trace_id: str = "trace-1",
        completed_at: Optional[float] = None,
    ):
        self.id = id
        self.status = status
        self.dependencies = dependencies
        self.payload: MutableMapping[str, Any] | None = payload if payload is not None else {}
        self.priority = priority
        self.workflow_id = workflow_id
        self.trace_id = trace_id
        self.completed_at = completed_at


class MockTaskStore:
    def __init__(self) -> None:
        self.tasks: dict[str, Any] = {}

    def upsert(self, task: Any) -> None:
        self.tasks[task.id] = task


@pytest.fixture
def mock_logger() -> MockLogger:
    return MockLogger()


@pytest.fixture
def mock_event_bus() -> MockEventBus:
    return MockEventBus()


@pytest.fixture
def mock_task_store() -> MockTaskStore:
    return MockTaskStore()


@pytest.fixture
def memory_db() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()
