# CLAUDE.md - Anthropic / Claude-Specific Notes For Oracle Agent

Start with `AGENTS.md`. This file only adds Claude-specific context.

## Important Reality Check

Claude is implemented in this repo, but it is not the default runtime path.

- `AnthropicAdapter` lives in `src/oracle/model_router.py` line 863.
- Claude is only used when:
  - `ORACLE_USE_MODEL_ROUTER=true`
  - the router config includes an `anthropic` provider
  - `ANTHROPIC_API_KEY` is available

Most root entry points instantiate `OracleAgent` directly and therefore stay on the Gemini path unless explicitly configured otherwise.

## Where Claude Logic Lives

- `src/oracle/model_router.py:863` `AnthropicAdapter`
- `src/oracle/model_router.py:1306` `ModelRouter`
- `src/oracle/model_router.py:1559` `create_provider_from_config`
- `src/oracle/model_router.py:1587` `create_router_from_config`

If a task is "make Claude work," start there, not in `src/oracle/agent_system.py`.

## Claude-Specific Integration Notes

### Message conversion

`AnthropicAdapter.generate()` splits the message list into:

- one optional `system` string
- regular chat messages
- optional tool definitions in Anthropic format

If you alter the neutral message schema used by `ModelRouter`, verify Anthropic conversion explicitly.

### Tool calls

Claude tool calls are converted into neutral `ToolCall` objects:

- Anthropic `tool_use` blocks -> `ToolCall`
- streamed `input_json_delta` chunks are accumulated into a final tool call

When debugging malformed tool arguments, inspect the streaming and non-streaming code paths separately.

### Cost tracking

All provider usage is funneled through `CostTracker`.

If Claude cost reporting looks wrong, inspect:

- `TokenUsage`
- `CostTracker.PRICING`
- `AnthropicAdapter.generate()`

## Known Caveats

- The router config example uses `priority`, but provider instances do not currently expose a priority field, so ordering mostly follows config insertion order.
- Env interpolation only reliably supports `${VAR}`, not shell-style defaults like `${VAR:-default}`.
- If a wrapper claims to be using Claude but instantiates `OracleAgent()` without enabling the router, it is still on the Gemini direct path.

## Search Shortcuts

```bash
rg -n "class AnthropicAdapter|class ModelRouter" src/oracle/model_router.py
rg -n "provider: anthropic|ANTHROPIC_API_KEY" config src/oracle
rg -n "ORACLE_USE_MODEL_ROUTER|create_router_from_config" src/oracle
```
