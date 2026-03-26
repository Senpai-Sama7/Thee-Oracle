"""
Tests for Model Router - Phase 1: Multi-LLM Support

Covers:
- ModelProvider protocol compliance
- Cost tracking accuracy
- ModelRouter failover behavior
- Streaming token order preservation
- Provider error handling
"""

import pytest
import asyncio
from typing import Any, AsyncIterator

from src.oracle.model_router import (
    ModelRouter,
    GenerateConfig,
    GenerateResponse,
    StreamChunk,
    TokenUsage,
    ToolCall,
    ProviderHealth,
    ProviderError,
    CostTracker,
    BaseAdapter,
    create_provider_from_config,
    get_cost_tracker,
)

pytestmark = pytest.mark.filterwarnings("ignore:coroutine method 'aclose' of 'MockProvider.stream' was never awaited")


# =============================================================================
# Fixtures and Mocks
# =============================================================================


class MockProvider(BaseAdapter):
    """Mock provider for testing."""

    def __init__(
        self, provider_id: str, model_id: str = "mock-model", should_fail: bool = False, fail_count: int = 999
    ):
        super().__init__(provider_id, model_id)
        self.should_fail = should_fail
        self.fail_count = fail_count  # Number of times to fail (default: always fail if should_fail)
        self.call_count = 0
        self.generated_responses: list[str] = []

    async def generate(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        config: GenerateConfig,
    ) -> GenerateResponse:
        self.call_count += 1

        if self.should_fail and self.call_count <= self.fail_count:
            raise ProviderError(self.provider_id, f"Mock failure {self.call_count}")

        content = f"Response from {self.provider_id}"
        self.generated_responses.append(content)

        return GenerateResponse(
            content=content,
            tool_calls=[],
            usage=TokenUsage(10, 10, 20, 0.001),
            provider_id=self.provider_id,
            model_id=self.model_id,
            latency_ms=100.0,
        )

    async def stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        config: GenerateConfig,
    ) -> AsyncIterator[StreamChunk]:
        self.call_count += 1

        if self.should_fail and self.call_count <= self.fail_count:
            # Yield error final chunk instead of raising
            yield StreamChunk.final(
                provider_id=self.provider_id, model_id=self.model_id, error=f"Mock stream failure {self.call_count}"
            )
            return

        # Yield tokens
        tokens = ["Hello", " from", " ", self.provider_id]
        for token in tokens:
            yield StreamChunk(delta=token, provider_id=self.provider_id, model_id=self.model_id)

        # Final chunk
        yield StreamChunk.final(
            provider_id=self.provider_id, model_id=self.model_id, usage=TokenUsage(10, 10, 20, 0.001)
        )


@pytest.fixture
def reset_cost_tracker():
    """Reset the global cost tracker before each test."""
    tracker = get_cost_tracker()
    tracker.reset()
    yield tracker
    tracker.reset()


@pytest.fixture
def mock_providers():
    """Create a set of mock providers for testing."""
    return {
        "primary": MockProvider("primary", "model-1"),
        "secondary": MockProvider("secondary", "model-2"),
        "tertiary": MockProvider("tertiary", "model-3"),
    }


# =============================================================================
# Cost Tracking Tests
# =============================================================================


class TestCostTracker:
    """Test cost tracking functionality."""

    def test_calculate_cost_known_models(self):
        """Cost calculation for known models should return non-zero."""
        tracker = CostTracker()

        # Gemini 2.0 Flash has non-zero pricing
        cost = tracker.calculate_cost("gemini-2.0-flash", 1000, 500)
        assert cost > 0

        # GPT-4o has non-zero pricing
        cost = tracker.calculate_cost("gpt-4o", 1000, 500)
        assert cost > 0

        # Claude Sonnet has non-zero pricing
        cost = tracker.calculate_cost("claude-3-5-sonnet-20241022", 1000, 500)
        assert cost > 0

    def test_calculate_cost_free_models(self):
        """Free tier models should return zero cost."""
        tracker = CostTracker()

        # Gemini 2.0 Flash Exp is free
        cost = tracker.calculate_cost("gemini-2.0-flash-exp", 10000, 5000)
        assert cost == 0.0

        # Ollama is local and free
        cost = tracker.calculate_cost("llama3", 10000, 5000)
        assert cost == 0.0

    def test_calculate_cost_unknown_model(self):
        """Unknown models should return zero cost."""
        tracker = CostTracker()
        cost = tracker.calculate_cost("unknown-model-v99", 1000, 500)
        assert cost == 0.0

    def test_token_usage_addition(self):
        """TokenUsage should support addition."""
        u1 = TokenUsage(100, 50, 150, 0.01)
        u2 = TokenUsage(200, 100, 300, 0.02)

        total = u1 + u2

        assert total.prompt_tokens == 300
        assert total.completion_tokens == 150
        assert total.total_tokens == 450
        assert total.cost_usd == 0.03

    @pytest.mark.asyncio
    async def test_record_usage_updates_totals(self, reset_cost_tracker):
        """Recording usage should update both session and total stats."""
        tracker = reset_cost_tracker

        usage1 = TokenUsage(100, 50, 150, None)  # Cost will be calculated
        await tracker.record_usage("session-1", "gpt-4o", usage1)

        # Check session cost
        session_cost = tracker.get_session_cost("session-1")
        assert session_cost > 0

        # Check total cost
        total_cost = tracker.get_total_cost()
        assert total_cost == session_cost

        # Add more usage to same session
        usage2 = TokenUsage(200, 100, 300, None)
        await tracker.record_usage("session-1", "gpt-4o", usage2)

        # Session cost should accumulate
        new_session_cost = tracker.get_session_cost("session-1")
        assert new_session_cost > session_cost

        # Different session
        await tracker.record_usage("session-2", "gpt-4o", usage1)
        assert tracker.get_session_cost("session-2") == session_cost

    def test_get_stats_structure(self):
        """get_stats should return correct structure."""
        tracker = CostTracker()
        stats = tracker.get_stats()

        assert "total_cost_usd" in stats
        assert "by_model" in stats


# =============================================================================
# ModelRouter Failover Tests
# =============================================================================


class TestModelRouterFailover:
    """Test ModelRouter failover behavior."""

    @pytest.mark.asyncio
    async def test_single_provider_success(self):
        """With one healthy provider, should succeed immediately."""
        provider = MockProvider("gemini")
        router = ModelRouter([provider], session_id="test")

        response = await router.generate(messages=[{"role": "user", "content": "Hello"}])

        assert not response.is_error
        assert response.provider_id == "gemini"
        assert provider.call_count == 1

    @pytest.mark.asyncio
    async def test_failover_to_secondary(self):
        """If primary fails, should failover to secondary."""
        primary = MockProvider("primary", should_fail=True, fail_count=1)
        secondary = MockProvider("secondary")

        router = ModelRouter([primary, secondary], session_id="test")

        response = await router.generate(messages=[{"role": "user", "content": "Hello"}])

        assert not response.is_error
        assert response.provider_id == "secondary"
        assert primary.call_count == 1
        assert secondary.call_count == 1

    @pytest.mark.asyncio
    async def test_failover_chain_exhaustion(self):
        """If all providers fail, should return error response."""
        p1 = MockProvider("p1", should_fail=True)  # Always fails
        p2 = MockProvider("p2", should_fail=True)  # Always fails
        p3 = MockProvider("p3", should_fail=True)  # Always fails

        router = ModelRouter([p1, p2, p3], session_id="test")

        response = await router.generate(messages=[{"role": "user", "content": "Hello"}])

        assert response.is_error
        assert "All providers exhausted" in (response.error or "")
        assert p1.call_count == 1
        assert p2.call_count == 1
        assert p3.call_count == 1

    @pytest.mark.asyncio
    async def test_failover_skips_unhealthy(self):
        """Should skip providers marked as unhealthy."""
        healthy = MockProvider("healthy")
        unhealthy = MockProvider("unhealthy")

        # Mark unhealthy
        unhealthy._health.healthy = False

        router = ModelRouter([unhealthy, healthy], session_id="test")
        router._health_status["unhealthy"] = unhealthy._health

        response = await router.generate(messages=[{"role": "user", "content": "Hello"}])

        assert not response.is_error
        assert response.provider_id == "healthy"
        assert unhealthy.call_count == 0
        assert healthy.call_count == 1

    @pytest.mark.asyncio
    async def test_empty_chain_returns_error(self):
        """Empty provider chain should return error."""
        router = ModelRouter([], session_id="test")

        response = await router.generate(messages=[{"role": "user", "content": "Hello"}])

        assert response.is_error
        assert "No providers configured" in (response.error or "")


# =============================================================================
# Streaming Tests
# =============================================================================


class TestStreaming:
    """Test streaming response handling."""

    @pytest.mark.asyncio
    async def test_stream_tokens_in_order(self):
        """Stream tokens should arrive in correct order."""
        provider = MockProvider("gemini")
        router = ModelRouter([provider], session_id="test")

        chunks = []
        async for chunk in router.stream(messages=[{"role": "user", "content": "Hello"}]):
            chunks.append(chunk)

        # Should have multiple chunks plus final
        assert len(chunks) >= 2

        # Tokens should be in order
        non_final = [c for c in chunks if not c.is_final]
        text = "".join(c.delta for c in non_final)
        assert "Hello from gemini" in text

        # Last chunk should be final
        assert chunks[-1].is_final

    @pytest.mark.asyncio
    async def test_stream_failover(self):
        """Should failover to next provider if stream fails."""
        failing = MockProvider("failing", should_fail=True, fail_count=1)
        backup = MockProvider("backup")

        router = ModelRouter([failing, backup], session_id="test")

        chunks = []
        async for chunk in router.stream(messages=[{"role": "user", "content": "Hello"}]):
            chunks.append(chunk)

        # Should get tokens from backup (first provider failed)
        non_final = [c for c in chunks if not c.is_final]
        text = "".join(c.delta for c in non_final)
        # Since failing returns error final chunk immediately, we should get backup tokens
        assert "backup" in text, f"Expected 'backup' in text, got: {text!r}"

        assert chunks[-1].is_final

    @pytest.mark.asyncio
    async def test_stream_all_fail(self):
        """Should return error final chunk if all streams fail."""
        p1 = MockProvider("p1", should_fail=True, fail_count=1)
        p2 = MockProvider("p2", should_fail=True, fail_count=1)

        router = ModelRouter([p1, p2], session_id="test")

        chunks = []
        async for chunk in router.stream(messages=[{"role": "user", "content": "Hello"}]):
            chunks.append(chunk)

        # Should get error final chunks from both providers + one from router
        final_chunks = [c for c in chunks if c.is_final]
        assert len(final_chunks) >= 1
        # Last chunk should indicate exhaustion
        assert chunks[-1].is_final


# =============================================================================
# Health Check Tests
# =============================================================================


class TestHealthChecks:
    """Test provider health check functionality."""

    @pytest.mark.asyncio
    async def test_health_loop_updates_status(self):
        """Health loop should update provider status."""
        provider = MockProvider("gemini")
        router = ModelRouter([provider], health_interval=0.1, session_id="test")

        await router.start()
        await asyncio.sleep(0.2)  # Let health check run
        await router.stop()

        status = router.get_chain_status()
        assert len(status) == 1
        assert status[0].provider_id == "gemini"
        assert status[0].last_checked > 0

    @pytest.mark.asyncio
    async def test_consecutive_failures_mark_unhealthy(self):
        """After 3 consecutive failures, provider should be unhealthy."""
        health = ProviderHealth("test", healthy=True, latency_ms=0)

        # 2 failures - still healthy
        health.consecutive_failures = 2
        assert health.is_healthy

        # 3 failures - unhealthy
        health.consecutive_failures = 3
        assert not health.is_healthy

    @pytest.mark.asyncio
    async def test_healthy_providers_list(self):
        """_get_healthy_providers should filter correctly."""
        healthy = MockProvider("healthy")
        unhealthy = MockProvider("unhealthy")

        router = ModelRouter([unhealthy, healthy], session_id="test")
        router._health_status["unhealthy"] = ProviderHealth("unhealthy", healthy=False, latency_ms=0)

        healthy_list = router._get_healthy_providers()
        assert len(healthy_list) == 1
        assert healthy_list[0].provider_id == "healthy"


# =============================================================================
# Provider Factory Tests
# =============================================================================


class TestProviderFactory:
    """Test provider creation from config."""

    def test_create_gemini_provider(self):
        """Should create GeminiAdapter from config."""
        config = {
            "provider": "gemini",
            "model": "gemini-2.0-flash-exp",
            "project_id": "test-project",
            "location": "us-central1",
        }

        # Skip if genai not available
        try:
            provider = create_provider_from_config(config)
            assert provider.provider_id == "gemini"
        except ImportError:
            pytest.skip("google-genai not installed")

    def test_create_ollama_provider(self):
        """Should create OllamaAdapter from config."""
        config = {"provider": "ollama", "model": "llama3.1", "base_url": "http://localhost:11434"}

        provider = create_provider_from_config(config)
        assert provider.provider_id == "ollama"
        assert provider.model_id == "llama3.1"

    def test_unknown_provider_raises(self):
        """Unknown provider type should raise ValueError."""
        config = {"provider": "unknown", "model": "model-v1"}

        with pytest.raises(ValueError) as exc:
            create_provider_from_config(config)

        assert "unknown" in str(exc.value).lower()


# =============================================================================
# GenerateResponse Tests
# =============================================================================


class TestGenerateResponse:
    """Test GenerateResponse data model."""

    def test_success_response(self):
        """Successful response should have correct properties."""
        response = GenerateResponse(
            content="Hello world",
            tool_calls=[],
            usage=TokenUsage(10, 5, 15, 0.001),
            provider_id="gemini",
            model_id="gemini-2.0-flash",
            latency_ms=100.0,
        )

        assert not response.is_error
        assert response.content == "Hello world"
        assert response.provider_id == "gemini"

    def test_error_response(self):
        """Error response should have correct properties."""
        response = GenerateResponse.make_error("gemini", "Rate limit exceeded")

        assert response.is_error
        assert "Rate limit exceeded" in (response.error or "")
        assert response.content == ""

    def test_error_response_with_finish_reason(self):
        """Response with error in finish_reason should be marked as error."""
        response = GenerateResponse(
            content="",
            tool_calls=[],
            usage=TokenUsage(0, 0, 0, None),
            provider_id="test",
            model_id="test",
            latency_ms=0.0,
            finish_reason="error: timeout",
        )

        assert response.is_error


# =============================================================================
# Tool Call Tests
# =============================================================================


class TestToolCalls:
    """Test tool call handling."""

    @pytest.mark.asyncio
    async def test_tool_calls_in_response(self):
        """Tool calls should be properly returned."""

        class ToolProvider(BaseAdapter):
            async def generate(self, messages, tools, config):
                return GenerateResponse(
                    content="",
                    tool_calls=[ToolCall(id="call_1", name="shell_execute", arguments={"command": "echo hello"})],
                    usage=TokenUsage(10, 5, 15, 0.001),
                    provider_id=self.provider_id,
                    model_id=self.model_id,
                    latency_ms=100.0,
                )

            async def stream(self, messages, tools, config):
                yield StreamChunk(
                    delta="",
                    tool_call_delta=ToolCall(id="call_1", name="shell_execute", arguments={"command": "echo hello"}),
                    provider_id=self.provider_id,
                    model_id=self.model_id,
                )
                yield StreamChunk.final(
                    provider_id=self.provider_id, model_id=self.model_id, usage=TokenUsage(10, 5, 15, 0.001)
                )

        provider = ToolProvider("test", "model")
        router = ModelRouter([provider], session_id="test")

        response = await router.generate(
            messages=[{"role": "user", "content": "Run a command"}],
            tools=[
                {
                    "name": "shell_execute",
                    "description": "Execute shell command",
                    "parameters": {"type": "object", "properties": {}},
                }
            ],
        )

        assert len(response.tool_calls) == 1
        assert response.tool_calls[0].name == "shell_execute"
        assert response.tool_calls[0].arguments["command"] == "echo hello"


# =============================================================================
# Integration Tests
# =============================================================================


class TestIntegration:
    """Integration tests for ModelRouter."""

    @pytest.mark.asyncio
    async def test_full_request_flow(self, reset_cost_tracker):
        """Test complete request flow with cost tracking."""
        p1 = MockProvider("gemini", model_id="gemini-2.0-flash")
        p2 = MockProvider("openai", model_id="gpt-4o")

        router = ModelRouter([p1, p2], session_id="integration-test")

        # Make request
        response = await router.generate(messages=[{"role": "user", "content": "Hello"}])

        # Verify response
        assert not response.is_error
        assert response.provider_id == "gemini"  # First provider

        # Verify cost tracking
        stats = router.get_cost_stats()
        assert stats["session_id"] == "integration-test"
        assert stats["session_cost_usd"] > 0

        # Stream
        chunks = []
        async for chunk in router.stream(messages=[{"role": "user", "content": "Hello"}]):
            chunks.append(chunk)

        # Verify stream
        assert chunks[-1].is_final

    @pytest.mark.asyncio
    async def test_cost_accumulation(self, reset_cost_tracker):
        """Multiple requests should accumulate costs correctly."""
        provider = MockProvider("gemini")
        router = ModelRouter([provider], session_id="cost-test")

        # Make multiple requests
        for _ in range(3):
            await router.generate(messages=[{"role": "user", "content": "Hello"}])

        stats = router.get_cost_stats()
        assert stats["session_cost_usd"] > 0
        # Should be roughly 3x a single request
        assert provider.call_count == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
