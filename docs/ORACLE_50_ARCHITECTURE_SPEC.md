# Oracle 5.0 - Detailed Architecture Specification
## Component-Level Design & Interfaces

---

## Table of Contents
1. [System Overview](#system-overview)
2. [Component Architecture](#component-architecture)
3. [Data Flow](#data-flow)
4. [Interface Specifications](#interface-specifications)
5. [Security Architecture](#security-architecture)

---

## System Overview

### Design Principles

1. **Modularity:** Each component can run independently
2. **Scalability:** Horizontal scaling via message queues
3. **Extensibility:** Plugin architecture for tools and interfaces
4. **Observability:** Comprehensive logging, metrics, and tracing
5. **Security:** Defense in depth with configurable trust levels

---

## Component Architecture

### 1. Gateway Service (`src/oracle/gateway/`)

**Purpose:** Central hub for all user interfaces (TUI, GUI, Messaging, Dev UI)

```
┌─────────────────────────────────────────────────────────────┐
│                    GATEWAY SERVICE                          │
│                    Port: 18789 (WebSocket/API)              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │   WebSocket  │  │   HTTP API   │  │   SSE Stream     │  │
│  │   Handler    │  │   Handler    │  │   Handler        │  │
│  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘  │
│         └─────────────────┴────────────────────┘            │
│                           │                                 │
│                    ┌──────┴──────┐                         │
│                    │   Router    │                         │
│                    │  (Session   │                         │
│                    │   Mgmt)     │                         │
│                    └──────┬──────┘                         │
│                           │                                 │
│         ┌─────────────────┼─────────────────┐              │
│         ▼                 ▼                 ▼              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   TUI        │  │   GUI        │  │   Messaging  │     │
│  │   Handler    │  │   Handler    │  │   Handler    │     │
│  │   (Local)    │  │   (Local)    │  │   (Remote)   │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Key Classes:**

```python
# src/oracle/gateway/server.py

class GatewayServer:
    """Central message routing hub."""
    
    def __init__(self, config: GatewayConfig):
        self.config = config
        self.app = FastAPI(title="Oracle Gateway")
        self.session_manager = SessionManager()
        self.message_router = MessageRouter()
        self.rate_limiter = RateLimiter()
        
    async def startup(self):
        """Initialize all protocol handlers."""
        
        # WebSocket for real-time interfaces
        @self.app.websocket("/ws/{client_id}")
        async def websocket_endpoint(websocket: WebSocket, client_id: str):
            await self.handle_websocket(websocket, client_id)
            
        # HTTP API for REST clients
        self.app.include_router(self._create_api_router())
        
        # SSE for streaming responses
        @self.app.get("/stream/{session_id}")
        async def stream_endpoint(session_id: str):
            return await self.handle_sse_stream(session_id)
            
    async def handle_websocket(self, websocket: WebSocket, client_id: str):
        """Handle WebSocket connection."""
        
        await websocket.accept()
        
        # Register client
        client = WebSocketClient(
            id=client_id,
            socket=websocket,
            capabilities=await self.negotiate_capabilities(websocket)
        )
        
        self.session_manager.register_client(client)
        
        try:
            while True:
                # Receive message
                data = await websocket.receive_json()
                message = InboundMessage.from_dict(data)
                
                # Rate limiting
                if not self.rate_limiter.allow(client_id):
                    await websocket.send_json({
                        "error": "Rate limit exceeded"
                    })
                    continue
                    
                # Route to session
                response = await self.route_message(message, client)
                
                # Send response
                if response.stream:
                    await self.stream_response(websocket, response)
                else:
                    await websocket.send_json(response.to_dict())
                    
        except WebSocketDisconnect:
            self.session_manager.unregister_client(client_id)
            
    async def route_message(
        self, 
        message: InboundMessage,
        client: Client
    ) -> OutboundMessage:
        """Route message to appropriate handler."""
        
        # Get or create session
        session = await self.session_manager.get_session(
            session_id=message.session_id,
            user_id=message.user_id,
            channel=client.type
        )
        
        # Process through orchestrator
        return await session.process(message)


class SessionManager:
    """Manages user sessions with isolation."""
    
    def __init__(self):
        self.sessions: Dict[str, Session] = {}
        self.clients: Dict[str, Client] = {}
        self.lock = asyncio.Lock()
        
    async def get_session(
        self,
        session_id: str,
        user_id: str,
        channel: str
    ) -> Session:
        """Get existing or create new isolated session."""
        
        async with self.lock:
            if session_id not in self.sessions:
                # Create new isolated session
                self.sessions[session_id] = await self._create_session(
                    session_id=session_id,
                    user_id=user_id,
                    channel=channel
                )
                
            return self.sessions[session_id]
            
    async def _create_session(
        self,
        session_id: str,
        user_id: str,
        channel: str
    ) -> Session:
        """Create new session with full isolation."""
        
        # Load user preferences and memory
        user_prefs = await self.persistence.load_user_prefs(user_id)
        memory = await self.persistence.load_memory(user_id)
        
        # Create crew for this session
        crew = await self.crew_manager.create_crew(
            crew_type=user_prefs.get("default_crew", "personal_assistant"),
            user_id=user_id,
            session_context={
                "channel": channel,
                "preferences": user_prefs,
                "memory": memory
            }
        )
        
        return Session(
            id=session_id,
            user_id=user_id,
            channel=channel,
            crew=crew,
            created_at=datetime.now(),
            message_queue=asyncio.Queue()
        )
```

---

### 2. LLM Router (`src/oracle/llm/`)

**Purpose:** Unified interface for multiple LLM providers with failover and cost optimization

```python
# src/oracle/llm/router.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncIterator, Literal
import asyncio

@dataclass
class LLMMessage:
    """Unified message format across all providers."""
    role: Literal["system", "user", "assistant", "tool"]
    content: Union[str, List[ContentPart]]
    tool_calls: Optional[List[ToolCall]] = None
    tool_results: Optional[List[ToolResult]] = None
    timestamp: Optional[datetime] = None
    
    @classmethod
    def text(cls, role: str, content: str) -> "LLMMessage":
        return cls(role=role, content=content)
        
    @classmethod
    def multimodal(
        cls, 
        role: str, 
        parts: List[ContentPart]
    ) -> "LLMMessage":
        return cls(role=role, content=parts)

@dataclass
class ContentPart:
    """Single part of multimodal content."""
    type: Literal["text", "image", "audio", "video"]
    content: Union[str, bytes]
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class LLMResponse:
    """Unified response format."""
    content: Union[str, List[ContentPart]]
    tool_calls: Optional[List[ToolCall]] = None
    thinking: Optional[str] = None
    usage: TokenUsage
    model: str
    provider: str
    latency_ms: int
    finish_reason: str

@dataclass
class TokenUsage:
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float

class BaseLLMProvider(ABC):
    """Abstract base for all LLM providers."""
    
    def __init__(self, config: ProviderConfig):
        self.config = config
        self.name = config.name
        self.model = config.model
        
    @abstractmethod
    async def generate(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[ToolSpec]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False
    ) -> LLMResponse:
        """Generate completion."""
        pass
        
    @abstractmethod
    async def generate_stream(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[ToolSpec]] = None
    ) -> AsyncIterator[StreamChunk]:
        """Stream response tokens."""
        pass
        
    @abstractmethod
    async def embed(self, text: str) -> List[float]:
        """Generate embedding vector."""
        pass
        
    @abstractmethod
    def count_tokens(self, messages: List[LLMMessage]) -> int:
        """Count tokens in messages."""
        pass

class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude implementation."""
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        import anthropic
        self.client = anthropic.AsyncAnthropic(api_key=config.api_key)
        
    async def generate(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[ToolSpec]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False
    ) -> LLMResponse:
        
        # Convert to Anthropic format
        anthropic_messages = []
        system_prompt = None
        
        for msg in messages:
            if msg.role == "system":
                system_prompt = self._extract_text(msg)
                continue
                
            anthropic_msg = {
                "role": "assistant" if msg.role == "assistant" else "user",
                "content": self._convert_content(msg.content)
            }
            anthropic_messages.append(anthropic_msg)
            
        # Build request
        kwargs = {
            "model": self.model,
            "messages": anthropic_messages,
            "max_tokens": max_tokens or 4096,
            "temperature": temperature
        }
        
        if system_prompt:
            kwargs["system"] = system_prompt
            
        if tools:
            kwargs["tools"] = [self._convert_tool(t) for t in tools]
            
        # Execute
        start = asyncio.get_event_loop().time()
        response = await self.client.messages.create(**kwargs)
        latency = int((asyncio.get_event_loop().time() - start) * 1000)
        
        # Convert back to unified format
        return self._convert_response(response, latency)
        
    async def generate_stream(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[ToolSpec]] = None
    ) -> AsyncIterator[StreamChunk]:
        
        kwargs = self._build_request(messages, tools, stream=True)
        
        async with self.client.messages.stream(**kwargs) as stream:
            async for event in stream:
                if event.type == "content_block_delta":
                    yield StreamChunk(
                        type="token",
                        content=event.delta.text,
                        timestamp=datetime.now()
                    )
                elif event.type == "thinking":
                    yield StreamChunk(
                        type="thinking",
                        content=event.thinking,
                        timestamp=datetime.now()
                    )

class LLMRouter:
    """Intelligent routing across multiple providers."""
    
    def __init__(self, config: RouterConfig):
        self.providers: Dict[str, BaseLLMProvider] = {}
        self.primary: Optional[str] = None
        self.fallback_chain: List[str] = []
        self.cost_tracker = CostTracker()
        self.health_checker = HealthChecker()
        
    def register_provider(
        self,
        name: str,
        provider: BaseLLMProvider,
        is_primary: bool = False
    ):
        """Register a provider."""
        self.providers[name] = provider
        
        if is_primary:
            self.primary = name
            
        # Start health checks
        self.health_checker.start_checking(name, provider)
        
    async def generate(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[ToolSpec]] = None,
        complexity: ComplexityLevel = ComplexityLevel.AUTO,
        preferred_provider: Optional[str] = None,
        require_tools: bool = False
    ) -> LLMResponse:
        """Generate with intelligent routing and failover."""
        
        # Determine provider order
        providers_to_try = self._select_providers(
            complexity=complexity,
            preferred=preferred_provider,
            require_tools=require_tools
        )
        
        last_error = None
        
        for provider_name in providers_to_try:
            provider = self.providers[provider_name]
            
            # Check health
            if not self.health_checker.is_healthy(provider_name):
                logger.warning(f"Skipping unhealthy provider: {provider_name}")
                continue
                
            try:
                logger.debug(f"Trying provider: {provider_name}")
                
                response = await provider.generate(
                    messages=messages,
                    tools=tools
                )
                
                # Track cost
                self.cost_tracker.record(
                    provider=provider_name,
                    model=provider.model,
                    usage=response.usage
                )
                
                # Mark success
                self.health_checker.record_success(provider_name)
                
                return response
                
            except Exception as e:
                logger.warning(f"Provider {provider_name} failed: {e}")
                self.health_checker.record_failure(provider_name, e)
                last_error = e
                continue
                
        raise AllProvidersFailed(f"All providers failed: {last_error}")
        
    def _select_providers(
        self,
        complexity: ComplexityLevel,
        preferred: Optional[str],
        require_tools: bool
    ) -> List[str]:
        """Select providers to try in order."""
        
        candidates = []
        
        # Add preferred if specified
        if preferred and preferred in self.providers:
            candidates.append(preferred)
            
        # Add complexity-appropriate providers
        if complexity == ComplexityLevel.SIMPLE:
            # Cheap/fast models for simple tasks
            candidates.extend([
                "gemini-flash-lite",
                "ollama"
            ])
        elif complexity == ComplexityLevel.COMPLEX:
            # Powerful models for complex tasks
            candidates.extend([
                "claude-opus",
                "gpt-4o",
                "gemini-pro"
            ])
        else:
            # Auto-detect or use defaults
            if self.primary:
                candidates.append(self.primary)
            candidates.extend(self.fallback_chain)
            
        # Filter for tool support if required
        if require_tools:
            candidates = [
                c for c in candidates 
                if self.providers[c].supports_tools
            ]
            
        # Remove duplicates while preserving order
        seen = set()
        unique = []
        for c in candidates:
            if c not in seen and c in self.providers:
                seen.add(c)
                unique.append(c)
                
        return unique
```

---

### 3. Crew Manager (`src/oracle/crew/`)

**Purpose:** Multi-agent orchestration with hierarchical, parallel, and conditional workflows

```python
# src/oracle/crew/manager.py

from typing import TypedDict, Annotated, Literal
import operator
from graphlib import TopologicalSorter

class WorkflowState(TypedDict):
    """Shared state across workflow execution."""
    messages: Annotated[List[LLMMessage], operator.add]
    tasks: Dict[str, Task]
    results: Dict[str, TaskResult]
    shared_memory: Dict[str, Any]
    execution_graph: Dict[str, Set[str]]  # task_id -> dependencies
    
class Agent:
    """Individual agent with specific role and capabilities."""
    
    def __init__(
        self,
        role: AgentRole,
        llm_router: LLMRouter,
        tool_registry: ToolRegistry,
        memory: Optional[AgentMemory] = None
    ):
        self.role = role
        self.llm = llm_router
        self.tools = {
            name: tool_registry.get(name) 
            for name in role.tools
        }
        self.memory = memory or AgentMemory()
        
    async def execute(
        self,
        task: Task,
        context: WorkflowState,
        streaming: bool = False
    ) -> TaskResult:
        """Execute task with ReAct loop."""
        
        start_time = asyncio.get_event_loop().time()
        
        # Build system prompt
        system_prompt = self._build_system_prompt(context)
        
        # Build conversation
        messages = [
            LLMMessage(role="system", content=system_prompt),
            *context["messages"],
            LLMMessage(role="user", content=task.description)
        ]
        
        # Add context from dependencies
        if task.dependencies:
            dep_results = [
                context["results"][dep_id].output
                for dep_id in task.dependencies
                if dep_id in context["results"]
            ]
            if dep_results:
                messages.append(LLMMessage(
                    role="user",
                    content=f"Context from previous tasks:\n" + "\n".join(dep_results)
                ))
                
        # ReAct loop
        tool_calls_made = []
        max_iterations = 20
        
        for iteration in range(max_iterations):
            # Convert tools to LLM format
            tools_spec = [
                {
                    "name": name,
                    "description": tool.description,
                    "parameters": tool.parameters
                }
                for name, tool in self.tools.items()
            ]
            
            # Generate
            response = await self.llm.generate(
                messages=messages,
                tools=tools_spec if tools_spec else None,
                preferred_provider=self.role.model
            )
            
            # Check for tool calls
            if response.tool_calls:
                for call in response.tool_calls:
                    tool = self.tools.get(call["name"])
                    
                    if tool:
                        # Execute tool
                        result = await tool.execute(**call["arguments"])
                        
                        tool_calls_made.append({
                            "tool": call["name"],
                            "arguments": call["arguments"],
                            "result": result
                        })
                        
                        # Add to conversation
                        messages.append(LLMMessage(
                            role="tool",
                            content=json.dumps(result)
                        ))
                    else:
                        messages.append(LLMMessage(
                            role="tool",
                            content=json.dumps({"error": f"Unknown tool: {call['name']}"})
                        ))
            else:
                # Task complete
                latency = int((asyncio.get_event_loop().time() - start_time) * 1000)
                
                return TaskResult(
                    task_id=task.id,
                    success=True,
                    output=self._extract_text(response),
                    agent=self.role.name,
                    tool_calls=tool_calls_made,
                    iterations=iteration + 1,
                    latency_ms=latency,
                    token_usage=response.usage
                )
                
        # Max iterations reached
        return TaskResult(
            task_id=task.id,
            success=False,
            output="Max iterations reached without completion",
            agent=self.role.name,
            tool_calls=tool_calls_made,
            iterations=max_iterations,
            latency_ms=int((asyncio.get_event_loop().time() - start_time) * 1000)
        )
        
    def _build_system_prompt(self, context: WorkflowState) -> str:
        """Build system prompt with role and context."""
        
        prompt_parts = [
            self.role.system_prompt,
            "",
            f"You are {self.role.name}. {self.role.description}",
            "",
            "Available tools:",
            *[f"- {name}: {tool.description}" for name, tool in self.tools.items()],
        ]
        
        if context.get("shared_memory"):
            prompt_parts.extend([
                "",
                "Shared context:",
                json.dumps(context["shared_memory"], indent=2)
            ])
            
        return "\n".join(prompt_parts)

class CrewManager:
    """Orchestrates multi-agent workflows."""
    
    def __init__(
        self,
        llm_router: LLMRouter,
        tool_registry: ToolRegistry,
        config: CrewConfig
    ):
        self.llm = llm_router
        self.tools = tool_registry
        self.config = config
        self.agents: Dict[str, Agent] = {}
        
    def register_agent(self, role: AgentRole):
        """Register an agent role."""
        
        self.agents[role.name] = Agent(
            role=role,
            llm_router=self.llm,
            tool_registry=self.tools
        )
        
    async def execute_workflow(
        self,
        user_input: str,
        workflow_type: Literal["hierarchical", "parallel", "sequential"] = "hierarchical",
        streaming: bool = False
    ) -> CrewResult:
        """Execute user request with appropriate workflow."""
        
        if workflow_type == "hierarchical":
            return await self._execute_hierarchical(user_input, streaming)
        elif workflow_type == "parallel":
            return await self._execute_parallel(user_input, streaming)
        else:
            return await self._execute_sequential(user_input, streaming)
            
    async def _execute_hierarchical(
        self,
        user_input: str,
        streaming: bool
    ) -> CrewResult:
        """Hierarchical: Planner → Workers → Synthesizer."""
        
        state: WorkflowState = {
            "messages": [LLMMessage(role="user", content=user_input)],
            "tasks": {},
            "results": {},
            "shared_memory": {},
            "execution_graph": {}
        }
        
        # Phase 1: Planning
        planner = self.agents.get("Planner")
        if not planner:
            raise ValueError("Hierarchical workflow requires Planner agent")
            
        plan_task = Task(
            id="plan",
            description=f"Create execution plan for: {user_input}",
            assigned_agent="Planner"
        )
        
        plan_result = await planner.execute(plan_task, state)
        state["results"]["plan"] = plan_result
        
        if not plan_result.success:
            return CrewResult(
                success=False,
                output=f"Planning failed: {plan_result.output}",
                agent_results={"Planner": plan_result}
            )
            
        # Parse plan
        subtasks = self._parse_plan(plan_result.output)
        
        # Phase 2: Execution
        if self.config.max_parallel > 1:
            results = await self._execute_parallel_tasks(subtasks, state)
        else:
            results = await self._execute_sequential_tasks(subtasks, state)
            
        # Phase 3: Synthesis
        synthesizer = self.agents.get("Synthesizer")
        if synthesizer:
            synthesis_task = Task(
                id="synthesis",
                description="Synthesize results into final response",
                assigned_agent="Synthesizer"
            )
            
            synthesis_context = {
                **state,
                "messages": [
                    *state["messages"],
                    LLMMessage(role="user", content=f"Synthesize these results:\n" + 
                              "\n".join(r.output for r in results))
                ]
            }
            
            synthesis_result = await synthesizer.execute(
                synthesis_task, 
                synthesis_context
            )
            
            return CrewResult(
                success=synthesis_result.success,
                output=synthesis_result.output,
                agent_results={
                    "Planner": plan_result,
                    **{r.agent: r for r in results},
                    "Synthesizer": synthesis_result
                },
                thought_process=self._build_thought_process(
                    plan_result, results, synthesis_result
                )
            )
        else:
            # No synthesizer - combine directly
            combined = "\n\n".join(r.output for r in results)
            return CrewResult(
                success=all(r.success for r in results),
                output=combined,
                agent_results={"Planner": plan_result, **{r.agent: r for r in results}}
            )
            
    async def _execute_parallel_tasks(
        self,
        tasks: List[TaskSpec],
        state: WorkflowState
    ) -> List[TaskResult]:
        """Execute independent tasks in parallel."""
        
        semaphore = asyncio.Semaphore(self.config.max_parallel)
        
        async def execute_with_limit(task_spec: TaskSpec) -> TaskResult:
            async with semaphore:
                agent = self.agents.get(task_spec["agent"])
                if not agent:
                    return TaskResult(
                        task_id=task_spec["id"],
                        success=False,
                        output=f"Agent {task_spec['agent']} not found",
                        agent=task_spec["agent"]
                    )
                    
                task = Task(
                    id=task_spec["id"],
                    description=task_spec["description"],
                    assigned_agent=task_spec["agent"],
                    dependencies=task_spec.get("dependencies", [])
                )
                
                return await agent.execute(task, state)
                
        # Build dependency graph
        graph = {t["id"]: set(t.get("dependencies", [])) for t in tasks}
        sorter = TopologicalSorter(graph)
        
        results = []
        for batch in sorter.static_order():
            batch_tasks = [t for t in tasks if t["id"] in batch]
            batch_results = await asyncio.gather(*[
                execute_with_limit(t) for t in batch_tasks
            ])
            results.extend(batch_results)
            
            # Update state with results
            for result in batch_results:
                state["results"][result.task_id] = result
                
        return results
```

---

## Data Flow

### Message Processing Flow

```
User Input
    │
    ▼
┌─────────────────┐
│  Interface      │ (TUI/GUI/Messaging)
│  (Textual/PyQt6/│
│   WebSocket)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Gateway        │ Normalize & route
│  (FastAPI)      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Session        │ Load context & memory
│  Manager        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Crew Manager   │ Plan & delegate
│  (Orchestrator) │
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌───────┐  ┌───────┐
│Agent 1│  │Agent 2│  ... (Parallel execution)
└───┬───┘  └───┬───┘
    │          │
    ▼          ▼
┌─────────────────┐
│  LLM Router     │ Route to best provider
│  (Multi-model)  │
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌───────┐  ┌───────┐
│Claude │  │Gemini │  ... (With failover)
└───┬───┘  └───┬───┘
    │          │
    └────┬─────┘
         │
         ▼
┌─────────────────┐
│  Tool Execution │ (Sandboxed/Docker/Full)
│  (if needed)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Synthesis      │ Combine results
│  (Synthesizer)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Persistence    │ Save to SQL/Markdown/Vector
│  (Multi-backend)│
└────────┬────────┘
         │
         ▼
    Response to User
```

---

## Interface Specifications

### WebSocket Protocol

```typescript
// Client -> Server
interface ClientMessage {
  type: "message" | "command" | "ping";
  id: string;
  timestamp: string;
  payload: MessagePayload | CommandPayload;
}

interface MessagePayload {
  content: string | MultimodalContent;
  session_id?: string;
  context?: Record<string, any>;
  streaming?: boolean;
}

interface CommandPayload {
  command: "reset" | "clear_history" | "switch_crew" | "get_status";
  args?: Record<string, any>;
}

// Server -> Client
interface ServerMessage {
  type: "response" | "stream_chunk" | "thinking" | "tool_call" | "error" | "pong";
  id: string;
  timestamp: string;
  payload: ResponsePayload | StreamPayload | ErrorPayload;
}

interface StreamPayload {
  content: string;
  agent?: string;
  is_complete: boolean;
}

interface ToolCallPayload {
  tool: string;
  arguments: Record<string, any>;
  status: "started" | "completed" | "failed";
  result?: any;
  latency_ms: number;
}
```

### REST API

```yaml
openapi: 3.0.0
info:
  title: Oracle API
  version: 5.0.0

paths:
  /sessions:
    post:
      summary: Create new session
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                user_id:
                  type: string
                crew_type:
                  type: string
      responses:
        201:
          description: Session created
          content:
            application/json:
              schema:
                type: object
                properties:
                  session_id:
                    type: string
                  ws_url:
                    type: string
                    
  /sessions/{session_id}/messages:
    post:
      summary: Send message to session
      parameters:
        - name: session_id
          in: path
          required: true
          schema:
            type: string
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                content:
                  type: string
                streaming:
                  type: boolean
                  default: false
      responses:
        200:
          description: Message processed
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/MessageResponse'
                
    get:
      summary: Get session history
      parameters:
        - name: session_id
          in: path
          required: true
          schema:
            type: string
        - name: limit
          in: query
          schema:
            type: integer
            default: 50
      responses:
        200:
          description: Session history
          content:
            application/json:
              schema:
                type: object
                properties:
                  messages:
                    type: array
                    items:
                      $ref: '#/components/schemas/Message'
                      
  /skills:
    get:
      summary: List installed skills
      responses:
        200:
          description: List of skills
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/Skill'
                  
    post:
      summary: Install skill
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                skill_id:
                  type: string
                source:
                  type: string
                  enum: [oracle_hub, clawhub, url]
      responses:
        201:
          description: Skill installed

components:
  schemas:
    Message:
      type: object
      properties:
        role:
          type: string
          enum: [user, assistant, tool]
        content:
          type: string
        timestamp:
          type: string
          format: date-time
          
    MessageResponse:
      type: object
      properties:
        content:
          type: string
        agent:
          type: string
        tool_calls:
          type: array
        latency_ms:
          type: integer
        token_usage:
          type: object
          properties:
            input:
              type: integer
            output:
              type: integer
            cost_usd:
              type: number
              
    Skill:
      type: object
      properties:
        name:
          type: string
        version:
          type: string
        description:
          type: string
        tools:
          type: array
          items:
            type: string
```

---

## Security Architecture

### Authentication & Authorization

```python
# src/oracle/security/auth.py

class AuthenticationManager:
    """Handle authentication for all interfaces."""
    
    def __init__(self, config: AuthConfig):
        self.config = config
        self.token_store = TokenStore()
        
    async def authenticate_tui(self) -> UserSession:
        """TUI uses local authentication (file-based)."""
        
        # Check if already authenticated
        token_path = Path.home() / ".oracle" / ".auth_token"
        
        if token_path.exists():
            token = token_path.read_text().strip()
            return await self.validate_token(token)
            
        # Prompt for credentials (first run)
        # In TUI, this is interactive
        raise AuthenticationRequired()
        
    async def authenticate_api_key(self, api_key: str) -> UserSession:
        """API key authentication for external clients."""
        
        # Hash and validate
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        user = await self.token_store.get_user_by_api_key(key_hash)
        if not user:
            raise InvalidCredentials()
            
        return UserSession(
            user_id=user.id,
            permissions=user.permissions,
            security_mode=user.security_mode
        )
        
    async def authenticate_messaging(
        self, 
        channel: str,
        sender_id: str,
        token: Optional[str] = None
    ) -> UserSession:
        """Messaging channel authentication."""
        
        # Check if sender is authorized
        authorized = await self.token_store.is_authorized_sender(
            channel=channel,
            sender_id=sender_id
        )
        
        if not authorized:
            raise UnauthorizedSender(channel, sender_id)
            
        return UserSession(
            user_id=sender_id,
            permissions=["chat", "read_memory"],
            security_mode=SecurityMode.SANDBOXED
        )
```

### Sandboxing Architecture

```python
# src/oracle/security/sandbox.py

class SandboxedExecutor:
    """Execute tools in restricted environment."""
    
    def __init__(self, config: SandboxConfig):
        self.config = config
        self.allowed_paths = [p.resolve() for p in config.allowed_paths]
        self.blocked_commands = config.blocked_commands
        self.network_allowlist = config.network_allowlist
        
    async def execute_shell(self, command: str) -> ExecutionResult:
        """Execute shell command safely."""
        
        # Parse command
        try:
            parsed = shlex.split(command)
        except ValueError as e:
            return ExecutionResult(error=f"Invalid command: {e}")
            
        # Check for blocked commands
        cmd = parsed[0]
        if cmd in self.blocked_commands:
            return ExecutionResult(
                error=f"Command '{cmd}' is not allowed in sandboxed mode"
            )
            
        # Check for dangerous patterns
        if self._contains_dangerous_patterns(command):
            return ExecutionResult(
                error="Command contains potentially dangerous patterns"
            )
            
        # Execute with restricted environment
        env = os.environ.copy()
        env["PATH"] = "/usr/local/bin:/usr/bin:/bin"
        env["HOME"] = str(self.config.workspace_path)
        
        try:
            result = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
                cwd=self.config.workspace_path,
                limit=1024 * 1024  # 1MB output limit
            )
            
            stdout, stderr = await result.communicate()
            
            return ExecutionResult(
                success=result.returncode == 0,
                stdout=stdout.decode(),
                stderr=stderr.decode(),
                exit_code=result.returncode
            )
            
        except Exception as e:
            return ExecutionResult(error=str(e))
            
    def _contains_dangerous_patterns(self, command: str) -> bool:
        """Check for dangerous shell patterns."""
        
        dangerous = [
            r";\s*rm",           # Command chaining with rm
            r"`.*rm`",            # Backtick execution
            r"\$\(.*rm",          # Command substitution
            r">\s*/dev/",         # Writing to device files
            r"curl.*\|.*sh",      # Pipe curl to shell
            r"wget.*-O-\|",       # Pipe wget to shell
            r"eval\s*\$",         # Eval with variable
            r"base64.*\|",        # Decode and execute
        ]
        
        for pattern in dangerous:
            if re.search(pattern, command, re.IGNORECASE):
                return True
                
        return False
        
    async def read_file(self, path: str) -> ExecutionResult:
        """Read file with path validation."""
        
        # Resolve and validate path
        full_path = (self.config.workspace_path / path).resolve()
        
        if not self._is_path_allowed(full_path):
            return ExecutionResult(
                error=f"Access denied: {path} is outside allowed paths"
            )
            
        if not full_path.exists():
            return ExecutionResult(error=f"File not found: {path}")
            
        try:
            content = full_path.read_text()
            return ExecutionResult(success=True, content=content)
        except Exception as e:
            return ExecutionResult(error=str(e))
            
    def _is_path_allowed(self, path: Path) -> bool:
        """Check if path is within allowed directories."""
        
        for allowed in self.allowed_paths:
            try:
                path.relative_to(allowed)
                return True
            except ValueError:
                continue
                
        return False
```

---

## Performance Considerations

### Caching Strategy

```python
# src/oracle/cache/manager.py

from functools import wraps
import hashlib

class CacheManager:
    """Multi-layer caching for performance."""
    
    def __init__(self):
        self.l1_cache: Dict[str, Any] = {}  # In-memory
        self.l2_cache = RedisCache()        # Shared (if available)
        self.l3_cache = DiskCache()         # Persistent
        
    async def get(self, key: str) -> Optional[Any]:
        """Get from cache (L1 -> L2 -> L3)."""
        
        # L1: In-memory
        if key in self.l1_cache:
            return self.l1_cache[key]
            
        # L2: Redis
        value = await self.l2_cache.get(key)
        if value is not None:
            self.l1_cache[key] = value
            return value
            
        # L3: Disk
        value = await self.l3_cache.get(key)
        if value is not None:
            await self.l2_cache.set(key, value)
            self.l1_cache[key] = value
            return value
            
        return None
        
    async def set(self, key: str, value: Any, ttl: int = 3600):
        """Set in all cache layers."""
        
        self.l1_cache[key] = value
        await self.l2_cache.set(key, value, ttl)
        await self.l3_cache.set(key, value, ttl)
        
def cached(ttl: int = 3600):
    """Decorator for caching function results."""
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            key_data = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            key = hashlib.sha256(key_data.encode()).hexdigest()
            
            cache = CacheManager()
            
            # Try cache
            cached_value = await cache.get(key)
            if cached_value is not None:
                return cached_value
                
            # Execute and cache
            result = await func(*args, **kwargs)
            await cache.set(key, result, ttl)
            
            return result
        return wrapper
    return decorator
```

---

*End of Architecture Specification*
