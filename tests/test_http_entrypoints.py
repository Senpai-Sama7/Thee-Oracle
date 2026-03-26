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
        self.reload_count = 0
        self.dispatched_tools: list[tuple[str, dict[str, object]]] = []
        self.cleared_sessions: list[str] = []
        self._tool_registry = None
        self.db = SimpleNamespace(save_history=self._save_history)
        self.skill_catalog = [
            {
                "name": "code-review-guidance",
                "description": "Repository-local code review procedure.",
                "source_type": "skill_package",
                "triggers": ["code review", "security audit"],
                "allowed_tools": ["shell_execute", "file_system_ops"],
                "tool_names": ["code_review_notes"],
                "resources": {
                    "scripts": ["scripts/run_review.py"],
                    "references": ["references/checklist.md"],
                    "assets": [],
                },
            },
            {
                "name": "incident-ops",
                "description": "Incident response operating procedure.",
                "source_type": "skill_package",
                "triggers": ["incident", "rollback"],
                "allowed_tools": [],
                "tool_names": [],
                "resources": {
                    "scripts": [],
                    "references": ["references/runbook.md"],
                    "assets": ["assets/war-room.png"],
                },
            },
        ]

    def run(self, prompt: str, session_id: str = "default") -> str:
        self.calls.append((prompt, session_id))
        return f"stub:{prompt}"

    def get_skill_catalog(self) -> list[dict[str, object]]:
        return self.skill_catalog

    def reload_skills(self) -> list[dict[str, object]]:
        self.reload_count += 1
        return self.skill_catalog

    def _dispatch(self, tool_name: str, args: dict[str, object]) -> dict[str, object]:
        self.dispatched_tools.append((tool_name, args))
        return {"success": True, "tool": tool_name, "args": args}

    def backup_to_gcs(self) -> dict[str, object]:
        return {"success": True, "gcs_uri": "gs://oracle/test-backup"}

    def _save_history(self, session_id: str, history: list[object]) -> None:
        assert history == []
        self.cleared_sessions.append(session_id)


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
def gui_app_module(monkeypatch: pytest.MonkeyPatch):
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

    return gui_app


@pytest.fixture
def gui_client(gui_app_module):
    gui_app = gui_app_module

    with gui_app.app.test_client() as client:
        yield client


def test_gui_status_and_health_endpoints(gui_client) -> None:
    status_response = gui_client.get("/api/status")
    health_response = gui_client.get("/api/health")

    assert status_response.status_code == 200
    assert status_response.json["initialized"] is True
    assert status_response.json["model_id"] == "stub-model"
    assert status_response.json["skill_count"] == 2
    assert status_response.json["transport"]["mode"] == "socketio"

    assert health_response.status_code == 200
    assert health_response.json["status"] == "healthy"
    assert health_response.json["agent_status"]["model_id"] == "stub-model"
    assert health_response.json["skill_count"] == 2
    assert health_response.json["transport"]["mode"] == "socketio"
    assert health_response.headers["X-Content-Type-Options"] == "nosniff"
    assert health_response.headers["X-Frame-Options"] == "SAMEORIGIN"
    assert "default-src 'self'" in health_response.headers["Content-Security-Policy"]


def test_gui_help_and_config_endpoints(gui_client) -> None:
    help_response = gui_client.get("/api/help/features")
    config_response = gui_client.get("/api/config", headers={"X-API-Key": "test-key"})

    assert help_response.status_code == 200
    assert set(help_response.json.keys()) == {"ai_conversations", "tools", "settings", "skills"}

    assert config_response.status_code == 200
    assert config_response.json["project_root"] == "/tmp/replit"
    assert config_response.json["model_id"] == "stub-model"


def test_gui_index_exposes_http_fallback_mode(gui_client, gui_app_module, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VERCEL", "1")

    response = gui_client.get("/")
    status_response = gui_client.get("/api/status")

    assert response.status_code == 200
    assert 'data-realtime-enabled="false"' in response.get_data(as_text=True)
    assert status_response.json["transport"]["mode"] == "http-fallback"


def test_gui_http_fallback_endpoints(gui_client, gui_app_module) -> None:
    chat_response = gui_client.post(
        "/api/chat",
        json={"message": "hello from http", "session_id": "session-http"},
        headers={"X-API-Key": "test-key"},
    )
    tool_response = gui_client.post(
        "/api/tools/execute",
        json={"tool": "shell_execute", "args": {"command": "pwd"}},
        headers={"X-API-Key": "test-key"},
    )
    backup_response = gui_client.post("/api/backup", headers={"X-API-Key": "test-key"})
    clear_response = gui_client.post(
        "/api/history/clear",
        json={"session_id": "session-http"},
        headers={"X-API-Key": "test-key"},
    )

    assert chat_response.status_code == 200
    assert chat_response.json["response"] == "stub:hello from http"
    assert gui_app_module.app_state.agent.calls[-1] == ("hello from http", "session-http")

    assert tool_response.status_code == 200
    assert tool_response.json["tool"] == "shell_execute"
    assert gui_app_module.app_state.agent.dispatched_tools[-1] == ("shell_execute", {"command": "pwd"})

    assert backup_response.status_code == 200
    assert backup_response.json["success"] is True

    assert clear_response.status_code == 200
    assert gui_app_module.app_state.agent.cleared_sessions[-1] == "session-http"


def test_gui_skills_endpoints(gui_client, gui_app_module) -> None:
    skills_response = gui_client.get("/api/skills")
    reload_response = gui_client.post("/api/skills/reload", headers={"X-API-Key": "test-key"})

    assert skills_response.status_code == 200
    assert skills_response.json["count"] == 2
    assert skills_response.json["tool_count"] == 1
    first_skill = skills_response.json["skills"][0]
    assert "manifest_path" not in first_skill
    assert "root_path" not in first_skill

    assert reload_response.status_code == 200
    assert reload_response.json["success"] is True
    assert reload_response.json["count"] == 2
    assert gui_app_module.app_state.agent.reload_count == 1


def test_gui_config_requires_api_key(gui_client) -> None:
    config_response = gui_client.get("/api/config")
    settings_response = gui_client.get("/api/settings")
    reset_response = gui_client.post("/api/settings/reset")

    assert config_response.status_code == 401
    assert config_response.json["error"] == "Unauthorized"
    assert settings_response.status_code == 401
    assert settings_response.json["error"] == "Unauthorized"
    assert reset_response.status_code == 401
    assert reset_response.json["error"] == "Unauthorized"


def test_gui_socket_connection_requires_api_key(gui_app_module) -> None:
    unauthorized_client = gui_app_module.socketio.test_client(gui_app_module.app)
    assert not unauthorized_client.is_connected()

    authorized_client = gui_app_module.socketio.test_client(
        gui_app_module.app,
        auth={"apiKey": "test-key"},
    )

    assert authorized_client.is_connected()
    authorized_client.disconnect()


def test_gui_socket_rejects_unsupported_tool(gui_app_module) -> None:
    authorized_client = gui_app_module.socketio.test_client(
        gui_app_module.app,
        auth={"apiKey": "test-key"},
    )
    assert authorized_client.is_connected()

    authorized_client.emit("execute_tool", {"tool": "dangerous_tool", "args": {}})
    events = authorized_client.get_received()

    assert any(
        event["name"] == "error" and event["args"][0]["message"] == "Unsupported tool"
        for event in events
    )
    authorized_client.disconnect()


def test_gui_socket_cors_defaults_to_same_origin(monkeypatch: pytest.MonkeyPatch, gui_app_module) -> None:
    monkeypatch.delenv("ORACLE_GUI_CORS_ORIGINS", raising=False)

    assert gui_app_module.get_socket_cors_origins() is None


def test_gui_socket_wildcard_cors_requires_explicit_override(
    monkeypatch: pytest.MonkeyPatch, gui_app_module
) -> None:
    monkeypatch.setenv("ORACLE_GUI_CORS_ORIGINS", "*")
    monkeypatch.delenv("ORACLE_GUI_ALLOW_ANY_ORIGIN", raising=False)
    assert gui_app_module.get_socket_cors_origins() is None

    monkeypatch.setenv("ORACLE_GUI_ALLOW_ANY_ORIGIN", "true")
    assert gui_app_module.get_socket_cors_origins() == "*"
