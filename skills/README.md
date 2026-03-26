# Oracle Skills

Oracle now supports two skill formats:

1. Legacy flat Python skills in `skills/*.py`
2. Claude-style skill packages in `skills/<skill-name>/SKILL.md`

Both formats can expose callable tools through `TOOLS`. Package skills can also be instruction-only and still participate in prompt-time skill discovery.

## Recommended Format

Use package skills for new work:

```text
skills/
  code-review-guidance/
    SKILL.md
    skill.py              # optional
    references/
      checklist.md        # optional
    scripts/
      helper.py           # optional
    assets/
      template.txt        # optional
```

## SKILL.md Requirements

Every package skill must have a `SKILL.md` with YAML frontmatter:

```md
---
name: code-review-guidance
description: Review repo-local code changes for bugs, regressions, auth gaps, and missing tests.
triggers:
  - code review
  - security audit
allowed-tools:
  - file_system_ops
  - shell_execute
entrypoint: skill.py
---

# Code Review Guidance

Use this skill when the task is a review, audit, or regression hunt.
Read `references/checklist.md` when a full checklist is needed.
```

Supported frontmatter fields:

- `name` (required)
- `description` (required)
- `triggers` (optional list)
- `allowed-tools` or `allowed_tools` (optional list)
- `entrypoint` (optional; defaults to `skill.py` or `__init__.py` if present)

## Discovery Rules

- Legacy skills are discovered from `skills/*.py`
- Package skills are discovered from `skills/*/SKILL.md`
- Package skills do not need a Python module to be useful; instruction-only skills are valid
- If a package has a Python entrypoint, its `TOOLS` are loaded into the normal tool registry
- Conflicts with built-in tool names are prefixed with `skill_name__`

## Prompt-Time Invocation Rules

When Oracle builds a request, it now:

1. discovers the skill catalog
2. scores skills against the current prompt using name, description, triggers, and tool names
3. injects a compact skill catalog into the system instruction
4. expands the top matching skills with their `SKILL.md` body and supporting file inventory

That means a skill can influence behavior even if it exposes no tools.

## Tool-Backed Skill Format

If you want a package skill to expose callable tools, add `skill.py`:

```python
def my_handler(message: str) -> dict:
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
        "handler": my_handler,
    }
]
```

## Supporting Files

Package skills can bundle:

- `references/` for docs the agent may read on demand
- `scripts/` for deterministic helpers the agent may execute or patch
- `assets/` for templates and output artifacts

The loader inventories these files and includes them in the prompt-time skill context so the agent knows they exist.

## Legacy Compatibility

Existing flat skills such as [skills/example_skill.py](/home/donovan/Projects/replit/skills/example_skill.py) and [skills/personal_agent.py](/home/donovan/Projects/replit/skills/personal_agent.py) still work.
New skills should prefer the package format.
