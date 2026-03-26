---
name: code-review-guidance
description: Review repo-local code changes for correctness, security regressions, weak defaults, and missing tests.
triggers:
  - code review
  - security audit
  - regression hunt
allowed-tools:
  - file_system_ops
  - shell_execute
---

# Code Review Guidance

Use this skill when the user asks for a review, audit, hostile scan, regression check, or vulnerability-oriented code assessment.

## Invocation Rules

- Prefer this skill when the task is to find defects, risks, trust-boundary mistakes, or missing tests.
- Do not use this skill for straightforward feature implementation unless the task explicitly includes review or audit work.
- Start with the highest-signal runtime and test files before drifting into historical docs or archive material.

## Workflow

1. Read the changed or targeted runtime files.
2. Cross-check wrapper surfaces, auth boundaries, URL/path validation, and subprocess usage.
3. Use the reference checklist for a deeper pass when the task is broad or security-sensitive.
4. Validate findings against tests before claiming a bug.

## Supporting Files

- Read `references/checklist.md` when you need the full repo review checklist.
