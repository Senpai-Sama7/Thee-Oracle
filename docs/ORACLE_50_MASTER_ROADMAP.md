# Oracle Agent 5.0 - Personal AI Assistant Platform
## Master Roadmap & Architecture Specification

**Version:** 5.0.0-Alpha  
**Codename:** "Chimera"  
**Status:** Specification Phase  
**Target Release:** Q3 2026  

---

## 🎯 Executive Summary

Oracle 5.0 represents a fundamental transformation from an enterprise automation tool to a **personal AI assistant platform** that combines:

- **OpenClaw's** messaging-first UX and accessibility
- **LangGraph's** multi-agent orchestration power
- **CrewAI's** role-based collaboration
- **Oracle's** enterprise-grade security foundation

### Core Value Proposition
> *"The first AI assistant that scales from personal productivity to enterprise automation without compromising security or control."*

---

## 📊 Feature Matrix: Oracle 4.0 → 5.0

| Capability | Oracle 4.0 | Oracle 5.0 | OpenClaw | Competitive Advantage |
|------------|-----------|------------|----------|----------------------|
| **Interface** | API-only | **TUI + GUI + Messaging + API** | Messaging only | Most comprehensive |
| **Agents** | Single | **Multi-agent crews (5+ roles)** | Single agent | Complex task handling |
| **Messaging** | ❌ | **6 platforms + iOS/Android nodes** | 6 platforms | Mobile companion apps |
| **LLM Support** | Gemini only | **6+ providers + local models** | 6+ providers | Cost optimization |
| **Persistence** | SQL only | **SQL + Markdown + Git** | Markdown only | Best of both worlds |
| **Security** | Sandboxed only | **3-tier (Sandbox/Docker/Full)** | Full access | Enterprise-safe defaults |
| **Skills** | 4 built-in | **5000+ community + MCP** | 5700+ | MCP protocol native |
| **Protocols** | ❌ | **MCP + A2A native** | ❌ | Interoperability |
| **Dev Tools** | ❌ | **Visual designer + TUI debugger** | Basic | Professional tooling |
| **Multimodal** | Screenshots | **Text/Image/Video/Audio/CDP** | Text/Image | Full browser control |
| **Heartbeat** | ❌ | **30min proactive + streaming** | 30min proactive | Real-time feel |
| **Vector DB** | ❌ | **Built-in embeddings** | ❌ | Semantic memory |
| **Model Failover** | ❌ | **Automatic cascade** | ❌ | High availability |
| **Streaming** | ❌ | **Full streaming support** | Partial | Real-time UX |

---

## 🏗️ System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              ORACLE 5.0 - SYSTEM ARCHITECTURE                            │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                         │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│  │                         USER INTERFACE LAYER                                     │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐ │   │
│  │  │   TUI        │  │   GUI        │  │   Dev UI     │  │   Messaging Apps     │ │   │
│  │  │  (Textual)   │  │  (PyQt6)     │  │  (React)     │  │  (WhatsApp/Telegram) │ │   │
│  │  │              │  │              │  │              │  │                      │ │   │
│  │  │ • Terminal   │  │ • System tray│  │ • Workflow   │  │ • iOS/Android nodes  │ │   │
│  │  │   interface  │  │ • Quick actions│   designer   │  │ • Push notifications │ │   │
│  │  │ • Live logs  │  │ • Voice mode │  │ • Debugger   │  │ • Camera/mic access  │ │   │
│  │  │ • REPL mode  │  │ • Canvas     │  │ • Metrics    │  │ • Location sharing   │ │   │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘ │   │
│  │         └─────────────────┴─────────────────┴─────────────────────┘               │   │
│  │                                    │                                               │   │
│  │                         ┌──────────┴──────────┐                                    │   │
│  │                         │   Gateway Service   │ ◄── WebSocket/API (Port 18789)    │   │
│  │                         │   (Python/FastAPI)  │                                    │   │
│  │                         └──────────┬──────────┘                                    │   │
│  └────────────────────────────────────┼───────────────────────────────────────────────┘   │
│                                       │                                                 │
│  ┌────────────────────────────────────┼───────────────────────────────────────────────┐   │
│  │                         ORCHESTRATION LAYER                                        │   │
│  │                                    │                                                │   │
│  │  ┌───────────────────────────────┐ │ ┌─────────────────────────────────────────┐  │   │
│  │  │      Session Manager          │ │ │         Crew Manager                   │  │   │
│  │  │  • Multi-session per channel  │ │ │  • Planner → Workers → Synthesizer     │  │   │
│  │  │  • Isolated contexts          │ │ │  • Parallel/Sequential/Conditional     │  │   │
│  │  │  • Memory per session         │ │ │  • Dynamic agent spawning              │  │   │
│  │  │  • Streaming aggregation      │ │ │  • Task delegation (A2A)               │  │   │
│  │  └───────────────────────────────┘ │ └─────────────────────────────────────────┘  │   │
│  │                                    │                                                │   │
│  │  ┌───────────────────────────────┴─┴───────────────────────────────────────────┐  │   │
│  │  │                         Agent Pool (ReAct Loop)                              │  │   │
│  │  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐               │  │   │
│  │  │  │ Planner │ │  Coder  │ │ Analyst │ │Research │ │General  │               │  │   │
│  │  │  │ (Route) │ │ (Code)  │ │ (Data)  │ │  (Web)  │ │ (Chat)  │               │  │   │
│  │  │  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘               │  │   │
│  │  │       └───────────┴───────────┴───────────┴───────────┘                     │  │   │
│  │  │                              │                                               │  │   │
│  │  └──────────────────────────────┼───────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────┼──────────────────────────────────────────────────┘   │
│                                    │                                                      │
│  ┌─────────────────────────────────┼──────────────────────────────────────────────────┐   │
│  │                      CAPABILITIES LAYER                                            │   │
│  │                                    │                                                │   │
│  │  ┌──────────────────┐  ┌──────────┴──────────┐  ┌──────────────────────────────┐  │   │
│  │  │   LLM Router     │  │   Tool Runtime      │  │      Protocol Clients        │  │   │
│  │  │                  │  │                     │  │                              │  │   │
│  │  │ • Gemini/Vertex  │  │ • Sandboxed (safe)  │  │ • MCP Client                 │  │   │
│  │  │ • Claude         │  │ • Docker (isolated) │  │ • A2A Agent                  │  │   │
│  │  │ • GPT-4o         │  │ • Full (trusted)    │  │ • Custom protocols           │  │   │
│  │  │ • Ollama/Local   │  │                     │  │                              │  │   │
│  │  │ • Failover chain │  │ • Skills (5000+)    │  │                              │  │   │
│  │  │ • Cost optimize  │  │ • CDP Browser       │  │                              │  │   │
│  │  │ • Streaming      │  │ • Shell/FS/HTTP     │  │                              │  │   │
│  │  └──────────────────┘  └─────────────────────┘  └──────────────────────────────┘  │   │
│  │                                                                                   │   │
│  └───────────────────────────────────────────────────────────────────────────────────┘   │
│                                    │                                                      │
│  ┌─────────────────────────────────┼──────────────────────────────────────────────────┐   │
│  │                      PERSISTENCE LAYER                                             │   │
│  │                                    │                                                │   │
│  │  ┌──────────────────┐  ┌──────────┴──────────┐  ┌──────────────────────────────┐   │   │
│  │  │   Structured     │  │   Unstructured      │  │   Vector/Memory              │   │   │
│  │  │                  │  │                     │  │                              │   │   │
│  │  │ • SQLite (WAL)   │  │ • Markdown files    │  │ • ChromaDB (embeddings)      │   │   │
│  │  │ • PostgreSQL     │  │ • Git versioning    │  │ • Semantic search            │   │   │
│  │  │ • GCS backup     │  │ • Human-readable    │  │ • Memory retrieval           │   │   │
│  │  └──────────────────┘  └─────────────────────┘  └──────────────────────────────┘   │   │
│  │                                                                                    │   │
│  └────────────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                           │
└───────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 📋 Phase Breakdown

### Phase 1: Foundation & Core Infrastructure (Weeks 1-6)

**Goal:** Establish the foundational architecture for multi-modal, multi-agent, multi-interface system.

#### Week 1-2: Model Router & Multi-LLM Support

**Deliverables:**
- [ ] Abstract LLM provider interface
- [ ] Gemini, Claude, GPT-4o, Ollama implementations
- [ ] Streaming support across all providers
- [ ] Cost tracking and optimization
- [ ] Automatic failover chain

**Key Files:**
```python
# src/oracle/llm/router.py
class LLMRouter:
    """Route requests to best available provider with failover."""
    
    def __init__(self):
        self.providers: Dict[str, BaseLLMProvider] = {}
        self.primary: str | None = None
        self.fallback_chain: List[str] = []
        self.cost_tracker = CostTracker()
        
    async def generate_with_failover(
        self, 
        messages: List[LLMMessage],
        complexity: ComplexityLevel = ComplexityLevel.AUTO
    ) -> LLMResponse:
        """Auto-select model based on complexity and availability."""
        
        # Complexity-based routing
        if complexity == ComplexityLevel.SIMPLE:
            providers = ["gemini-flash-lite", "ollama"]
        elif complexity == ComplexityLevel.COMPLEX:
            providers = ["claude-opus", "gpt-4o", "gemini-pro"]
        else:
            providers = [self.primary] + self.fallback_chain
            
        for provider_name in providers:
            try:
                return await self._generate(provider_name, messages)
            except Exception as e:
                logger.warning(f"{provider_name} failed: {e}")
                continue
                
        raise AllProvidersFailed()
```

#### Week 3-4: Messaging Gateway

**Deliverables:**
- [ ] Universal Gateway service (FastAPI + WebSocket)
- [ ] WhatsApp integration (Baileys bridge)
- [ ] Telegram integration (aiogram)
- [ ] Session management per channel
- [ ] Message normalization layer

**Architecture:**
```python
# src/oracle/gateway/server.py
class UniversalGateway:
    """Central hub for all messaging interfaces."""
    
    def __init__(self):
        self.channels: Dict[str, MessageChannel] = {}
        self.sessions: Dict[str, Session] = {}
        self.app = FastAPI()
        
    async def route_message(self, message: InboundMessage):
        """Route to appropriate session with isolation."""
        
        # Create isolated session per user+channel combo
        session_key = f"{message.channel}:{message.sender_id}"
        
        if session_key not in self.sessions:
            self.sessions[session_key] = await self.create_session(
                channel=message.channel,
                user_id=message.sender_id,
                isolated=True  # Each session has own memory/context
            )
            
        session = self.sessions[session_key]
        await session.process(message)
```

#### Week 5-6: Multi-Agent Orchestration (Crew Manager)

**Deliverables:**
- [ ] Agent role definitions (Planner, Coder, Analyst, Researcher, General)
- [ ] Hierarchical workflow (Planner → Workers → Synthesizer)
- [ ] Parallel execution for independent tasks
- [ ] Conditional branching support
- [ ] Inter-agent communication (A2A protocol foundation)

**Crew Configuration:**
```yaml
# ~/.oracle/crews/personal_assistant.yaml
crew:
  name: Personal Assistant
  workflow_type: hierarchical
  max_parallel: 3
  
agents:
  - name: Planner
    description: Analyzes requests and creates execution plans
    model: claude-3-5-sonnet
    system_prompt: |
      You are a planning specialist. Break down complex requests into 
      specific tasks and assign them to appropriate agents.
    tools: []
    
  - name: Coder
    description: Writes and debugs code
    model: claude-3-5-sonnet
    system_prompt: |
      You are a senior software engineer. Write clean, tested code.
    tools: [shell_execute, file_system_ops, code_interpreter]
    can_receive_from: [Planner]
    
  - name: Analyst
    description: Analyzes data and creates visualizations
    model: gemini-2.0-flash
    system_prompt: |
      You are a data analyst. Extract insights and create visualizations.
    tools: [file_system_ops, data_analysis, chart_generation]
    can_receive_from: [Planner]
    
  - name: Synthesizer
    description: Combines outputs into polished responses
    model: claude-3-5-sonnet
    system_prompt: |
      You combine agent outputs into clear, helpful responses.
    tools: []
    can_receive_from: [Coder, Analyst, Researcher]
    
conditional_branching:
  enabled: true
  rules:
    - condition: "task_type == 'coding'"
      route_to: Coder
    - condition: "task_type == 'data_analysis'"
      route_to: Analyst
    - condition: "requires_research"
      spawn: Researcher
```

---

### Phase 2: Interfaces & Protocols (Weeks 7-12)

#### Week 7-8: TUI (Terminal User Interface)

**Technology:** Textual (Python TUI framework)

**Features:**
- Real-time conversation view
- Live streaming of agent thoughts
- Split-pane: Chat | Logs | Metrics
- Command palette (Ctrl+K)
- Session switcher
- Interactive configuration

```python
# src/oracle/ui/tui/app.py
from textual.app import App
from textual.containers import Horizontal, Vertical
from textual.widgets import Header, Footer, DataTable, Log, Input, Static

class OracleTUI(App):
    """Terminal interface for Oracle 5.0."""
    
    CSS = """
    Screen { align: center middle; }
    #main { width: 100%; height: 100%; }
    #chat { width: 60%; }
    #sidebar { width: 40%; }
    #metrics { height: 30%; }
    #logs { height: 70%; }
    """
    
    def compose(self):
        yield Header(show_clock=True)
        
        with Horizontal(id="main"):
            # Main chat area
            with Vertical(id="chat"):
                yield ConversationView(id="conversation")
                yield Input(placeholder="Type a message...", id="input")
            
            # Sidebar: Metrics + Logs
            with Vertical(id="sidebar"):
                yield MetricsView(id="metrics")
                yield LogView(id="logs")
                
        yield Footer()
        
    async def on_input_submitted(self, event: Input.Submitted):
        """Handle user message."""
        await self.process_message(event.value)
        
    async def process_message(self, message: str):
        """Stream agent response to UI."""
        conversation = self.query_one("#conversation", ConversationView)
        
        # Add user message
        conversation.add_message(role="user", content=message)
        
        # Stream agent response
        async for chunk in self.oracle.generate_stream(message):
            conversation.append_to_last_message(chunk)
            
        # Update metrics
        self.query_one("#metrics", MetricsView).update(
            self.oracle.get_session_metrics()
        )
```

#### Week 9-10: GUI (Desktop Application)

**Technology:** PyQt6 (cross-platform) or Tauri (Rust + Web)

**Features:**
- System tray icon with quick actions
- Voice mode (push-to-talk)
- Canvas mode (visual workspace)
- Screenshot annotation
- File drag-and-drop
- Settings GUI

```python
# src/oracle/ui/gui/main_window.py
from PyQt6.QtWidgets import QMainWindow, QSystemTrayIcon, QMenu
from PyQt6.QtCore import Qt, QThread, pyqtSignal

class OracleGUI(QMainWindow):
    """Desktop GUI for Oracle 5.0."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Oracle")
        self.setGeometry(100, 100, 1200, 800)
        
        # System tray
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon("oracle.png"))
        self.tray_icon.setVisible(True)
        
        # Tray menu
        tray_menu = QMenu()
        tray_menu.addAction("Quick Action", self.show_quick_action)
        tray_menu.addAction("Voice Mode", self.toggle_voice_mode)
        tray_menu.addSeparator()
        tray_menu.addAction("Exit", self.quit)
        self.tray_icon.setContextMenu(tray_menu)
        
        # Main tabs
        self.tabs = QTabWidget()
        self.tabs.addTab(ChatWidget(), "Chat")
        self.tabs.addTab(CanvasWidget(), "Canvas")
        self.tabs.addTab(WorkflowWidget(), "Workflows")
        self.tabs.addTab(SettingsWidget(), "Settings")
        
        self.setCentralWidget(self.tabs)
        
    def show_quick_action(self):
        """Global quick action popup."""
        dialog = QuickActionDialog(self)
        dialog.exec()
```

#### Week 11-12: Dev UI (Web-Based)

**Technology:** React + TypeScript + Vite

**Features:**
- Visual workflow designer (ReactFlow)
- Real-time debugging panel
- Cost/token tracking
- Agent state visualization
- Memory inspection
- Tool execution trace

```typescript
// dev-ui/src/components/WorkflowDesigner.tsx
import ReactFlow, { 
  Background, Controls, MiniMap,
  useNodesState, useEdgesState, addEdge,
  Node, Edge
} from 'reactflow';

interface WorkflowNode extends Node {
  data: {
    agent: string;
    role: string;
    tools: string[];
    condition?: string;
  };
}

export const WorkflowDesigner: React.FC = () => {
  const [nodes, setNodes, onNodesChange] = useNodesState<WorkflowNode>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  
  const onConnect = useCallback(
    (params) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  );
  
  const addAgentNode = (agentType: string) => {
    const newNode: WorkflowNode = {
      id: `agent-${nodes.length}`,
      type: 'agent',
      position: { x: 250, y: nodes.length * 100 },
      data: {
        agent: agentType,
        role: getAgentRole(agentType),
        tools: getAgentTools(agentType)
      }
    };
    setNodes((nds) => [...nds, newNode]);
  };
  
  const exportToYAML = () => {
    const workflow = {
      crew: {
        name: 'Custom Workflow',
        workflow_type: 'graph',
        agents: nodes.map(n => ({
          name: n.data.agent,
          role: n.data.role,
          tools: n.data.tools
        })),
        edges: edges.map(e => ({
          from: e.source,
          to: e.target,
          condition: nodes.find(n => n.id === e.source)?.data.condition
        }))
      }
    };
    
    downloadYAML(yaml.dump(workflow));
  };
  
  return (
    <div style={{ height: '100vh' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        nodeTypes={{ agent: AgentNode }}
        fitView
      >
        <Background />
        <Controls />
        <MiniMap />
      </ReactFlow>
      
      <Toolbar>
        <button onClick={() => addAgentNode('Planner')}>+ Planner</button>
        <button onClick={() => addAgentNode('Coder')}>+ Coder</button>
        <button onClick={() => addAgentNode('Analyst')}>+ Analyst</button>
        <button onClick={exportToYAML}>Export YAML</button>
        <button onClick={deployWorkflow}>Deploy</button>
      </Toolbar>
    </div>
  );
};
```

---

### Phase 3: Protocols & Ecosystem (Weeks 13-18)

#### Week 13-14: MCP (Model Context Protocol)

**Native MCP Client:**
```python
# src/oracle/protocols/mcp/client.py
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class OracleMCPClient:
    """Native MCP client for tool discovery and execution."""
    
    def __init__(self):
        self.sessions: Dict[str, ClientSession] = {}
        self.available_tools: Dict[str, MCPTool] = {}
        
    async def connect_servers(self, config: MCPConfig):
        """Connect to configured MCP servers."""
        
        for name, server_config in config.servers.items():
            await self._connect_server(name, server_config)
            
    async def _connect_server(self, name: str, config: MCPServerConfig):
        """Connect to single MCP server."""
        
        server_params = StdioServerParameters(
            command=config.command,
            args=config.args,
            env=config.env
        )
        
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # Discover tools
                tools_response = await session.list_tools()
                
                for tool in tools_response.tools:
                    self.available_tools[f"{name}.{tool.name}"] = MCPTool(
                        server=name,
                        name=tool.name,
                        description=tool.description,
                        schema=tool.inputSchema,
                        session=session
                    )
                    
                self.sessions[name] = session
                logger.info(f"Connected MCP server: {name} ({len(tools_response.tools)} tools)")
                
    async def execute_tool(self, tool_name: str, arguments: dict) -> ToolResult:
        """Execute MCP tool with automatic retry."""
        
        tool = self.available_tools.get(tool_name)
        if not tool:
            return ToolResult(error=f"Unknown tool: {tool_name}")
            
        try:
            result = await tool.session.call_tool(
                tool.name,
                arguments=arguments
            )
            
            return ToolResult(
                success=not result.isError,
                content=result.content,
                error=result.error if result.isError else None
            )
            
        except Exception as e:
            logger.error(f"MCP tool execution failed: {e}")
            return ToolResult(error=str(e))
```

#### Week 15-16: A2A Protocol (Agent-to-Agent)

```python
# src/oracle/protocols/a2a/server.py
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from typing import AsyncIterable

class AgentCard(BaseModel):
    """A2A Agent discovery card."""
    name: str
    description: str
    url: str
    version: str
    capabilities: Dict[str, bool]
    skills: List[SkillInfo]
    
class TaskSendParams(BaseModel):
    """A2A task request parameters."""
    id: str
    session_id: str
    message: Message
    accepted_output_modes: List[str] = ["text", "json", "artifact"]
    push_notification: Optional[PushNotificationConfig] = None

class A2AServer:
    """A2A protocol server for receiving tasks from other agents."""
    
    def __init__(self, agent_card: AgentCard, port: int = 10000):
        self.agent_card = agent_card
        self.port = port
        self.app = FastAPI(title=f"A2A - {agent_card.name}")
        self._setup_routes()
        
    def _setup_routes(self):
        
        @self.app.get("/.well-known/agent.json")
        async def get_agent_card():
            """Return agent card for discovery."""
            return self.agent_card.model_dump()
            
        @self.app.post("/tasks/send")
        async def send_task(params: TaskSendParams) -> Task:
            """Handle synchronous task request."""
            
            # Route to appropriate agent in crew
            result = await self.crew_manager.execute(
                user_input=params.message.content,
                context={"source": "a2a", "session_id": params.session_id}
            )
            
            return Task(
                id=params.id,
                session_id=params.session_id,
                status=TaskStatus.COMPLETED if result.success else TaskStatus.FAILED,
                artifacts=[Artifact(text=result.output)] if result.success else [],
                history=[Message(role="agent", content=result.output)]
            )
            
        @self.app.post("/tasks/sendSubscribe")
        async def send_task_subscribe(params: TaskSendParams) -> StreamingResponse:
            """Handle streaming task request."""
            
            async def event_stream():
                async for update in self.crew_manager.execute_streaming(
                    user_input=params.message.content
                ):
                    yield f"data: {json.dumps(update.model_dump())}\n\n"
                    
            return StreamingResponse(
                event_stream(),
                media_type="text/event-stream"
            )
```

#### Week 17-18: Skills Ecosystem

**Skill Format (OpenClaw-compatible):**
```yaml
# ~/.oracle/skills/github/skill.yaml
---
skill_version: "2.0"
name: github
description: GitHub repository management and PR reviews
author: Oracle Community
license: MIT

target_oracle_version: ">=5.0.0"
compatible_frameworks: [oracle, openclaw]

# Permissions for sandboxed mode
permissions:
  network:
    outbound:
      - api.github.com
      - raw.githubusercontent.com
  filesystem:
    read:
      - ~/.oracle/credentials/github.json
    write:
      - ~/.oracle/cache/github/

# Triggers
triggers:
  commands:
    - /github
    - /pr
    - /repo
  patterns:
    - "create (?:a )?pull request"
    - "review (?:my )?code"
    - "check (?:github )?notifications"

# Configuration schema
config:
  github_token:
    type: secret
    required: true
    description: GitHub personal access token
  default_repo:
    type: string
    required: false
    description: Default repository (owner/repo format)

# Tool definitions
tools:
  github_create_pr:
    description: Create a pull request
    parameters:
      repo:
        type: string
        description: Repository (owner/repo)
      title:
        type: string
        description: PR title
      body:
        type: string
        description: PR description
      base:
        type: string
        default: main
      head:
        type: string
        description: Branch to merge
        
  github_review_pr:
    description: Review a pull request with AI
    parameters:
      repo:
        type: string
      pr_number:
        type: integer
      focus_areas:
        type: array
        items:
          enum: [security, performance, style, logic]

# Implementation
type: python
entrypoint: github_skill.py
sandbox_mode: network_restricted  # strict | network_restricted | none

# Dependencies (auto-installed in sandbox)
dependencies:
  - PyGithub>=2.0
  - gitpython
```

**Skill Marketplace Integration:**
```python
# src/oracle/skills/marketplace.py
class SkillMarketplace:
    """Integration with Oracle Hub and ClawHub."""
    
    HUBS = {
        "oracle": "https://hub.oracle.ai/api",
        "clawhub": "https://clawhub.openclaw.ai/api"
    }
    
    async def search(self, query: str, filters: SearchFilters) -> List[SkillInfo]:
        """Search across all configured hubs."""
        
        results = []
        
        async with httpx.AsyncClient() as client:
            for hub_name, hub_url in self.HUBS.items():
                try:
                    response = await client.get(
                        f"{hub_url}/skills",
                        params={"q": query, **filters.model_dump()}
                    )
                    skills = [SkillInfo(**s, source=hub_name) for s in response.json()["skills"]]
                    results.extend(skills)
                except Exception as e:
                    logger.warning(f"Failed to search {hub_name}: {e}")
                    
        return sorted(results, key=lambda s: s.rating, reverse=True)
        
    async def install(self, skill_id: str, source: str = "auto") -> Skill:
        """Install skill from marketplace."""
        
        # Determine source
        if source == "auto":
            # Try Oracle Hub first, fallback to ClawHub
            sources = ["oracle", "clawhub"]
        else:
            sources = [source]
            
        for src in sources:
            try:
                return await self._install_from_hub(skill_id, src)
            except SkillNotFound:
                continue
                
        raise SkillNotFound(f"Skill {skill_id} not found in any hub")
        
    async def auto_install(self, task_description: str) -> Optional[Skill]:
        """Automatically find and install skill for task."""
        
        # Search for relevant skills
        results = await self.search(task_description, limit=5)
        
        if not results:
            return None
            
        # Score relevance
        best_match = max(results, key=lambda s: s.relevance_score)
        
        if best_match.relevance_score > 0.8:
            logger.info(f"Auto-installing skill {best_match.name} for task")
            return await self.install(best_match.id, best_match.source)
            
        return None
```

---

### Phase 4: Advanced Features (Weeks 19-24)

#### Week 19-20: Vector Embeddings & Semantic Memory

```python
# src/oracle/memory/vector_store.py
import chromadb
from chromadb.config import Settings
import numpy as np

class SemanticMemory:
    """Vector-based semantic memory with ChromaDB."""
    
    def __init__(self, persist_dir: Path):
        self.client = chromadb.Client(Settings(
            persist_directory=str(persist_dir),
            anonymized_telemetry=False
        ))
        
    async def remember(self, user_id: str, content: str, category: str = "general"):
        """Store memory with embedding."""
        
        collection = self.client.get_or_create_collection(
            name=f"memory_{user_id}",
            metadata={"category": category}
        )
        
        # Generate embedding
        embedding = await self.embed(content)
        
        # Store with metadata
        collection.add(
            documents=[content],
            embeddings=[embedding],
            metadatas=[{
                "timestamp": datetime.now().isoformat(),
                "category": category
            }],
            ids=[f"{category}_{uuid.uuid4()}"]
        )
        
    async def recall(
        self, 
        user_id: str, 
        query: str, 
        limit: int = 5,
        category: Optional[str] = None
    ) -> List[MemoryEntry]:
        """Retrieve relevant memories."""
        
        collection = self.client.get_collection(f"memory_{user_id}")
        
        # Generate query embedding
        query_embedding = await self.embed(query)
        
        # Search
        where = {"category": category} if category else None
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=limit,
            where=where
        )
        
        return [
            MemoryEntry(
                content=doc,
                relevance=1 - distance,  # Convert distance to similarity
                metadata=meta,
                timestamp=meta["timestamp"]
            )
            for doc, distance, meta in zip(
                results["documents"][0],
                results["distances"][0],
                results["metadatas"][0]
            )
        ]
        
    async def embed(self, text: str) -> List[float]:
        """Generate embedding using local model or API."""
        
        # Prefer local embedding model
        if self.local_embedder:
            return self.local_embedder.encode(text)
            
        # Fallback to API
        return await self.llm_router.embed(text)
```

#### Week 21-22: CDP Browser Control & Multimodal

```python
# src/oracle/tools/browser/cdp.py
from playwright.async_api import async_playwright, Page, Browser

class CDPBrowserController:
    """Full browser automation via Chrome DevTools Protocol."""
    
    def __init__(self):
        self.browser: Browser | None = None
        self.pages: Dict[str, Page] = {}
        
    async def launch(self, headless: bool = False):
        """Launch browser with CDP."""
        
        self.playwright = await async_playwright().start()
        
        # Connect to existing Chrome or launch new
        try:
            self.browser = await self.playwright.chromium.connect_over_cdp(
                "http://localhost:9222"
            )
        except:
            self.browser = await self.playwright.chromium.launch(
                headless=headless,
                args=["--remote-debugging-port=9222"]
            )
            
    async def navigate(self, session_id: str, url: str):
        """Navigate to URL."""
        
        if session_id not in self.pages:
            self.pages[session_id] = await self.browser.new_page()
            
        page = self.pages[session_id]
        await page.goto(url)
        
    async def perform_action(
        self, 
        session_id: str, 
        action: BrowserAction
    ) -> ActionResult:
        """Perform browser action."""
        
        page = self.pages.get(session_id)
        if not page:
            return ActionResult(error="No active session")
            
        try:
            if action.type == "click":
                await page.click(action.selector)
                
            elif action.type == "type":
                await page.fill(action.selector, action.text)
                
            elif action.type == "screenshot":
                screenshot = await page.screenshot(full_page=action.full_page)
                return ActionResult(screenshot=screenshot)
                
            elif action.type == "extract":
                content = await page.eval_on_selector(
                    action.selector,
                    "el => el.innerText"
                )
                return ActionResult(content=content)
                
            elif action.type == "scroll":
                await page.evaluate(f"window.scrollBy(0, {action.amount})")
                
            return ActionResult(success=True)
            
        except Exception as e:
            return ActionResult(error=str(e))
            
    async def observe(self, session_id: str) -> PageObservation:
        """Get current page state for agent."""
        
        page = self.pages[session_id]
        
        return PageObservation(
            url=page.url,
            title=await page.title(),
            screenshot=await page.screenshot(),
            interactive_elements=await self._find_interactive_elements(page),
            text_content=await page.inner_text("body")
        )
```

#### Week 23-24: Heartbeat, Streaming & Mobile Nodes

**Heartbeat System:**
```python
# src/oracle/heartbeat/scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler

class HeartbeatScheduler:
    """Proactive task checking and scheduled work."""
    
    def __init__(self, oracle: OracleCore):
        self.oracle = oracle
        self.scheduler = AsyncIOScheduler()
        self.checklist_path = Path.home() / ".oracle" / "HEARTBEAT.md"
        
    async def start(self):
        """Start heartbeat scheduler."""
        
        # Schedule main heartbeat
        self.scheduler.add_job(
            self._run_heartbeat,
            "interval",
            minutes=30,
            id="main_heartbeat"
        )
        
        # Schedule quiet hours check
        self.scheduler.add_job(
            self._check_quiet_hours,
            "cron",
            hour="23",
            minute="0"
        )
        
        self.scheduler.start()
        
    async def _run_heartbeat(self):
        """Execute heartbeat checklist."""
        
        # Check if in quiet hours
        if self._in_quiet_hours():
            logger.debug("In quiet hours, skipping heartbeat")
            return
            
        # Parse checklist
        checklist = self._parse_checklist()
        
        # Use cheap model for heartbeat
        response = await self.oracle.generate(
            messages=[
                LLMMessage(
                    role="system",
                    content="You are checking scheduled tasks. Be concise."
                ),
                LLMMessage(
                    role="user",
                    content=f"Check these tasks: {checklist}"
                )
            ],
            preferred_provider="gemini-flash-lite"  # Cost optimization
        )
        
        # If action needed, notify user
        if "HEARTBEAT_OK" not in response.content:
            await self._notify_user(response.content)
            
    async def _notify_user(self, message: str):
        """Send notification through primary channel."""
        
        # Get user's primary channel
        primary_channel = self.oracle.get_user_preference("primary_channel")
        
        await self.oracle.gateway.send_message(
            channel=primary_channel,
            content=f"🔔 {message}"
        )
```

**Streaming Support:**
```python
# src/oracle/generation/streaming.py
from typing import AsyncIterator, Callable

class StreamingGenerator:
    """Real-time streaming for all interfaces."""
    
    def __init__(self):
        self.subscribers: List[Callable[[StreamEvent], None]] = []
        
    async def generate_stream(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Tool]] = None
    ) -> AsyncIterator[StreamChunk]:
        """Generate with real-time streaming."""
        
        provider = self.llm_router.get_provider()
        
        # Stream tokens
        async for token in provider.generate_stream(messages, tools):
            chunk = StreamChunk(
                type="token",
                content=token,
                timestamp=datetime.now()
            )
            
            # Notify all subscribers (TUI, GUI, messaging)
            for subscriber in self.subscribers:
                await subscriber(chunk)
                
            yield chunk
            
        # Stream thinking/reasoning if available
        if hasattr(provider, 'get_thinking'):
            thinking = await provider.get_thinking()
            yield StreamChunk(
                type="thinking",
                content=thinking
            )
            
    def subscribe(self, callback: Callable[[StreamEvent], None]):
        """Subscribe to stream events."""
        self.subscribers.append(callback)
        
    def unsubscribe(self, callback: Callable[[StreamEvent], None]):
        """Unsubscribe from stream events."""
        self.subscribers.remove(callback)
```

**Mobile Companion Nodes:**
```swift
// iOS/OracleNode/ContentView.swift
import SwiftUI

struct ContentView: View {
    @StateObject private var viewModel = NodeViewModel()
    
    var body: some View {
        NavigationView {
            VStack {
                // Connection status
                ConnectionStatusView(status: viewModel.connectionStatus)
                
                // Messages
                ScrollView {
                    LazyVStack {
                        ForEach(viewModel.messages) { message in
                            MessageBubble(message: message)
                        }
                    }
                }
                
                // Input
                HStack {
                    Button(action: { viewModel.showCamera() }) {
                        Image(systemName: "camera")
                    }
                    
                    Button(action: { viewModel.startVoice() }) {
                        Image(systemName: "mic")
                    }
                    
                    TextField("Message...", text: $viewModel.inputText)
                    
                    Button(action: { viewModel.send() }) {
                        Image(systemName: "arrow.up.circle.fill")
                    }
                }
                .padding()
            }
            .navigationTitle("Oracle")
        }
        .onAppear {
            viewModel.connect()
        }
    }
}

class NodeViewModel: ObservableObject {
    @Published var messages: [Message] = []
    @Published var connectionStatus: ConnectionStatus = .disconnected
    
    private var webSocketTask: URLSessionWebSocketTask?
    
    func connect() {
        // Connect to Oracle Gateway
        let url = URL(string: "ws://oracle.local:18789/node/ios")!
        webSocketTask = URLSession.shared.webSocketTask(with: url)
        
        webSocketTask?.resume()
        receiveMessage()
        
        // Register capabilities
        sendCapabilities([
            "camera": true,
            "microphone": true,
            "location": true,
            "notifications": true
        ])
    }
    
    func send() {
        let message = [
            "type": "text",
            "content": inputText,
            "timestamp": ISO8601DateFormatter().string(from: Date())
        ]
        
        webSocketTask?.send(.data(try! JSONSerialization.data(withJSONObject: message)))
        inputText = ""
    }
    
    func sendPhoto(_ image: UIImage) {
        // Convert and send photo
        let base64 = image.jpegData(compressionQuality: 0.8)!.base64EncodedString()
        
        let message = [
            "type": "image",
            "content": base64,
            "mime_type": "image/jpeg"
        ]
        
        webSocketTask?.send(.data(try! JSONSerialization.data(withJSONObject: message)))
    }
    
    private func receiveMessage() {
        webSocketTask?.receive { [weak self] result in
            switch result {
            case .success(let message):
                // Handle incoming message
                self?.handleIncoming(message)
                self?.receiveMessage() // Continue listening
                
            case .failure(let error):
                self?.connectionStatus = .error(error.localizedDescription)
            }
        }
    }
}
```

---

## 🔐 Security Model Specification

### Three-Tier Security

```python
# src/oracle/security/manager.py
from enum import Enum

class SecurityMode(Enum):
    SANDBOXED = "sandboxed"      # Default: maximum safety
    DOCKER = "docker"            # Middle: containerized
    FULL = "full"                # Maximum power: user responsibility

class SecurityManager:
    """Configurable security with explicit consent."""
    
    def __init__(self, mode: SecurityMode = SecurityMode.SANDBOXED):
        self.mode = mode
        self.audit_log = AuditLogger()
        
    def get_executor(self) -> ToolExecutor:
        """Get appropriate executor for current security mode."""
        
        if self.mode == SecurityMode.SANDBOXED:
            return SandboxedExecutor(
                allowed_paths=[Path.home() / ".oracle" / "workspace"],
                blocked_commands=["sudo", "rm -rf /", "chmod 777", ">/dev/null"],
                network_allowlist=[
                    "*.googleapis.com",
                    "*.anthropic.com",
                    "*.openai.com",
                    "api.github.com"
                ]
            )
            
        elif self.mode == SecurityMode.DOCKER:
            return DockerExecutor(
                image="oracle/sandbox:latest",
                volumes={
                    Path.home() / ".oracle/workspace": "/workspace"
                },
                network_mode="bridge",
                resource_limits={
                    "memory": "2g",
                    "cpus": "2.0"
                }
            )
            
        elif self.mode == SecurityMode.FULL:
            # Requires explicit user consent
            return FullAccessExecutor(
                audit_callback=self.audit_log.record,
                require_confirmation_for=self.config.dangerous_actions
            )
            
    async def request_elevation(self, to_mode: SecurityMode) -> bool:
        """Request security mode elevation with consent."""
        
        if to_mode == SecurityMode.FULL:
            # Require explicit typed confirmation
            confirmation = await self.prompt_user(
                title="⚠️ Enable Full System Access?",
                message="""
This will allow Oracle to:
• Access any file on your computer
• Execute any command
• Modify system settings

Only enable if you understand the risks.

Type "I understand and accept the risks" to continue:
                """,
                require_exact_match="I understand and accept the risks"
            )
            
            if not confirmation:
                return False
                
            # Log the change
            self.audit_log.record_security_change(
                from_mode=self.mode,
                to_mode=to_mode,
                user_consent=True,
                timestamp=datetime.now()
            )
            
        self.mode = to_mode
        return True
```

---

## 📊 Configuration Schema

### oraclesettings.json (Complete)

```json
{
  "$schema": "https://oracle.ai/schemas/settings-v5.json",
  "version": "5.0.0",
  
  "oracle": {
    "name": "My Oracle Assistant",
    "mode": "personal",
    "auto_start": true,
    "workspace_path": "~/.oracle/workspace"
  },
  
  "interfaces": {
    "tui": {
      "enabled": true,
      "theme": "dark",
      "split_layout": "horizontal"
    },
    "gui": {
      "enabled": true,
      "system_tray": true,
      "start_minimized": false
    },
    "dev_ui": {
      "enabled": true,
      "port": 8080,
      "features": {
        "workflow_designer": true,
        "debugger": true,
        "metrics": true
      }
    },
    "messaging": {
      "gateway": {
        "enabled": true,
        "port": 18789,
        "host": "0.0.0.0"
      },
      "channels": {
        "whatsapp": {
          "enabled": true,
          "qr_timeout": 60
        },
        "telegram": {
          "enabled": true,
          "bot_token": "${TELEGRAM_BOT_TOKEN}"
        },
        "slack": {
          "enabled": false,
          "socket_mode": true
        },
        "discord": {
          "enabled": false
        },
        "signal": {
          "enabled": false
        },
        "imessage": {
          "enabled": false,
          "platform": "macos"
        },
        "teams": {
          "enabled": false
        }
      }
    }
  },
  
  "llm": {
    "providers": {
      "anthropic": {
        "enabled": true,
        "model": "claude-3-5-sonnet-20241022",
        "api_key": "${ANTHROPIC_API_KEY}",
        "temperature": 0.7
      },
      "openai": {
        "enabled": true,
        "model": "gpt-4o",
        "api_key": "${OPENAI_API_KEY}"
      },
      "gemini": {
        "enabled": true,
        "model": "gemini-2.0-flash-exp",
        "api_key": "${GEMINI_API_KEY}"
      },
      "ollama": {
        "enabled": false,
        "model": "llama3.2:70b",
        "base_url": "http://localhost:11434"
      }
    },
    "routing": {
      "primary": "anthropic",
      "fallback_chain": ["gemini", "ollama"],
      "strategy": "failover",
      "cost_optimization": {
        "enabled": true,
        "simple_tasks": "gemini-2.0-flash-lite",
        "complex_tasks": "claude-3-5-sonnet",
        "heartbeat": "gemini-2.0-flash-lite"
      }
    },
    "streaming": {
      "enabled": true,
      "show_thinking": true
    }
  },
  
  "crew": {
    "default": "personal_assistant",
    "max_parallel_agents": 3,
    "conditional_branching": true,
    "agents": {
      "planner": {
        "enabled": true,
        "model": "claude-3-5-sonnet"
      },
      "coder": {
        "enabled": true,
        "model": "claude-3-5-sonnet",
        "tools": ["shell", "filesystem", "code_interpreter"]
      },
      "analyst": {
        "enabled": true,
        "model": "gemini-2.0-flash"
      },
      "researcher": {
        "enabled": true,
        "model": "perplexity-online"
      }
    }
  },
  
  "persistence": {
    "backend": "hybrid",
    "sql": {
      "url": "sqlite:///~/.oracle/oracle.db"
    },
    "markdown": {
      "enabled": true,
      "path": "~/.oracle",
      "git_integration": true,
      "auto_commit": true
    },
    "vector": {
      "enabled": true,
      "backend": "chroma",
      "persist_dir": "~/.oracle/vector_db"
    }
  },
  
  "protocols": {
    "mcp": {
      "enabled": true,
      "servers": {
        "filesystem": {
          "command": "npx",
          "args": ["-y", "@modelcontextprotocol/server-filesystem", "~/.oracle/workspace"]
        },
        "github": {
          "command": "npx",
          "args": ["-y", "@modelcontextprotocol/server-github"],
          "env": {
            "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}"
          }
        }
      }
    },
    "a2a": {
      "enabled": true,
      "port": 10000,
      "discoverable": false
    }
  },
  
  "skills": {
    "path": "~/.oracle/skills",
    "auto_install": true,
    "trusted_hubs": [
      "https://hub.oracle.ai",
      "https://clawhub.openclaw.ai"
    ],
    "sandbox": {
      "default_mode": "strict"
    }
  },
  
  "security": {
    "mode": "sandboxed",
    "elevation": {
      "require_confirmation": true,
      "timeout_seconds": 300
    },
    "audit": {
      "enabled": true,
      "log_path": "~/.oracle/logs/audit.log"
    }
  },
  
  "heartbeat": {
    "enabled": true,
    "interval_minutes": 30,
    "quiet_hours": {
      "start": "23:00",
      "end": "08:00"
    }
  },
  
  "multimodal": {
    "enabled": true,
    "image": {
      "max_size": 4096,
      "formats": ["png", "jpg", "webp"]
    },
    "video": {
      "enabled": true,
      "max_duration": 300
    },
    "audio": {
      "enabled": true,
      "transcribe": true
    }
  }
}
```

---

## 📈 Success Metrics & Milestones

### Phase 1 (Weeks 1-6)
| Metric | Target | Measurement |
|--------|--------|-------------|
| Multi-LLM support | 4 providers | Integration tests pass |
| Messaging | 2 channels (WhatsApp, Telegram) | E2E tests pass |
| Multi-agent | 3+ agents collaborating | Unit test coverage >80% |
| Performance | <2s p95 response | Benchmark suite |

### Phase 2 (Weeks 7-12)
| Metric | Target | Measurement |
|--------|--------|-------------|
| TUI usability | 10 min setup | User testing |
| GUI stability | <1 crash/day | Telemetry |
| Dev UI adoption | 50% of devs | Analytics |

### Phase 3 (Weeks 13-18)
| Metric | Target | Measurement |
|--------|--------|-------------|
| MCP tools | 20+ tools | Registry count |
| Skill installs | 100+ skills | Hub analytics |
| A2A agents | 5+ connected | Integration tests |

### Phase 4 (Weeks 19-24)
| Metric | Target | Measurement |
|--------|--------|-------------|
| Mobile nodes | iOS + Android | App store release |
| Heartbeat tasks | 5+ daily | Usage analytics |
| Vector memory | 90% recall accuracy | Benchmark |

---

## 🚀 Getting Started (Quick Start)

```bash
# Install Oracle 5.0
curl -fsSL https://oracle.ai/install.sh | bash

# Or using pip
pip install oracle-assistant

# Initialize configuration
oracle init --interactive

# Start all services
oracle start --all

# Or start specific interfaces
oracle start --tui      # Terminal UI
oracle start --gui      # Desktop app
oracle start --gateway  # Messaging hub
oracle start --dev-ui   # Web interface
```

---

*Document Version: 5.0.0-Alpha*  
*Last Updated: 2026-03-15*  
*Next Review: 2026-04-01*
