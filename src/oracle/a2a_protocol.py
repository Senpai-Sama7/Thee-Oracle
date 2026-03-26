import asyncio
from enum import Enum
from dataclasses import dataclass
from typing import Any, Dict, Optional, Set, Tuple

from .agent_system import PersistenceLayer


class DeliveryMode(str, Enum):
    AT_MOST_ONCE = "at_most_once"
    AT_LEAST_ONCE = "at_least_once"
    EXACTLY_ONCE = "exactly_once"


@dataclass
class A2AMessage:
    message_id: str
    from_node: str
    to_node: str
    payload: Dict[str, Any]
    timestamp: str
    correlation_id: Optional[str] = None


class A2AProtocol:
    """Implements Google A2A spec for agent-to-agent communication."""

    def __init__(self, registry: Any, persistence: PersistenceLayer) -> None:
        self.registry = registry
        self.persistence = persistence
        self._queues: Dict[str, asyncio.Queue[Tuple[A2AMessage, DeliveryMode]]] = {}
        self._delivered_messages: Set[str] = set()  # Deduplication for Exactly-Once
        self._lock = asyncio.Lock()

    def _get_queue(self, node_id: str) -> asyncio.Queue[Tuple[A2AMessage, DeliveryMode]]:
        if node_id not in self._queues:
            self._queues[node_id] = asyncio.Queue()
        return self._queues[node_id]

    async def send(
        self,
        from_node: str,
        to_node: str,
        message: A2AMessage,
        delivery: DeliveryMode = DeliveryMode.AT_LEAST_ONCE,
    ) -> str:
        """Sends a message to another node."""
        async with self._lock:
            # Deduplication check for EXACTLY_ONCE
            if delivery == DeliveryMode.EXACTLY_ONCE and message.message_id in self._delivered_messages:
                return message.message_id

            queue = self._get_queue(to_node)
            await queue.put((message, delivery))

            # Record delivery
            if delivery == DeliveryMode.EXACTLY_ONCE:
                self._delivered_messages.add(message.message_id)

            # Audit log via persistence
            self.persistence.log_event(
                session_id=message.correlation_id or "system",
                event_type="A2A_SEND",
                payload={
                    "message_id": message.message_id,
                    "from_node": from_node,
                    "to_node": to_node,
                    "delivery": delivery.value,
                },
            )
        return message.message_id

    async def receive(self, node_id: str, timeout: float = 30.0) -> Optional[A2AMessage]:
        """Receives a message from the queue."""
        queue = self._get_queue(node_id)
        try:
            message, delivery = await asyncio.wait_for(queue.get(), timeout=timeout)
            return message
        except asyncio.TimeoutError:
            return None

    async def ack(self, message_id: str) -> None:
        """Acknowledge a message."""
        self.persistence.log_event(session_id="system", event_type="A2A_ACK", payload={"message_id": message_id})
