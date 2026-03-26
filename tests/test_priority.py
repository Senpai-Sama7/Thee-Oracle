from orchestrator import apply_priority_inheritance
from tests.conftest import MockTask, MockTaskStore


def test_priority_inheritance_basic() -> None:
    store = MockTaskStore()

    t1 = MockTask(id="root", priority=10)  # parent
    t2 = MockTask(id="mid", priority=10, dependencies=["root"])
    t3 = MockTask(id="leaf", priority=1, dependencies=["mid"])  # urgent child

    tasks = {t.id: t for t in [t1, t2, t3]}
    store.tasks = tasks

    # Apply from leaf
    count = apply_priority_inheritance(child_task=t3, tasks=tasks, store=store)

    assert count == 2
    assert t1.priority == 1
    assert t2.priority == 1
    assert t3.priority == 1


def test_priority_inheritance_no_change() -> None:
    store = MockTaskStore()

    t1 = MockTask(id="parent", priority=0)  # already very high
    t2 = MockTask(id="child", priority=5, dependencies=[{"task_id": "parent", "on": "completed"}])

    tasks = {t.id: t for t in [t1, t2]}
    store.tasks = tasks

    count = apply_priority_inheritance(t2, tasks, store)

    assert count == 0
    assert t1.priority == 0
    assert t2.priority == 5


def test_priority_inheritance_missing_parent() -> None:
    store = MockTaskStore()

    t1 = MockTask(id="child", priority=1, dependencies=["missing_parent"])

    tasks = {t1.id: t1}
    store.tasks = tasks

    count = apply_priority_inheritance(t1, tasks, store)
    assert count == 0
