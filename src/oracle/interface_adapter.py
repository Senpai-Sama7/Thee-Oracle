import asyncio
from typing import Protocol, runtime_checkable, Any, Callable
from dataclasses import dataclass, field

from .model_router import StreamChunk


@dataclass
class Attachment:
    type: str  # "image" | "audio" | "video" | "file"
    data: bytes | None
    url: str | None
    mime_type: str


@dataclass
class InboundMessage:
    session_id: str  # channel_id + thread_id -> unique session
    channel_id: str
    user_id: str
    text: str | None
    attachments: list[Attachment]
    timestamp: str
    reply_to: str | None


@dataclass
class OutboundMessage:
    session_id: str
    text: str
    attachments: list[Attachment] = field(default_factory=list)
    reply_to: str | None = None
    parse_mode: str = "markdown"


@runtime_checkable
class InterfaceAdapter(Protocol):
    adapter_id: str
    channel_type: str  # "telegram" | "discord" | "slack" | "tui" | "gui" | ...

    async def send(self, session_id: str, message: OutboundMessage) -> None: ...
    async def stream_token(self, session_id: str, chunk: StreamChunk) -> None: ...
    async def start(self) -> None: ...
    async def stop(self) -> None: ...


class InterfaceBus:
    """Bus for routing messages between interfaces and the Oracle Agent."""

    def __init__(self) -> None:
        self.adapters: dict[str, InterfaceAdapter] = {}
        self.message_handlers: list[Callable[[InboundMessage], Any]] = []

    def register_adapter(self, adapter: InterfaceAdapter) -> None:
        self.adapters[adapter.adapter_id] = adapter

    def on_message(self, handler: Callable[[InboundMessage], Any]) -> None:
        self.message_handlers.append(handler)

    async def dispatch_inbound(self, message: InboundMessage) -> None:
        for handler in self.message_handlers:
            if asyncio.iscoroutinefunction(handler):
                await handler(message)
            else:
                handler(message)

    async def dispatch_outbound(self, adapter_id: str, message: OutboundMessage) -> None:
        if adapter_id in self.adapters:
            await self.adapters[adapter_id].send(message.session_id, message)
        else:
            raise ValueError(f"Adapter not found: {adapter_id}")

    async def stream_token(self, adapter_id: str, session_id: str, chunk: StreamChunk) -> None:
        if adapter_id in self.adapters:
            await self.adapters[adapter_id].stream_token(session_id, chunk)
        else:
            raise ValueError(f"Adapter not found: {adapter_id}")
