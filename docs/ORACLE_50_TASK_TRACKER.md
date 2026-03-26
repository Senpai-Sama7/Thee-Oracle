# Oracle 5.0 - Implementation Task Tracker
## Systematic Development Roadmap

---

## 🎯 Current Status Overview

### Phase 0: MCP + Skills Foundation (HARDENED)
**Progress: 100% Complete**

| Component | Status | Completion % |
|-----------|--------|--------------|
| MCP Client | [x] Complete | 100% |
| MCP Registry | [x] Complete | 100% |
| Skill Loader | [x] Complete | 100% |
| Tool Registry | [x] Complete | 100% |
| OracleAgent Integration | [x] Complete | 100% |
| Configuration | [x] Complete | 100% |
| Tests | [x] Complete | 100% |

**Legend:**
- [ ] Not Started
- [~] In Progress
- [x] Complete (Hardened)
- [!] Blocked

---

## 📋 Detailed Task Breakdown

### Phase 0.1: MCP Client (Week 1)

#### Task 1.1: Environment Configuration
```markdown
Status: [~]
Priority: HIGH
Estimated: 2 hours

Description:
Add MCP-related configuration to OracleConfig class.

Acceptance Criteria:
- [x] ORACLE_MCP_CONFIG env var support (default: config/mcp_servers.yaml)
- [x] ORACLE_MCP_TIMEOUT env var support (default: 30)
- [x] Config validation in OracleConfig.__init__

Files to Modify:
- src/oracle/agent_system.py (OracleConfig class)

Implementation Notes:
Add these fields to OracleConfig.__init__:
- mcp_config_path: str
- mcp_timeout: int
```

#### Task 1.2: MCPServerConfig Dataclass
```markdown
Status: [~]
Priority: HIGH
Estimated: 1 hour

Description:
Create dataclass for MCP server configuration.

Acceptance Criteria:
- [x] MCPServerConfig dataclass defined
- [x] All required fields: name, transport, command/args/url, env, timeout, disabled
- [x] Type hints complete
- [x] Docstrings

Files to Create:
- src/oracle/mcp_client.py (add dataclass)
```

#### Task 1.3: MCP Config Loader
```markdown
Status: [~]
Priority: HIGH
Estimated: 4 hours

Description:
Implement configuration loading from YAML file.

Acceptance Criteria:
- [x] Load YAML from ORACLE_MCP_CONFIG path
- [x] Validate required fields (name, transport, command/url)
- [x] Skip disabled entries
- [x] Log errors for invalid entries
- [x] Handle missing file gracefully
- [x] Support env var expansion in env fields
- [x] Return list[MCPServerConfig]

Test Cases:
- Valid stdio server config
- Valid SSE server config
- Missing required field → skip with error log
- Disabled server → skip with info log
- Missing file → warning, empty list
- Invalid YAML → error, empty list

Files to Modify:
- src/oracle/mcp_client.py (_load_config method)
```

#### Task 1.4: MCP Connection Management
```markdown
Status: [~]
Priority: HIGH
Estimated: 6 hours

Description:
Implement connection to MCP servers (stdio and SSE).

Acceptance Criteria:
- [x] Connect to stdio servers via subprocess
- [x] Connect to SSE servers via HTTP
- [x] Store ClientSession instances
- [x] Discover tools from each server
- [x] Handle connection failures gracefully
- [x] Log connection status

Implementation Notes:
Use mcp library:
- stdio_client for subprocess transport
- sse_client for HTTP transport
- ClientSession for MCP protocol

Files to Modify:
- src/oracle/mcp_client.py (connect_all, _connect_stdio, _connect_sse)
```

#### Task 1.5: MCP Tool Invocation
```markdown
Status: [~]
Priority: HIGH
Estimated: 4 hours

Description:
Implement tool call routing with timeout and error handling.

Acceptance Criteria:
- [x] Route calls to correct server
- [x] Timeout support (configurable per server)
- [x] Handle isError responses
- [x] Handle timeout errors
- [x] Handle connection errors
- [x] Always return Tool_Envelope dict
- [x] Never raise exceptions

Test Cases:
- Successful tool call
- Tool returns isError → success: False
- Timeout → success: False with timeout message
- Server unavailable → success: False
- Invalid tool name → success: False

Files to Modify:
- src/oracle/mcp_client.py (call_tool method)
```

#### Task 1.6: MCP Shutdown & Cleanup
```markdown
Status: [~]
Priority: MEDIUM
Estimated: 2 hours

Description:
Implement clean shutdown of MCP connections.

Acceptance Criteria:
- [x] Close all ClientSessions
- [x] Terminate subprocesses
- [x] Handle shutdown errors gracefully
- [x] Log shutdown status

Files to Modify:
- src/oracle/mcp_client.py (shutdown method)
```

---

### Phase 0.2: MCP Registry (Week 1-2)

#### Task 2.1: Schema Translation
```markdown
Status: [~]
Priority: HIGH
Estimated: 6 hours

Description:
Translate MCP JSON Schema to Gemini FunctionDeclaration.

Acceptance Criteria:
- [x] Map type, description, properties, required
- [x] Support enum fields
- [x] Support nested objects
- [x] Support array items
- [x] Log warnings for unsupported keywords ($ref, allOf, anyOf, oneOf)
- [x] Omit unsupported keywords (don't fail)

Test Cases:
- Simple string parameter
- Object with properties
- Array with items
- Enum values
- Nested objects
- Unsupported keyword → warning, omitted

Files to Create:
- src/oracle/mcp_registry.py
```

#### Task 2.2: Tool Name Management
```markdown
Status: [~]
Priority: HIGH
Estimated: 3 hours

Description:
Handle tool name conflicts and mapping.

Acceptance Criteria:
- [x] Detect conflicts with built-in tools
- [x] Prefix with server_name: {server}__{tool}
- [x] Detect conflicts between MCP servers
- [x] Store round-trip mapping
- [x] Log warnings for renamed tools

Files to Modify:
- src/oracle/mcp_registry.py (build_registry method)
```

#### Task 2.3: Function Declaration Generation
```markdown
Status: [~]
Priority: HIGH
Estimated: 2 hours

Description:
Generate Gemini FunctionDeclaration objects.

Acceptance Criteria:
- [x] Create FunctionDeclaration for each MCP tool
- [x] Use translated schema for parameters
- [x] Use tool description (with fallback)
- [x] Return list for model config

Files to Modify:
- src/oracle/mcp_registry.py (_translate_tool, get_function_declarations)
```

#### Task 2.4: MCP Dispatch
```markdown
Status: [~]
Priority: HIGH
Estimated: 2 hours

Description:
Route tool calls to MCP client.

Acceptance Criteria:
- [x] Lookup server/original name from mapping
- [x] Call MCPClient.call_tool
- [x] Return result directly
- [x] Log structured call info

Files to Modify:
- src/oracle/mcp_registry.py (dispatch method)
```

---

### Phase 0.3: Skill Loader (Week 2)

#### Task 3.1: Skill Definition Interface
```markdown
Status: [~]
Priority: HIGH
Estimated: 2 hours

Description:
Define SkillToolDef dataclass and validation.

Acceptance Criteria:
- [x] SkillToolDef dataclass
- [x] Fields: name, description, parameters, handler
- [x] Validation methods
- [x] Support both dataclass and dict formats

Files to Create:
- src/oracle/skill_loader.py
```

#### Task 3.2: Skill Discovery
```markdown
Status: [~]
Priority: HIGH
Estimated: 3 hours

Description:
Scan and import skill modules.

Acceptance Criteria:
- [x] Scan ORACLE_SKILLS_DIR for .py files
- [x] Create directory if missing
- [x] Import each module via importlib
- [x] Skip files without TOOLS attribute
- [x] Handle import errors gracefully
- [x] Continue loading on individual failures

Files to Modify:
- src/oracle/skill_loader.py (load_all method)
```

#### Task 3.3: Skill Lifecycle
```markdown
Status: [~]
Priority: MEDIUM
Estimated: 3 hours

Description:
Implement setup() and teardown() hooks.

Acceptance Criteria:
- [x] Call setup() after successful import
- [x] Support async and sync setup
- [x] Call teardown() on shutdown
- [x] Support async and sync teardown
- [x] Log errors without stopping
- [x] Continue teardown of other skills on error

Files to Modify:
- src/oracle/skill_loader.py (setup, teardown methods)
```

#### Task 3.4: Skill Reload
```markdown
Status: [~]
Priority: MEDIUM
Estimated: 2 hours

Description:
Implement hot-reload of skills.

Acceptance Criteria:
- [x] Rescan skills directory
- [x] Re-import changed modules
- [x] Update ToolRegistry
- [x] Call teardown on old skills
- [x] Call setup on new skills

Files to Modify:
- src/oracle/skill_loader.py (reload method)
```

---

### Phase 0.4: Tool Registry (Week 2-3)

#### Task 4.1: Registry Aggregation
```markdown
Status: [~]
Priority: HIGH
Estimated: 4 hours

Description:
Aggregate tools from all sources.

Acceptance Criteria:
- [x] Accept ToolExecutor, MCPRegistry, SkillLoader
- [x] Build built-in declarations
- [x] Merge MCP declarations
- [x] Merge skill declarations
- [x] Log counts per source

Files to Create:
- src/oracle/tool_registry.py
```

#### Task 4.2: Unified Dispatch
```markdown
Status: [~]
Priority: HIGH
Estimated: 4 hours

Description:
Route calls to correct handler.

Acceptance Criteria:
- [x] Check built-in tools first
- [x] Route MCP tools via MCPRegistry
- [x] Route skill tools via handlers
- [x] Return error for unknown tools
- [x] Try/except at top level
- [x] Never raise exceptions

Files to Modify:
- src/oracle/tool_registry.py (dispatch method)
```

#### Task 4.3: Statistics Tracking
```markdown
Status: [~]
Priority: LOW
Estimated: 2 hours

Description:
Track tool usage statistics.

Acceptance Criteria:
- [x] Count calls per tool
- [x] Count failures per tool
- [x] Provide get_stats() method
- [x] Provide tool_count() method

Files to Modify:
- src/oracle/tool_registry.py
```

---

### Phase 0.5: OracleAgent Integration (Week 3)

#### Task 5.1: Initialize New Components
```markdown
Status: [~]
Priority: HIGH
Estimated: 3 hours

Description:
Add MCP and Skill initialization to OracleAgent.

Acceptance Criteria:
- [x] Create MCPClient in __init__
- [x] Create MCPRegistry
- [x] Create SkillLoader
- [x] Create ToolRegistry
- [x] Call async initialization
- [x] Handle initialization errors

Files to Modify:
- src/oracle/agent_system.py (OracleAgent.__init__)
```

#### Task 5.2: Update _build_config
```markdown
Status: [~]
Priority: HIGH
Estimated: 1 hour

Description:
Use ToolRegistry for function declarations.

Acceptance Criteria:
- [x] Replace hardcoded declarations
- [x] Call ToolRegistry.get_function_declarations()
- [x] Include all tool sources

Files to Modify:
- src/oracle/agent_system.py (_build_config method)
```

#### Task 5.3: Update _dispatch
```markdown
Status: [~]
Priority: HIGH
Estimated: 1 hour

Description:
Delegate dispatch to ToolRegistry.

Acceptance Criteria:
- [x] Replace match statement
- [x] Call ToolRegistry.dispatch()
- [x] Handle async properly

Files to Modify:
- src/oracle/agent_system.py (_dispatch method)
```

#### Task 5.4: Add Shutdown Method
```markdown
Status: [~]
Priority: MEDIUM
Estimated: 2 hours

Description:
Clean shutdown of MCP and skills.

Acceptance Criteria:
- [x] Add close() method
- [x] Call MCPClient.shutdown()
- [x] Call SkillLoader.teardown_all()
- [x] Call from main exit handler

Files to Modify:
- src/oracle/agent_system.py (close method)
- main.py (atexit handler)
```

---

### Phase 0.6: Configuration & Documentation (Week 3)

#### Task 6.1: Example Config Files
```markdown
Status: [~]
Priority: MEDIUM
Estimated: 2 hours

Description:
Create example configuration files.

Acceptance Criteria:
- [x] config/mcp_servers.example.yaml
- [x] Document stdio server example
- [x] Document SSE server example
- [x] Document all fields

Files to Create:
- config/mcp_servers.example.yaml
```

#### Task 6.2: Skills Directory Scaffold
```markdown
Status: [~]
Priority: MEDIUM
Estimated: 2 hours

Description:
Create skills directory with examples.

Acceptance Criteria:
- [x] skills/README.md
- [x] skills/example_skill.py
- [x] Document skill interface
- [x] Show setup/teardown usage

Files to Create:
- skills/README.md
- skills/example_skill.py
```

---

### Phase 0.7: Testing (Week 3-4)

#### Task 7.1: MCP Client Tests
```markdown
Status: [~]
Priority: HIGH
Estimated: 8 hours

Test Cases:
- [~] Config loading (valid, invalid, missing)
- [~] Stdio connection
- [~] SSE connection
- [~] Tool discovery
- [~] Tool invocation (success, error, timeout)
- [~] Server failure handling
- [~] Shutdown cleanup

Property Tests:
- [~] Config round-trip
- [~] Tool envelope structure
```

#### Task 7.2: MCP Registry Tests
```markdown
Status: [~]
Priority: HIGH
Estimated: 6 hours

Test Cases:
- [~] Schema translation (all types)
- [~] Nested objects
- [~] Arrays
- [~] Enums
- [~] Unsupported keywords
- [~] Name conflict resolution
- [~] Dispatch routing

Property Tests:
- [~] Schema translation round-trip
- [~] Name resolution determinism
```

#### Task 7.3: Skill Loader Tests
```markdown
Status: [~]
Priority: HIGH
Estimated: 6 hours

Test Cases:
- [~] Module discovery
- [~] Import success/failure
- [~] TOOLS validation
- [~] Setup/teardown hooks
- [~] Error isolation
- [~] Reload functionality

Property Tests:
- [~] Skill validation
- [~] Reload idempotence
```

#### Task 7.4: Tool Registry Tests
```markdown
Status: [~]
Priority: HIGH
Estimated: 8 hours

Test Cases:
- [~] Built-in tools present
- [~] MCP tools merged
- [~] Skill tools merged
- [~] Dispatch routing
- [~] Unknown tool error
- [~] Exception handling
- [~] Stats tracking

Property Tests:
- [~] Dispatch never raises
- [~] Count consistency
- [~] Built-ins always present
```

#### Task 7.5: Integration Tests
```markdown
Status: [~]
Priority: HIGH
Estimated: 6 hours

Test Cases:
- [~] End-to-end with MCP tool
- [~] End-to-end with skill tool
- [~] Mixed tool sources
- [~] OracleAgent initialization
- [~] OracleAgent shutdown
```

---

## 🚀 Phase 1-6: Future Roadmap

### Phase 1: Model Router
**Timeline: Weeks 5-6**

| Task | Priority | Est. Hours | Status |
|------|----------|------------|--------|
| ModelProvider protocol | HIGH | 4 | [ ] |
| GeminiAdapter | HIGH | 6 | [ ] |
| AnthropicAdapter | HIGH | 6 | [ ] |
| OpenAIAdapter | HIGH | 6 | [ ] |
| OllamaAdapter | HIGH | 4 | [ ] |
| ModelRouter with failover | HIGH | 8 | [ ] |
| Health checks | MEDIUM | 4 | [ ] |
| Cost tracking | MEDIUM | 4 | [ ] |
| Streaming support | HIGH | 6 | [ ] |
| **Total** | | **48** | |

### Phase 2: Multi-Agent
**Timeline: Weeks 7-8**

| Task | Priority | Est. Hours | Status |
|------|----------|------------|--------|
| AgentNode base class | HIGH | 6 | [ ] |
| AgentGraph DAG | HIGH | 8 | [ ] |
| WorkflowEngine | HIGH | 10 | [ ] |
| Conditional branching | HIGH | 6 | [ ] |
| Parallel execution | HIGH | 6 | [ ] |
| A2A protocol | MEDIUM | 8 | [ ] |
| **Total** | | **54** | |

### Phase 3: Interface Layer
**Timeline: Weeks 9-12**

| Task | Priority | Est. Hours | Status |
|------|----------|------------|--------|
| InterfaceBus | HIGH | 6 | [ ] |
| TUI (Textual) | HIGH | 16 | [ ] |
| GUI (PyQt6) | MEDIUM | 20 | [ ] |
| Dev UI (React) | MEDIUM | 24 | [ ] |
| Telegram adapter | HIGH | 6 | [ ] |
| Discord adapter | MEDIUM | 6 | [ ] |
| Slack adapter | MEDIUM | 6 | [ ] |
| WhatsApp adapter | MEDIUM | 8 | [ ] |
| Signal adapter | LOW | 6 | [ ] |
| Teams adapter | LOW | 6 | [ ] |
| **Total** | | **108** | |

### Phase 4: Knowledge Layer
**Timeline: Weeks 13-14**

| Task | Priority | Est. Hours | Status |
|------|----------|------------|--------|
| EmbeddingProvider protocol | HIGH | 4 | [ ] |
| Local embeddings | HIGH | 6 | [ ] |
| Cloud embeddings | MEDIUM | 4 | [ ] |
| ChromaDB integration | HIGH | 6 | [ ] |
| Semantic search | HIGH | 6 | [ ] |
| MarkdownVault | MEDIUM | 8 | [ ] |
| KnowledgeGraph | LOW | 8 | [ ] |
| **Total** | | **42** | |

### Phase 5: Browser + Skills Ecosystem
**Timeline: Weeks 15-16**

| Task | Priority | Est. Hours | Status |
|------|----------|------------|--------|
| Playwright integration | HIGH | 6 | [ ] |
| BrowserAgent | HIGH | 10 | [ ] |
| CDP tools | HIGH | 8 | [ ] |
| SkillRegistry | MEDIUM | 8 | [ ] |
| SkillSandbox | MEDIUM | 8 | [ ] |
| Skill marketplace | MEDIUM | 10 | [ ] |
| **Total** | | **50** | |

### Phase 6: Mobile + Production
**Timeline: Weeks 17-18**

| Task | Priority | Est. Hours | Status |
|------|----------|------------|--------|
| iOS companion app | MEDIUM | 24 | [ ] |
| Android companion app | MEDIUM | 24 | [ ] |
| Heartbeat scheduler | HIGH | 8 | [ ] |
| RBAC system | MEDIUM | 10 | [ ] |
| Production hardening | HIGH | 8 | [ ] |
| **Total** | | **74** | |

---

## 📊 Resource Allocation

### Total Effort Estimate

| Phase | Weeks | Hours | Developers |
|-------|-------|-------|------------|
| 0: MCP + Skills | 4 | 160 | 2 |
| 1: Model Router | 2 | 96 | 2 |
| 2: Multi-Agent | 2 | 108 | 2 |
| 3: Interfaces | 4 | 216 | 3 |
| 4: Knowledge | 2 | 84 | 2 |
| 5: Browser + Skills | 2 | 100 | 2 |
| 6: Mobile + Prod | 2 | 148 | 3 |
| **Total** | **18** | **912** | |

### Parallel Workstreams

```
Week 1-4:  Backend Team (MCP/Skills/Model/Multi-Agent)
           ↓
Week 5-8:  Backend Team → Frontend Team (Interfaces)
           ↓
Week 9-12: Frontend Team → Mobile Team (iOS/Android)
           ↓
Week 13-18: All teams → Integration → Release
```

---

## ✅ Definition of Done (Per Task)

Each task must satisfy:

1. **Code Complete**
   - Implementation follows spec
   - Type hints complete
   - Docstrings added
   - No linting errors

2. **Tests Passing**
   - Unit tests >80% coverage
   - Property tests (where applicable)
   - Integration tests
   - All CI checks pass

3. **Documentation**
   - Code comments
   - README updates
   - Example usage

4. **Review**
   - PR reviewed
   - Changes approved
   - Merged to develop

---

## 🎯 Critical Path

The following tasks are on the critical path (must complete before next phase):

1. **Phase 0:**
   - MCP Client connection management
   - MCP Registry schema translation
   - Tool Registry unified dispatch
   - OracleAgent integration

2. **Phase 1:**
   - ModelRouter failover
   - 2+ provider adapters

3. **Phase 2:**
   - AgentGraph DAG
   - WorkflowEngine

4. **Phase 3:**
   - InterfaceBus
   - TUI or GUI (minimum one)

---

## 📈 Progress Tracking

### Weekly Standup Template

```markdown
## Week X Standup

### Completed
- Task A: [x] Description
- Task B: [x] Description

### In Progress
- Task C: [~] Description (50%)
- Task D: [~] Description (20%)

### Blocked
- Task E: [!] Blocked by ...

### Next Week
- Task F
- Task G
```

### Sprint Review Template

```markdown
## Sprint X Review

### Goals Achieved
- Goal 1: [x] Achieved
- Goal 2: [~] Partial

### Demo
- Feature A working
- Feature B working

### Blockers
- Blocker 1
- Blocker 2

### Next Sprint
- Goal 3
- Goal 4
```

---

*Task Tracker Version: 5.0.0*  
*Last Updated: 2026-03-15*  
*Next Update: Weekly*
