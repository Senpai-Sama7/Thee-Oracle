import asyncio
import logging
from datetime import datetime
from typing import Any
from slack_bolt.async_app import AsyncApp

from src.oracle.interface_adapter import InterfaceBus, InboundMessage, OutboundMessage
from src.oracle.model_router import StreamChunk

log = logging.getLogger(__name__)


class SlackAdapter:
    adapter_id: str = "slack"
    channel_type: str = "slack"

    def __init__(self, bot_token: str, app_token: str, interface_bus: InterfaceBus) -> None:
        self.bot_token = bot_token
        self.app_token = app_token
        self.interface_bus = interface_bus

        self.app = AsyncApp(token=self.bot_token)

        @self.app.event("message")
        async def handle_message_events(body, logger):  # type: ignore
            event = body.get("event", {})
            if "bot_id" in event:
                return

            channel_id = event.get("channel")
            thread_ts = event.get("thread_ts")
            text = event.get("text")
            user_id = event.get("user")
            session_id = self._get_session_id(channel_id, thread_ts)

            inbound = InboundMessage(
                session_id=session_id,
                channel_id=str(channel_id),
                user_id=str(user_id),
                text=text,
                attachments=[],
                timestamp=datetime.now().isoformat(),
                reply_to=str(thread_ts) if thread_ts else None,
            )

            await self.interface_bus.dispatch_inbound(inbound)

        self._message_locks: dict[str, asyncio.Lock] = {}
        self._streaming_messages: dict[str, tuple[str, str]] = {}  # session_id -> (ts, current_text)
        self._runner: Any = None
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        from slack_bolt.adapter.socket_mode.aiohttp import AsyncSocketModeHandler

        self._runner = AsyncSocketModeHandler(self.app, self.app_token)
        self._task = asyncio.create_task(self._runner.start_async())
        await asyncio.sleep(1)

    async def stop(self) -> None:
        if self._runner:
            await self._runner.close_async()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    def _get_session_id(self, channel_id: str, thread_ts: str | None) -> str:
        tid = thread_ts if thread_ts is not None else "0"
        return f"{self.adapter_id}:{channel_id}:{tid}"

    async def send(self, session_id: str, message: OutboundMessage) -> None:
        parts = session_id.split(":")
        if len(parts) != 3 or parts[0] != self.adapter_id:
            return

        channel_id = parts[1]
        thread_ts = parts[2] if parts[2] != "0" else None

        await self.app.client.chat_postMessage(channel=channel_id, thread_ts=thread_ts, text=message.text)

    async def stream_token(self, session_id: str, chunk: StreamChunk) -> None:
        parts = session_id.split(":")
        if len(parts) != 3 or parts[0] != self.adapter_id:
            return

        channel_id = parts[1]
        thread_ts = parts[2] if parts[2] != "0" else None

        if session_id not in self._message_locks:
            self._message_locks[session_id] = asyncio.Lock()

        async with self._message_locks[session_id]:
            if session_id not in self._streaming_messages:
                response = await self.app.client.chat_postMessage(
                    channel=channel_id, thread_ts=thread_ts, text=chunk.delta or "..."
                )
                ts = response.get("ts")
                if ts:
                    self._streaming_messages[session_id] = (ts, chunk.delta or "")
            else:
                ts, current_text = self._streaming_messages[session_id]
                new_text = current_text + (chunk.delta or "")

                if new_text != current_text and new_text.strip():
                    try:
                        await self.app.client.chat_update(channel=channel_id, ts=ts, text=new_text)
                    except Exception as err:
                        log.warning("Slack streaming update failed for session %s: %s", session_id, err)

                if chunk.is_final:
                    del self._streaming_messages[session_id]
                else:
                    self._streaming_messages[session_id] = (ts, new_text)
