# RALPH.md — Oracle Platform v2 Knowledge Base

> Load this file before any task. It is the authoritative context document for AI coding agents working on the Oracle Platform v2 codebase, specifically tailored for Ralph.

---

## Project Overview

**Oracle Platform v2** is the evolution of the Oracle Agent v1 system. It transforms a single-agent system built on Gemini into a model-agnostic, multi-agent personal AI assistant platform. 

- **Python**: 3.11+ with strict mypy type checking
- **Architecture**: Multi-Agent orchestration (DAG-based), model-agnostic failover routing, messaging-first interfaces, vector knowledge stores, and a community skills ecosystem.
- **Persistence**: SQLite with WAL mode (local) + PostgreSQL (production option) + MarkdownVault (Obsidian-compatible)
- **Message Queue**: RabbitMQ for distributed knowledge worker tasks and A2A Protocol
- **Browser Automation**: CDP control via Playwright (sandboxed)

---

## Phased Roadmap

As Ralph, you are implementing the following phases strictly in order, ensuring backward compatibility with v1 at every step:

| Phase | Name                       | Key Deliverable                            |
| ----- | -------------------------- | ------------------------------------------ |
| 0     | MCP + Skills               | ToolRegistry, MCPClient, SkillLoader       |
| 1     | Model Layer                | ModelRouter, provider adapters, streaming  |
| 2     | Multi-Agent                | AgentGraph, WorkflowEngine, A2A protocol   |
| 3     | Interface Layer            | Messaging adapters, TUI, GUI               |
| 4     | Knowledge + Embeddings     | VectorStore, MarkdownVault, KnowledgeGraph |
| 5     | Browser + Skills Ecosystem | BrowserAgent, SkillRegistry, SkillSandbox  |
| 6     | Mobile + Production        | iOS/Android nodes, heartbeat, RBAC         |

---

## Architecture (v2)

### High-Level Components

1. **Model Layer (Phase 1)**
   - `ModelRouter`: Implements failover chain for LLM providers (Gemini, OpenAI, Anthropic, Ollama).
   - `StreamChunk`: Standardized streaming interface end-to-end.
2. **Multi-Agent Layer (Phase 2)**
   - `AgentGraph`: DAG orchestrator.
   - `WorkflowEngine`: Branching, loops, fan-out/fan-in.
   - `A2AProtocol`: Agent-to-Agent communication (Google A2A spec).
3. **Interface Layer (Phase 3)**
   - `InterfaceAdapter`: Protocol for Telegram, Discord, Slack, etc.
   - Session isolation mapping: `{adapter_id}:{channel_id}:{thread_id} → session_id`
4. **Knowledge Layer (Phase 4)**
   - `EmbeddingProvider`, `VectorStore` (Chroma/Pinecone), `MarkdownVault` (Obsidian sync).
5. **Browser & Skills (Phase 5)**
   - `BrowserAgent` (Playwright), `SkillRegistry` (PyPI-style search), `SkillSandbox` (Containment).

---

## Security & Constraints (Non-Negotiable)

These v1 invariants MUST be preserved throughout all v2 phases:

1. **No pickle serialization**: Use Pydantic JSON only (`HistorySerializer`).
2. **No `shell=True`**: Always use `["bash", "-c", cmd]`.
3. **Path containment**: Verify relative paths against `project_root` before any file operation (especially in `SkillSandbox`).
4. **Tool Envelopes**: All tool handlers must return `{"success": bool, ...}` and never raise exceptions out to the model.
5. **Turn Consolidation**: All function responses per model turn are consolidated into one `Content(role="tool")`.
6. **Append-Only History**: Session resume appends a new user turn, never overwrites history.
7. **Exactly-Once A2A Delivery**: Deduplication is required for agent messages.
8. **Cycle Detection**: `AgentGraph` must reject cyclic edges at configuration time.

---

## Error Handling Strategy

- **ModelRouter**: On `ProviderError` (e.g., timeout/rate limit), log and failover to the next adapter. Only if the chain exhausts do you return an error envelope `{"success": False, "error": "All providers exhausted"}`.
- **WorkflowEngine**: Conditional branch mutual exclusivity is enforced. Node timeouts return structured errors.
- **Interface Adapters**: Disconnects trigger exponential backoff.
- **SkillSandbox**: Path traversal attempts return `{"success": False, "error": "Path traversal denied"}` and do NOT throw unhandled exceptions.

---

## Testing Instructions

- **Framework**: `pytest` with `asyncio_mode = "auto"`.
- **Property-Based Testing**: Use `hypothesis` for correctness properties (P1 - P17) defined in the design spec.
  - Examples: Model failover transparency, Streaming token order, A2A Exactly-Once delivery, Sandbox path containment, DAG acyclicity.
- **Mocks**: Mock external platform APIs (Discord, Telegram, OpenAI) via `pytest-mock` to avoid real network calls in CI.

---

## File Structure Additions

```
src/oracle/
  model_router.py          # Phase 1
  agent_graph.py           # Phase 2
  a2a_protocol.py          # Phase 2
  interface_adapter.py     # Phase 3
  embedding_provider.py    # Phase 4
  markdown_vault.py        # Phase 4
  browser_agent.py         # Phase 5
  skill_registry.py        # Phase 5
  mobile_node.py           # Phase 6
```