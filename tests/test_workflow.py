import pytest
from typing import Any
from orchestrator import WorkflowController, TaskStatus
from tests.conftest import MockLogger, MockEventBus, MockTaskStore, MockTask


@pytest.fixture
def workflow_tasks() -> dict[str, MockTask]:
    return {
        "t1": MockTask(id="t1", workflow_id="wf1", status=TaskStatus.PENDING),
        "t2": MockTask(id="t2", workflow_id="wf1", status=TaskStatus.RUNNING),
        "t3": MockTask(id="t3", workflow_id="wf2", status=TaskStatus.PENDING),
        "t4": MockTask(id="t4", workflow_id="wf1", status=TaskStatus.PAUSED),
    }


@pytest.mark.asyncio
async def test_workflow_pause_resume(
    workflow_tasks: dict[str, MockTask],
    mock_logger: MockLogger,
    mock_event_bus: MockEventBus,
    mock_task_store: MockTaskStore,
) -> None:
    ctrl = WorkflowController(tasks=workflow_tasks, store=mock_task_store, log=mock_logger, bus=mock_event_bus)

    # Pause wf1
    count = await ctrl.pause_workflow("wf1")
    assert count == 1  # Only t1 transitions (PENDING -> PAUSED). t2 is RUNNING, t4 is already PAUSED.
    assert workflow_tasks["t1"].status == TaskStatus.PAUSED
    assert workflow_tasks["t2"].status == TaskStatus.RUNNING
    assert workflow_tasks["t3"].status == TaskStatus.PENDING  # Different wf

    assert len(mock_task_store.tasks) == 1
    assert mock_event_bus.events[0][0] == "workflow.paused"

    # Resume wf1
    count_resume = await ctrl.resume_workflow("wf1")
    assert count_resume == 2  # t1 and t4 both PAUSED -> PENDING
    assert workflow_tasks["t1"].status == TaskStatus.PENDING  # type: ignore[comparison-overlap]
    assert workflow_tasks["t4"].status == TaskStatus.PENDING
    assert len(mock_task_store.tasks) == 2


@pytest.mark.asyncio
async def test_workflow_cancel(
    workflow_tasks: dict[str, MockTask], mock_logger: MockLogger, mock_task_store: MockTaskStore
) -> None:
    async def cancel_running(task: Any) -> bool:
        return True

    ctrl = WorkflowController(
        tasks=workflow_tasks, store=mock_task_store, log=mock_logger, cancel_running_task=cancel_running
    )

    count = await ctrl.cancel_workflow("wf1")
    # t1 (PENDING), t4 (PAUSED), t2 (RUNNING) -> all cancelled
    assert count == 3
    assert workflow_tasks["t1"].status == TaskStatus.CANCELLED
    assert workflow_tasks["t2"].status == TaskStatus.CANCELLED
    assert workflow_tasks["t4"].status == TaskStatus.CANCELLED
    assert workflow_tasks["t3"].status == TaskStatus.PENDING

    # Check that it recorded terminal state
    assert workflow_tasks["t1"].completed_at is not None
