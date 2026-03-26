from __future__ import annotations

import logging
from pathlib import Path

from email_worker.main import start_worker
from personal_agent.main import _send_email_impl
from src.oracle.agent_system import OracleConfig


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


def test_send_email_requires_rabbitmq_url(monkeypatch) -> None:
    monkeypatch.delenv("RABBITMQ_URL", raising=False)

    result = _send_email_impl("test@example.com", "Subject", "Body")

    assert result == "Email queuing unavailable: RABBITMQ_URL is not configured."


def test_email_worker_start_worker_returns_when_rabbitmq_url_missing(monkeypatch, caplog) -> None:
    monkeypatch.delenv("RABBITMQ_URL", raising=False)

    with caplog.at_level(logging.ERROR, logger="email_worker"):
        start_worker()

    assert "rabbitmq_url_missing" in caplog.text
