from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest

from src.oracle.agent_system import OracleAgent
from src.oracle.skill_loader import SkillLoader
from src.oracle.tool_registry import ToolRegistry


def test_instruction_only_skill_package_is_discoverable(tmp_path: Path) -> None:
    skill_dir = tmp_path / "review-skill"
    references_dir = skill_dir / "references"
    references_dir.mkdir(parents=True)

    (skill_dir / "SKILL.md").write_text(
        """---
name: review-skill
description: Review changes for regressions and missing tests.
triggers:
  - code review
  - regression audit
allowed-tools:
  - file_system_ops
---

# Review Skill

Use this skill for reviews and audits.
""",
        encoding="utf-8",
    )
    (references_dir / "checklist.md").write_text("# Checklist\n", encoding="utf-8")

    loader = SkillLoader(str(tmp_path))
    tools = loader.load_all()

    assert tools == {}
    assert "review-skill" in loader.skills

    skill = loader.skills["review-skill"]
    assert skill.description == "Review changes for regressions and missing tests."
    assert skill.triggers == ["code review", "regression audit"]
    assert skill.allowed_tools == ["file_system_ops"]
    assert skill.resources.references == ["references/checklist.md"]


def test_package_skill_with_entrypoint_loads_tools(tmp_path: Path) -> None:
    skill_dir = tmp_path / "repo-helper"
    skill_dir.mkdir()

    (skill_dir / "SKILL.md").write_text(
        """---
name: repo-helper
description: Repo-local helper skill.
entrypoint: skill.py
---

# Repo Helper

Use this when repo-local helper tools are relevant.
""",
        encoding="utf-8",
    )
    (skill_dir / "skill.py").write_text(
        """
def echo_message(message: str):
    return {"success": True, "result": message}

TOOLS = [
    {
        "name": "echo_message",
        "description": "Echo a message back.",
        "parameters": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "Message to echo"}
            },
            "required": ["message"],
        },
        "handler": echo_message,
    }
]
""",
        encoding="utf-8",
    )

    loader = SkillLoader(str(tmp_path))
    tools = loader.load_all()

    assert "echo_message" in tools
    handler = cast(Any, tools["echo_message"].handler)
    assert handler("hello") == {"success": True, "result": "hello"}
    assert "repo-helper" in loader.skills
    assert loader.skills["repo-helper"].tool_names() == ["echo_message"]


def test_skill_prompt_context_prefers_matching_skills(tmp_path: Path) -> None:
    review_dir = tmp_path / "review-skill"
    review_dir.mkdir()
    (review_dir / "SKILL.md").write_text(
        """---
name: review-skill
description: Review code changes for regressions and security issues.
triggers:
  - code review
  - security audit
allowed-tools:
  - file_system_ops
---

# Review Skill

Read references/checklist.md for the full review workflow.
""",
        encoding="utf-8",
    )

    docs_dir = tmp_path / "docs-skill"
    docs_dir.mkdir()
    (docs_dir / "SKILL.md").write_text(
        """---
name: docs-skill
description: Write and polish repo documentation.
triggers:
  - documentation
---

# Docs Skill

Use this for docs refresh tasks.
""",
        encoding="utf-8",
    )

    loader = SkillLoader(str(tmp_path))
    loader.load_all()

    selected = loader.select_for_prompt("Perform a code review and security audit", limit=2)
    assert [skill.name for skill in selected] == ["review-skill"]

    prompt_context = loader.build_prompt_context("Perform a code review and security audit", max_skills=2)
    assert "Selected skill instructions for this request" in prompt_context
    assert "## review-skill" in prompt_context
    assert "docs-skill" in prompt_context
    assert "Preferred existing tools: file_system_ops" in prompt_context


@pytest.mark.skipif(os.name == "nt", reason="permission-mode hardening test is POSIX-specific")
def test_world_writable_instruction_only_skill_is_rejected(tmp_path: Path) -> None:
    skill_dir = tmp_path / "unsafe-skill"
    skill_dir.mkdir()
    manifest = skill_dir / "SKILL.md"
    manifest.write_text(
        """---
name: unsafe-skill
description: Should not load when permissions are unsafe.
---

# Unsafe Skill
""",
        encoding="utf-8",
    )
    os.chmod(skill_dir, 0o777)
    os.chmod(manifest, 0o666)

    try:
        loader = SkillLoader(str(tmp_path))
        tools = loader.load_all()
    finally:
        os.chmod(manifest, 0o644)
        os.chmod(skill_dir, 0o755)

    assert tools == {}
    assert "unsafe-skill" not in loader.skills


def test_skill_prompt_context_truncates_large_instruction_bodies(tmp_path: Path) -> None:
    skill_dir = tmp_path / "large-skill"
    skill_dir.mkdir()
    huge_instruction = "A" * 5000
    (skill_dir / "SKILL.md").write_text(
        f"""---
name: large-skill
description: Skill with a very large instruction body.
triggers:
  - large prompt
---

# Large Skill

{huge_instruction}
""",
        encoding="utf-8",
    )

    loader = SkillLoader(str(tmp_path))
    loader.load_all()
    context = loader.build_prompt_context("use the large prompt skill", max_skills=1)

    assert "[skill instructions truncated]" in context
    assert len(context) < 9500


def test_tool_registry_exposes_skill_prompt_context(tmp_path: Path) -> None:
    skill_dir = tmp_path / "review-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        """---
name: review-skill
description: Review code changes for regressions and security issues.
triggers:
  - code review
---

# Review Skill

Use this for review work.
""",
        encoding="utf-8",
    )

    class StubToolExecutor:
        def shell_execute(self, command: str) -> dict[str, str]:
            return {"success": "true", "stdout": command}

        def vision_capture(self, reason: str) -> dict[str, str]:
            return {"success": "true", "path": reason}

        def file_system_ops(self, operation: str, path: str, content: str | None = None) -> dict[str, str]:
            del operation, path, content
            return {"success": "true"}

        def http_fetch(self, url: str, method: str = "GET", headers: dict[str, str] | None = None) -> dict[str, str]:
            del method, headers
            return {"success": "true", "content": url}

    loader = SkillLoader(str(tmp_path))
    registry = ToolRegistry(StubToolExecutor(), skill_loader=loader)
    loader.load_all()

    catalog = registry.get_skill_catalog()
    context = registry.build_skill_prompt_context("Please do a code review")

    assert catalog[0]["name"] == "review-skill"
    assert "## review-skill" in context


def test_oracle_agent_builds_skill_system_instruction() -> None:
    agent = OracleAgent.__new__(OracleAgent)
    agent.cfg = cast(Any, SimpleNamespace(enable_skill_context=True, max_active_skills=2))
    agent._tool_registry = cast(
        Any,
        SimpleNamespace(
            build_skill_prompt_context=lambda prompt, max_skills=3: f"skill-context::{prompt}::{max_skills}"
        ),
    )

    system_instruction = OracleAgent._build_skill_system_instruction(agent, "review auth flow")

    assert system_instruction == "skill-context::review auth flow::2"
