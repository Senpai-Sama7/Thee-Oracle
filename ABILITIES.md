# ABILITIES.md — Oracle Agent System Intelligence

> [!IMPORTANT]
> This is a high-fidelity intelligence report and instruction set for AI Agents working on the Oracle Platform. Load this first. It provides the semantically cohesive context needed for zero-shot task execution.

---

## 1. Topology Map (Macro Layer)

The Oracle Platform is structured as a **Resilient Agentic Kernel**. It separates transient LLM reasoning from persistent state and task orchestration.

```
.
├── main.py                        # Production Entry (FastAPI + Oracle Loop)
├── orchestrator.py                # The Kernel: Task Lifecycle, Resilience, Scheduling
├── src/oracle/                    # The Brain: Agent Logic, Routing, Tooling
│   ├── agent_system.py            # ReAct Core: Gemini Integration, History, Persistence
│   ├── model_router.py            # Intelligence Switchboard: Multi-LLM failover & cost
│   ├── tool_registry.py           # Peripheral nervous system: Unified Tool/MCP dispatch
│   ├── mcp_client.py              # MCP Transport: Stdio/SSE connection management
│   ├── gcs_storage.py             # External Memory: Cloud file/screenshot persistence
│   ├── knowledge_worker.py        # Semantic Search: RabbitMQ + Google Discovery Engine
│   └── health_check.py            # Autonomic System: Monitoring & Metrics
├── data/                          # Persistent State: SQLite (WAL Mode)
└── infrastructure/                # Orchestration: Docker, Terraform, Prometheus
```

---

## 2. Module Decomposition (Meso Layer)

### A. The Reasoning Core (`src/oracle/agent_system.py`)
- **OracleAgent**: The primary state machine. It manages a `history` of `Content` objects.
- **HistorySerializer**: Critical component. Uses Pydantic to preserve **Thought Signatures** (bytes) across JSON/SQLite round-trips. Never use `pickle`.
- **ToolExecutor**: Sandbox for side effects. Every method returns a `{"success": bool}` envelope.

### B. The Resiliency Kernel (`orchestrator.py`)
- **Task Hierarchy**: `Task` objects with priority inheritance and dependency resolution.
- **CircuitBreaker**: Prevents cascading failures in external API calls (LLMs/Storage).
- **AsyncTokenBucket**: Handles rate limiting for distributed agents.

### C. The Intelligence Router (`src/oracle/model_router.py`)
- **Protocol-Based**: Uses the `ModelProvider` protocol to unify Gemini, OpenAI, Claude, and Ollama.
- **Cost Tracker**: Dynamically tracks USD spend per session/model using pricing tiers.

---

## 3. Relationship & Dependency Graph

1.  **Request Flow**: `main.py` -> `OracleAgent.run()`.
2.  **Reasoning Loop**: `OracleAgent` -> `ModelRouter.generate()` -> `GeminiAdapter` -> `Vertex AI`.
3.  **Action Flow**: `OracleAgent` -> `ToolRegistry.dispatch()` -> `ToolExecutor` / `MCPClient`.
4.  **Observer Flow**: `health_check.py` observes the shared `OracleAgent` and `TaskStore`.
5.  **Persistence**: Every tool turn results in an immediate checkpoint to `PersistenceLayer` (SQLite).

---

## 4. System Intelligence Report

### Architecture Details
- **Pattern**: ReAct (Reason + Act).
- **Failover**: `ModelRouter` implements a priority-based chain (e.g., Gemini -> OpenAI fallback).
- **Communication**: RabbitMQ for asynchronous heavy-lift RAG tasks; REST for synchronous agentic turns.

### Coding Conventions (Mandatory)
- **Typing**: Python 3.11+ strict mypy. All functions must have return types.
- **Async**: Prefer `asyncio` for I/O. Use `asyncio.to_thread` for blocking SDK calls (like Google GenAI).
- **Error Envelopes**: Tools **never** raise exceptions. They return `{"success": False, "error": "..."}`.
- **History**: All model interaction for one turn MUST be consolidated into a single `Content(role="tool")` turn.

### Testing Requirements
- **Framework**: `pytest` + `pytest-asyncio`.
- **Safety**: Use the `memory_db` fixture to avoid polluting `data/oracle_core.db`.
- **Mocks**: Use `MockTaskStore` and `MockEventBus` from `tests/conftest.py`.

### Preferred Tools/Commands
- **Lint/Check**: `ruff check .`, `mypy src/oracle/`.
- **Format**: `ruff format .`.
- **Run**: `python3 main.py` for full AI; `python3 demo.py` for tool-only dry runs.

---

## 5. Semantic Analysis & Troubleshooting

### Critical Symbols
- `OracleAgent.run`: Primary entry point for reasoning.
- `orchestrator.CircuitBreaker.call`: Wrapper for all flakey network calls.
- `HistorySerializer.to_dicts`: Crucial for state persistence.

### Known Security Gotchas
- **Graph Eval**: `src/oracle/agent_graph.py` contains an `eval()` call. DO NOT use it for user-provided strings.
- **Path Traversal**: Always use `Path.is_relative_to(project_root)` for file operations.
- **Shell**: Built-in shell tool uses `["bash", "-c", cmd]`. No `shell=True`.

### Performance Nodes
- **Metric Collection**: `health_check.py` should read from a singleton, not re-initialize the agent.
- **Stream Failover**: `ModelRouter.stream` logic requires careful handling of partial token yields during failover.
