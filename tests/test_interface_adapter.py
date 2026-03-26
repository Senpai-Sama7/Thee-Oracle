import pytest
import asyncio
from src.oracle.interface_adapter import InterfaceBus, InboundMessage, OutboundMessage
from src.oracle.model_router import StreamChunk


class DummyAdapter:
    adapter_id = "dummy"
    channel_type = "dummy"

    def __init__(self):
        self.sent_messages = []
        self.streamed_chunks = []

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass

    async def send(self, session_id: str, message: OutboundMessage) -> None:
        self.sent_messages.append((session_id, message))

    async def stream_token(self, session_id: str, chunk: StreamChunk) -> None:
        self.streamed_chunks.append((session_id, chunk))


@pytest.mark.asyncio
async def test_interface_bus_dispatch_inbound():
    bus = InterfaceBus()

    received_messages = []

    async def handler(msg: InboundMessage):
        received_messages.append(msg)

    bus.on_message(handler)

    msg = InboundMessage(
        session_id="dummy:1:0",
        channel_id="1",
        user_id="user1",
        text="Hello",
        attachments=[],
        timestamp="2023-01-01T00:00:00Z",
        reply_to=None,
    )

    await bus.dispatch_inbound(msg)
    assert len(received_messages) == 1
    assert received_messages[0].text == "Hello"


@pytest.mark.asyncio
async def test_interface_bus_dispatch_outbound():
    bus = InterfaceBus()
    adapter = DummyAdapter()
    bus.register_adapter(adapter)  # type: ignore

    msg = OutboundMessage(session_id="dummy:1:0", text="Response", attachments=[], reply_to=None)

    await bus.dispatch_outbound("dummy", msg)
    assert len(adapter.sent_messages) == 1
    assert adapter.sent_messages[0][1].text == "Response"


@pytest.mark.asyncio
async def test_interface_bus_stream_token():
    bus = InterfaceBus()
    adapter = DummyAdapter()
    bus.register_adapter(adapter)  # type: ignore

    chunk = StreamChunk(delta="token")
    await bus.stream_token("dummy", "dummy:1:0", chunk)
    assert len(adapter.streamed_chunks) == 1
    assert adapter.streamed_chunks[0][1].delta == "token"


def test_missing_adapter():
    bus = InterfaceBus()
    msg = OutboundMessage(session_id="dummy:1:0", text="Test")
    with pytest.raises(ValueError):
        asyncio.run(bus.dispatch_outbound("missing", msg))
