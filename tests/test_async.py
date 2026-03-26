import asyncio
import time
import pytest
from orchestrator import AsyncTokenBucket, MiddlewareChain, MiddlewareContext, RateLimitError
from tests.conftest import MockLogger, MockTask


@pytest.mark.asyncio
async def test_token_bucket_acquire() -> None:
    bucket = AsyncTokenBucket(rate=10.0, capacity=2.0)

    # Bucket starts full
    assert await bucket.try_consume(1.0) is True
    assert await bucket.try_consume(1.0) is True

    # Bucket is now empty
    assert await bucket.try_consume(1.0) is False

    # Wait for refill (10 tokens/sec -> 0.1s/token)
    await asyncio.sleep(0.15)

    # Should be able to consume 1 token
    assert await bucket.try_consume(1.0) is True


@pytest.mark.asyncio
async def test_token_bucket_wait() -> None:
    bucket = AsyncTokenBucket(rate=10.0, capacity=1.0)

    # Consume existing token
    await bucket.acquire(1.0)

    # This should wait ~0.1s
    start = time.monotonic()
    await bucket.acquire(1.0)
    duration = time.monotonic() - start

    assert duration >= 0.05
    assert duration <= 0.2


@pytest.mark.asyncio
async def test_token_bucket_timeout() -> None:
    bucket = AsyncTokenBucket(rate=1.0, capacity=1.0)
    await bucket.acquire(1.0)

    # Next token takes 1.0s, timeout is 0.1s
    with pytest.raises(RateLimitError):
        await bucket.acquire(1.0, timeout_s=0.1)


@pytest.mark.asyncio
async def test_middleware_success(mock_logger: MockLogger) -> None:
    chain = MiddlewareChain(log=mock_logger)

    called_phases = []

    def mw(ctx: MiddlewareContext) -> None:
        called_phases.append(ctx.phase)

    chain.use(mw)  # type: ignore

    task = MockTask(id="m1")
    await chain.run_before(task)
    assert called_phases == ["before"]

    await chain.run_after(task, {"res": 1}, 0.5)
    assert called_phases == ["before", "after"]

    await chain.run_error(task, ValueError("test error"), 0.1)
    assert called_phases == ["before", "after", "error"]


@pytest.mark.asyncio
async def test_middleware_fail_open(mock_logger: MockLogger) -> None:
    chain = MiddlewareChain(log=mock_logger, fail_open=True)

    async def bad_mw(ctx: MiddlewareContext) -> None:
        raise ValueError("I fail")

    chain.use(bad_mw)
    task = MockTask(id="m2")

    # Should not raise
    await chain.run_before(task)


@pytest.mark.asyncio
async def test_middleware_fail_closed(mock_logger: MockLogger) -> None:
    chain = MiddlewareChain(log=mock_logger, fail_open=False)

    async def bad_mw(ctx: MiddlewareContext) -> None:
        raise ValueError("I fail")

    chain.use(bad_mw)
    task = MockTask(id="m3")

    # Should raise
    with pytest.raises(ValueError):
        await chain.run_before(task)
