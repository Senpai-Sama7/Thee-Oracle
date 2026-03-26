import pytest
from unittest.mock import Mock

from src.oracle.a2a_protocol import A2AProtocol, A2AMessage, DeliveryMode


@pytest.fixture
def mock_persistence():
    persistence = Mock()
    persistence.log_event = Mock()
    return persistence


@pytest.mark.asyncio
async def test_a2a_send_receive_basic(mock_persistence):
    protocol = A2AProtocol(registry=None, persistence=mock_persistence)

    msg = A2AMessage(
        message_id="msg-1",
        from_node="node-a",
        to_node="node-b",
        payload={"data": "test"},
        timestamp="2023-01-01T00:00:00Z",
    )

    msg_id = await protocol.send("node-a", "node-b", msg)
    assert msg_id == "msg-1"

    received = await protocol.receive("node-b", timeout=0.1)
    assert received is not None
    assert received.message_id == "msg-1"
    assert received.payload["data"] == "test"


@pytest.mark.asyncio
async def test_exactly_once_deduplication(mock_persistence):
    protocol = A2AProtocol(registry=None, persistence=mock_persistence)

    msg = A2AMessage(
        message_id="unique-123", from_node="node-a", to_node="node-b", payload={"hello": "world"}, timestamp="now"
    )

    # Send same message twice
    await protocol.send("node-a", "node-b", msg, delivery=DeliveryMode.EXACTLY_ONCE)
    await protocol.send("node-a", "node-b", msg, delivery=DeliveryMode.EXACTLY_ONCE)

    # Should only receive it once, second receive should timeout
    received1 = await protocol.receive("node-b", timeout=0.1)
    assert received1 is not None
    assert received1.message_id == "unique-123"

    received2 = await protocol.receive("node-b", timeout=0.1)
    assert received2 is None
