# GEMINI.md - Gemini-Specific Notes For Oracle Agent

Start with `AGENTS.md`. This file only adds Gemini-specific context.

## Where Gemini Actually Runs

There are two Gemini paths in this repo:

1. Direct path in `src/oracle/agent_system.py`
   - `OracleAgent.run()` at line 940
   - uses `genai.Client.models.generate_content(...)`
   - this is the default runtime path

2. Routed path in `src/oracle/model_router.py`
   - `GeminiAdapter` at line 429
   - `ModelRouter` at line 1306
   - only active when `ORACLE_USE_MODEL_ROUTER=true`

Do not assume OpenAI or Anthropic behavior matters unless the router path is explicitly enabled.

## Mandatory Gemini Invariants

### History round-trip must preserve thought signatures

- `HistorySerializer` in `src/oracle/agent_system.py` line 194 is critical.
- It uses Pydantic JSON serialization to preserve Gemini `thought_signature` bytes.
- If you rewrite persistence or history conversion, do not replace it with ad hoc dict mapping unless you fully preserve `types.Content` fidelity.

### Tool responses must be consolidated into one tool turn

- `OracleAgent.run()` collects all function calls from one model turn, dispatches them, and appends exactly one `types.Content(role="tool", parts=[...])`.
- This is the correct Gemini contract.
- Do not emit one tool content per function call.

### Tool declarations and dispatch must stay in sync

If you add or rename a built-in tool in the direct Gemini path, update both:

- `_build_config()` in `src/oracle/agent_system.py` line 599
- `_dispatch()` in `src/oracle/agent_system.py` line 892

If the registry path is enabled, also verify:

- `src/oracle/tool_registry.py`
- `src/oracle/skill_loader.py`
- `src/oracle/mcp_registry.py`

## Gemini-Specific Operational Notes

- `OracleConfig` defaults `ORACLE_MODEL_ID` to `gemini-2.0-flash-exp`.
- Direct `OracleAgent.run()` always builds Gemini config with `include_thoughts=True`.
- Direct `OracleAgent.run()` does not currently route temperature or top-p from env.
- `run_async()` uses `GenerateConfig` and the router abstractions instead of raw SDK content objects.

## Common Failure Modes

### Tool-calling session resumes break

First inspect:

- `src/oracle/agent_system.py:194` `HistorySerializer`
- `src/oracle/agent_system.py:940` `OracleAgent.run`

### A tool exists but Gemini never calls it

Check:

- `src/oracle/agent_system.py:599` `_build_config`
- `src/oracle/tool_registry.py:212` `get_function_declarations`

### Router path works differently from direct path

That is expected. The router path converts to a provider-neutral message format and does not preserve Gemini SDK objects directly.

## Search Shortcuts

```bash
rg -n "class HistorySerializer|def _build_config|def run\\(" src/oracle/agent_system.py
rg -n "class GeminiAdapter|class ModelRouter" src/oracle/model_router.py
rg -n "FunctionDeclaration|from_function_response" src/oracle
```
