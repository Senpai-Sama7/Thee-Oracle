import sqlite3
from orchestrator import ResultStore
from tests.conftest import MockTask


def test_result_store_init(memory_db: sqlite3.Connection) -> None:
    _ = ResultStore(memory_db)
    # Ensure table is created
    cur = memory_db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='task_results'")
    assert cur.fetchone() is not None


def test_result_store_store_and_get(memory_db: sqlite3.Connection) -> None:
    store = ResultStore(memory_db)

    # Save a result
    store.store("task_1", {"output": 42, "status": "ok"})

    # Get it back
    res = store.get("task_1")
    assert isinstance(res, dict)
    assert res["output"] == 42
    assert res["status"] == "ok"


def test_result_store_delete(memory_db: sqlite3.Connection) -> None:
    store = ResultStore(memory_db)
    store.store("delete_me", {"data": 123})
    assert isinstance(store.get("delete_me"), dict)
    assert store.get("delete_me")["data"] == 123  # type: ignore

    store.delete("delete_me")
    assert store.get("delete_me") is None


def test_result_store_get_many(memory_db: sqlite3.Connection) -> None:
    store = ResultStore(memory_db)
    store.store("t1", {"val": 1})
    store.store("t2", {"val": 2})
    store.store("t3", {"val": 3})

    results = store.get_many(["t1", "t3", "t4"])
    assert len(results) == 2
    assert results["t1"]["val"] == 1  # type: ignore
    assert results["t3"]["val"] == 3  # type: ignore


def test_result_store_inject_parent(memory_db: sqlite3.Connection) -> None:
    store = ResultStore(memory_db)
    store.store("parent_1", {"keyA": "valueA"})
    store.store("parent_2", {"keyB": "valueB"})

    # Task with these dependencies
    task = MockTask(id="child", dependencies=["parent_1", "parent_2"])
    assert not task.payload

    store.inject_parent_results(task)

    assert task.payload is not None
    assert "__results__" in task.payload
    assert task.payload["__results__"]["parent_1"]["keyA"] == "valueA"
    assert task.payload["__results__"]["parent_2"]["keyB"] == "valueB"
