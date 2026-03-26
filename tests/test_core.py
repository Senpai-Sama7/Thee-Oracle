import pytest
from orchestrator import (
    TaskStatus,
    Dependency,
    DependencyCondition,
    InvalidDependencyError,
    normalize_status,
)


def test_task_status_enum() -> None:
    assert TaskStatus.PENDING.value == "pending"
    assert TaskStatus.RUNNING.value == "running"
    assert TaskStatus.COMPLETED.value == "completed"
    assert TaskStatus.FAILED.value == "failed"
    assert TaskStatus.CANCELLED.value == "cancelled"
    assert TaskStatus.TIMED_OUT.value == "timed_out"
    assert TaskStatus.DEAD_LETTER.value == "dead_letter"

    assert TaskStatus.COMPLETED.is_terminal is True
    assert TaskStatus.FAILED.is_terminal is True
    assert TaskStatus.PENDING.is_terminal is False


def test_normalize_status_from_enum() -> None:
    assert normalize_status(TaskStatus.COMPLETED) == TaskStatus.COMPLETED


def test_normalize_status_from_string() -> None:
    assert normalize_status("FAILED") == TaskStatus.FAILED
    assert normalize_status(" pending  ") == TaskStatus.PENDING
    assert normalize_status("cancelled") == TaskStatus.CANCELLED


def test_normalize_status_unknown() -> None:
    with pytest.raises(ValueError):
        normalize_status("unknown_status")


def test_dependency_coerce_string() -> None:
    dep = Dependency.coerce("task-123")
    assert dep.task_id == "task-123"
    assert dep.on == DependencyCondition.COMPLETED


def test_dependency_coerce_dict_success() -> None:
    dep = Dependency.coerce({"task_id": "task-456", "on": "failed"})
    assert dep.task_id == "task-456"
    assert dep.on == DependencyCondition.FAILED


def test_dependency_coerce_dependency_obj() -> None:
    orig = Dependency(task_id="task-789", on=DependencyCondition.ANY)
    dep = Dependency.coerce(orig)
    assert dep is orig


def test_dependency_coerce_invalid_dict() -> None:
    with pytest.raises(InvalidDependencyError):
        Dependency.coerce({"on": "completed"})  # missing task_id


def test_dependency_coerce_invalid_type() -> None:
    with pytest.raises(InvalidDependencyError):
        Dependency.coerce(123)  # type: ignore


def test_dependency_eq() -> None:
    dep1 = Dependency("t1", DependencyCondition.COMPLETED)
    dep2 = Dependency("t1", DependencyCondition.COMPLETED)
    dep3 = Dependency("t1", DependencyCondition.FAILED)
    assert dep1 == dep2
    assert dep1 != dep3
