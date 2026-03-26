from __future__ import annotations

import importlib
import sys
from typing import Any

import pytest
from fastapi.testclient import TestClient

from src.oracle import agent_system
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


class _FakeResponse:
    def __init__(self, status_code: int, text: str = "", headers: dict[str, str] | None = None) -> None:
        self.status_code = status_code
        self.text = text
        self.headers = headers or {}

    def raise_for_status(self) -> None:
        return None


class _FakeJsonResponse(_FakeResponse):
    def __init__(self, status_code: int, payload: dict[str, Any]) -> None:
        super().__init__(status_code, headers={"content-type": "application/json"})
        self._payload = payload

    def json(self) -> dict[str, Any]:
        return self._payload


def test_http_fetch_rejects_non_http_schemes(tmp_path) -> None:
    executor = ToolExecutor(tmp_path, shell_timeout=5, http_timeout=5)

    result = executor.http_fetch("file:///etc/passwd")

    assert result == {"success": False, "error": "Only absolute http(s) URLs are allowed"}


def test_http_fetch_rejects_private_hosts(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    executor = ToolExecutor(tmp_path, shell_timeout=5, http_timeout=5)

    def fail_request(*args: Any, **kwargs: Any) -> _FakeResponse:
        raise AssertionError("requests.request should not be called for blocked private hosts")

    monkeypatch.setattr(agent_system.requests, "request", fail_request)

    for url in (
        "http://127.0.0.1/admin",
        "http://localhost/health",
        "http://169.254.169.254/latest/meta-data",
    ):
        result = executor.http_fetch(url)
        assert result == {
            "success": False,
            "error": "Private, loopback, link-local, localhost, and metadata targets are not allowed",
        }


def test_http_fetch_blocks_redirect_responses(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    executor = ToolExecutor(tmp_path, shell_timeout=5, http_timeout=5)

    def fake_request(*args: Any, **kwargs: Any) -> _FakeResponse:
        assert kwargs["allow_redirects"] is False
        return _FakeResponse(302, headers={"location": "http://127.0.0.1/admin"})

    monkeypatch.setattr(agent_system.requests, "request", fake_request)

    result = executor.http_fetch("https://8.8.8.8/example")

    assert result == {
        "success": False,
        "status": 302,
        "error": "Redirect responses are not allowed",
    }


def test_http_fetch_allows_private_hosts_when_explicitly_enabled(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    executor = ToolExecutor(tmp_path, shell_timeout=5, http_timeout=5)
    monkeypatch.setenv("ORACLE_ALLOW_PRIVATE_HTTP", "true")

    def fake_request(*args: Any, **kwargs: Any) -> _FakeResponse:
        assert kwargs["allow_redirects"] is False
        return _FakeResponse(200, text="ok")

    monkeypatch.setattr(agent_system.requests, "request", fake_request)

    result = executor.http_fetch("http://127.0.0.1:8080/internal")

    assert result == {
        "success": True,
        "status": 200,
        "url": "http://127.0.0.1:8080/internal",
        "content": "ok",
        "truncated": False,
    }


def test_http_fetch_disables_redirects_for_public_targets(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    executor = ToolExecutor(tmp_path, shell_timeout=5, http_timeout=5)
    captured: dict[str, Any] = {}

    def fake_request(method: str, url: str, **kwargs: Any) -> _FakeResponse:
        captured["method"] = method
        captured["url"] = url
        captured.update(kwargs)
        return _FakeResponse(200, text="ok")

    monkeypatch.setattr(agent_system.requests, "request", fake_request)

    result = executor.http_fetch("https://8.8.8.8/example", method="post")

    assert result["success"] is True
    assert captured["method"] == "POST"
    assert captured["url"] == "https://8.8.8.8/example"
    assert captured["allow_redirects"] is False


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
    with pytest.raises(ValueError, match=r"Only absolute http\(s\) URLs are allowed"):
        integration.execute("read", {"method": "GET"})


def test_integration_rejects_private_http_urls(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_get(*args: Any, **kwargs: Any) -> _FakeResponse:
        raise AssertionError("requests.get should not be called for blocked private hosts")

    monkeypatch.setattr("src.oracle.integration_framework.requests.get", fail_get)

    integration = Integration("test", IntegrationType.API, {"url": "http://127.0.0.1/internal"})

    assert integration.connect() is False
    with pytest.raises(
        ValueError,
        match="Private, loopback, link-local, localhost, and metadata targets are not allowed",
    ):
        integration.execute("read", {"method": "GET"})


def test_integration_blocks_redirect_responses(monkeypatch: pytest.MonkeyPatch) -> None:
    integration = Integration("test", IntegrationType.API, {"url": "https://8.8.8.8/api"})

    def fake_request(*args: Any, **kwargs: Any) -> _FakeResponse:
        assert kwargs["allow_redirects"] is False
        return _FakeResponse(302)

    monkeypatch.setattr("src.oracle.integration_framework.requests.request", fake_request)

    with pytest.raises(ValueError, match="Redirect responses are not allowed"):
        integration.execute("read", {"method": "GET"})


def test_integration_allows_private_hosts_when_explicitly_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ORACLE_ALLOW_PRIVATE_HTTP", "true")
    integration = Integration("test", IntegrationType.API, {"url": "http://127.0.0.1/internal"})

    def fake_get(*args: Any, **kwargs: Any) -> _FakeResponse:
        assert kwargs["allow_redirects"] is False
        return _FakeResponse(200)

    def fake_request(*args: Any, **kwargs: Any) -> _FakeJsonResponse:
        assert kwargs["allow_redirects"] is False
        return _FakeJsonResponse(200, {"ok": True})

    monkeypatch.setattr("src.oracle.integration_framework.requests.get", fake_get)
    monkeypatch.setattr("src.oracle.integration_framework.requests.request", fake_request)

    assert integration.connect() is True
    assert integration.execute("read", {"method": "GET"}) == {"status_code": 200, "data": {"ok": True}}


def test_simple_workflow_engine_allows_safe_condition() -> None:
    engine = SimpleWorkflowEngine()

    assert engine._safe_eval("(a + b) > 10", {"a": 7, "b": 5}) is True


def test_simple_workflow_engine_blocks_unsafe_eval() -> None:
    engine = SimpleWorkflowEngine()

    with pytest.raises(ValueError, match="Only direct builtin calls are allowed|Unsafe function call"):
        engine._safe_eval("__import__('os').system('id')", {})


@pytest.mark.asyncio
async def test_simple_workflow_engine_rejects_private_api_urls() -> None:
    engine = SimpleWorkflowEngine()

    with pytest.raises(
        ValueError,
        match="Private, loopback, link-local, localhost, and metadata targets are not allowed",
    ):
        await engine._execute_api_step({"url": "http://127.0.0.1:8000/admin"}, {})


@pytest.mark.asyncio
async def test_simple_workflow_engine_blocks_redirect_responses(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = SimpleWorkflowEngine()

    def fake_request(*args: Any, **kwargs: Any) -> _FakeResponse:
        assert kwargs["allow_redirects"] is False
        return _FakeResponse(302)

    monkeypatch.setattr("src.oracle.workflow_engine.requests.request", fake_request)

    with pytest.raises(ValueError, match="Redirect responses are not allowed"):
        await engine._execute_api_step({"url": "https://8.8.8.8/api", "method": "GET"}, {})


@pytest.mark.asyncio
async def test_simple_workflow_engine_disables_shell_steps_by_default() -> None:
    engine = SimpleWorkflowEngine()

    with pytest.raises(ValueError, match="Shell workflow steps are disabled by default"):
        await engine._execute_shell_step({"command": "echo hello"}, {})


@pytest.mark.asyncio
async def test_simple_workflow_engine_allows_shell_steps_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = SimpleWorkflowEngine()
    monkeypatch.setenv("ORACLE_ENABLE_WORKFLOW_SHELL", "true")
    monkeypatch.setattr("src.oracle.workflow_engine.which", lambda name: "/bin/bash" if name == "bash" else None)

    class _ShellResult:
        stdout = "hello\n"
        stderr = ""
        returncode = 0

    def fake_run(*args: Any, **kwargs: Any) -> _ShellResult:
        assert args[0] == ["/bin/bash", "-lc", "echo hello"]
        return _ShellResult()

    monkeypatch.setattr("src.oracle.workflow_engine.subprocess.run", fake_run)

    result = await engine._execute_shell_step({"command": "echo hello"}, {})

    assert result == {"stdout": "hello\n", "stderr": "", "returncode": 0}
