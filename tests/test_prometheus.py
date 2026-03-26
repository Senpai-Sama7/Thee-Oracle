from typing import Any
from orchestrator import PrometheusExporter


class HashableMapping(dict[str, str]):
    def __hash__(self) -> int:  # type: ignore[override]
        return hash(frozenset(self.items()))


class DummyRegistry:
    def __init__(self) -> None:
        self._counters: dict[str, float] = {"tasks_completed": 5}
        self._gauges: dict[Any, float] = {
            'active_tasks{queue="default"}': 10,
            ("active_tasks", HashableMapping({"queue": "high"})): 5,  # Tuple format
        }
        self._hists: dict[str, list[float]] = {'task_duration_seconds{status="ok"}': [0.1, 0.5, 0.9, 1.2, 2.5]}


def test_prometheus_formatting() -> None:
    exporter = PrometheusExporter(namespace="my_app")
    registry = DummyRegistry()

    out = exporter.export(registry)  # type: ignore

    assert "# TYPE my_app_tasks_completed_total counter" in out
    assert "my_app_tasks_completed_total 5.0" in out

    assert "# TYPE my_app_active_tasks gauge" in out
    assert 'my_app_active_tasks{queue="default"} 10.0' in out
    assert 'my_app_active_tasks{queue="high"} 5.0' in out

    assert "# TYPE my_app_task_duration_seconds summary" in out
    assert 'my_app_task_duration_seconds_sum{status="ok"} 5.2' in out
    assert 'my_app_task_duration_seconds_count{status="ok"} 5' in out
    assert 'my_app_task_duration_seconds{quantile="0.5",status="ok"} 0.9' in out


def test_prometheus_empty() -> None:
    exporter = PrometheusExporter()

    class EmptyReg:
        _counters: dict[str, float] = {}
        _gauges: dict[Any, float] = {}
        _hists: dict[str, list[float]] = {}

    out = exporter.export(EmptyReg())  # type: ignore
    assert out == ""


def test_quantile_calculation() -> None:
    exporter = PrometheusExporter()

    # 5 items: index 0 to 4
    # p50 -> index 2 (value: 30)
    # p95 -> index 4 * 0.95 = 3.8 -> 20% index 3, 80% index 4 -> 40 * 0.2 + 50 * 0.8 = 8 + 40 = 48
    values = [10.0, 20.0, 30.0, 40.0, 50.0]

    assert exporter._quantile(values, 0.5) == 30.0
    assert exporter._quantile(values, 0.95) == 48.0
