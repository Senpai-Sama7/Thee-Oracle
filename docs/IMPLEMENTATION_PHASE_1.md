# Phase 1 Implementation Plan
## Oracle 5.0 - Foundation Layer

---

## Overview

Phase 1 establishes the core architectural changes needed for Oracle 5.0:
1. **Model Router** - Support multiple LLM providers
2. **Gateway Service** - Messaging platform integration
3. **Crew Manager** - Multi-agent orchestration
4. **Markdown Persistence** - File-based storage option

**Duration:** 4 weeks  
**Dependencies:** None (foundational)  
**Output:** Working multi-agent system with messaging interface

---

## Week 1: Model-Agnostic Router

### Day 1-2: Design & Interface

```python
# src/oracle/llm/__init__.py
"""
LLM Router - Unified interface for multiple providers.
"""

from .router import LLMRouter
from .providers import (
    GeminiProvider,
    AnthropicProvider, 
    OpenAIProvider,
    OllamaProvider
)
from .types import LLMMessage, LLMConfig, StreamingResponse

__all__ = [
    "LLMRouter",
    "GeminiProvider",
    "AnthropicProvider",
    "OpenAIProvider", 
    "OllamaProvider",
    "LLMMessage",
    "LLMConfig",
    "StreamingResponse"
]
```

### Day 3-4: Provider Implementations

**Tasks:**
- [ ] Implement `BaseLLMProvider` abstract class
- [ ] Implement `GeminiProvider` (port from existing)
- [ ] Implement `AnthropicProvider` with tool support
- [ ] Implement `OpenAIProvider` with function calling
- [ ] Implement `OllamaProvider` for local models

```python
# src/oracle/llm/providers/anthropic.py

import anthropic
from typing import AsyncIterator
from ..types import LLMMessage, LLMConfig
from .base import BaseLLMProvider

class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude implementation with native tool support."""
    
    def __init__(self, config: LLMConfig):
        self.client = anthropic.AsyncAnthropic(api_key=config.api_key)
        self.model = config.model
        self.temperature = config.temperature
        self.max_tokens = config.max_tokens
        
    def _convert_messages(self, messages: list[LLMMessage]) -> list[dict]:
        """Convert internal format to Anthropic format."""
        anthropic_messages = []
        system_content = None
        
        for msg in messages:
            if msg.role == "system":
                system_content = msg.content
                continue
                
            anthropic_msg = {
                "role": "assistant" if msg.role == "assistant" else "user",
                "content": []
            }
            
            # Handle text content
            if isinstance(msg.content, str):
                anthropic_msg["content"].append({
                    "type": "text",
                    "text": msg.content
                })
            elif isinstance(msg.content, list):
                # Handle multimodal
                for part in msg.content:
                    if part["type"] == "text":
                        anthropic_msg["content"].append({
                            "type": "text", 
                            "text": part["text"]
                        })
                    elif part["type"] == "image":
                        anthropic_msg["content"].append({
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": part["mime_type"],
                                "data": part["base64_data"]
                            }
                        })
                        
            # Handle tool calls
            if msg.tool_calls:
                for call in msg.tool_calls:
                    anthropic_msg["content"].append({
                        "type": "tool_use",
                        "id": call["id"],
                        "name": call["name"],
                        "input": call["arguments"]
                    })
                    
            # Handle tool results
            if msg.tool_results:
                for result in msg.tool_results:
                    anthropic_msg["content"].append({
                        "type": "tool_result",
                        "tool_use_id": result["tool_call_id"],
                        "content": result["content"]
                    })
                    
            anthropic_messages.append(anthropic_msg)
            
        return anthropic_messages, system_content
        
    def _convert_tools(self, tools: list[dict]) -> list[dict]:
        """Convert internal tool format to Anthropic format."""
        anthropic_tools = []
        for tool in tools:
            anthropic_tools.append({
                "name": tool["name"],
                "description": tool["description"],
                "input_schema": tool["parameters"]
            })
        return anthropic_tools
        
    async def generate(
        self,
        messages: list[LLMMessage],
        tools: list[dict] | None = None,
        stream: bool = False
    ) -> LLMMessage:
        """Generate completion with optional tool use."""
        
        anthropic_messages, system = self._convert_messages(messages)
        anthropic_tools = self._convert_tools(tools) if tools else None
        
        kwargs = {
            "model": self.model,
            "messages": anthropic_messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature
        }
        
        if system:
            kwargs["system"] = system
        if anthropic_tools:
            kwargs["tools"] = anthropic_tools
            
        response = await self.client.messages.create(**kwargs)
        
        # Convert response back to internal format
        content_parts = []
        tool_calls = []
        
        for block in response.content:
            if block.type == "text":
                content_parts.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                tool_calls.append({
                    "id": block.id,
                    "name": block.name,
                    "arguments": block.input
                })
                
        return LLMMessage(
            role="assistant",
            content=content_parts if len(content_parts) > 1 else content_parts[0]["text"],
            tool_calls=tool_calls if tool_calls else None
        )
        
    async def generate_stream(
        self,
        messages: list[LLMMessage],
        tools: list[dict] | None = None
    ) -> AsyncIterator[str]:
        """Stream response tokens."""
        
        anthropic_messages, system = self._convert_messages(messages)
        anthropic_tools = self._convert_tools(tools) if tools else None
        
        kwargs = {
            "model": self.model,
            "messages": anthropic_messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "stream": True
        }
        
        if system:
            kwargs["system"] = system
        if anthropic_tools:
            kwargs["tools"] = anthropic_tools
            
        async with self.client.messages.stream(**kwargs) as stream:
            async for text in stream.text_stream:
                yield text
                
    def count_tokens(self, messages: list[LLMMessage]) -> int:
        """Count tokens using Anthropic's tokenizer."""
        # Use tiktoken or Anthropic's tokenizer
        anthropic_messages, _ = self._convert_messages(messages)
        # Approximate: 4 chars per token
        total = sum(len(str(m)) for m in anthropic_messages) // 4
        return total
```

### Day 5: Router & Failover

```python
# src/oracle/llm/router.py

import asyncio
import logging
from typing import Type, AsyncIterator
from .types import LLMMessage, LLMConfig, LLMError
from .base import BaseLLMProvider

logger = logging.getLogger(__name__)

class LLMRouter:
    """Route LLM requests to appropriate provider with failover."""
    
    def __init__(self):
        self.providers: dict[str, BaseLLMProvider] = {}
        self.provider_configs: dict[str, LLMConfig] = {}
        self.primary: str | None = None
        self.fallback_chain: list[str] = []
        self.cost_tracker: dict[str, float] = {}
        
    def register_provider(
        self,
        name: str,
        provider_class: Type[BaseLLMProvider],
        config: LLMConfig,
        is_primary: bool = False
    ):
        """Register a provider with the router."""
        
        self.providers[name] = provider_class(config)
        self.provider_configs[name] = config
        
        if is_primary:
            self.primary = name
            
        logger.info(f"Registered provider: {name} ({config.provider})")
        
    def set_fallback_chain(self, names: list[str]):
        """Set order of fallback providers."""
        self.fallback_chain = names
        
    async def generate(
        self,
        messages: list[LLMMessage],
        tools: list[dict] | None = None,
        preferred_provider: str | None = None,
        track_cost: bool = True
    ) -> LLMMessage:
        """Generate with automatic failover."""
        
        providers_to_try = []
        
        if preferred_provider and preferred_provider in self.providers:
            providers_to_try.append(preferred_provider)
            
        if self.primary and self.primary not in providers_to_try:
            providers_to_try.append(self.primary)
            
        for name in self.fallback_chain:
            if name not in providers_to_try:
                providers_to_try.append(name)
                
        last_error = None
        
        for provider_name in providers_to_try:
            provider = self.providers[provider_name]
            
            try:
                logger.debug(f"Trying provider: {provider_name}")
                
                start_time = asyncio.get_event_loop().time()
                response = await provider.generate(messages, tools)
                latency = asyncio.get_event_loop().time() - start_time
                
                # Track cost if enabled
                if track_cost:
                    cost = self._estimate_cost(provider_name, messages, response)
                    self.cost_tracker[provider_name] = self.cost_tracker.get(provider_name, 0) + cost
                    
                logger.info(
                    f"Successfully generated with {provider_name} "
                    f"({latency:.2f}s)"
                )
                
                return response
                
            except Exception as e:
                logger.warning(f"Provider {provider_name} failed: {e}")
                last_error = e
                continue
                
        raise LLMError(
            f"All providers failed. Last error: {last_error}"
        )
        
    async def generate_stream(
        self,
        messages: list[LLMMessage],
        tools: list[dict] | None = None
    ) -> AsyncIterator[str]:
        """Stream with failover (only tries one provider)."""
        
        provider_name = self.primary or self.fallback_chain[0]
        provider = self.providers[provider_name]
        
        async for token in provider.generate_stream(messages, tools):
            yield token
            
    def _estimate_cost(
        self,
        provider_name: str,
        messages: list[LLMMessage],
        response: LLMMessage
    ) -> float:
        """Estimate cost in USD."""
        
        config = self.provider_configs[provider_name]
        
        # Get pricing (would come from config or external source)
        pricing = self._get_pricing(config.provider, config.model)
        
        # Count tokens
        input_tokens = sum(self._estimate_message_tokens(m) for m in messages)
        output_tokens = self._estimate_message_tokens(response)
        
        cost = (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1000000
        return cost
        
    def _get_pricing(self, provider: str, model: str) -> dict:
        """Get pricing per 1M tokens."""
        
        pricing_map = {
            "anthropic": {
                "claude-3-opus": {"input": 15.0, "output": 75.0},
                "claude-3-sonnet": {"input": 3.0, "output": 15.0},
                "claude-3-haiku": {"input": 0.25, "output": 1.25}
            },
            "openai": {
                "gpt-4o": {"input": 5.0, "output": 15.0},
                "gpt-4-turbo": {"input": 10.0, "output": 30.0}
            },
            "gemini": {
                "gemini-2.0-flash": {"input": 0.35, "output": 1.05},
                "gemini-2.0-flash-lite": {"input": 0.075, "output": 0.30}
            },
            "ollama": {
                "default": {"input": 0.0, "output": 0.0}
            }
        }
        
        provider_pricing = pricing_map.get(provider, {})
        return provider_pricing.get(model, provider_pricing.get("default", {"input": 0, "output": 0}))
        
    def _estimate_message_tokens(self, message: LLMMessage) -> int:
        """Rough token estimation."""
        if isinstance(message.content, str):
            return len(message.content) // 4
        return 100  # Default for complex content
        
    def get_cost_summary(self) -> dict:
        """Get total cost breakdown."""
        total = sum(self.cost_tracker.values())
        return {
            "total_usd": round(total, 4),
            "by_provider": {
                k: round(v, 4) for k, v in self.cost_tracker.items()
            }
        }
```

### Deliverables Week 1

- [ ] All provider implementations with tool support
- [ ] Router with failover and cost tracking
- [ ] Configuration loader from `oraclesettings.json`
- [ ] Unit tests for all providers (mocked API calls)
- [ ] Integration test with real APIs (optional)

---

## Week 2: Gateway Service

### Day 1-2: Gateway Architecture

```python
# src/oracle/gateway/server.py

import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from contextlib import asynccontextmanager

class GatewayServer:
    """Central message hub for all channels."""
    
    def __init__(self, config: GatewayConfig):
        self.config = config
        self.channels: dict[str, MessageChannel] = {}
        self.sessions: dict[str, Session] = {}
        self.agent_router: AgentRouter | None = None
        self.app = self._create_app()
        
    def _create_app(self) -> FastAPI:
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            # Startup
            await self.startup()
            yield
            # Shutdown
            await self.shutdown()
            
        app = FastAPI(title="Oracle Gateway", lifespan=lifespan)
        
        @app.get("/health")
        async def health():
            return {
                "status": "healthy",
                "channels": list(self.channels.keys()),
                "active_sessions": len(self.sessions)
            }
            
        @app.websocket("/ws/{session_id}")
        async def websocket(websocket: WebSocket, session_id: str):
            await self.handle_websocket(websocket, session_id)
            
        return app
        
    async def startup(self):
        """Initialize all channels."""
        
        for name, channel_config in self.config.channels.items():
            if not channel_config.enabled:
                continue
                
            channel = self._create_channel(name, channel_config)
            await channel.connect()
            
            # Set up message handler
            asyncio.create_task(self._channel_listener(channel))
            
            self.channels[name] = channel
            logger.info(f"Connected channel: {name}")
            
    def _create_channel(self, name: str, config: ChannelConfig) -> MessageChannel:
        """Factory for channel creation."""
        
        if name == "whatsapp":
            from .channels.whatsapp import WhatsAppChannel
            return WhatsAppChannel(config)
        elif name == "telegram":
            from .channels.telegram import TelegramChannel
            return TelegramChannel(config)
        elif name == "slack":
            from .channels.slack import SlackChannel
            return SlackChannel(config)
        elif name == "discord":
            from .channels.discord import DiscordChannel
            return DiscordChannel(config)
        else:
            raise ValueError(f"Unknown channel: {name}")
            
    async def _channel_listener(self, channel: MessageChannel):
        """Listen for messages from a channel."""
        
        async def handler(message: InboundMessage):
            await self._route_message(message)
            
        await channel.on_message(handler)
        
    async def _route_message(self, message: InboundMessage):
        """Route message to appropriate session."""
        
        # Get or create session
        session = self.sessions.get(message.session_id)
        if not session:
            session = await self._create_session(message)
            
        # Queue message for processing
        await session.message_queue.put(message)
        
    async def _create_session(self, message: InboundMessage) -> Session:
        """Create new session with crew."""
        
        session = Session(
            id=message.session_id,
            user_id=message.sender_id,
            channel=self.channels[message.channel],
            message_queue=asyncio.Queue(),
            created_at=datetime.now()
        )
        
        self.sessions[message.session_id] = session
        
        # Start session processor
        asyncio.create_task(self._process_session(session))
        
        return session
        
    async def _process_session(self, session: Session):
        """Process messages for a session."""
        
        while True:
            try:
                message = await asyncio.wait_for(
                    session.message_queue.get(),
                    timeout=300  # 5 minute timeout
                )
                
                # Process with agent/crew
                if self.agent_router:
                    response = await self.agent_router.handle(message)
                    
                    # Send response
                    await session.channel.send_message(
                        session_id=session.id,
                        content=response.content,
                        attachments=response.attachments
                    )
                    
            except asyncio.TimeoutError:
                # Session timeout - clean up
                logger.info(f"Session {session.id} timed out")
                del self.sessions[session.id]
                break
                
    async def shutdown(self):
        """Graceful shutdown."""
        
        for name, channel in self.channels.items():
            await channel.disconnect()
            logger.info(f"Disconnected channel: {name}")
            
        self.channels.clear()
```

### Day 3: WhatsApp Channel

```python
# src/oracle/gateway/channels/whatsapp.py

import subprocess
import json
import asyncio
from pathlib import Path

class WhatsAppChannel(MessageChannel):
    """WhatsApp Web integration via Baileys (Node.js)."""
    
    def __init__(self, config: WhatsAppConfig):
        self.config = config
        self.process: subprocess.Process | None = None
        self.message_handler: Callable | None = None
        self._connected = False
        
    async def connect(self):
        """Start Baileys bridge process."""
        
        # Create Baileys wrapper script
        wrapper_path = Path.home() / ".oracle" / "whatsapp-bridge.js"
        wrapper_path.write_text(self._generate_bridge_script())
        
        # Start Node.js process
        self.process = await asyncio.create_subprocess_exec(
            "node", str(wrapper_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.PIPE
        )
        
        # Start output reader
        asyncio.create_task(self._read_output())
        
        # Wait for QR code or connection
        qr_code = await self._wait_for_qr()
        
        if qr_code:
            logger.info("WhatsApp QR code generated - scan with phone")
            # Could send QR to user via alternate channel
            
        # Wait for connection
        await self._wait_for_connection()
        
    def _generate_bridge_script(self) -> str:
        """Generate Node.js Baileys wrapper."""
        
        return '''
const { default: makeWASocket, DisconnectReason, useSingleFileAuthState } = require('@whiskeysockets/baileys');
const fs = require('fs');

const { state, saveState } = useSingleFileAuthState('./whatsapp-auth.json');

async function start() {
    const sock = makeWASocket({
        auth: state,
        printQRInTerminal: true
    });
    
    sock.ev.on('connection.update', (update) => {
        const { connection, lastDisconnect, qr } = update;
        
        if (qr) {
            console.log(JSON.stringify({ type: 'qr', data: qr }));
        }
        
        if (connection === 'close') {
            const shouldReconnect = lastDisconnect?.error?.output?.statusCode !== DisconnectReason.loggedOut;
            console.log(JSON.stringify({ type: 'disconnected', shouldReconnect }));
            if (shouldReconnect) start();
        } else if (connection === 'open') {
            console.log(JSON.stringify({ type: 'connected' }));
        }
    });
    
    sock.ev.on('messages.upsert', async (m) => {
        const msg = m.messages[0];
        if (!msg.key.fromMe && m.type === 'notify') {
            console.log(JSON.stringify({
                type: 'message',
                from: msg.key.remoteJid,
                text: msg.message?.conversation || msg.message?.extendedTextMessage?.text,
                timestamp: msg.messageTimestamp
            }));
        }
    });
    
    sock.ev.on('creds.update', saveState);
    
    // Read commands from stdin
    process.stdin.on('data', async (data) => {
        const cmd = JSON.parse(data.toString());
        if (cmd.type === 'send') {
            await sock.sendMessage(cmd.to, { text: cmd.text });
        }
    });
}

start();
'''
        
    async def _read_output(self):
        """Read and process Baileys output."""
        
        while self.process and self.process.stdout:
            line = await self.process.stdout.readline()
            if not line:
                break
                
            try:
                event = json.loads(line.decode().strip())
                await self._handle_event(event)
            except json.JSONDecodeError:
                logger.debug(f"Baileys output: {line.decode().strip()}")
                
    async def _handle_event(self, event: dict):
        """Handle Baileys events."""
        
        if event["type"] == "message" and self.message_handler:
            message = InboundMessage(
                session_id=f"whatsapp-{event['from']}",
                sender_id=event["from"],
                channel="whatsapp",
                content=event["text"],
                timestamp=datetime.fromtimestamp(event["timestamp"])
            )
            await self.message_handler(message)
            
        elif event["type"] == "connected":
            self._connected = True
            logger.info("WhatsApp connected")
            
    async def send_message(self, session_id: str, content: str, attachments: list | None = None):
        """Send WhatsApp message."""
        
        # Extract JID from session_id
        jid = session_id.replace("whatsapp-", "")
        
        cmd = {
            "type": "send",
            "to": jid,
            "text": content
        }
        
        self.process.stdin.write(json.dumps(cmd).encode() + b"\n")
        await self.process.stdin.drain()
        
    async def on_message(self, handler: Callable[[InboundMessage], Awaitable[None]]):
        self.message_handler = handler
```

### Day 4: Telegram Channel

```python
# src/oracle/gateway/channels/telegram.py

from aiogram import Bot, Dispatcher
from aiogram.types import Message

class TelegramChannel(MessageChannel):
    """Telegram Bot API integration."""
    
    def __init__(self, config: TelegramConfig):
        self.config = config
        self.bot: Bot | None = None
        self.dp: Dispatcher | None = None
        self.message_handler: Callable | None = None
        
    async def connect(self):
        """Start Telegram bot."""
        
        self.bot = Bot(token=self.config.bot_token)
        self.dp = Dispatcher()
        
        @self.dp.message()
        async def handle_message(message: Message):
            # Filter by allowed usernames if configured
            if self.config.allowed_usernames:
                username = f"@{message.from_user.username}"
                if username not in self.config.allowed_usernames:
                    await message.reply("You're not authorized to use this bot.")
                    return
                    
            # Handle commands
            if message.text and message.text.startswith('/'):
                await self._handle_command(message)
                return
                
            # Create normalized message
            inbound = InboundMessage(
                session_id=f"telegram-{message.chat.id}",
                sender_id=str(message.from_user.id),
                channel="telegram",
                content=message.text or "",
                timestamp=message.date,
                attachments=self._extract_attachments(message)
            )
            
            if self.message_handler:
                await self.message_handler(inbound)
                
        # Start polling
        asyncio.create_task(self.dp.start_polling(self.bot))
        
    async def send_message(
        self,
        session_id: str,
        content: str,
        attachments: list | None = None
    ):
        """Send Telegram message."""
        
        chat_id = int(session_id.replace("telegram-", ""))
        
        # Send text
        await self.bot.send_message(chat_id, content, parse_mode="Markdown")
        
        # Send attachments
        if attachments:
            for attachment in attachments:
                if attachment.type == "image":
                    await self.bot.send_photo(chat_id, attachment.data)
                elif attachment.type == "document":
                    await self.bot.send_document(chat_id, attachment.data)
                    
    def _extract_attachments(self, message: Message) -> list[Attachment]:
        """Extract attachments from Telegram message."""
        
        attachments = []
        
        if message.photo:
            # Get largest photo
            photo = message.photo[-1]
            attachments.append(Attachment(
                type="image",
                mime_type="image/jpeg",
                file_id=photo.file_id
            ))
            
        if message.document:
            attachments.append(Attachment(
                type="document",
                mime_type=message.document.mime_type,
                file_id=message.document.file_id,
                filename=message.document.file_name
            ))
            
        if message.voice:
            attachments.append(Attachment(
                type="audio",
                mime_type="audio/ogg",
                file_id=message.voice.file_id
            ))
            
        return attachments
```

### Day 5: Integration & Testing

**Deliverables Week 2:**
- [ ] Gateway server with WebSocket support
- [ ] WhatsApp channel (Baileys integration)
- [ ] Telegram channel (aiogram integration)
- [ ] Slack channel foundation
- [ ] Session management
- [ ] End-to-end message flow test

---

## Week 3: Crew Manager

### Day 1-2: Agent & Crew Abstractions

```python
# src/oracle/crew/agent.py

from dataclasses import dataclass, field
from typing import Callable
import json

@dataclass
class AgentRole:
    """Definition of an agent's capabilities."""
    name: str
    description: str
    system_prompt: str
    tools: list[str] = field(default_factory=list)
    model_config: dict = field(default_factory=dict)
    can_delegate_to: list[str] = field(default_factory=list)
    
@dataclass
class Task:
    """Unit of work assigned to an agent."""
    id: str
    description: str
    assigned_agent: str
    status: str = "pending"  # pending, in_progress, completed, failed
    result: Any = None
    dependencies: list[str] = field(default_factory=list)
    
@dataclass
class TaskResult:
    """Result of task execution."""
    task_id: str
    success: bool
    output: str
    agent: str
    tool_calls: list[dict] = field(default_factory=list)
    iterations: int = 0
    latency_ms: int = 0

class Agent:
    """Individual agent with specific role."""
    
    def __init__(
        self,
        role: AgentRole,
        llm_router: LLMRouter,
        tool_registry: ToolRegistry,
        max_iterations: int = 20
    ):
        self.role = role
        self.llm = llm_router
        self.tools = {
            name: tool_registry.get(name)
            for name in role.tools
            if tool_registry.has(name)
        }
        self.max_iterations = max_iterations
        
    async def execute(self, task: Task, context: dict) -> TaskResult:
        """Execute task using ReAct loop."""
        
        start_time = asyncio.get_event_loop().time()
        
        # Build messages
        messages = [
            LLMMessage(role="system", content=self.role.system_prompt),
            LLMMessage(role="user", content=task.description)
        ]
        
        # Add context if provided
        if context.get("previous_results"):
            context_msg = "Previous results:\n"
            for result in context["previous_results"]:
                context_msg += f"- {result}\n"
            messages.append(LLMMessage(role="user", content=context_msg))
            
        tool_calls_made = []
        
        # ReAct loop
        for iteration in range(self.max_iterations):
            # Convert tools to LLM format
            tools_spec = [
                {
                    "name": name,
                    "description": tool.description,
                    "parameters": tool.parameters
                }
                for name, tool in self.tools.items()
            ]
            
            # Get response from LLM
            response = await self.llm.generate(messages, tools=tools_spec)
            
            # Check if done
            if not response.tool_calls:
                # Task complete
                latency = int((asyncio.get_event_loop().time() - start_time) * 1000)
                return TaskResult(
                    task_id=task.id,
                    success=True,
                    output=response.content,
                    agent=self.role.name,
                    tool_calls=tool_calls_made,
                    iterations=iteration + 1,
                    latency_ms=latency
                )
                
            # Execute tools
            for call in response.tool_calls:
                tool = self.tools.get(call["name"])
                if not tool:
                    result = {"error": f"Unknown tool: {call['name']}"}
                else:
                    try:
                        result = await tool.execute(**call["arguments"])
                    except Exception as e:
                        result = {"error": str(e)}
                        
                tool_calls_made.append({
                    "tool": call["name"],
                    "arguments": call["arguments"],
                    "result": result
                })
                
                # Add result to conversation
                messages.append(LLMMessage(
                    role="tool",
                    content=json.dumps(result)
                ))
                
        # Max iterations reached
        return TaskResult(
            task_id=task.id,
            success=False,
            output="Max iterations reached without completion",
            agent=self.role.name,
            tool_calls=tool_calls_made,
            iterations=self.max_iterations,
            latency_ms=int((asyncio.get_event_loop().time() - start_time) * 1000)
        )
```

### Day 3-4: Crew Orchestrator

```python
# src/oracle/crew/manager.py

from typing import Literal
import asyncio

class CrewManager:
    """Orchestrates multi-agent collaboration."""
    
    def __init__(
        self,
        config: CrewConfig,
        llm_router: LLMRouter,
        tool_registry: ToolRegistry
    ):
        self.config = config
        self.llm = llm_router
        self.tools = tool_registry
        self.agents: dict[str, Agent] = {}
        
    def register_agent(self, role: AgentRole):
        """Register an agent with the crew."""
        
        self.agents[role.name] = Agent(
            role=role,
            llm_router=self.llm,
            tool_registry=self.tools,
            max_iterations=self.config.max_iterations
        )
        
    async def execute(self, user_input: str, context: dict | None = None) -> CrewResult:
        """Execute user request with the crew."""
        
        if self.config.workflow_type == "hierarchical":
            return await self._execute_hierarchical(user_input, context)
        elif self.config.workflow_type == "parallel":
            return await self._execute_parallel(user_input, context)
        else:
            return await self._execute_sequential(user_input, context)
            
    async def _execute_hierarchical(
        self,
        user_input: str,
        context: dict | None
    ) -> CrewResult:
        """Hierarchical: Planner delegates to specialists."""
        
        # Phase 1: Planning
        planner = self.agents.get("Planner")
        if not planner:
            raise ValueError("Hierarchical workflow requires a Planner agent")
            
        plan_task = Task(
            id="plan-1",
            description=f"Create execution plan for: {user_input}",
            assigned_agent="Planner"
        )
        
        plan_result = await planner.execute(plan_task, context or {})
        
        if not plan_result.success:
            return CrewResult(
                success=False,
                output="Planning failed: " + plan_result.output,
                agent_results={"Planner": plan_result}
            )
            
        # Parse plan (expect JSON list of tasks)
        try:
            tasks = json.loads(plan_result.output)
        except json.JSONDecodeError:
            # Fallback: treat entire output as single task
            tasks = [{"agent": "Coder", "description": user_input}]
            
        # Phase 2: Execution
        agent_results = {"Planner": plan_result}
        task_results = []
        
        if self.config.max_parallel > 1:
            # Execute in parallel where possible
            task_results = await self._execute_parallel_tasks(tasks, context)
        else:
            # Execute sequentially
            for task_spec in tasks:
                agent_name = task_spec["agent"]
                agent = self.agents.get(agent_name)
                
                if not agent:
                    continue
                    
                task = Task(
                    id=f"task-{len(task_results)}",
                    description=task_spec["description"],
                    assigned_agent=agent_name
                )
                
                result = await agent.execute(
                    task,
                    {**context, "previous_results": task_results}
                )
                
                task_results.append(result)
                agent_results[agent_name] = result
                
        # Phase 3: Synthesis
        synthesizer = self.agents.get("Synthesizer")
        if synthesizer:
            synthesis_task = Task(
                id="synthesis-1",
                description=f"Synthesize results into final response. Original request: {user_input}",
                assigned_agent="Synthesizer"
            )
            
            synthesis_context = {
                "previous_results": [
                    f"{r.agent}: {r.output}" for r in task_results
                ]
            }
            
            synthesis_result = await synthesizer.execute(
                synthesis_task,
                synthesis_context
            )
            
            agent_results["Synthesizer"] = synthesis_result
            
            return CrewResult(
                success=synthesis_result.success,
                output=synthesis_result.output,
                agent_results=agent_results,
                thought_process=self._build_thought_process(agent_results)
            )
        else:
            # No synthesizer - combine results directly
            combined = "\n\n".join(r.output for r in task_results)
            return CrewResult(
                success=all(r.success for r in task_results),
                output=combined,
                agent_results=agent_results
            )
            
    async def _execute_parallel_tasks(
        self,
        tasks: list[dict],
        context: dict
    ) -> list[TaskResult]:
        """Execute independent tasks in parallel."""
        
        async def run_task(task_spec: dict) -> TaskResult:
            agent = self.agents.get(task_spec["agent"])
            if not agent:
                return TaskResult(
                    task_id="",
                    success=False,
                    output=f"Agent {task_spec['agent']} not found",
                    agent=task_spec["agent"]
                )
                
            task = Task(
                id=f"task-{task_spec['agent']}-{asyncio.current_task().get_name()}",
                description=task_spec["description"],
                assigned_agent=task_spec["agent"]
            )
            
            return await agent.execute(task, context)
            
        # Limit concurrency
        semaphore = asyncio.Semaphore(self.config.max_parallel)
        
        async def bounded_run(task_spec):
            async with semaphore:
                return await run_task(task_spec)
                
        # Run all tasks
        results = await asyncio.gather(*[
            bounded_run(t) for t in tasks
        ])
        
        return list(results)
        
    def _build_thought_process(self, results: dict) -> list[dict]:
        """Build human-readable thought process."""
        
        thought_process = []
        
        for agent_name, result in results.items():
            thought_process.append({
                "agent": agent_name,
                "action": "executed_task",
                "iterations": result.iterations,
                "tool_calls": len(result.tool_calls),
                "latency_ms": result.latency_ms
            })
            
        return thought_process
```

### Day 5: Crew Configuration Loader

```python
# src/oracle/crew/loader.py

import yaml
import frontmatter
from pathlib import Path

class CrewLoader:
    """Load crew configuration from Markdown files."""
    
    @staticmethod
    def from_markdown(path: Path) -> CrewConfig:
        """Load crew from AGENTS.md file."""
        
        post = frontmatter.load(path)
        content = post.content
        
        # Parse agents from markdown
        agents = []
        current_agent = None
        
        for line in content.split('\n'):
            if line.startswith('### '):
                # New agent
                if current_agent:
                    agents.append(current_agent)
                current_agent = {
                    'name': line[4:].strip(),
                    'description': '',
                    'system_prompt': '',
                    'tools': [],
                    'model': 'claude-3-5-sonnet'
                }
            elif line.startswith('**Model:**') and current_agent:
                current_agent['model'] = line[10:].strip()
            elif line.startswith('**Role:**') and current_agent:
                current_agent['description'] = line[9:].strip()
            elif line.startswith('**Tools:**') and current_agent:
                tools_str = line[10:].strip()
                current_agent['tools'] = [t.strip() for t in tools_str.split(',')]
            elif line.startswith('You are') and current_agent:
                # System prompt
                current_agent['system_prompt'] += line + '\n'
                
        if current_agent:
            agents.append(current_agent)
            
        # Parse workflow section
        workflow = {
            'type': 'hierarchical',
            'max_parallel': 3
        }
        
        if '**Type:**' in content:
            workflow['type'] = content.split('**Type:**')[1].split()[0].strip()
            
        return CrewConfig(
            name=post.get('name', 'default'),
            agents=[AgentRole(**a) for a in agents],
            workflow_type=workflow['type'],
            max_parallel=workflow['max_parallel']
        )
        
    @staticmethod
    def from_yaml(path: Path) -> CrewConfig:
        """Load crew from YAML file."""
        
        data = yaml.safe_load(path.read_text())
        
        return CrewConfig(
            name=data['name'],
            agents=[AgentRole(**a) for a in data['agents']],
            workflow_type=data.get('workflow', {}).get('type', 'hierarchical'),
            max_parallel=data.get('workflow', {}).get('max_parallel', 3)
        )
```

### Deliverables Week 3

- [ ] Agent abstraction with ReAct loop
- [ ] Crew manager with hierarchical/parallel/sequential workflows
- [ ] Crew configuration from Markdown/YAML
- [ ] Task dependency resolution
- [ ] Result synthesis
- [ ] Integration tests

---

## Week 4: Markdown Persistence

### Day 1-2: Backend Implementation

```python
# src/oracle/persistence/markdown_backend.py

import frontmatter
import yaml
from pathlib import Path
from datetime import datetime
from typing import AsyncIterator

class MarkdownPersistence:
    """File-based persistence with Git-friendly format."""
    
    def __init__(self, base_path: Path):
        self.base_path = Path(base_path).expanduser()
        self._ensure_structure()
        
    def _ensure_structure(self):
        """Create directory structure if needed."""
        
        dirs = ['sessions', 'memory', 'skills', 'agents', 'logs']
        for d in dirs:
            (self.base_path / d).mkdir(parents=True, exist_ok=True)
            
    async def save_session(self, session_id: str, messages: list[LLMMessage]):
        """Save conversation to Markdown."""
        
        session_file = self.base_path / 'sessions' / f'{session_id}.md'
        
        # Build content
        lines = ['# Session History\n']
        
        for msg in messages:
            timestamp = msg.timestamp.isoformat() if hasattr(msg, 'timestamp') else datetime.now().isoformat()
            
            # Role header
            lines.append(f'## {msg.role.title()} ({timestamp})\n')
            
            # Content
            if isinstance(msg.content, str):
                lines.append(f'{msg.content}\n')
            elif isinstance(msg.content, list):
                for part in msg.content:
                    if part.get('type') == 'text':
                        lines.append(f'{part["text"]}\n')
                    elif part.get('type') == 'image':
                        lines.append(f'![Image]({part.get("source", "image.png")})\n')
                        
            # Tool calls
            if msg.tool_calls:
                lines.append('\n**Tool Calls:**\n')
                for call in msg.tool_calls:
                    lines.append(f'- `{call["name"]}`: `{call["arguments"]}`\n')
                    
            # Tool results
            if msg.tool_results:
                lines.append('\n**Tool Results:**\n')
                for result in msg.tool_results:
                    lines.append(f'- {result}\n')
                    
            lines.append('\n---\n')
            
        # Create frontmatter
        post = frontmatter.Post(
            '\n'.join(lines),
            session_id=session_id,
            message_count=len(messages),
            updated_at=datetime.now().isoformat(),
            version='1.0'
        )
        
        # Atomic write
        temp_file = session_file.with_suffix('.tmp')
        temp_file.write_text(frontmatter.dumps(post))
        temp_file.replace(session_file)
        
    async def load_session(self, session_id: str) -> list[LLMMessage] | None:
        """Load conversation from Markdown."""
        
        session_file = self.base_path / 'sessions' / f'{session_id}.md'
        
        if not session_file.exists():
            return None
            
        post = frontmatter.load(session_file)
        
        # Parse messages from content
        messages = []
        sections = post.content.split('## ')
        
        for section in sections[1:]:  # Skip header
            lines = section.strip().split('\n')
            header = lines[0]
            
            # Parse role and timestamp
            role_timestamp = header.split('(')
            role = role_timestamp[0].strip().lower()
            timestamp = role_timestamp[1].rstrip(')') if len(role_timestamp) > 1 else None
            
            # Parse content
            content_lines = []
            for line in lines[1:]:
                if line.startswith('**Tool'):
                    break
                content_lines.append(line)
                
            content = '\n'.join(content_lines).strip()
            
            messages.append(LLMMessage(
                role=role,
                content=content,
                timestamp=datetime.fromisoformat(timestamp) if timestamp else None
            ))
            
        return messages
        
    async def append_memory(self, user_id: str, category: str, entry: str):
        """Append to long-term memory."""
        
        memory_file = self.base_path / 'memory' / f'{user_id}.md'
        
        # Load existing or create new
        if memory_file.exists():
            post = frontmatter.load(memory_file)
        else:
            post = frontmatter.Post(
                '',
                user_id=user_id,
                created_at=datetime.now().isoformat()
            )
            
        # Append entry
        timestamp = datetime.now().strftime('%Y-%m-%d')
        section = category.replace('_', ' ').title()
        
        if f'## {section}' not in post.content:
            post.content += f'\n## {section}\n'
            
        post.content += f'- [{timestamp}] {entry}\n'
        post.metadata['updated_at'] = datetime.now().isoformat()
        
        memory_file.write_text(frontmatter.dumps(post))
        
    async def get_memory(self, user_id: str, category: str | None = None) -> dict:
        """Get user memory."""
        
        memory_file = self.base_path / 'memory' / f'{user_id}.md'
        
        if not memory_file.exists():
            return {}
            
        post = frontmatter.load(memory_file)
        
        # Parse sections
        memory = {}
        current_section = None
        
        for line in post.content.split('\n'):
            if line.startswith('## '):
                current_section = line[3:].strip().lower().replace(' ', '_')
                memory[current_section] = []
            elif line.startswith('- ['):
                if current_section:
                    memory[current_section].append(line)
                    
        if category:
            return {category: memory.get(category, [])}
        return memory
```

### Day 3-4: Git Integration

```python
# src/oracle/persistence/git_sync.py

import subprocess
from pathlib import Path

class GitIntegration:
    """Automatic Git versioning for markdown files."""
    
    def __init__(self, repo_path: Path, auto_commit: bool = True):
        self.repo_path = Path(repo_path)
        self.auto_commit = auto_commit
        self._ensure_git()
        
    def _ensure_git(self):
        """Initialize git repo if needed."""
        
        git_dir = self.repo_path / '.git'
        if not git_dir.exists():
            subprocess.run(
                ['git', 'init'],
                cwd=self.repo_path,
                capture_output=True
            )
            
            # Create .gitignore
            gitignore = self.repo_path / '.gitignore'
            gitignore.write_text('''
credentials/
*.tmp
*.log
cache/
''')
            
            subprocess.run(
                ['git', 'add', '.gitignore'],
                cwd=self.repo_path,
                capture_output=True
            )
            subprocess.run(
                ['git', 'commit', '-m', 'Initial commit'],
                cwd=self.repo_path,
                capture_output=True
            )
            
    async def commit_changes(self, message: str | None = None):
        """Commit pending changes."""
        
        if not self.auto_commit:
            return
            
        # Check for changes
        result = subprocess.run(
            ['git', 'status', '--porcelain'],
            cwd=self.repo_path,
            capture_output=True,
            text=True
        )
        
        if not result.stdout.strip():
            return  # No changes
            
        # Add all changes
        subprocess.run(
            ['git', 'add', '.'],
            cwd=self.repo_path,
            capture_output=True
        )
        
        # Commit
        commit_msg = message or f'Auto-commit: {datetime.now().isoformat()}'
        subprocess.run(
            ['git', 'commit', '-m', commit_msg],
            cwd=self.repo_path,
            capture_output=True
        )
        
    def get_history(self, file_path: Path, limit: int = 10) -> list[dict]:
        """Get commit history for a file."""
        
        result = subprocess.run(
            ['git', 'log', f'-{limit}', '--pretty=format:%H|%ai|%s', '--', file_path],
            cwd=self.repo_path,
            capture_output=True,
            text=True
        )
        
        history = []
        for line in result.stdout.strip().split('\n'):
            if '|' in line:
                commit_hash, date, message = line.split('|', 2)
                history.append({
                    'commit': commit_hash,
                    'date': date,
                    'message': message
                })
                
        return history
```

### Day 5: Integration & Migration

```python
# src/oracle/persistence/unified.py

class UnifiedPersistence:
    """Unified interface supporting both SQL and Markdown backends."""
    
    def __init__(self, config: PersistenceConfig):
        self.config = config
        
        if config.backend == 'sql':
            from .sql_backend import SQLPersistence
            self.backend = SQLPersistence(config.sql.url)
        elif config.backend == 'markdown':
            self.backend = MarkdownPersistence(config.markdown.path)
            if config.markdown.git_integration:
                self.git = GitIntegration(config.markdown.path)
        else:
            raise ValueError(f"Unknown backend: {config.backend}")
            
    async def save_session(self, session_id: str, messages: list[LLMMessage]):
        await self.backend.save_session(session_id, messages)
        
        if hasattr(self, 'git'):
            await self.git.commit_changes(f'Update session {session_id}')
            
    async def load_session(self, session_id: str) -> list[LLMMessage] | None:
        return await self.backend.load_session(session_id)
        
    # Delegate all other methods to backend
    def __getattr__(self, name):
        return getattr(self.backend, name)
```

### Deliverables Week 4

- [ ] Markdown persistence backend
- [ ] Git integration with auto-commit
- [ ] Unified persistence interface
- [ ] Migration tool from SQL to Markdown
- [ ] Session history visualization
- [ ] Memory search/retrieval

---

## Integration: Putting It All Together

```python
# src/oracle/core.py (Main Entry Point)

class OraclePersonalAssistant:
    """Main orchestrator for Oracle 5.0."""
    
    def __init__(self, config_path: Path | None = None):
        self.config = self._load_config(config_path)
        
        # Initialize LLM router
        self.llm_router = LLMRouter()
        self._setup_llm_providers()
        
        # Initialize persistence
        self.persistence = UnifiedPersistence(self.config.persistence)
        
        # Initialize tool registry
        self.tools = ToolRegistry()
        self._register_builtin_tools()
        
        # Initialize crew manager
        self.crew_manager = CrewManager(
            config=self.config.crew,
            llm_router=self.llm_router,
            tool_registry=self.tools
        )
        self._setup_default_crew()
        
        # Initialize gateway (if messaging enabled)
        self.gateway: GatewayServer | None = None
        if self.config.messaging.gateway.enabled:
            self.gateway = GatewayServer(self.config.messaging)
            self.gateway.agent_router = self
            
    async def start(self):
        """Start all services."""
        
        if self.gateway:
            await self.gateway.startup()
            logger.info(f"Gateway listening on {self.config.messaging.gateway.host}:{self.config.messaging.gateway.port}")
            
    async def handle(self, message: InboundMessage) -> OutboundMessage:
        """Main entry point for processing messages."""
        
        # Load session history
        history = await self.persistence.load_session(message.session_id) or []
        
        # Add new message to history
        history.append(LLMMessage(
            role="user",
            content=message.content,
            timestamp=message.timestamp
        ))
        
        # Process with crew
        crew_result = await self.crew_manager.execute(
            user_input=message.content,
            context={"history": history}
        )
        
        # Save updated history
        history.append(LLMMessage(
            role="assistant",
            content=crew_result.output,
            timestamp=datetime.now()
        ))
        await self.persistence.save_session(message.session_id, history)
        
        return OutboundMessage(
            content=crew_result.output,
            attachments=[],  # Could extract from result
            metadata={
                "agents_involved": list(crew_result.agent_results.keys()),
                "success": crew_result.success
            }
        )
        
    async def run_cli(self):
        """Run interactive CLI mode."""
        
        import asyncio
        
        print("👋 Oracle Personal Assistant 5.0")
        print("Type 'exit' to quit\n")
        
        session_id = f"cli-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        while True:
            try:
                user_input = input("You: ").strip()
                
                if user_input.lower() in ['exit', 'quit']:
                    break
                    
                message = InboundMessage(
                    session_id=session_id,
                    sender_id="cli-user",
                    channel="cli",
                    content=user_input,
                    timestamp=datetime.now()
                )
                
                response = await self.handle(message)
                
                print(f"\n🤖 Oracle: {response.content}\n")
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.exception("Error processing message")
                print(f"Error: {e}\n")
                
        print("\nGoodbye! 👋")
```

---

## Testing Strategy

### Unit Tests
```python
# tests/test_crew.py

@pytest.mark.asyncio
async def test_hierarchical_workflow():
    """Test planner → worker → synthesizer flow."""
    
    # Setup mock LLM
    mock_llm = MockLLMRouter()
    mock_llm.set_response("Planner", '{"tasks": [{"agent": "Coder", "description": "Write hello world"}]}')
    mock_llm.set_response("Coder", 'print("Hello, World!")')
    mock_llm.set_response("Synthesizer", "Here's your code:")
    
    # Create crew
    crew = CrewManager(config, mock_llm, MockToolRegistry())
    crew.register_agent(AgentRole(name="Planner", ...))
    crew.register_agent(AgentRole(name="Coder", ...))
    crew.register_agent(AgentRole(name="Synthesizer", ...))
    
    # Execute
    result = await crew.execute("Write hello world")
    
    assert result.success
    assert "Planner" in result.agent_results
    assert "Coder" in result.agent_results
    assert "Synthesizer" in result.agent_results
```

### Integration Tests
```python
# tests/test_gateway.py

@pytest.mark.asyncio
async def test_whatsapp_message_flow():
    """Test full message flow through WhatsApp."""
    
    # Start gateway
    gateway = GatewayServer(test_config)
    await gateway.startup()
    
    # Simulate WhatsApp message
    test_message = InboundMessage(
        session_id="whatsapp-test",
        sender_id="1234567890",
        channel="whatsapp",
        content="What time is it?"
    )
    
    # Process
    response = await gateway._route_message(test_message)
    
    assert response is not None
    assert "time" in response.content.lower()
    
    await gateway.shutdown()
```

---

## Success Criteria for Phase 1

| Criterion | Target | Measurement |
|-----------|--------|-------------|
| Multi-provider LLM | 4+ providers working | Integration tests pass |
| Messaging channels | 2+ channels (WhatsApp, Telegram) | Manual E2E test |
| Multi-agent crew | 3+ agents collaborating | Unit test coverage >80% |
| Markdown persistence | Sessions, memory, config | Migration tool works |
| Performance | <2s response time | Benchmark test |

---

*Next: Phase 2 - Protocols & Ecosystem (MCP, A2A, Skills)*
