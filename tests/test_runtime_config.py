from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from email_worker.main import start_worker
from personal_agent.main import _send_email_impl
from src.oracle import agent_system
from src.oracle.agent_system import OracleAgent, OracleConfig


def test_oracle_config_uses_oracle_project_root(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("GCP_PROJECT_ID", "test-project")
    monkeypatch.setenv("ORACLE_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("ORACLE_MCP_CONFIG", "config/custom_mcp.yaml")
    monkeypatch.setenv("ORACLE_SKILLS_DIR", "custom_skills")
    monkeypatch.setenv("ORACLE_MODEL_CHAIN_CONFIG", "config/custom_model_chain.yaml")
    monkeypatch.setenv("ORACLE_MAX_ACTIVE_SKILLS", "5")
    monkeypatch.setenv("ORACLE_ENABLE_SKILL_CONTEXT", "false")

    config = OracleConfig()

    assert config.project_root == tmp_path.resolve()
    assert config.db_path == tmp_path.resolve() / "data" / "oracle_core.db"
    assert config.mcp_config_path == tmp_path.resolve() / "config" / "custom_mcp.yaml"
    assert config.skills_dir == tmp_path.resolve() / "custom_skills"
    assert config.model_chain_config == tmp_path.resolve() / "config" / "custom_model_chain.yaml"
    assert config.max_active_skills == 5
    assert config.enable_skill_context is False


def test_oracle_config_defaults_to_repo_root(monkeypatch) -> None:
    monkeypatch.setenv("GCP_PROJECT_ID", "test-project")
    monkeypatch.delenv("ORACLE_PROJECT_ROOT", raising=False)
    monkeypatch.delenv("ORACLE_MCP_CONFIG", raising=False)
    monkeypatch.delenv("ORACLE_SKILLS_DIR", raising=False)
    monkeypatch.delenv("ORACLE_MODEL_CHAIN_CONFIG", raising=False)

    config = OracleConfig()
    repo_root = Path(__file__).resolve().parents[1]

    assert config.project_root == repo_root
    assert config.mcp_config_path == repo_root / "config" / "mcp_servers.yaml"
    assert config.skills_dir == repo_root / "skills"
    assert config.model_chain_config == repo_root / "config" / "model_chain.yaml"
    assert config.max_active_skills == 3
    assert config.enable_skill_context is True


def test_oracle_config_uses_tmp_db_on_vercel(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("GCP_PROJECT_ID", "test-project")
    monkeypatch.setenv("ORACLE_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.delenv("ORACLE_DB_PATH", raising=False)

    config = OracleConfig()

    assert config.project_root == tmp_path.resolve()
    assert config.db_path == Path("/tmp/oracle_core.db")


def test_oracle_config_strips_quoted_env_values(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("GCP_PROJECT_ID", '"quoted-project"')
    monkeypatch.setenv("GCP_LOCATION", "'global'")
    monkeypatch.setenv("ORACLE_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("ORACLE_MODEL_ID", '"gemini-2.0-flash-exp"')

    config = OracleConfig()

    assert config.gcp_project == "quoted-project"
    assert config.gcp_location == "global"
    assert config.model_id == "gemini-2.0-flash-exp"


def test_oracle_agent_prefers_api_key_client_over_vertex(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, Any] = {}

    class FakeClient:
        def __init__(self, **kwargs: Any) -> None:
            captured.update(kwargs)

    monkeypatch.setenv("ORACLE_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("ORACLE_DB_PATH", str(tmp_path / "oracle.db"))
    monkeypatch.setenv("GOOGLE_API_KEY", "api-key")
    monkeypatch.setenv("GCP_PROJECT_ID", "vertex-project")
    monkeypatch.setenv("GCP_LOCATION", "us-central1")
    monkeypatch.setattr(agent_system.genai, "Client", FakeClient)
    monkeypatch.setattr(agent_system, "MCP_AVAILABLE", False)
    monkeypatch.setattr(agent_system.OracleAgent, "_setup_gcs_backup", lambda self: None)

    agent = OracleAgent(OracleConfig())

    assert captured == {"api_key": "api-key"}
    assert isinstance(agent.client, FakeClient)


def test_oracle_agent_uses_vertex_when_api_key_missing(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, Any] = {}

    class FakeClient:
        def __init__(self, **kwargs: Any) -> None:
            captured.update(kwargs)

    monkeypatch.setenv("ORACLE_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("ORACLE_DB_PATH", str(tmp_path / "oracle.db"))
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("GCP_PROJECT_ID", "vertex-project")
    monkeypatch.setenv("GCP_LOCATION", "us-central1")
    monkeypatch.setattr(agent_system.genai, "Client", FakeClient)
    monkeypatch.setattr(agent_system, "MCP_AVAILABLE", False)
    monkeypatch.setattr(agent_system.OracleAgent, "_setup_gcs_backup", lambda self: None)

    agent = OracleAgent(OracleConfig())

    assert captured == {"vertexai": True, "project": "vertex-project", "location": "us-central1"}
    assert isinstance(agent.client, FakeClient)


def test_send_email_requires_rabbitmq_url(monkeypatch) -> None:
    monkeypatch.delenv("RABBITMQ_URL", raising=False)

    result = _send_email_impl("test@example.com", "Subject", "Body")

    assert result == "Email queuing unavailable: RABBITMQ_URL is not configured."


def test_email_worker_start_worker_returns_when_rabbitmq_url_missing(monkeypatch, caplog) -> None:
    monkeypatch.delenv("RABBITMQ_URL", raising=False)

    with caplog.at_level(logging.ERROR, logger="email_worker"):
        start_worker()

    assert "rabbitmq_url_missing" in caplog.text
