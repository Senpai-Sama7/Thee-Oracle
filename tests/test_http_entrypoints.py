from __future__ import annotations

import importlib
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

class StubOracleAgent:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []
        self.cfg = SimpleNamespace(model_id="stub-model")
        self.gcs_backup_enabled = False

    def run(self, prompt: str, session_id: str = "default") -> str:
        self.calls.append((prompt, session_id))
        return f"stub:{prompt}"


@pytest.fixture
def oracle_webhook_client(monkeypatch: pytest.MonkeyPatch) -> tuple[TestClient, StubOracleAgent]:
    oracle_webhook_main = importlib.import_module("src.oracle.main")
    stub = StubOracleAgent()
    monkeypatch.setattr(oracle_webhook_main, "agent", stub)
    with TestClient(oracle_webhook_main.app) as client:
        yield client, stub


def test_oracle_webhook_health(oracle_webhook_client: tuple[TestClient, StubOracleAgent]) -> None:
    client, _stub = oracle_webhook_client
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "personal-agent-webhook",
        "agent_type": "OracleAgent",
        "model": "stub-model",
    }


def test_oracle_webhook_uses_last_user_utterance(
    oracle_webhook_client: tuple[TestClient, StubOracleAgent],
) -> None:
    client, stub = oracle_webhook_client
    response = client.post(
        "/webhook",
        json={
            "text": "",
            "sessionInfo": {
                "session": "session-123",
                "parameters": {"last_user_utterance": "check my calendar"},
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["fulfillmentResponse"]["messages"][0]["text"]["text"] == ["stub:check my calendar"]
    assert stub.calls == [("check my calendar", "session-123")]


def test_oracle_chat_endpoint_returns_requested_thread(
    oracle_webhook_client: tuple[TestClient, StubOracleAgent],
) -> None:
    client, stub = oracle_webhook_client
    response = client.post("/chat", json={"message": "hello", "thread_id": "thread-abc"})

    assert response.status_code == 200
    assert response.json() == {"thread_id": "thread-abc", "response": "stub:hello"}
    assert stub.calls == [("hello", "thread-abc")]


@pytest.fixture
def personal_agent_client(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[TestClient, list[tuple[str, str, str, str | None]]]:
    personal_agent_main = importlib.import_module("personal_agent.main")
    if personal_agent_main.app is None:
        pytest.skip("FastAPI is not installed")

    calls: list[tuple[str, str, str, str | None]] = []

    async def fake_handle_input(
        user_input: str,
        session_id: str,
        tag: str = "default",
        image_b64: str | None = None,
    ) -> str:
        calls.append((user_input, session_id, tag, image_b64))
        return f"reply:{user_input}"

    monkeypatch.setattr(personal_agent_main, "handle_input", fake_handle_input)

    with TestClient(personal_agent_main.app) as client:
        yield client, calls


def test_personal_agent_health_endpoint(
    personal_agent_client: tuple[TestClient, list[tuple[str, str, str, str | None]]],
) -> None:
    client, _calls = personal_agent_client
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "vertex_ai_cb" in body
    assert "rabbitmq_cb" in body
    assert "gemini_tokens_available" in body


def test_personal_agent_webhook_uses_handle_input(
    personal_agent_client: tuple[TestClient, list[tuple[str, str, str, str | None]]],
) -> None:
    client, calls = personal_agent_client
    response = client.post(
        "/webhook",
        json={
            "text": "send status update",
            "sessionInfo": {"session": "session-42", "parameters": {"existing": "value"}},
            "fulfillmentInfo": {"tag": "ops"},
            "image_base64": "abc123",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["fulfillmentResponse"]["messages"][0]["text"]["text"] == ["reply:send status update"]
    assert body["sessionInfo"]["parameters"] == {"existing": "value"}
    assert calls == [("send status update", "session-42", "ops", "abc123")]


def test_personal_agent_chat_requires_message(
    personal_agent_client: tuple[TestClient, list[tuple[str, str, str, str | None]]],
) -> None:
    client, _calls = personal_agent_client
    response = client.post("/chat", json={"thread_id": "thread-1"})

    assert response.status_code == 400
    assert response.json()["detail"] == "'message' field is required"


@pytest.fixture
def gui_client(monkeypatch: pytest.MonkeyPatch):
    gui_app = importlib.import_module("gui.app")

    stub_agent = StubOracleAgent()
    stub_config = SimpleNamespace(
        model_id="stub-model",
        gcp_project="test-project",
        gcp_location="us-central1",
        max_turns=20,
        shell_timeout=60,
        http_timeout=15,
        project_root=Path("/tmp/replit"),
    )

    monkeypatch.setenv("ORACLE_API_KEY", "test-key")
    monkeypatch.setattr(gui_app.app_state, "agent", stub_agent, raising=False)
    monkeypatch.setattr(gui_app.app_state, "agent_config", stub_config, raising=False)
    gui_app.app.config["TESTING"] = True

    with gui_app.app.test_client() as client:
        yield client


def test_gui_status_and_health_endpoints(gui_client) -> None:
    status_response = gui_client.get("/api/status")
    health_response = gui_client.get("/api/health")

    assert status_response.status_code == 200
    assert status_response.json["initialized"] is True
    assert status_response.json["model_id"] == "stub-model"

    assert health_response.status_code == 200
    assert health_response.json["status"] == "healthy"
    assert health_response.json["agent_status"]["model_id"] == "stub-model"


def test_gui_help_and_config_endpoints(gui_client) -> None:
    help_response = gui_client.get("/api/help/features")
    config_response = gui_client.get("/api/config", headers={"X-API-Key": "test-key"})

    assert help_response.status_code == 200
    assert set(help_response.json.keys()) == {"ai_conversations", "tools", "settings"}

    assert config_response.status_code == 200
    assert config_response.json["project_root"] == "/tmp/replit"
    assert config_response.json["model_id"] == "stub-model"
