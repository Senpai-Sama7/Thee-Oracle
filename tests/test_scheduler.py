import time
from orchestrator import RecurringScheduler, RecurringSpec
from tests.conftest import MockLogger, MockTask


def test_recurring_spec_init() -> None:
    spec = RecurringSpec(prefix="test", type="my_task", interval_s=10.0)
    assert spec.prefix == "test"
    assert spec.interval_s == 10.0
    assert spec.active_count == 0


def test_recurring_scheduler_basic(mock_logger: MockLogger) -> None:
    submitted = []

    def mock_submit(id: str, **kwargs: object) -> MockTask:
        kwargs.pop("type", None)
        kwargs.pop("timeout_s", None)
        kwargs.pop("max_retries", None)
        t = MockTask(id=id, **kwargs)  # type: ignore
        submitted.append(t)
        return t

    sched = RecurringScheduler(mock_submit, log=mock_logger)
    spec = RecurringSpec(prefix="heartbeat", type="ping", interval_s=0.1, max_instances=2)

    # Backdate to ensure immediate execution
    spec.next_run_at_mono = time.monotonic() - 1.0
    sched.schedule(spec)

    # Run 1: Should submit
    res = sched.check_and_submit({})
    assert len(res) == 1
    assert res[0].id.startswith("heartbeat_")
    assert spec.active_count == 1

    # Try again immediately: Should not submit (because next_run_at_mono is in future)
    res2 = sched.check_and_submit({res[0].id: res[0]})
    assert len(res2) == 0


def test_scheduler_max_instances(mock_logger: MockLogger) -> None:
    submitted: list[MockTask] = []

    def mock_submit(id: str, **kwargs: object) -> MockTask:
        kwargs.pop("type", None)
        kwargs.pop("timeout_s", None)
        kwargs.pop("max_retries", None)
        t = MockTask(id=id, **kwargs)  # type: ignore
        submitted.append(t)
        return t

    sched = RecurringScheduler(mock_submit, log=mock_logger)
    spec = RecurringSpec(prefix="job", type="work", interval_s=0.01, max_instances=1)
    spec.next_run_at_mono = time.monotonic() - 1.0
    sched.schedule(spec)

    # First submit -> works
    t1 = sched.check_and_submit({})[0]
    assert spec.active_count == 1

    # Force next run
    spec.next_run_at_mono = time.monotonic() - 1.0

    # Max instances is reached -> no submit
    assert len(sched.check_and_submit({})) == 0
    assert spec.active_count == 1

    # Mark tasks terminal
    sched.mark_terminal(t1.id)
    assert spec.active_count == 0

    # Force next run
    spec.next_run_at_mono = time.monotonic() - 1.0

    # Should submit again
    _ = sched.check_and_submit({})[0]
    assert len(submitted) == 2


def test_scheduler_pause_resume() -> None:
    sched = RecurringScheduler(lambda id, **kw: MockTask(id=id))
    spec = RecurringSpec("job", "type", 0.01)
    spec.next_run_at_mono = time.monotonic() - 1.0
    sched.schedule(spec)

    sched.pause("job")
    assert len(sched.check_and_submit({})) == 0

    sched.resume("job")
    # Resume sets next_run_at_mono to monotonic() + interval, so we must backdate again for immediate run
    spec.next_run_at_mono = time.monotonic() - 1.0
    assert len(sched.check_and_submit({})) == 1
