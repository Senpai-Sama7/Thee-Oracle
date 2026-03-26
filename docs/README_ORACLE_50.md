# Oracle 5.0 - Personal AI Assistant Platform

> **"Enterprise security, consumer simplicity"**

## 📚 Documentation Index

This directory contains comprehensive specifications for transforming Oracle Agent into a Personal AI Assistant platform.

### Core Roadmap Documents

| Document | Purpose | Audience |
|----------|---------|----------|
| [`ORACLE_50_MASTER_ROADMAP.md`](ORACLE_50_MASTER_ROADMAP.md) | Complete 24-week transformation plan | Architects, Tech Leads |
| [`ORACLE_50_ARCHITECTURE_SPEC.md`](ORACLE_50_ARCHITECTURE_SPEC.md) | Component-level technical design | Senior Developers |
| [`ORACLE_50_SYSTEMATIC_IMPLEMENTATION.md`](ORACLE_50_SYSTEMATIC_IMPLEMENTATION.md) | Phase-by-phase implementation guide | Development Team |
| [`ORACLE_50_TASK_TRACKER.md`](ORACLE_50_TASK_TRACKER.md) | Detailed task breakdown & tracking | Project Managers |
| [`ORACLE_50_IMPLEMENTATION_GUIDE.md`](ORACLE_50_IMPLEMENTATION_GUIDE.md) | Developer onboarding & workflows | New Team Members |

### Supporting Documents

| Document | Purpose |
|----------|---------|
| [`ORACLE_PERSONAL_ASSISTANT_ROADMAP.md`](ORACLE_PERSONAL_ASSISTANT_ROADMAP.md) | High-level vision & feature comparison |
| [`ORACLE_CONFIG_SPECIFICATION.md`](ORACLE_CONFIG_SPECIFICATION.md) | Configuration schemas & Markdown formats |
| [`ORACLE_50_COMPARISON.md`](ORACLE_50_COMPARISON.md) | Competitive analysis vs OpenClaw |
| [`IMPLEMENTATION_PHASE_1.md`](IMPLEMENTATION_PHASE_1.md) | Phase 1 detailed implementation |

---

## 🎯 Quick Start

### For Executives

**Read:** [`ORACLE_PERSONAL_ASSISTANT_ROADMAP.md`](ORACLE_PERSONAL_ASSISTANT_ROADMAP.md)

Key Points:
- 24-week transformation from enterprise to personal AI assistant
- Combines Oracle's security with OpenClaw's usability
- 6 messaging platforms, multi-agent orchestration, visual workflow designer
- Maintains backward compatibility throughout

### For Architects

**Read:** [`ORACLE_50_MASTER_ROADMAP.md`](ORACLE_50_MASTER_ROADMAP.md) + [`ORACLE_50_ARCHITECTURE_SPEC.md`](ORACLE_50_ARCHITECTURE_SPEC.md)

Key Components:
1. **Gateway Service** - Universal messaging hub (WebSocket/API)
2. **Model Router** - Multi-LLM with failover (Gemini, Claude, GPT, Ollama)
3. **Crew Manager** - Multi-agent orchestration (Planner → Workers → Synthesizer)
4. **Tool Registry** - Unified tool dispatch (built-in + MCP + skills)
5. **Interface Layer** - TUI, GUI, Dev UI, messaging adapters

### For Developers

**Read:** [`ORACLE_50_SYSTEMATIC_IMPLEMENTATION.md`](ORACLE_50_SYSTEMATIC_IMPLEMENTATION.md) + [`ORACLE_50_TASK_TRACKER.md`](ORACLE_50_TASK_TRACKER.md)

Getting Started:
```bash
# Phase 0: MCP + Skills Foundation
git checkout feature/mcp-skills-integration

# See task tracker for current status
cat docs/ORACLE_50_TASK_TRACKER.md
```

### For Project Managers

**Read:** [`ORACLE_50_TASK_TRACKER.md`](ORACLE_50_TASK_TRACKER.md)

Key Metrics:
- **Phase 0:** 4 weeks, ~160 hours, 2 developers
- **Phase 1:** 2 weeks, ~96 hours, 2 developers
- **Phase 2:** 2 weeks, ~108 hours, 2 developers
- **Phase 3:** 4 weeks, ~216 hours, 3 developers
- **Total:** 18 weeks, ~912 hours

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     USER INTERFACES                             │
├─────────────────────────────────────────────────────────────────┤
│  TUI (Textual) │ GUI (PyQt6) │ Dev UI (React) │ Messaging      │
│  • Terminal    │ • Desktop   │ • Workflow     │ • WhatsApp     │
│  • Live logs   │   app       │   designer     │ • Telegram     │
│  • REPL mode   │ • System    │ • Debugger     │ • Slack        │
│                │   tray      │ • Metrics      │ • Discord      │
└────────────────┴─────────────┴────────────────┴────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     GATEWAY SERVICE                             │
│              WebSocket/API Hub (Port 18789)                     │
│         • Message normalization  • Session management           │
│         • Rate limiting          • Multi-channel routing        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     ORCHESTRATION LAYER                         │
├─────────────────────────────────────────────────────────────────┤
│  Session Manager     │     Crew Manager                         │
│  • Multi-session     │     • Planner → Workers → Synthesizer    │
│  • Isolated contexts │     • Parallel/Sequential/Conditional    │
│  • Per-channel       │     • A2A agent-to-agent protocol        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     CAPABILITIES LAYER                          │
├──────────────────────────┬──────────────────┬───────────────────┤
│     LLM Router           │   Tool Runtime   │   Protocols       │
│  • Gemini/Vertex         │  • Sandboxed     │  • MCP Client     │
│  • Claude                │  • Docker        │  • A2A Server     │
│  • GPT-4o                │  • Full Access   │  • Custom         │
│  • Ollama/Local          │  • 5000+ Skills  │                   │
│  • Failover chain        │  • CDP Browser   │                   │
│  • Cost optimization     │                  │                   │
└──────────────────────────┴──────────────────┴───────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     PERSISTENCE LAYER                           │
├──────────────────────────┬──────────────────┬───────────────────┤
│   Structured (SQLite/    │   Unstructured   │   Vector Store    │
│   PostgreSQL)            │   (Markdown)     │   (ChromaDB)      │
│  • Sessions              │  • Git-friendly  │  • Embeddings     │
│  • Task logs             │  • Human-readable│  • Semantic       │
│  • Workflows             │  • Obsidian      │    search         │
│                          │    compatible    │                   │
└──────────────────────────┴──────────────────┴───────────────────┘
```

---

## 📅 Implementation Phases

### Phase 0: MCP + Skills Foundation (Weeks 1-4) 🔧 **IN PROGRESS**

**Status:** ~70% Complete

**Goal:** Complete MCP client, registry, skill loader, and tool registry integration

**Key Deliverables:**
- [~] MCP Client (stdio + SSE transports)
- [~] MCP Registry (schema translation)
- [~] Skill Loader (dynamic loading)
- [~] Tool Registry (unified dispatch)
- [~] OracleAgent integration
- [~] Tests (property-based + integration)

**Files:**
- `src/oracle/mcp_client.py`
- `src/oracle/mcp_registry.py`
- `src/oracle/skill_loader.py`
- `src/oracle/tool_registry.py`
- `config/mcp_servers.example.yaml`
- `skills/example_skill.py`

### Phase 1: Model Router (Weeks 5-6)

**Goal:** Multi-LLM support with automatic failover

**Key Deliverables:**
- [ ] ModelProvider protocol
- [ ] Gemini, Claude, GPT-4o, Ollama adapters
- [ ] Automatic failover chain
- [ ] Cost tracking & optimization
- [ ] Streaming support

**Configuration:**
```yaml
model_chain:
  - provider: gemini
    model: gemini-2.0-flash-exp
    priority: 1
  - provider: anthropic
    model: claude-3-5-sonnet
    priority: 2
  - provider: ollama
    model: llama3.2:70b
    priority: 3
```

### Phase 2: Multi-Agent (Weeks 7-8)

**Goal:** Agent graph orchestration with workflows

**Key Deliverables:**
- [ ] AgentNode base class
- [ ] AgentGraph (DAG orchestrator)
- [ ] WorkflowEngine (branching, loops, fan-out)
- [ ] A2A protocol (agent-to-agent)

**Workflow Example:**
```yaml
workflow:
  type: hierarchical
  agents:
    - Planner: Analyzes and delegates
    - Coder: Writes code
    - Analyst: Processes data
    - Synthesizer: Combines outputs
```

### Phase 3: Interface Layer (Weeks 9-12)

**Goal:** TUI, GUI, and messaging platform support

**Key Deliverables:**
- [ ] TUI (Textual) with streaming
- [ ] GUI (PyQt6) with system tray
- [ ] Dev UI (React) with workflow designer
- [ ] 6 messaging adapters (WhatsApp, Telegram, Slack, Discord, Signal, Teams)
- [ ] iOS/Android companion apps

### Phase 4: Knowledge Layer (Weeks 13-14)

**Goal:** Vector embeddings and Markdown vault

**Key Deliverables:**
- [ ] Embedding providers (local + cloud)
- [ ] ChromaDB integration
- [ ] Semantic memory
- [ ] Markdown vault (Git-friendly)
- [ ] Knowledge graph

### Phase 5: Browser + Skills Ecosystem (Weeks 15-16)

**Goal:** CDP browser control and community skills

**Key Deliverables:**
- [ ] Playwright browser automation
- [ ] Skill registry (search/install)
- [ ] Skill sandboxing
- [ ] 5000+ community skills

### Phase 6: Mobile + Production (Weeks 17-18)

**Goal:** Production hardening and mobile apps

**Key Deliverables:**
- [ ] iOS companion app
- [ ] Android companion app
- [ ] Heartbeat scheduler (proactive tasks)
- [ ] RBAC system
- [ ] Production monitoring

---

## 🔧 Current Development Focus

### Active Work (Phase 0)

Based on `.kiro/specs/mcp-skills-integration/tasks.md`:

| Task | Component | Status | Priority |
|------|-----------|--------|----------|
| 1.1 | Add env vars to OracleConfig | [~] | HIGH |
| 2.1-2.2 | MCPServerConfig + loader | [~] | HIGH |
| 3.1-3.6 | MCPClient implementation | [~] | HIGH |
| 4.1-4.3 | MCPRegistry | [~] | HIGH |
| 5.1-5.6 | SkillLoader | [~] | HIGH |
| 6.1-6.6 | ToolRegistry | [~] | HIGH |
| 7.1-7.4 | OracleAgent integration | [~] | HIGH |
| 8.1-8.2 | Config examples + skills scaffold | [~] | MEDIUM |
| 9.1-9.5 | MCP property tests | [~] | HIGH |
| 10.1-10.4 | SkillLoader tests | [~] | HIGH |
| 11.1-11.7 | ToolRegistry tests | [~] | HIGH |

### Next Steps

1. **Complete MCP Client** (Week 1)
   - Finish connection management
   - Implement tool invocation with timeout
   - Add shutdown cleanup

2. **Complete MCP Registry** (Week 1-2)
   - Finish schema translation
   - Implement name conflict resolution
   - Add dispatch routing

3. **Complete Skill Loader** (Week 2)
   - Finish module discovery
   - Implement setup/teardown hooks
   - Add hot-reload support

4. **Complete Tool Registry** (Week 2-3)
   - Aggregate all tool sources
   - Implement unified dispatch
   - Add statistics tracking

5. **Integrate with OracleAgent** (Week 3)
   - Initialize new components
   - Update _build_config()
   - Update _dispatch()
   - Add shutdown handler

6. **Write Tests** (Week 3-4)
   - Property-based tests (Hypothesis)
   - Unit tests
   - Integration tests

---

## 🎯 Success Criteria

### Phase 0 Complete When:

- [ ] MCP Client connects to stdio and SSE servers
- [ ] MCP tools are discovered and translated to Gemini schemas
- [ ] Skills load from directory with setup/teardown hooks
- [ ] Tool Registry aggregates built-in + MCP + skill tools
- [ ] OracleAgent uses ToolRegistry for all tool dispatch
- [ ] All 10 requirements from MCP spec pass tests
- [ ] No breaking changes to existing functionality

### Oracle 5.0 Complete When:

- [ ] 4+ LLM providers with automatic failover
- [ ] Multi-agent crews with visual workflow designer
- [ ] 3+ interfaces (TUI, GUI, messaging)
- [ ] 6+ messaging platforms supported
- [ ] Vector embeddings with semantic search
- [ ] 5000+ community skills
- [ ] iOS and Android companion apps
- [ ] Production-ready with monitoring

---

## 📖 Key Specifications

### From `.kiro/specs/`

| Spec | Description | Status |
|------|-------------|--------|
| `mcp-skills-integration/requirements.md` | MCP + Skills requirements (10 reqs) | In Progress |
| `mcp-skills-integration/tasks.md` | Detailed task breakdown | In Progress |
| `oracle-platform-v2/design.md` | Full platform v2 architecture | Reference |

### Critical Invariants (Must Preserve)

1. **No pickle** — Pydantic JSON only
2. **No shell=True** — Always `["bash", "-c", cmd]`
3. **Path containment** — Check `is_relative_to()` before file ops
4. **Tool envelope** — All tools return `{success: bool, ...}`
5. **Single tool Content** — One `Content(role="tool")` per model turn
6. **Session append** — Resume appends, never overwrites

---

## 🤝 Contributing

### Development Workflow

```bash
# 1. Check current status
cat docs/ORACLE_50_TASK_TRACKER.md

# 2. Pick a task from current phase
git checkout -b feature/mcp-client-stdio

# 3. Implement with tests
# See ORACLE_50_SYSTEMATIC_IMPLEMENTATION.md for code examples

# 4. Run tests
pytest tests/ -v

# 5. Update task tracker
# Mark task as [x] in ORACLE_50_TASK_TRACKER.md

# 6. Submit PR
```

### Code Standards

- Type hints mandatory
- Docstrings for all public APIs
- Property tests for critical paths
- No exceptions escape tool handlers
- Structured logging

---

## 📞 Support

| Resource | Location |
|----------|----------|
| Architecture Questions | `ORACLE_50_ARCHITECTURE_SPEC.md` |
| Implementation Guide | `ORACLE_50_SYSTEMATIC_IMPLEMENTATION.md` |
| Task Tracking | `ORACLE_50_TASK_TRACKER.md` |
| API Reference | `ORACLE_CONFIG_SPECIFICATION.md` |

---

## 📝 Version History

| Version | Date | Description |
|---------|------|-------------|
| 5.0.0-Alpha | 2026-03-15 | Initial comprehensive roadmap |

---

*Oracle 5.0 - The Enterprise-Grade Personal AI Assistant*
