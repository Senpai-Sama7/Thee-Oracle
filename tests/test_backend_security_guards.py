from __future__ import annotations

import importlib
import sys

import pytest
from fastapi.testclient import TestClient

from src.oracle.agent_system import ToolExecutor
from src.oracle.integration_framework import Integration, IntegrationType
from src.oracle.workflow_engine import WorkflowEngine as SimpleWorkflowEngine


class StubOracleAgent:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []
        self.cfg = type("Cfg", (), {"model_id": "stub-model"})()

    def run(self, prompt: str, session_id: str = "default") -> str:
        self.calls.append((prompt, session_id))
        return f"stub:{prompt}"


def _reload_module(module_name: str):
    sys.modules.pop(module_name, None)
    return importlib.import_module(module_name)


def test_http_fetch_rejects_non_http_schemes(tmp_path) -> None:
    executor = ToolExecutor(tmp_path, shell_timeout=5, http_timeout=5)

    result = executor.http_fetch("file:///etc/passwd")

    assert result == {"success": False, "error": "Only absolute http(s) URLs are allowed"}


def test_oracle_webhook_requires_api_key_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WEBHOOK_API_KEY", "secret-key")
    oracle_webhook_main = _reload_module("src.oracle.main")
    oracle_webhook_main.agent = StubOracleAgent()

    with TestClient(oracle_webhook_main.app) as client:
        unauthorized = client.post("/chat", json={"message": "hello", "thread_id": "t-1"})
        authorized = client.post(
            "/chat",
            json={"message": "hello", "thread_id": "t-1"},
            headers={"X-API-Key": "secret-key"},
        )

    assert unauthorized.status_code == 403
    assert authorized.status_code == 200
    assert authorized.json() == {"thread_id": "t-1", "response": "stub:hello"}


def test_personal_agent_requires_api_key_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PERSONAL_AGENT_API_KEY", "secret-key")
    personal_agent_main = _reload_module("personal_agent.main")
    if personal_agent_main.app is None:
        pytest.skip("FastAPI is not installed")

    async def fake_handle_input(
        user_input: str,
        session_id: str,
        tag: str = "default",
        image_b64: str | None = None,
    ) -> str:
        del image_b64
        return f"reply:{user_input}:{session_id}:{tag}"

    monkeypatch.setattr(personal_agent_main, "handle_input", fake_handle_input)

    with TestClient(personal_agent_main.app) as client:
        unauthorized = client.post("/chat", json={"message": "hello", "thread_id": "t-1"})
        authorized = client.post(
            "/chat",
            json={"message": "hello", "thread_id": "t-1"},
            headers={"X-API-Key": "secret-key"},
        )

    assert unauthorized.status_code == 403
    assert authorized.status_code == 200
    assert authorized.json()["response"] == "reply:hello:t-1:chat"


def test_integration_rejects_non_http_urls() -> None:
    integration = Integration("test", IntegrationType.API, {"url": "file:///etc/passwd"})

    assert integration.connect() is False
    with pytest.raises(ValueError, match="API integration missing URL"):
        integration.execute("read", {"method": "GET"})


def test_simple_workflow_engine_allows_safe_condition() -> None:
    engine = SimpleWorkflowEngine()

    assert engine._safe_eval("(a + b) > 10", {"a": 7, "b": 5}) is True


def test_simple_workflow_engine_blocks_unsafe_eval() -> None:
    engine = SimpleWorkflowEngine()

    with pytest.raises(ValueError, match="Only direct builtin calls are allowed|Unsafe function call"):
        engine._safe_eval("__import__('os').system('id')", {})
