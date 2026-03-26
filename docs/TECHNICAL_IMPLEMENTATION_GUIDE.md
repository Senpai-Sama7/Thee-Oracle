# Oracle Agent - Technical Implementation Guide

## 🎯 Development & Deployment Reference

This guide provides technical details for developers and system architects working with the Oracle Agent platform v5.0.

---

## 📋 Quick Reference

### System Commands
```bash
# Demo mode (no GCP required)
python3 demo.py

# Full AI mode (requires GCP setup)
python3 main.py

# Infrastructure services
docker-compose -f infrastructure/docker-compose.yml up -d

# Development tools (Strict Verification)
mypy src/oracle/
ruff check .
pytest tests/
```

---

## 🏗️ Architecture & Core Components

### 1. Unified Oracle Agent (`agent_system.py`)
The `OracleAgent` is the central orchestrator. It manages the ReAct loop, tool dispatching, and state persistence.

```python
class OracleAgent:
    def __init__(self, config: OracleConfig = None):
        self.config = config or OracleConfig()
        self.persistence = PersistenceLayer(self.config.db_path)
        self.registry = ToolRegistry()  # Unified tool discovery
        # ...
        
    def run(self, prompt: str, session_id: str = "default") -> str:
        """Main entry point for agentic execution"""
```

### 2. Tool Registry & Skill Loading
Oracle v5.0 introduces a modular skill architecture. Tools are no longer hardcoded but loaded from the `skills/` directory.

- **`ToolRegistry`**: Aggregates built-in tools, MCP tools, and skills.
- **`SkillLoader`**: Dynamically imports Python modules from the skills directory and extracts tool definitions.

### 3. Resilience Layers (`orchestrator.py`)
- **Circuit Breaker**: Prevents cascading failures when Vertex AI or RabbitMQ are unreachable.
- **Result Store**: captures every step of the agent's reasoning for auditing.

---

## 🔧 Development Guidelines

### 1. Strict Typing Mandatory
All new code MUST pass `mypy --strict`. This is enforced via the CI pipeline and local `mypy` commands.

```python
# Required: Full annotations for all arguments and return types
def register_skill(name: str, path: Path) -> bool:
    ...
```

### 2. Skill Implementation
Skills should be placed in the `skills/` directory. Each skill must export a `TOOLS` list.

```python
# skills/example.py
def my_handler(arg: str) -> str:
    return f"Processed {arg}"

TOOLS = [
    {
        "name": "example_tool",
        "description": "Example tool description",
        "parameters": { ... },
        "handler": my_handler
    }
]
```

### 3. Tool Dispatch Policy
Every tool MUST return a dictionary envelope with a `success` boolean.

```python
def my_tool() -> dict[str, Any]:
    try:
        return {"success": True, "result": "..."}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

---

## 🔒 Security & Sandboxing

### Path Containment
All file operations are checked against the project root using `is_relative_to()`.

```python
def file_system_ops(self, op: str, path: str):
    full_path = (self.project_root / path).resolve()
    if not full_path.is_relative_to(self.project_root):
        return {"success": False, "error": "Sandbox violation"}
```

### Shell Safety
Subprocess calls must always use the list form to prevent simple shell injection, while allowing complex bash syntax via `["bash", "-c", cmd]`.

---

## 📊 Monitoring & Health

The platform exposes a health check service on port 8080.

- **`/health`**: Database and GCP connectivity checks.
- **`/metrics`**: Prometheus-compliant metrics (uptime, database size, turn count).
- **`/status`**: System resource utilization (CPU/Memory).

---

## 🔍 Troubleshooting

### Missing Dependencies
The platform relies on several specialized libraries. Ensure the virtual environment is updated:
```bash
pip install -r requirements.txt
```

### Authentication Errors
Verify GCP credentials:
```bash
gcloud auth application-default print-access-token
```
Ensure `GCP_PROJECT_ID` is set correctly in `.env`.

---

**Oracle Agent Platform v5.0** - Engineering Excellence in AI Orchestration. 🚀
echnical Implementation Guide** - Complete reference for developers and operators. 🚀
