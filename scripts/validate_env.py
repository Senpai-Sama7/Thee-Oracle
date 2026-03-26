#!/usr/bin/env python3
"""
Oracle Agent environment validator.

Reads the local .env file, reports the variables relevant to the maintained
runtime paths, and explains which modes are fully configured.
"""

from __future__ import annotations

import sys
from pathlib import Path


ENV_PATH = Path(".env")

SECTION_VARS: list[tuple[str, list[tuple[str, bool, str]]]] = [
    (
        "Core Oracle Agent",
        [
            ("ORACLE_MODEL_ID", True, "Default model ID for OracleAgent."),
            ("GCP_PROJECT_ID", False, "Required for live Gemini/Vertex AI calls."),
            ("GCP_LOCATION", False, "Vertex AI region."),
            ("ORACLE_PROJECT_ROOT", False, "Sandbox root for file operations."),
            ("ORACLE_MAX_TURNS", False, "Maximum turns in the ReAct loop."),
            ("ORACLE_SHELL_TIMEOUT", False, "Shell tool timeout in seconds."),
            ("ORACLE_HTTP_TIMEOUT", False, "HTTP tool timeout in seconds."),
            ("ORACLE_LOG_LEVEL", False, "Runtime log level."),
        ],
    ),
    (
        "Router / MCP / Skills",
        [
            ("ORACLE_USE_MODEL_ROUTER", False, "Enable the multi-provider router path."),
            ("ORACLE_MODEL_CHAIN_CONFIG", False, "Router provider-chain config."),
            ("ORACLE_MCP_CONFIG", False, "MCP server config file."),
            ("ORACLE_MCP_TIMEOUT", False, "MCP connection timeout."),
            ("ORACLE_SKILLS_DIR", False, "Directory scanned by SkillLoader."),
            ("OPENAI_API_KEY", False, "Optional OpenAI fallback provider key."),
            ("ANTHROPIC_API_KEY", False, "Optional Anthropic fallback provider key."),
            ("OLLAMA_BASE_URL", False, "Optional Ollama endpoint."),
        ],
    ),
    (
        "Webhook and GUI",
        [
            ("WEBHOOK_API_KEY", False, "Optional API key for src/oracle/main.py."),
            ("ORACLE_API_KEY", False, "API key for protected GUI config endpoints."),
            ("ORACLE_GUI_PORT", False, "Port used by gui/launch.py and gui/app.py."),
        ],
    ),
    (
        "Personal Agent and Email Worker",
        [
            ("PERSONAL_AGENT_DB", False, "SQLite path for personal-agent state."),
            ("RABBITMQ_URL", False, "Required for personal_agent and email_worker message flow."),
            ("EMAIL_QUEUE", False, "Email worker queue name."),
            ("DLX_QUEUE", False, "Email worker dead-letter queue."),
            ("SMTP_HOST", False, "SMTP host for email delivery."),
            ("SMTP_PORT", False, "SMTP port."),
            ("SMTP_USER", False, "SMTP username."),
            ("SMTP_PASSWORD", False, "SMTP password."),
            ("SMTP_FROM", False, "From address for outbound mail."),
            ("SMTP_USE_TLS", False, "Enable STARTTLS for SMTP."),
        ],
    ),
    (
        "Knowledge Worker",
        [
            ("RABBITMQ_HOST", False, "Host for src/oracle/knowledge_worker.py."),
            ("RABBITMQ_USER", False, "RabbitMQ username for the knowledge worker."),
            ("RABBITMQ_PASS", False, "RabbitMQ password for the knowledge worker."),
            ("DISCOVERY_ENGINE_ID", False, "Discovery Engine serving engine ID."),
            ("GCP_PROJECT_NUMBER", False, "Used by Discovery Engine API URL construction."),
            ("SAFE_GCP_SERVICES", False, "Optional allowlist of permitted GCP services."),
        ],
    ),
    (
        "Storage",
        [
            ("GCS_BUCKET_NAME", False, "Enable backup and screenshot uploads to GCS."),
        ],
    ),
]


def load_env(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key] = value
    return env


def print_section(name: str, entries: list[tuple[str, bool, str]], env: dict[str, str]) -> None:
    print(f"{name}:")
    for key, required, description in entries:
        value = env.get(key, "")
        configured = value != ""
        status = "OK " if configured else ("REQ" if required else "OPT")
        shown = value if configured else "NOT SET"
        print(f"  [{status}] {key} = {shown}")
        print(f"        {description}")
    print()


def validate_env_variables() -> int:
    print("Oracle Agent Environment Validation")
    print("=" * 60)

    if not ENV_PATH.exists():
        print("ERROR: .env file not found in the project root.")
        print("Create one from .env.example before running this validator.")
        return 1

    env = load_env(ENV_PATH)
    print(f"Loaded {len(env)} variables from {ENV_PATH}")
    print()

    for section_name, entries in SECTION_VARS:
        print_section(section_name, entries, env)

    missing_required = [key for key, required, _ in SECTION_VARS[0][1] if required and env.get(key, "") == ""]

    print("Mode Summary:")
    if env.get("GCP_PROJECT_ID", ""):
        print("  - OracleAgent live Gemini mode: configured")
    else:
        print("  - OracleAgent live Gemini mode: not configured (demo/local tool mode still works)")

    if env.get("RABBITMQ_URL", ""):
        print("  - Personal agent / email worker AMQP flow: configured")
    else:
        print("  - Personal agent / email worker AMQP flow: disabled until RABBITMQ_URL is set")

    if env.get("GCS_BUCKET_NAME", ""):
        print("  - GCS backups: configured")
    else:
        print("  - GCS backups: disabled")

    if missing_required:
        print()
        print(f"ERROR: missing required variables: {', '.join(missing_required)}")
        return 1

    print()
    print("Validation complete.")
    return 0


if __name__ == "__main__":
    sys.exit(validate_env_variables())
