"""
Tests for Hardening Sprint Fixes (March 2026)

Covers:
1. eval() restriction in WorkflowEngine (agent_graph.py)
2. RabbitMQ credential env-var loading (knowledge_worker.py)
3. Health check metrics without agent re-instantiation (health_check.py)
4. Stream failover double-yield prevention (model_router.py)
5. MCP client stdio context key collision fix (mcp_client.py)
"""

import os
import pytest
from unittest.mock import MagicMock
from typing import AsyncIterator

# =============================================================================
# 1. eval() Restriction Tests — agent_graph.py
# =============================================================================

from src.oracle.agent_graph import (
    WorkflowEngine,
    WorkflowDefinition,
    WorkflowStep,
    WorkflowStatus,
    ErrorStrategy,
    AgentGraph,
    AgentNode,
    NodeTask,
    NodeResult,
)
from src.oracle.knowledge_worker import load_env
from src.oracle.model_router import (
    ModelRouter,
    BaseAdapter,
    GenerateResponse,
    StreamChunk,
    TokenUsage,
    ProviderError,
)

pytestmark = pytest.mark.filterwarnings("ignore:coroutine method 'aclose' of '.*stream' was never awaited")


class PassthroughNode(AgentNode):
    """Simple node that succeeds immediately."""

    async def run(self, task: NodeTask) -> NodeResult:
        return NodeResult(
            task_id=task.task_id,
            node_id=self.node_id,
            output="ok",
            tool_calls=[],
            success=True,
            latency_ms=1.0,
        )


def _make_engine() -> WorkflowEngine:
    """Create a WorkflowEngine with a single passthrough node and mock persistence."""
    graph = AgentGraph(registry=None)
    node = PassthroughNode("worker")
    graph.add_node(node)
    mock_persistence = MagicMock()
    return WorkflowEngine(graph, mock_persistence)


class TestEvalRestriction:
    """Verify that eval() in WorkflowEngine.run_workflow is restricted."""

    @pytest.mark.asyncio
    async def test_safe_boolean_condition_passes(self):
        """Normal boolean expressions in workflow variables should work."""
        engine = _make_engine()
        definition = WorkflowDefinition(
            workflow_id="wf-safe",
            name="Safe Workflow",
            steps=[
                WorkflowStep(step_id="s1", node_id="worker", condition="x > 5"),
            ],
            variables={"x": 10},
            on_error=ErrorStrategy.CONTINUE,
        )
        result = await engine.run_workflow(definition)
        assert result.status == WorkflowStatus.COMPLETED
        assert "s1" in result.results  # Step ran because x(10) > 5

    @pytest.mark.asyncio
    async def test_false_condition_skips_step(self):
        """A false condition should skip the step without error."""
        engine = _make_engine()
        definition = WorkflowDefinition(
            workflow_id="wf-skip",
            name="Skip Workflow",
            steps=[
                WorkflowStep(step_id="s1", node_id="worker", condition="x > 100"),
            ],
            variables={"x": 5},
            on_error=ErrorStrategy.CONTINUE,
        )
        result = await engine.run_workflow(definition)
        assert result.status == WorkflowStatus.COMPLETED
        assert "s1" not in result.results  # Step skipped because x(5) <= 100

    @pytest.mark.asyncio
    async def test_eval_blocks_import(self):
        """__import__('os') should be blocked by the restricted eval."""
        engine = _make_engine()
        definition = WorkflowDefinition(
            workflow_id="wf-import",
            name="Import Attack",
            steps=[
                WorkflowStep(
                    step_id="s1",
                    node_id="worker",
                    condition="__import__('os').system('echo pwned')",
                ),
            ],
            variables={},
            on_error=ErrorStrategy.CONTINUE,
        )
        result = await engine.run_workflow(definition)
        # With CONTINUE strategy, the eval error is caught and step is skipped
        assert result.status == WorkflowStatus.COMPLETED
        assert "s1" not in result.results  # Attack was blocked

    @pytest.mark.asyncio
    async def test_eval_blocks_import_stops_on_error(self):
        """__import__ attack with STOP strategy should raise and fail the workflow."""
        engine = _make_engine()
        definition = WorkflowDefinition(
            workflow_id="wf-import-stop",
            name="Import Attack Stop",
            steps=[
                WorkflowStep(
                    step_id="s1",
                    node_id="worker",
                    condition="__import__('os').system('id')",
                ),
            ],
            variables={},
            on_error=ErrorStrategy.STOP,
        )
        result = await engine.run_workflow(definition)
        assert result.status == WorkflowStatus.FAILED
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_eval_blocks_exec(self):
        """exec() should be blocked in restricted eval."""
        engine = _make_engine()
        definition = WorkflowDefinition(
            workflow_id="wf-exec",
            name="Exec Attack",
            steps=[
                WorkflowStep(
                    step_id="s1",
                    node_id="worker",
                    condition="exec('import os')",
                ),
            ],
            variables={},
            on_error=ErrorStrategy.CONTINUE,
        )
        result = await engine.run_workflow(definition)
        assert result.status == WorkflowStatus.COMPLETED
        assert "s1" not in result.results  # exec was blocked

    @pytest.mark.asyncio
    async def test_eval_blocks_open(self):
        """open() should be blocked in restricted eval."""
        engine = _make_engine()
        definition = WorkflowDefinition(
            workflow_id="wf-open",
            name="File Read Attack",
            steps=[
                WorkflowStep(
                    step_id="s1",
                    node_id="worker",
                    condition="open('/etc/passwd').read()",
                ),
            ],
            variables={},
            on_error=ErrorStrategy.CONTINUE,
        )
        result = await engine.run_workflow(definition)
        assert result.status == WorkflowStatus.COMPLETED
        assert "s1" not in result.results  # open was blocked

    @pytest.mark.asyncio
    async def test_eval_allows_arithmetic(self):
        """Basic arithmetic and comparisons should work in restricted eval."""
        engine = _make_engine()
        definition = WorkflowDefinition(
            workflow_id="wf-arith",
            name="Arithmetic",
            steps=[
                WorkflowStep(step_id="s1", node_id="worker", condition="(a + b) > 10"),
            ],
            variables={"a": 7, "b": 5},
            on_error=ErrorStrategy.CONTINUE,
        )
        result = await engine.run_workflow(definition)
        assert result.status == WorkflowStatus.COMPLETED
        assert "s1" in result.results  # 7 + 5 = 12 > 10


# =============================================================================
# 2. RabbitMQ Credential Loading Tests — knowledge_worker.py
# =============================================================================


class TestCredentialLoading:
    """Verify that knowledge_worker reads credentials from env, not hardcoded."""

    def test_load_env_parses_file(self, tmp_path):
        """load_env should parse key=value pairs from .env file."""
        env_file = tmp_path / ".env"
        env_file.write_text("RABBITMQ_HOST=my-rmq-host\nRABBITMQ_USER=admin\nRABBITMQ_PASS=s3cret\n")
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            env = load_env()
            assert env.get("RABBITMQ_HOST") == "my-rmq-host"
            assert env.get("RABBITMQ_USER") == "admin"
            assert env.get("RABBITMQ_PASS") == "s3cret"
        finally:
            os.chdir(original_cwd)

    def test_load_env_missing_file_returns_empty(self, tmp_path):
        """load_env should return empty dict when .env is missing."""
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            env = load_env()
            assert env == {}
        finally:
            os.chdir(original_cwd)

    def test_load_env_skips_comments(self, tmp_path):
        """load_env should skip lines starting with #."""
        env_file = tmp_path / ".env"
        env_file.write_text("# This is a comment\nKEY=value\n")
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            env = load_env()
            assert "# This is a comment" not in env
            assert env.get("KEY") == "value"
        finally:
            os.chdir(original_cwd)

    def test_no_hardcoded_credentials_in_source(self):
        """Verify that knowledge_worker.py does NOT contain hardcoded credentials."""
        import inspect
        import src.oracle.knowledge_worker as kw

        source = inspect.getsource(kw)
        # The old hardcoded password must not be present
        assert "oracle_pass_2026" not in source, "Hardcoded password found in knowledge_worker.py"
        # Verify we use env-var pattern
        assert "RABBITMQ_HOST" in source
        assert "RABBITMQ_USER" in source
        assert "RABBITMQ_PASS" in source


# =============================================================================
# 3. Health Check Metrics Tests — health_check.py
# =============================================================================


class TestHealthCheckMetrics:
    """Verify that health_check.py does not instantiate OracleAgent for metrics."""

    def test_no_oracle_agent_import_in_collect_metrics(self):
        """The collect_metrics path should not import OracleAgent."""
        import inspect
        import src.oracle.health_check as hc

        source = inspect.getsource(hc)
        # There should be no OracleAgent() or OracleConfig() instantiation
        # in the do_GET handler for /metrics
        assert "OracleAgent()" not in source, (
            "OracleAgent() instantiation found in health_check.py — "
            "this causes resource exhaustion under monitoring load"
        )
        assert "OracleConfig()" not in source, "OracleConfig() instantiation found in health_check.py"


# =============================================================================
# 4. Stream Failover Safety Tests — model_router.py
# =============================================================================


class MidStreamFailProvider(BaseAdapter):
    """Provider that yields some tokens then fails mid-stream."""

    def __init__(self, provider_id: str, tokens_before_fail: int = 3):
        super().__init__(provider_id, "mock-model")
        self.tokens_before_fail = tokens_before_fail
        self.call_count = 0

    async def generate(self, messages, tools, config):
        raise ProviderError(self.provider_id, "Not implemented")

    async def stream(self, messages, tools, config) -> AsyncIterator[StreamChunk]:
        self.call_count += 1
        for i in range(self.tokens_before_fail):
            yield StreamChunk(
                delta=f"tok{i}",
                provider_id=self.provider_id,
                model_id=self.model_id,
            )
        # Fail mid-stream by yielding error final chunk
        yield StreamChunk.final(
            provider_id=self.provider_id,
            model_id=self.model_id,
            error="Mid-stream failure",
        )


class HealthyStreamProvider(BaseAdapter):
    """Provider that streams successfully."""

    def __init__(self, provider_id: str):
        super().__init__(provider_id, "mock-model")
        self.call_count = 0

    async def generate(self, messages, tools, config):
        return GenerateResponse(
            content="hello",
            tool_calls=[],
            usage=TokenUsage(10, 10, 20, 0.001),
            provider_id=self.provider_id,
            model_id=self.model_id,
            latency_ms=50.0,
        )

    async def stream(self, messages, tools, config) -> AsyncIterator[StreamChunk]:
        self.call_count += 1
        for word in ["Hello", " World"]:
            yield StreamChunk(
                delta=word,
                provider_id=self.provider_id,
                model_id=self.model_id,
            )
        yield StreamChunk.final(
            provider_id=self.provider_id,
            model_id=self.model_id,
            usage=TokenUsage(5, 5, 10, 0.0),
        )


class TestStreamFailoverSafety:
    """Verify stream failover does not duplicate tokens."""

    @pytest.mark.asyncio
    async def test_mid_stream_failure_does_not_failover(self):
        """If Provider A yields tokens then fails, Provider B should NOT be tried.
        This prevents duplicate/garbled output."""
        failing = MidStreamFailProvider("failing", tokens_before_fail=3)
        backup = HealthyStreamProvider("backup")

        router = ModelRouter([failing, backup], session_id="test-no-dup")

        chunks = []
        async for chunk in router.stream(messages=[{"role": "user", "content": "Hello"}]):
            chunks.append(chunk)

        # The backup provider should NOT have been called since failing yielded tokens
        # (Our fix: once tokens are yielded, no failover)
        non_final = [c for c in chunks if not c.is_final]
        text = "".join(c.delta for c in non_final)

        # We should see tokens from the failing provider (tok0, tok1, tok2)
        # but NOT from the backup provider
        assert "tok0" in text
        assert "Hello World" not in text, (
            "Backup provider was called after mid-stream failure — this would cause duplicate tokens"
        )

    @pytest.mark.asyncio
    async def test_pre_stream_failure_does_failover(self):
        """If Provider A fails BEFORE yielding any tokens, Provider B SHOULD be tried."""
        # Provider that fails immediately with an error chunk (0 real tokens)
        failing = MidStreamFailProvider("failing", tokens_before_fail=0)
        backup = HealthyStreamProvider("backup")

        router = ModelRouter([failing, backup], session_id="test-pre-fail")

        chunks = []
        async for chunk in router.stream(messages=[{"role": "user", "content": "Hello"}]):
            chunks.append(chunk)

        non_final = [c for c in chunks if not c.is_final]
        text = "".join(c.delta for c in non_final)

        # Backup should have been called and yielded its tokens
        assert backup.call_count >= 1
        assert "Hello World" in text


# =============================================================================
# 5. MCP Client Context Key Collision Tests — mcp_client.py
# =============================================================================


class TestMCPContextKeying:
    """Verify MCP client tracks stdio contexts by server name, not command binary."""

    def test_stdio_contexts_keyed_by_name(self):
        """Two servers using same command binary should have separate context entries."""
        import src.oracle.mcp_client as mcp_mod
        import inspect

        source = inspect.getsource(mcp_mod)

        # Verify the fix: the key should use `name` parameter, not just command
        assert "name: str" in source, "_stdio_client_connect should accept a 'name' parameter"
        # The context should be stored under the name key
        assert "key = name or server_params.command" in source, (
            "Context should be keyed by name (with command as fallback)"
        )


# =============================================================================
# 6. .env.example Completeness Test
# =============================================================================


class TestEnvExampleCompleteness:
    """Verify .env.example has all required RabbitMQ credential variables."""

    def test_env_example_has_rabbitmq_credentials(self):
        """The .env.example must include RABBITMQ_HOST, RABBITMQ_USER, RABBITMQ_PASS."""
        env_example_path = os.path.join(os.path.dirname(__file__), "..", ".env.example")
        with open(env_example_path) as f:
            content = f.read()

        assert "RABBITMQ_HOST=" in content, "Missing RABBITMQ_HOST in .env.example"
        assert "RABBITMQ_USER=" in content, "Missing RABBITMQ_USER in .env.example"
        assert "RABBITMQ_PASS=" in content, "Missing RABBITMQ_PASS in .env.example"


# =============================================================================
# 7. pyproject.toml Version Test
# =============================================================================


class TestVersionConsistency:
    """Verify the project version matches across files."""

    def test_pyproject_version_is_v5(self):
        """pyproject.toml should be at version 5.x."""
        pyproject_path = os.path.join(os.path.dirname(__file__), "..", "pyproject.toml")
        with open(pyproject_path) as f:
            content = f.read()

        assert "5.0.0" in content, f"pyproject.toml version should be 5.0.0-alpha, got: {content}"
