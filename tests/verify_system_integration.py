#!/usr/bin/env python3
"""
Comprehensive System Integration Tests

Tests the complete orchestrator-enhancements system including:
- Core orchestrator functionality
- Circuit breaker operations
- Result store persistence
- Workflow control
- Priority inheritance
- All major components working together
"""

import asyncio
import sqlite3
import tempfile
import time
from typing import Any, Dict

# Import orchestrator components
from orchestrator import (
    CircuitBreaker,
    CircuitBreakerState,
    ResultStore,
    TaskStatus,
    Dependency,
    DependencyCondition,
    RecurringSpec,
    RecurringScheduler,
    WorkflowController,
    apply_priority_inheritance,
    normalize_status,
)


class MockTask:
    """Mock task implementation for testing."""

    def __init__(
        self,
        task_id: str,
        status: TaskStatus | str = TaskStatus.PENDING,
        dependencies: list = None,
        payload: dict = None,
        priority: int = 5,
        workflow_id: str = None,
        trace_id: str = None,
        type: str = None,
        timeout_s: float = 30.0,
        max_retries: int = 1,
    ):
        self.id = task_id
        self.status = status
        self.dependencies = dependencies or []
        self.payload = payload or {}
        self.priority = priority
        self.workflow_id = workflow_id
        self.trace_id = trace_id or f"trace_{task_id}"
        self.type = type
        self.timeout_s = timeout_s
        self.max_retries = max_retries
        self.completed_at = None


class MockTaskStore:
    """Mock task store for testing."""

    def __init__(self):
        self.tasks: Dict[str, MockTask] = {}

    def upsert(self, task: MockTask) -> None:
        self.tasks[task.id] = task

    def get(self, task_id: str) -> MockTask | None:
        return self.tasks.get(task_id)

    def get_all(self) -> Dict[str, MockTask]:
        return self.tasks.copy()


class MockLogger:
    """Mock logger for testing."""

    def __init__(self):
        self.messages = []

    def debug(self, event: str, **fields: Any) -> None:
        self.messages.append(("DEBUG", event, fields))

    def info(self, event: str, **fields: Any) -> None:
        self.messages.append(("INFO", event, fields))

    def warning(self, event: str, **fields: Any) -> None:
        self.messages.append(("WARNING", event, fields))

    def error(self, event: str, **fields: Any) -> None:
        self.messages.append(("ERROR", event, fields))


def test_circuit_breaker_lifecycle():
    """Test complete circuit breaker lifecycle."""
    print("\n🔌 Testing Circuit Breaker Lifecycle...")

    # Create circuit breaker
    cb = CircuitBreaker(
        task_type="test_service",
        failure_threshold=3,
        recovery_timeout_s=1.0,
        success_threshold=2,
    )

    # Initial state should be CLOSED
    assert cb.state == CircuitBreakerState.CLOSED
    assert cb.should_attempt()
    print("✅ Initial state: CLOSED")

    # Record failures to trigger OPEN
    for i in range(3):
        cb.record_failure()
        print(f"  Recorded failure {i + 1}, state: {cb.state.value}")

    # Should be OPEN now
    assert cb.state == CircuitBreakerState.OPEN
    assert not cb.should_attempt()
    print("✅ State transitioned to OPEN")

    # Wait for recovery timeout
    time.sleep(1.1)

    # Next attempt should transition to HALF_OPEN
    assert cb.should_attempt()
    assert cb.state == CircuitBreakerState.HALF_OPEN
    print("✅ State transitioned to HALF_OPEN")

    # Record successes to close circuit
    for i in range(2):
        cb.record_success()
        print(f"  Recorded success {i + 1}, state: {cb.state.value}")

    # Should be CLOSED again
    assert cb.state == CircuitBreakerState.CLOSED
    assert cb.should_attempt()
    print("✅ State transitioned back to CLOSED")


def test_result_store_operations():
    """Test result store CRUD operations."""
    print("\n💾 Testing Result Store Operations...")

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        conn = sqlite3.connect(db_path)
        store = ResultStore(conn)

        # Test storing and retrieving single result
        test_data = {"status": "success", "output": "test_result", "count": 42}
        store.store("task_1", test_data)

        retrieved = store.get("task_1")
        assert retrieved == test_data
        print("✅ Single result store/retrieve works")

        # Test storing multiple results
        store.store("task_2", {"status": "failed", "error": "timeout"})
        store.store("task_3", {"status": "success", "output": "another_result"})

        # Test batch retrieval
        results = store.get_many(["task_1", "task_2", "task_3"])
        assert len(results) == 3
        assert results["task_1"]["count"] == 42
        print("✅ Batch retrieval works")

        # Test deletion
        store.delete("task_2")
        results_after_delete = store.get_many(["task_1", "task_2", "task_3"])
        assert len(results_after_delete) == 2
        assert "task_2" not in results_after_delete
        print("✅ Deletion works")

    finally:
        import os

        os.unlink(db_path)


def test_dependency_management():
    """Test dependency creation and satisfaction."""
    print("\n🔗 Testing Dependency Management...")

    # Test dependency coercion
    dep1 = Dependency.coerce("task_a")
    assert dep1.task_id == "task_a"
    assert dep1.on == DependencyCondition.COMPLETED
    print("✅ String dependency coercion")

    dep2 = Dependency.coerce({"task_id": "task_b", "on": "failed"})
    assert dep2.task_id == "task_b"
    assert dep2.on == DependencyCondition.FAILED
    print("✅ Dict dependency coercion")

    # Test dependency satisfaction
    completed_dep = Dependency("task_c", DependencyCondition.COMPLETED)
    assert completed_dep.is_satisfied_by(TaskStatus.COMPLETED)
    assert not completed_dep.is_satisfied_by(TaskStatus.FAILED)
    print("✅ COMPLETED dependency satisfaction")

    failed_dep = Dependency("task_d", DependencyCondition.FAILED)
    assert failed_dep.is_satisfied_by(TaskStatus.FAILED)
    assert failed_dep.is_satisfied_by(TaskStatus.TIMED_OUT)
    assert not failed_dep.is_satisfied_by(TaskStatus.COMPLETED)
    print("✅ FAILED dependency satisfaction")

    any_dep = Dependency("task_e", DependencyCondition.ANY)
    assert any_dep.is_satisfied_by(TaskStatus.COMPLETED)
    assert any_dep.is_satisfied_by(TaskStatus.FAILED)
    assert any_dep.is_satisfied_by(TaskStatus.CANCELLED)
    print("✅ ANY dependency satisfaction")


def test_workflow_control():
    """Test workflow controller operations."""
    print("\n🎛️ Testing Workflow Control...")

    store = MockTaskStore()
    logger = MockLogger()

    # Create tasks in a workflow
    tasks = {
        "task_1": MockTask("task_1", TaskStatus.PENDING, workflow_id="workflow_1"),
        "task_2": MockTask("task_2", TaskStatus.RUNNING, workflow_id="workflow_1"),
        "task_3": MockTask("task_3", TaskStatus.PENDING, workflow_id="workflow_1"),
        "task_4": MockTask("task_4", TaskStatus.PENDING, workflow_id="workflow_2"),
    }

    for task in tasks.values():
        store.upsert(task)

    controller = WorkflowController(tasks, store, logger)

    # Test pausing workflow
    async def test_pause():
        count = await controller.pause_workflow("workflow_1")
        assert count == 2  # Only PENDING tasks should be paused
        assert tasks["task_1"].status == TaskStatus.PAUSED
        assert tasks["task_3"].status == TaskStatus.PAUSED
        assert tasks["task_2"].status == TaskStatus.RUNNING  # RUNNING task unchanged
        print("✅ Workflow pause works")

    asyncio.run(test_pause())

    # Test resuming workflow
    async def test_resume():
        count = await controller.resume_workflow("workflow_1")
        assert count == 2
        assert tasks["task_1"].status == TaskStatus.PENDING
        assert tasks["task_3"].status == TaskStatus.PENDING
        print("✅ Workflow resume works")

    asyncio.run(test_resume())


def test_priority_inheritance():
    """Test priority inheritance system."""
    print("\n⚡ Testing Priority Inheritance...")

    store = MockTaskStore()

    # Create task hierarchy: grandparent -> parent -> child
    grandparent = MockTask("grandparent", priority=8)
    parent = MockTask("parent", priority=6, dependencies=[Dependency("grandparent")])
    child = MockTask("child", priority=4, dependencies=[Dependency("parent")])

    tasks = {"grandparent": grandparent, "parent": parent, "child": child}

    for task in tasks.values():
        store.upsert(task)

    # Child has higher priority (lower number) than parent
    # Priority inheritance should propagate up
    updated = apply_priority_inheritance(child, tasks, store)

    assert updated == 2  # Both parent and grandparent should be updated
    assert parent.priority == 4  # Should match child's priority
    assert grandparent.priority == 4  # Should also match child's priority
    print("✅ Priority inheritance propagates correctly")


def test_recurring_scheduler():
    """Test recurring task scheduler."""
    print("\n⏰ Testing Recurring Scheduler...")

    store = MockTaskStore()
    logger = MockLogger()

    submitted_tasks = []

    def submit_task(task_id, **kwargs):
        task = MockTask(task_id, **kwargs)
        store.upsert(task)
        submitted_tasks.append(task)
        return task

    scheduler = RecurringScheduler(submit_task, log=logger)

    # Create recurring spec
    spec = RecurringSpec(
        prefix="heartbeat",
        type="health_check",
        interval_s=0.1,  # Very short for testing
        payload={"endpoint": "/health"},
        priority=2,
    )

    scheduler.schedule(spec)

    # First check should submit task
    current_tasks = {}
    submitted = scheduler.check_and_submit(current_tasks)
    assert len(submitted) == 1
    assert submitted[0].id.startswith("heartbeat_")
    assert spec.active_count == 1
    print("✅ Initial task submission")

    # Immediate check should not submit (interval not elapsed)
    submitted = scheduler.check_and_submit(current_tasks)
    assert len(submitted) == 0
    print("✅ Interval respected")

    # Mark task as completed to free up slot
    task_id = submitted_tasks[0].id
    scheduler.mark_terminal(task_id)
    assert spec.active_count == 0
    print("✅ Task completion frees slot")

    # Wait for interval and check again
    time.sleep(0.11)
    submitted = scheduler.check_and_submit(current_tasks)
    assert len(submitted) == 1
    assert spec.active_count == 1
    print("✅ Recurring submission works after task completion")

    # Mark second task as completed
    second_task_id = submitted[0].id
    scheduler.mark_terminal(second_task_id)
    assert spec.active_count == 0
    print("✅ Second task completion frees slot")

    # Test pause/resume
    assert scheduler.pause("heartbeat")
    time.sleep(0.11)
    submitted = scheduler.check_and_submit(current_tasks)
    assert len(submitted) == 0
    print("✅ Pause prevents submission")

    assert scheduler.resume("heartbeat")
    time.sleep(0.11)
    submitted = scheduler.check_and_submit(current_tasks)
    print(f"Debug: Resume test - submitted {len(submitted)} tasks")
    print(f"Debug: Spec paused = {spec.paused}")
    print(f"Debug: Spec active_count = {spec.active_count}")
    print(f"Debug: Current time = {time.monotonic()}")
    print(f"Debug: Spec next_run_at_mono = {spec.next_run_at_mono}")
    assert len(submitted) == 1
    print("✅ Resume allows submission")


def test_status_normalization():
    """Test task status normalization."""
    print("\n📊 Testing Status Normalization...")

    # Test enum normalization
    assert normalize_status(TaskStatus.COMPLETED) == TaskStatus.COMPLETED
    print("✅ Enum normalization")

    # Test string normalization
    assert normalize_status("completed") == TaskStatus.COMPLETED
    assert normalize_status("COMPLETED") == TaskStatus.COMPLETED
    assert normalize_status("  completed  ") == TaskStatus.COMPLETED
    print("✅ String normalization")

    # Test invalid status
    try:
        normalize_status("invalid_status")
        raise AssertionError("Should have raised ValueError")
    except ValueError:
        print("✅ Invalid status raises ValueError")


def test_system_integration():
    """Run all system integration tests."""
    print("🚀 Starting System Integration Tests\n")

    try:
        test_circuit_breaker_lifecycle()
        test_result_store_operations()
        test_dependency_management()
        test_workflow_control()
        test_priority_inheritance()
        test_recurring_scheduler()
        test_status_normalization()

        print("\n🎉 ALL SYSTEM INTEGRATION TESTS PASSED!")
        print("📋 System Components Verified:")
        print("   ✅ Circuit Breaker Lifecycle Management")
        print("   ✅ Result Store Persistence")
        print("   ✅ Dependency Resolution")
        print("   ✅ Workflow Control Operations")
        print("   ✅ Priority Inheritance")
        print("   ✅ Recurring Task Scheduling")
        print("   ✅ Status Normalization")
        print("\n🔗 The orchestrator-enhancements system is fully operational!")

        return 0

    except Exception as e:
        print(f"\n❌ SYSTEM TEST FAILED: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(test_system_integration())
