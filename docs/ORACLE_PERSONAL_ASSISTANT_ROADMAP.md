# Oracle Personal Assistant: Transformation Roadmap
## From Enterprise Agent to Consumer AI Platform

**Version:** 5.0 Proposal  
**Date:** March 2026  
**Status:** Specification Phase  

---

## 🎯 Vision Statement

Transform Oracle Agent from an enterprise-focused, single-agent automation system into a **personal AI assistant platform** that combines:
- OpenClaw's messaging-first UX and accessibility
- LangGraph's multi-agent orchestration power  
- CrewAI's role-based collaboration
- Enterprise-grade security with consumer-friendly defaults

**Core Philosophy:** *"Enterprise security, consumer simplicity"*

---

## 📋 Executive Summary

| Current Oracle | Transformed Oracle |
|---------------|-------------------|
| Single-agent | **Multi-agent crews with role-based collaboration** |
| API-first | **Messaging-first with API** |
| Gemini-only | **Model-agnostic** (Gemini, Claude, GPT, Ollama) |
| Sandboxed only | **Configurable: sandboxed ↔ full-access** |
| 4 built-in tools | **5000+ community skills + MCP ecosystem** |
| SQLite/PostgreSQL | **Markdown files OR structured DB** |
| Command-line | **Visual Dev UI + workflow designer** |
| Enterprise users | **Everyone: technical and non-technical** |

---

## 🏗️ New Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         ORACLE PERSONAL ASSISTANT 5.0                           │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐       │
│  │WhatsApp │ │Telegram │ │  Slack  │ │Discord  │ │  Email  │ │  SMS    │       │
│  │(Baileys)│ │(grammY) │ │(Socket) │ │(Bot)    │ │(IMAP)   │ │(Twilio) │       │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘       │
│       └────────────┴───────────┴───────────┴───────────┴───────────┘            │
│                                     │                                           │
│                                     ▼                                           │
│                         ┌─────────────────────┐                                 │
│                         │   UNIVERSAL GATEWAY │  ◄─── Node.js/Python bridge     │
│                         │   (Port 18789)      │       Message normalization      │
│                         └──────────┬──────────┘                                 │
│                                    │                                            │
│       ┌────────────────────────────┼────────────────────────────┐               │
│       │                            │                            │               │
│       ▼                            ▼                            ▼               │
│  ┌─────────┐               ┌──────────────┐              ┌──────────────┐      │
│  │ Dev UI  │◄─────────────▶│   ORACLE     │◄────────────▶│  MCP Client  │      │
│  │(React)  │   WebSocket   │   ORACLESTR  │   A2A Proto  │  (Tools)     │      │
│  └─────────┘               └──────┬───────┘              └──────────────┘      │
│                                   │                                             │
│           ┌───────────────────────┼───────────────────────┐                     │
│           │                       │                       │                     │
│           ▼                       ▼                       ▼                     │
│    ┌─────────────┐       ┌─────────────┐       ┌─────────────────┐             │
│    │  Crew       │       │   Model     │       │   Persistence   │             │
│    │  Manager    │◄─────▶│   Router    │◄─────▶│   Layer         │             │
│    │ (Orchestrate│       │ (Multi-LLM) │       │ (SQL + Markdown)│             │
│    └──────┬──────┘       └─────────────┘       └─────────────────┘             │
│           │                                                                     │
│    ┌──────┴──────┐                                                              │
│    │  AGENT POOL │                                                              │
│    ├─────────────┤                                                              │
│    │ 🤖 Planner  │──┐                                                           │
│    │ 🔧 Coder    │──┤                                                           │
│    │ 📊 Analyst  │──┼──► Multi-agent collaboration via A2A                      │
│    │ 🎨 Designer │──┤                                                           │
│    │ 🔍 Research │──┘                                                           │
│    └─────────────┘                                                              │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                      SKILL RUNTIME                                     │   │
│  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────────┐     │   │
│  │  │  Sandboxed  │ OR │  Docker     │ OR │  Full Access (Trust)    │     │   │
│  │  │  (Default)  │    │  (Isolated) │    │  (User-enabled)         │     │   │
│  │  └─────────────┘    └─────────────┘    └─────────────────────────┘     │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 📦 Phase 1: Foundation (Weeks 1-4)

### 1.1 Model-Agnostic Router

**Current State:** Hardcoded `genai.Client` for Gemini only  
**Target:** Pluggable LLM providers with unified interface

```python
# src/oracle/llm_router.py

from abc import ABC, abstractmethod
from typing import AsyncIterator, Literal
from dataclasses import dataclass
import os

@dataclass
class LLMMessage:
    role: Literal["user", "assistant", "tool", "system"]
    content: str | list[dict]  # Text or multimodal content
    tool_calls: list[dict] | None = None
    tool_results: list[dict] | None = None

@dataclass  
class LLMConfig:
    provider: Literal["gemini", "anthropic", "openai", "ollama", "deepseek"]
    model: str
    api_key: str | None = None
    base_url: str | None = None
    temperature: float = 0.7
    max_tokens: int = 4096
    
class BaseLLMProvider(ABC):
    """Abstract base for all LLM providers."""
    
    @abstractmethod
    async def generate(
        self, 
        messages: list[LLMMessage],
        tools: list[dict] | None = None,
        stream: bool = False
    ) -> LLMMessage:
        """Generate completion with tool support."""
        pass
    
    @abstractmethod
    async def generate_stream(
        self,
        messages: list[LLMMessage],
        tools: list[dict] | None = None
    ) -> AsyncIterator[str]:
        """Stream response tokens."""
        pass
    
    @abstractmethod
    def count_tokens(self, messages: list[LLMMessage]) -> int:
        """Count tokens for rate limiting."""
        pass

class GeminiProvider(BaseLLMProvider):
    """Google Gemini/Vertex AI implementation."""
    def __init__(self, config: LLMConfig):
        from google import genai
        self.client = genai.Client(api_key=config.api_key)
        self.model = config.model
        
    async def generate(self, messages, tools=None, stream=False):
        # Convert to Gemini format, call API, normalize response
        ...
        
class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude implementation."""
    def __init__(self, config: LLMConfig):
        import anthropic
        self.client = anthropic.AsyncAnthropic(api_key=config.api_key)
        self.model = config.model
        
class OpenAIProvider(BaseLLMProvider):
    """OpenAI GPT implementation."""
    ...
    
class OllamaProvider(BaseLLMProvider):
    """Local Ollama models."""
    ...

class LLMRouter:
    """Route requests to appropriate provider with failover."""
    
    def __init__(self):
        self.providers: dict[str, BaseLLMProvider] = {}
        self.primary: str | None = None
        self.fallbacks: list[str] = []
        
    def register_provider(self, name: str, provider: BaseLLMProvider, 
                          is_primary: bool = False):
        self.providers[name] = provider
        if is_primary:
            self.primary = name
            
    def set_fallback_chain(self, names: list[str]):
        self.fallbacks = names
        
    async def generate_with_failover(
        self, 
        messages: list[LLMMessage],
        tools: list[dict] | None = None
    ) -> LLMMessage:
        """Try primary, fall back on failure."""
        providers_to_try = [self.primary] + self.fallbacks if self.primary else self.fallbacks
        
        last_error = None
        for provider_name in providers_to_try:
            try:
                provider = self.providers[provider_name]
                return await provider.generate(messages, tools)
            except Exception as e:
                last_error = e
                logger.warning(f"Provider {provider_name} failed: {e}")
                continue
                
        raise LLMError(f"All providers failed. Last error: {last_error}")
```

**Configuration (oraclesettings.json):**
```json
{
  "llm": {
    "primary": {
      "provider": "anthropic",
      "model": "claude-3-5-sonnet-20241022",
      "api_key": "${ANTHROPIC_API_KEY}"
    },
    "fallbacks": [
      {
        "provider": "gemini",
        "model": "gemini-2.0-flash-exp",
        "api_key": "${GEMINI_API_KEY}"
      },
      {
        "provider": "ollama",
        "model": "llama3.2:70b",
        "base_url": "http://localhost:11434"
      }
    ],
    "routing_strategy": "failover",
    "cost_optimization": {
      "heartbeat_model": "gemini-2.0-flash-lite",
      "complex_tasks": "claude-3-5-sonnet"
    }
  }
}
```

---

### 1.2 Universal Gateway (Messaging Hub)

**New Component:** `src/oracle/gateway/` - Async message normalization service

```python
# src/oracle/gateway/server.py

from fastapi import FastAPI, WebSocket
from typing import Callable, Awaitable
import asyncio

class MessageChannel(ABC):
    """Abstract interface for messaging platforms."""
    
    @abstractmethod
    async def connect(self):
        pass
    
    @abstractmethod
    async def send_message(self, session_id: str, content: str, 
                          attachments: list[Attachment] | None = None):
        pass
    
    @abstractmethod
    async def on_message(self, handler: Callable[[InboundMessage], Awaitable[None]]):
        pass

class InboundMessage:
    """Normalized message format across all platforms."""
    session_id: str  # Unique conversation thread
    sender_id: str   # User identifier
    channel: Literal["whatsapp", "telegram", "slack", "discord", "email", "sms"]
    content: str | MultimodalContent
    timestamp: datetime
    reply_to: str | None  # Threading support
    
class WhatsAppChannel(MessageChannel):
    """WhatsApp Web integration via Baileys."""
    # Node.js bridge or Python implementation
    ...
    
class TelegramChannel(MessageChannel):
    """Telegram Bot API."""
    ...
    
class SlackChannel(MessageChannel):
    """Slack Socket Mode."""
    ...

class GatewayServer:
    """Central message routing hub."""
    
    def __init__(self, port: int = 18789):
        self.app = FastAPI()
        self.channels: dict[str, MessageChannel] = {}
        self.agent_router: AgentRouter | None = None
        self.active_sessions: dict[str, Session] = {}
        
    def register_channel(self, name: str, channel: MessageChannel):
        self.channels[name] = channel
        
    async def handle_inbound(self, message: InboundMessage):
        """Route incoming message to appropriate agent session."""
        
        # Get or create session
        session = self.active_sessions.get(message.session_id)
        if not session:
            session = await self.create_session(message)
            
        # Queue message for processing (serialized per session)
        await session.message_queue.put(message)
        
    async def create_session(self, message: InboundMessage) -> Session:
        """Initialize new agent session with context."""
        
        # Load user preferences from memory
        user_prefs = await self.memory.load_user_prefs(message.sender_id)
        
        # Determine agent crew based on context
        crew = self.orchestrator.create_crew(
            session_id=message.session_id,
            user_id=message.sender_id,
            channel=message.channel,
            preferences=user_prefs
        )
        
        session = Session(
            id=message.session_id,
            crew=crew,
            message_queue=asyncio.Queue(),
            channel=self.channels[message.channel]
        )
        
        self.active_sessions[message.session_id] = session
        
        # Start session processor
        asyncio.create_task(self.process_session(session))
        
        return session
        
    async def process_session(self, session: Session):
        """Process messages for a session sequentially."""
        while True:
            message = await session.message_queue.get()
            
            # Execute agent loop
            response = await session.crew.execute(message)
            
            # Send response back through original channel
            await session.channel.send_message(
                session.id,
                response.content,
                response.attachments
            )
```

---

### 1.3 Multi-Agent Orchestration (Crew Manager)

**New Component:** `src/oracle/crew/` - Multi-agent collaboration system

```python
# src/oracle/crew/manager.py

from typing import TypedDict, Annotated
import operator

class AgentRole(TypedDict):
    """Definition of an agent's role and capabilities."""
    name: str
    description: str
    system_prompt: str
    tools: list[str]
    model_config: LLMConfig
    can_delegate_to: list[str]

class CrewState(TypedDict):
    """Shared state across crew execution."""
    messages: Annotated[list[LLMMessage], operator.add]
    task_plan: list[Task]
    current_task: Task | None
    results: dict[str, Any]
    shared_memory: dict[str, Any]

class Agent:
    """Individual agent with specific role."""
    
    def __init__(self, role: AgentRole, tools: ToolRegistry):
        self.role = role
        self.llm = LLMRouter().get_provider(role.model_config)
        self.tools = {name: tools.get(name) for name in role.tools}
        
    async def execute(self, task: Task, context: CrewState) -> TaskResult:
        """Execute assigned task with available tools."""
        
        messages = [
            LLMMessage(role="system", content=self.role.system_prompt),
            *context["messages"],
            LLMMessage(role="user", content=task.description)
        ]
        
        # ReAct loop
        max_iterations = 20
        for i in range(max_iterations):
            response = await self.llm.generate(messages, tools=self.tools)
            
            if response.tool_calls:
                # Execute tools
                results = await self.execute_tools(response.tool_calls)
                messages.append(LLMMessage(
                    role="tool",
                    content=json.dumps(results)
                ))
            else:
                # Task complete
                return TaskResult(
                    output=response.content,
                    agent=self.role.name,
                    iterations=i
                )
                
    async def execute_tools(self, tool_calls: list[dict]) -> list[dict]:
        """Execute requested tools safely."""
        results = []
        for call in tool_calls:
            tool = self.tools.get(call["name"])
            if tool:
                result = await tool.execute(**call["arguments"])
                results.append({"tool": call["name"], "result": result})
        return results

class CrewManager:
    """Orchestrates multi-agent collaboration."""
    
    def __init__(self):
        self.agents: dict[str, Agent] = {}
        self.orchestration_strategy: Literal["hierarchical", "parallel", "round_robin"] = "hierarchical"
        
    def register_agent(self, agent: Agent):
        self.agents[agent.role.name] = agent
        
    async def execute(self, user_message: InboundMessage) -> CrewOutput:
        """Execute user request with appropriate agents."""
        
        # Phase 1: Planning (Planner agent analyzes and creates task plan)
        planner = self.agents.get("planner")
        plan = await planner.execute(
            Task(description=user_message.content, type="plan"),
            CrewState(messages=[LLMMessage(role="user", content=user_message.content)])
        )
        
        # Phase 2: Execution (Assign tasks to specialized agents)
        results = []
        for task in plan.task_plan:
            agent = self.agents.get(task.assigned_agent)
            if agent:
                result = await agent.execute(task, CrewState(
                    messages=plan.messages,
                    task_plan=plan.task_plan
                ))
                results.append(result)
                
        # Phase 3: Synthesis (Combine results into final response)
        synthesizer = self.agents.get("synthesizer")
        final = await synthesizer.execute(
            Task(description="Synthesize results", context=results),
            CrewState()
        )
        
        return CrewOutput(
            content=final.output,
            thought_process=results,
            agents_involved=[r.agent for r in results]
        )
```

**Default Crew Configuration:**

```yaml
# ~/.oracle/agents/crew-default.yaml
name: default_crew
description: General-purpose personal assistant crew

agents:
  planner:
    name: Planner
    description: Analyzes requests and creates execution plans
    model: claude-3-5-sonnet
    tools: []
    system_prompt: |
      You are a planning specialist. Analyze user requests and break them 
      into specific tasks. Assign each task to the most appropriate agent.
      
  coder:
    name: Code Expert
    description: Writes and debugs code
    model: claude-3-5-sonnet
    tools: [shell_execute, file_system_ops, code_interpreter]
    system_prompt: |
      You are a senior software engineer. Write clean, efficient code.
      Always test your solutions before marking complete.
      
  analyst:
    name: Data Analyst
    description: Analyzes data and creates visualizations
    model: gemini-2.0-flash
    tools: [file_system_ops, data_analysis, chart_generation]
    system_prompt: |
      You are a data analyst. Extract insights from data and create 
      clear visualizations.
      
  researcher:
    name: Researcher
    description: Gathers information from web sources
    model: perplexity-online
    tools: [http_fetch, web_search, news_api]
    system_prompt: |
      You are a research specialist. Find accurate, up-to-date information.
      Cite your sources.

  synthesizer:
    name: Response Writer
    description: Combines outputs into polished responses
    model: claude-3-5-sonnet
    tools: []
    system_prompt: |
      You combine outputs from multiple agents into clear, helpful responses.
      Maintain the user's preferred tone and format.

workflow:
  type: hierarchical
  planner_delegates: true
  max_parallel_agents: 3
  require_approval_for: [shell_execute, file_write, email_send]
```

---

### 1.4 Markdown Persistence Layer

**New Option:** File-based persistence alongside existing SQL

```python
# src/oracle/persistence/markdown_backend.py

from pathlib import Path
import yaml
import frontmatter

class MarkdownPersistence:
    """Git-friendly file-based persistence."""
    
    def __init__(self, workspace_path: Path):
        self.workspace = Path(workspace_path).expanduser()
        self.workspace.mkdir(parents=True, exist_ok=True)
        
        # Create directory structure
        (self.workspace / "sessions").mkdir(exist_ok=True)
        (self.workspace / "memory").mkdir(exist_ok=True)
        (self.workspace / "skills").mkdir(exist_ok=True)
        (self.workspace / "agents").mkdir(exist_ok=True)
        (self.workspace / "logs").mkdir(exist_ok=True)
        
    async def save_session(self, session_id: str, messages: list[LLMMessage]):
        """Save conversation to Markdown file."""
        
        session_file = self.workspace / "sessions" / f"{session_id}.md"
        
        # Build markdown content
        content = "# Session History\n\n"
        for msg in messages:
            timestamp = msg.timestamp.isoformat() if hasattr(msg, 'timestamp') else ""
            content += f"## {msg.role} ({timestamp})\n\n"
            
            if isinstance(msg.content, str):
                content += f"{msg.content}\n\n"
            elif isinstance(msg.content, list):  # Multimodal
                for part in msg.content:
                    if part["type"] == "text":
                        content += f"{part['text']}\n\n"
                    elif part["type"] == "image":
                        content += f"![Image]({part['source']})\n\n"
                        
            if msg.tool_calls:
                content += "### Tool Calls\n\n"
                for call in msg.tool_calls:
                    content += f"- **{call['name']}**: `{call['arguments']}`\n"
                content += "\n"
                
        # Write with YAML frontmatter
        post = frontmatter.Post(
            content,
            session_id=session_id,
            message_count=len(messages),
            updated_at=datetime.now().isoformat()
        )
        
        session_file.write_text(frontmatter.dumps(post))
        
    async def load_memory(self, user_id: str) -> dict:
        """Load user preferences and long-term memory."""
        
        memory_file = self.workspace / "memory" / f"{user_id}.md"
        
        if not memory_file.exists():
            return self._default_memory()
            
        post = frontmatter.load(memory_file)
        
        return {
            "preferences": post.get("preferences", {}),
            "facts": post.get("facts", []),
            "relationships": post.get("relationships", {}),
            "content": post.content  # Free-form notes
        }
        
    async def append_memory(self, user_id: str, category: str, entry: str):
        """Add to long-term memory."""
        
        memory = await self.load_memory(user_id)
        
        if category == "facts":
            memory["facts"].append({
                "content": entry,
                "timestamp": datetime.now().isoformat()
            })
            
        # Rewrite file
        await self._save_memory(user_id, memory)
        
    def _default_memory(self) -> dict:
        return {
            "preferences": {
                "response_style": "concise",
                "notification_hours": ["09:00", "18:00"],
                "preferred_model": "claude-3-5-sonnet"
            },
            "facts": [],
            "relationships": {},
            "content": ""
        }
```

**File Structure:**
```
~/.oracle/
├── oraclesettings.json          # Main configuration
├── sessions/                    # Conversation history
│   ├── whatsapp-12345.md
│   ├── telegram-67890.md
│   └── slack-workspace-abc.md
├── memory/                      # Long-term memory per user
│   ├── user-alice.md
│   └── user-bob.md
├── skills/                      # Installed skills
│   ├── gmail/
│   │   └── skill.yaml
│   ├── github/
│   │   └── skill.yaml
│   └── custom-data-analysis/
│       ├── skill.yaml
│       └── analyze.py
├── agents/                      # Agent crew definitions
│   ├── crew-default.yaml
│   ├── crew-developer.yaml
│   └── crew-creative.yaml
├── logs/                        # Execution logs
│   └── 2026-03/
│       └── 15-execution.log
└── heartbeat.md                 # Scheduled task checklist
```

---

## 📦 Phase 2: Protocols & Ecosystem (Weeks 5-8)

### 2.1 Native MCP (Model Context Protocol) Support

```python
# src/oracle/protocols/mcp_client.py

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class MCPClient:
    """Native MCP client for tool discovery and execution."""
    
    def __init__(self):
        self.sessions: dict[str, ClientSession] = {}
        self.available_tools: dict[str, MCPTool] = {}
        
    async def connect_server(self, name: str, command: str, args: list[str]):
        """Connect to an MCP server."""
        
        server_params = StdioServerParameters(
            command=command,
            args=args,
            env=None
        )
        
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # Discover tools
                tools = await session.list_tools()
                for tool in tools:
                    self.available_tools[f"{name}.{tool.name}"] = MCPTool(
                        session=session,
                        definition=tool
                    )
                    
                self.sessions[name] = session
                
    async def execute_tool(self, tool_name: str, arguments: dict) -> dict:
        """Execute an MCP tool."""
        
        tool = self.available_tools.get(tool_name)
        if not tool:
            raise ValueError(f"Unknown tool: {tool_name}")
            
        result = await tool.session.call_tool(
            tool.definition.name,
            arguments=arguments
        )
        
        return {
            "success": not result.isError,
            "content": result.content,
            "error": result.error if result.isError else None
        }
```

**MCP Servers Configuration:**
```json
{
  "mcp_servers": {
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
    },
    "postgres": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres", "postgresql://localhost/mydb"]
    },
    "puppeteer": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-puppeteer"]
    }
  }
}
```

---

### 2.2 A2A Protocol (Agent-to-Agent Communication)

```python
# src/oracle/protocols/a2a.py

from pydantic import BaseModel
from typing import AsyncIterable

class AgentCard(BaseModel):
    """A2A Agent discovery card."""
    name: str
    description: str
    url: str
    version: str
    capabilities: dict
    skills: list[dict]

class TaskSendParams(BaseModel):
    """A2A task request."""
    id: str
    session_id: str
    message: Message
    accepted_output_modes: list[str] = ["text", "json", "artifact"]
    push_notification: PushNotificationConfig | None = None

class A2AClient:
    """Client for agent-to-agent communication."""
    
    def __init__(self, agent_card: AgentCard):
        self.agent_card = agent_card
        self.http_client = httpx.AsyncClient()
        
    async def discover_agents(self, hub_url: str) -> list[AgentCard]:
        """Discover available agents from A2A hub."""
        response = await self.http_client.get(f"{hub_url}/.well-known/agent.json")
        return [AgentCard(**card) for card in response.json()["agents"]]
        
    async def send_task(self, target_agent: AgentCard, 
                       params: TaskSendParams) -> Task:
        """Send task to another agent."""
        
        response = await self.http_client.post(
            f"{target_agent.url}/tasks/send",
            json=params.model_dump()
        )
        
        return Task(**response.json())
        
    async def send_task_subscribe(
        self, 
        target_agent: AgentCard,
        params: TaskSendParams
    ) -> AsyncIterable[TaskStatusUpdateEvent | TaskArtifactUpdateEvent]:
        """Stream task updates from another agent."""
        
        async with self.http_client.stream(
            "POST",
            f"{target_agent.url}/tasks/sendSubscribe",
            json=params.model_dump()
        ) as response:
            async for line in response.aiter_lines():
                event = json.loads(line)
                if event["type"] == "status":
                    yield TaskStatusUpdateEvent(**event)
                elif event["type"] == "artifact":
                    yield TaskArtifactUpdateEvent(**event)

class A2AServer:
    """A2A protocol server for receiving tasks from other agents."""
    
    def __init__(self, agent_card: AgentCard, port: int = 10000):
        self.agent_card = agent_card
        self.app = FastAPI()
        self.port = port
        
    def setup_routes(self):
        
        @self.app.get("/.well-known/agent.json")
        async def get_agent_card():
            return self.agent_card.model_dump()
            
        @self.app.post("/tasks/send")
        async def send_task(params: TaskSendParams):
            # Handle synchronous task
            result = await self.handle_task(params)
            return result.model_dump()
            
        @self.app.post("/tasks/sendSubscribe")
        async def send_task_subscribe(params: TaskSendParams):
            # Handle streaming task
            async def event_generator():
                async for event in self.handle_task_streaming(params):
                    yield f"data: {json.dumps(event.model_dump())}\n\n"
                    
            return StreamingResponse(
                event_generator(),
                media_type="text/event-stream"
            )
```

---

### 2.3 Oracle Skills Format (Compatible with OpenClaw)

```yaml
# ~/.oracle/skills/gmail/skill.yaml
---
name: gmail
version: 2.1.0
description: Send and receive Gmail messages, manage labels
author: Oracle Community
license: MIT

# Compatibility
target_oracle_version: ">=5.0.0"
compatible_frameworks: [oracle, openclaw]

# Permissions (for sandboxed mode)
permissions:
  - network:outbound:https://gmail.googleapis.com
  - filesystem:read:~/.oracle/credentials/gmail.json
  - filesystem:write:~/.oracle/cache/gmail/

# Triggers
triggers:
  - command: /email
  - command: /gmail
  - pattern: "send (?:an? )?email"
  - pattern: "check (?:my )?inbox"

# Required configuration
config:
  - name: gmail_credentials_path
    type: path
    default: ~/.oracle/credentials/gmail.json
    required: true
  - name: default_recipient
    type: string
    required: false

# Tool definitions (for MCP compatibility)
tools:
  - name: gmail_send
    description: Send an email
    parameters:
      to: { type: string, required: true }
      subject: { type: string, required: true }
      body: { type: string, required: true }
      attachments: { type: array, items: path }
      
  - name: gmail_list
    description: List emails in inbox
    parameters:
      query: { type: string }
      max_results: { type: integer, default: 10 }
      label: { type: string }

# Execution
type: python
main: gmail_skill.py
entrypoint: handle_request

# Sandboxing (default: strict)
sandbox:
  mode: network_restricted  # strict | network_restricted | none
  allowed_hosts:
    - gmail.googleapis.com
    - www.googleapis.com
  filesystem:
    read:
      - ~/.oracle/credentials/
      - ~/.oracle/cache/gmail/
    write:
      - ~/.oracle/cache/gmail/
```

```python
# ~/.oracle/skills/gmail/gmail_skill.py

from oracle.skills import SkillContext, SkillResponse
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

async def handle_request(intent: str, params: dict, context: SkillContext) -> SkillResponse:
    """Main entry point for Gmail skill."""
    
    # Load credentials (skill has permission to read this file)
    creds_path = context.config["gmail_credentials_path"]
    creds = Credentials.from_authorized_user_file(creds_path)
    service = build('gmail', 'v1', credentials=creds)
    
    if intent == "gmail_send":
        result = await send_email(service, params)
        return SkillResponse(
            success=True,
            message=f"Email sent to {params['to']}",
            data=result
        )
        
    elif intent == "gmail_list":
        messages = await list_inbox(service, params)
        return SkillResponse(
            success=True,
            message=f"Found {len(messages)} messages",
            data={"messages": messages}
        )

async def send_email(service, params: dict) -> dict:
    ""Send email via Gmail API."""
    # Implementation...
    pass
```

---

### 2.4 Skill Marketplace Integration

```python
# src/oracle/skills/marketplace.py

class SkillMarketplace:
    """Integration with Oracle Hub (skill registry)."""
    
    HUB_URL = "https://hub.oracle.ai"
    
    async def search_skills(self, query: str, category: str | None = None) -> list[SkillInfo]:
        """Search for skills in the marketplace."""
        
        params = {"q": query}
        if category:
            params["category"] = category
            
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.HUB_URL}/api/skills", params=params)
            return [SkillInfo(**s) for s in response.json()["skills"]]
            
    async def install_skill(self, skill_id: str, version: str | None = None) -> Skill:
        """Download and install a skill."""
        
        # Download skill package
        url = f"{self.HUB_URL}/api/skills/{skill_id}/download"
        if version:
            url += f"?version={version}"
            
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            package = response.content
            
        # Verify signature
        if not self.verify_signature(package):
            raise SecurityError("Skill package signature verification failed")
            
        # Extract to skills directory
        skill_path = Path.home() / ".oracle" / "skills" / skill_id
        await self.extract_package(package, skill_path)
        
        # Load skill manifest
        manifest = yaml.safe_load((skill_path / "skill.yaml").read_text())
        
        # Install dependencies if sandboxed
        if manifest.get("sandbox", {}).get("mode") != "none":
            await self.install_dependencies(skill_path, manifest)
            
        return Skill.from_manifest(manifest, skill_path)
        
    async def get_compatible_skills(self) -> list[SkillInfo]:
        """Get skills compatible with OpenClaw (leverage their ecosystem)."""
        
        # Query both Oracle Hub and ClawHub
        oracle_skills = await self.search_skills("")
        
        async with httpx.AsyncClient() as client:
            clawhub_response = await client.get("https://clawhub.openclaw.ai/api/skills")
            clawhub_skills = clawhub_response.json()
            
        # Filter for skills marked as oracle-compatible
        compatible = [
            s for s in clawhub_skills 
            if "oracle" in s.get("compatible_frameworks", [])
        ]
        
        return oracle_skills + compatible
```

---

## 📦 Phase 3: Visual Experience (Weeks 9-12)

### 3.1 Dev UI Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     DEV UI (React + TypeScript)                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Toolbar: [Sessions] [Crews] [Skills] [Settings]        │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────┐  ┌──────────────────────────────────────┐   │
│  │              │  │                                      │   │
│  │  Session     │  │   Main Content Area                  │   │
│  │  List        │  │                                      │   │
│  │              │  │   ┌──────────────────────────────┐  │   │
│  │  📱 WhatsApp │  │   │   Workflow Designer          │  │   │
│  │  💬 Telegram │  │   │   (ReactFlow Canvas)         │  │   │
│  │  💼 Slack    │  │   └──────────────────────────────┘  │   │
│  │  🎮 Discord  │  │                                      │   │
│  │              │  │   OR                                 │   │
│  │  [+ New]     │  │                                      │   │
│  │              │  │   ┌──────────────────────────────┐  │   │
│  └──────────────┘  │   │   Live Conversation          │  │   │
│                    │   │   + Tool Execution Trace     │  │   │
│  ┌──────────────┐  │   └──────────────────────────────┘  │   │
│  │  Agent Crew  │  │                                      │   │
│  │  Status      │  │   OR                                 │   │
│  │              │  │                                      │   │
│  │  🤖 Planner  │  │   ┌──────────────────────────────┐  │   │
│  │  🔧 Coder    │  │   │   Skill Configuration        │  │   │
│  │  📊 Analyst  │  │   │   (YAML Editor + Form)       │  │   │
│  │  [+] Add     │  │   └──────────────────────────────┘  │   │
│  └──────────────┘  │                                      │   │
│                    └──────────────────────────────────────┘   │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Status Bar: 🟢 Gateway | 🟢 LLM | ⏳ 3 Tasks | 💰 $0.12 │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Visual Workflow Designer

```typescript
// dev-ui/src/components/WorkflowDesigner.tsx

import ReactFlow, { 
  Controls, Background, MiniMap,
  useNodesState, useEdgesState, addEdge 
} from 'reactflow';
import 'reactflow/dist/style.css';

interface WorkflowNode {
  id: string;
  type: 'agent' | 'condition' | 'tool' | 'input' | 'output';
  position: { x: number; y: number };
  data: {
    label: string;
    role?: string;
    tools?: string[];
    condition?: string;
    config?: Record<string, any>;
  };
}

const nodeTypes = {
  agent: AgentNode,
  condition: ConditionNode,
  tool: ToolNode,
  input: InputNode,
  output: OutputNode,
};

export const WorkflowDesigner: React.FC = () => {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  
  const onConnect = useCallback(
    (params) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  );
  
  const exportToCrewYAML = () => {
    // Convert ReactFlow graph to crew configuration
    const crewConfig = {
      name: 'custom_crew',
      agents: nodes
        .filter(n => n.type === 'agent')
        .map(n => ({
          name: n.data.label,
          tools: n.data.tools,
          model: n.data.config?.model || 'claude-3-5-sonnet'
        })),
      workflow: {
        type: 'graph',
        edges: edges.map(e => ({
          from: e.source,
          to: e.target,
          condition: nodes.find(n => n.id === e.source)?.type === 'condition' 
            ? e.data?.condition 
            : undefined
        }))
      }
    };
    
    return yaml.dump(crewConfig);
  };
  
  return (
    <div style={{ height: '100vh' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        nodeTypes={nodeTypes}
        fitView
      >
        <Controls />
        <MiniMap />
        <Background variant="dots" gap={12} size={1} />
      </ReactFlow>
      
      <Toolbar>
        <button onClick={() => addNode('agent')}>+ Agent</button>
        <button onClick={() => addNode('condition')}>+ Condition</button>
        <button onClick={() => addNode('tool')}>+ Tool</button>
        <button onClick={exportToCrewYAML}>Export to YAML</button>
        <button onClick={deployCrew}>Deploy Crew</button>
      </Toolbar>
    </div>
  );
};

// Custom node components
const AgentNode: React.FC<NodeProps> = ({ data }) => {
  return (
    <div className="agent-node">
      <div className="agent-icon">🤖</div>
      <div className="agent-name">{data.label}</div>
      <div className="agent-role">{data.role}</div>
      <div className="agent-tools">
        {data.tools?.map(t => <span key={t} className="tool-badge">{t}</span>)}
      </div>
      <Handle type="target" position={Position.Top} />
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
};
```

### 3.3 Real-Time Debugging Panel

```typescript
// dev-ui/src/components/DebugPanel.tsx

interface ExecutionTrace {
  timestamp: string;
  sessionId: string;
  agent: string;
  step: number;
  thought: string;
  action: ToolCall | null;
  observation: any;
  latency: number;
  tokens: { input: number; output: number };
}

export const DebugPanel: React.FC<{ sessionId: string }> = ({ sessionId }) => {
  const [traces, setTraces] = useState<ExecutionTrace[]>([]);
  const [selectedTrace, setSelectedTrace] = useState<ExecutionTrace | null>(null);
  
  useEffect(() => {
    // WebSocket connection for real-time updates
    const ws = new WebSocket(`ws://localhost:18789/debug/${sessionId}`);
    
    ws.onmessage = (event) => {
      const trace: ExecutionTrace = JSON.parse(event.data);
      setTraces(prev => [...prev, trace]);
    };
    
    return () => ws.close();
  }, [sessionId]);
  
  return (
    <div className="debug-panel">
      <div className="trace-timeline">
        {traces.map((trace, i) => (
          <div 
            key={i}
            className={`trace-item ${trace.agent}`}
            onClick={() => setSelectedTrace(trace)}
          >
            <div className="trace-header">
              <span className="agent-badge">{trace.agent}</span>
              <span className="timestamp">{trace.timestamp}</span>
              <span className="latency">{trace.latency}ms</span>
            </div>
            <div className="thought-preview">
              {trace.thought.substring(0, 100)}...
            </div>
            {trace.action && (
              <div className="action-badge">
                🔧 {trace.action.name}
              </div>
            )}
          </div>
        ))}
      </div>
      
      <div className="trace-detail">
        {selectedTrace ? (
          <>
            <h3>Step {selectedTrace.step}: {selectedTrace.agent}</h3>
            
            <section>
              <h4>🧠 Thought</h4>
              <pre>{selectedTrace.thought}</pre>
            </section>
            
            {selectedTrace.action && (
              <section>
                <h4>🔧 Action</h4>
                <pre>{JSON.stringify(selectedTrace.action, null, 2)}</pre>
              </section>
            )}
            
            <section>
              <h4>👁️ Observation</h4>
              <pre>{JSON.stringify(selectedTrace.observation, null, 2)}</pre>
            </section>
            
            <section>
              <h4>📊 Metrics</h4>
              <div>Latency: {selectedTrace.latency}ms</div>
              <div>Tokens: {selectedTrace.tokens.input} in / {selectedTrace.tokens.output} out</div>
              <div>Cost: ~${calculateCost(selectedTrace.tokens)}</div>
            </section>
          </>
        ) : (
          <div className="empty-state">Select a trace to view details</div>
        )}
      </div>
    </div>
  );
};
```

---

## 📦 Phase 4: Multimodal & Accessibility (Weeks 13-16)

### 4.1 Multimodal Content Processing

```python
# src/oracle/multimodal/processor.py

from PIL import Image
import aiofiles

class MultimodalContent:
    """Unified content type supporting text, image, video, audio."""
    
    def __init__(self, parts: list[ContentPart]):
        self.parts = parts
        
    @classmethod
    def from_text(cls, text: str) -> "MultimodalContent":
        return cls([TextPart(text)])
        
    @classmethod
    async def from_image_path(cls, path: Path) -> "MultimodalContent":
        """Load and optimize image for LLM consumption."""
        
        # Read image
        image = Image.open(path)
        
        # Optimize size (max 4096x4096 for most models)
        max_size = (4096, 4096)
        image.thumbnail(max_size)
        
        # Convert to base64
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        base64_image = base64.b64encode(buffer.getvalue()).decode()
        
        return cls([ImagePart(
            mime_type="image/png",
            base64_data=base64_image,
            width=image.width,
            height=image.height
        )])
        
    @classmethod
    async def from_video_path(cls, path: Path) -> "MultimodalContent":
        """Extract frames from video for analysis."""
        
        # Use ffmpeg to extract key frames
        frames = await extract_key_frames(path, max_frames=10)
        
        parts = []
        for frame in frames:
            parts.append(await cls.frame_to_image_part(frame))
            
        return cls(parts)
        
    @classmethod
    async def from_audio_path(cls, path: Path) -> "MultimodalContent":
        """Transcribe and analyze audio."""
        
        # Transcribe with Whisper
        transcription = await transcribe_audio(path)
        
        return cls([
            AudioPart(
                mime_type="audio/mp3",
                transcript=transcription.text,
                duration=transcription.duration
            )
        ])
        
    def to_gemini_format(self) -> list[dict]:
        """Convert to Gemini API format."""
        return [part.to_gemini() for part in self.parts]
        
    def to_anthropic_format(self) -> list[dict]:
        """Convert to Anthropic API format."""
        return [part.to_anthropic() for part in self.parts]

class MultimodalSkill:
    """Base class for skills that handle multimodal content."""
    
    supported_modalities = ["text", "image", "video", "audio"]
    
    async def process(self, content: MultimodalContent, context: SkillContext) -> SkillResponse:
        """Process multimodal input."""
        
        # Route to appropriate handler based on content type
        if content.has_video():
            return await self.process_video(content, context)
        elif content.has_audio():
            return await self.process_audio(content, context)
        elif content.has_image():
            return await self.process_image(content, context)
        else:
            return await self.process_text(content, context)
```

### 4.2 Non-Technical User Onboarding

```python
# src/oracle/onboarding/flow.py

class OnboardingFlow:
    """Guided setup for non-technical users."""
    
    STEPS = [
        "welcome",
        "model_selection",
        "messaging_setup", 
        "security_preferences",
        "first_agent",
        "done"
    ]
    
    async def run_interactive(self, channel: MessageChannel):
        """Run interactive onboarding via messaging."""
        
        await channel.send_message(
            session_id="onboarding",
            content="👋 Welcome to Oracle! I'm your personal AI assistant. Let's get you set up in 5 minutes."
        )
        
        # Step 1: Model Selection
        await channel.send_message(
            session_id="onboarding",
            content=(
                "**Choose your AI model:**\n\n"
                "1️⃣ **Claude (Anthropic)** - Best reasoning, $15/month typical\n"
                "2️⃣ **Gemini (Google)** - Fast & affordable, $2/month typical\n"
                "3️⃣ **GPT (OpenAI)** - Most capable, $20/month typical\n"
                "4️⃣ **Local (Ollama)** - Free but requires gaming PC\n\n"
                "Reply with 1, 2, 3, or 4."
            )
        )
        
        selection = await self.wait_for_response("onboarding")
        model_config = self.get_model_config(selection)
        
        # Step 2: Messaging Setup (simplified)
        await channel.send_message(
            session_id="onboarding",
            content=(
                "**Connect your messaging apps:**\n\n"
                "I'll send you connection links for:\n"
                "• WhatsApp\n"
                "• Telegram\n"
                "• Slack\n\n"
                "Click the ones you want to use. You can add more later."
            ),
            attachments=[
                Attachment(type="link", url=self.generate_whatsapp_qr()),
                Attachment(type="link", url=self.generate_telegram_link())
            ]
        )
        
        # Step 3: Security Preferences
        await channel.send_message(
            session_id="onboarding",
            content=(
                "**Security Level:**\n\n"
                "🔒 **Safe Mode** (Recommended)\n"
                "I can only access files in my workspace and run safe commands.\n\n"
                "⚠️ **Trust Mode**\n"
                "I can access your entire computer. Only use if you understand the risks.\n\n"
                "Reply SAFE or TRUST"
            )
        )
        
        security_mode = await self.wait_for_response("onboarding")
        
        # Save configuration
        config = UserConfig(
            model=model_config,
            security_mode="sandboxed" if security_mode.lower() == "safe" else "full",
            channels=[],
            preferences={
                "response_style": "friendly",
                "proactive_notifications": True
            }
        )
        
        await self.save_config(config)
        
        # Completion
        await channel.send_message(
            session_id="onboarding",
            content=(
                "✅ **You're all set!**\n\n"
                "Try these commands:\n"
                "• 'Check my email'\n"
                "• 'Summarize this PDF' (attach a file)\n"
                "• 'Research cheap flights to Tokyo'\n"
                "• 'What can you do?'\n\n"
                "I'll learn your preferences over time. Happy assisting! 🤖"
            )
        )
```

### 4.3 Security Mode Toggle

```python
# src/oracle/security/modes.py

class SecurityMode(Enum):
    SANDBOXED = "sandboxed"  # Default: restricted access
    DOCKER = "docker"        # Containerized isolation
    FULL = "full"            # Full system access (user-enabled)

class SecurityManager:
    """Manage security modes with user consent."""
    
    def __init__(self, config: SecurityConfig):
        self.mode = config.security_mode
        self.audit_log: list[SecurityEvent] = []
        
    async def request_elevation(self, action: str, reason: str) -> bool:
        """Request user approval for elevated permissions."""
        
        if self.mode == SecurityMode.FULL:
            return True
            
        # Send approval request to user's primary channel
        approval = await self.send_approval_request(
            title="Permission Required",
            message=f"Action: {action}\nReason: {reason}",
            timeout_seconds=300
        )
        
        self.audit_log.append(SecurityEvent(
            timestamp=datetime.now(),
            action=action,
            approved=approval,
            reason=reason
        ))
        
        return approval
        
    def get_tool_executor(self) -> ToolExecutor:
        """Get appropriate tool executor for current security mode."""
        
        if self.mode == SecurityMode.SANDBOXED:
            return SandboxedToolExecutor(
                allowed_paths=[Path.home() / ".oracle" / "workspace"],
                blocked_commands=["rm -rf /", "sudo", "chmod"],
                network_allowlist=["*.googleapis.com", "*.anthropic.com"]
            )
            
        elif self.mode == SecurityMode.DOCKER:
            return DockerizedToolExecutor(
                image="oracle/sandbox:latest",
                volumes={
                    Path.home() / ".oracle/workspace": "/workspace"
                }
            )
            
        elif self.mode == SecurityMode.FULL:
            # User has explicitly enabled full access
            return FullAccessToolExecutor(
                audit_callback=self.log_full_access_action
            )
            
    async def enable_full_access(self, user_confirmation: str):
        """Enable full system access with explicit consent."""
        
        required_confirmation = (
            "I understand that enabling full access allows the AI to execute "
            "any command on my computer, which could result in data loss or "
            "security breaches. I accept full responsibility for any consequences."
        )
        
        if user_confirmation != required_confirmation:
            raise SecurityError("Confirmation phrase does not match")
            
        # Log the change
        self.audit_log.append(SecurityEvent(
            timestamp=datetime.now(),
            action="SECURITY_MODE_CHANGED",
            old_mode=self.mode,
            new_mode=SecurityMode.FULL,
            user_confirmation_hash=hash(user_confirmation)
        ))
        
        self.mode = SecurityMode.FULL
```

---

## 🛠️ Implementation Roadmap

### Month 1: Foundation
| Week | Deliverable | Key Changes |
|------|-------------|-------------|
| 1 | Model Router | Abstract LLM client, support Gemini/Anthropic/OpenAI/Ollama |
| 2 | Gateway Service | WhatsApp + Telegram integration, message normalization |
| 3 | Crew Manager | Multi-agent orchestration, role-based collaboration |
| 4 | Markdown Persistence | File-based storage option alongside SQL |

### Month 2: Protocols & Ecosystem
| Week | Deliverable | Key Changes |
|------|-------------|-------------|
| 5 | MCP Client | Native MCP support, tool discovery |
| 6 | A2A Protocol | Agent-to-agent communication |
| 7 | Skills System | Skill format, sandboxed execution |
| 8 | Marketplace | Oracle Hub integration, OpenClaw compatibility |

### Month 3: Visual Experience
| Week | Deliverable | Key Changes |
|------|-------------|-------------|
| 9 | Dev UI Foundation | React app, WebSocket real-time updates |
| 10 | Workflow Designer | Visual graph editor, crew YAML export |
| 11 | Debugging Tools | Execution trace, token/cost tracking |
| 12 | Mobile Companion | iOS/Android apps for notifications |

### Month 4: Multimodal & Polish
| Week | Deliverable | Key Changes |
|------|-------------|-------------|
| 13 | Multimodal Support | Image, video, audio processing |
| 14 | Voice Interface | Speech-to-text, text-to-speech |
| 15 | Onboarding Flow | Non-technical user setup |
| 16 | Documentation | Tutorials, examples, migration guide |

---

## 📁 File Structure Changes

```
src/oracle/
├── __init__.py
├── agent_system.py              # Refactored: Core orchestrator
├── llm_router.py                # NEW: Model-agnostic LLM routing
├── gateway/                     # NEW: Messaging hub
│   ├── __init__.py
│   ├── server.py
│   ├── channels/
│   │   ├── __init__.py
│   │   ├── whatsapp.py
│   │   ├── telegram.py
│   │   ├── slack.py
│   │   └── discord.py
│   └── normalization.py
├── crew/                        # NEW: Multi-agent orchestration
│   ├── __init__.py
│   ├── manager.py
│   ├── agent.py
│   ├── workflow.py
│   └── roles/
│       ├── planner.py
│       ├── coder.py
│       ├── analyst.py
│       └── researcher.py
├── protocols/                   # NEW: MCP + A2A
│   ├── __init__.py
│   ├── mcp_client.py
│   └── a2a.py
├── skills/                      # NEW: Skill system
│   ├── __init__.py
│   ├── runtime.py
│   ├── sandbox.py
│   ├── marketplace.py
│   └── registry.py
├── persistence/                 # NEW: Multiple backends
│   ├── __init__.py
│   ├── base.py
│   ├── sql_backend.py           # Existing SQLite/PostgreSQL
│   └── markdown_backend.py      # NEW: File-based
├── multimodal/                  # NEW: Multimodal processing
│   ├── __init__.py
│   ├── processor.py
│   ├── image.py
│   ├── video.py
│   └── audio.py
├── security/                    # NEW: Configurable security
│   ├── __init__.py
│   ├── modes.py
│   ├── sandbox.py
│   └── audit.py
├── dev_ui/                      # NEW: Visual interface
│   ├── frontend/                # React app
│   │   ├── src/
│   │   ├── package.json
│   │   └── tsconfig.json
│   └── server.py                # FastAPI backend
└── onboarding/                  # NEW: User onboarding
    ├── __init__.py
    ├── flow.py
    └── templates/

docs/
├── ORACLE_PERSONAL_ASSISTANT_ROADMAP.md  # This document
├── MIGRATION_GUIDE.md
├── API_REFERENCE.md
└── TUTORIALS/
    ├── getting-started.md
    ├── creating-skills.md
    └── building-crews.md
```

---

## 🔐 Security Considerations

### Default Security Posture
- **Sand-boxed by default**: Only workspace directory access
- **Network restricted**: Whitelist-based outbound connections
- **Tool approval**: High-risk actions require confirmation
- **Audit logging**: All actions logged to immutable log

### Trust Mode (Full Access)
Requires explicit user action:
1. Type exact confirmation phrase
2. Understand risks via interactive quiz
3. Configure approval workflows for destructive actions
4. Regular security audits

### Skill Security
- **Signature verification**: All skills cryptographically signed
- **Permission manifest**: Explicit permission declarations
- **Sandbox options**: strict | network_restricted | none
- **Community ratings**: User reviews and security scores

---

## 📊 Success Metrics

| Metric | Current | Target (6 months) |
|--------|---------|-------------------|
| GitHub Stars | Private | 10,000+ (open source) |
| Active Users | Enterprise only | 50,000+ personal users |
| Skills Available | 4 built-in | 3,000+ community skills |
| Avg. Setup Time | 2 hours | 5 minutes |
| NPS Score | N/A | 50+ |
| Retention (7-day) | N/A | 40%+ |

---

## 🎉 Conclusion

This transformation positions Oracle as the first AI assistant platform to combine:
- 🏢 **Enterprise-grade security** with consumer accessibility
- 🤖 **Multi-agent orchestration** with intuitive UX
- 🔧 **Professional tools** with non-technical onboarding
- 🌐 **Open ecosystem** with safety guarantees

**Next Step:** Review this roadmap and prioritize Phase 1 implementation.
