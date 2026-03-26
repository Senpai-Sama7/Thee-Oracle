import asyncio
from datetime import datetime
import discord

from src.oracle.interface_adapter import InterfaceBus, InboundMessage, OutboundMessage
from src.oracle.model_router import StreamChunk


class DiscordAdapter:
    adapter_id: str = "discord"
    channel_type: str = "discord"

    def __init__(self, token: str, interface_bus: InterfaceBus) -> None:
        self.token = token
        self.interface_bus = interface_bus

        intents = discord.Intents.default()
        intents.message_content = True
        self.client = discord.Client(intents=intents)

        self.client.event(self.on_ready)  # type: ignore
        self.client.event(self.on_message)  # type: ignore

        self._message_locks: dict[str, asyncio.Lock] = {}
        self._streaming_messages: dict[str, tuple[discord.Message, str]] = {}
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        # Create a task for the client start, which blocks
        self._task = asyncio.create_task(self.client.start(self.token))
        # Wait a bit for client to connect
        await asyncio.sleep(1)

    async def stop(self) -> None:
        await self.client.close()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    def _get_session_id(self, channel_id: int, thread_id: int | None) -> str:
        tid = thread_id if thread_id is not None else 0
        return f"{self.adapter_id}:{channel_id}:{tid}"

    async def on_ready(self) -> None:
        pass

    async def on_message(self, message: discord.Message) -> None:
        if message.author == self.client.user:
            return

        channel_id = message.channel.id
        thread_id = None
        if isinstance(message.channel, discord.Thread):
            thread_id = message.channel.id
            channel_id = message.channel.parent_id if message.channel.parent_id else channel_id

        session_id = self._get_session_id(channel_id, thread_id)

        inbound = InboundMessage(
            session_id=session_id,
            channel_id=str(channel_id),
            user_id=str(message.author.id),
            text=message.content,
            attachments=[],
            timestamp=datetime.now().isoformat(),
            reply_to=str(message.reference.message_id) if message.reference else None,
        )

        await self.interface_bus.dispatch_inbound(inbound)

    async def send(self, session_id: str, message: OutboundMessage) -> None:
        parts = session_id.split(":")
        if len(parts) != 3 or parts[0] != self.adapter_id:
            return

        channel_id = int(parts[1])
        thread_id = int(parts[2])

        target_channel_id = thread_id if thread_id != 0 else channel_id
        channel = self.client.get_channel(target_channel_id)

        if isinstance(channel, (discord.TextChannel, discord.Thread, discord.DMChannel)):
            await channel.send(content=message.text)

    async def stream_token(self, session_id: str, chunk: StreamChunk) -> None:
        parts = session_id.split(":")
        if len(parts) != 3 or parts[0] != self.adapter_id:
            return

        channel_id = int(parts[1])
        thread_id = int(parts[2])

        target_channel_id = thread_id if thread_id != 0 else channel_id
        channel = self.client.get_channel(target_channel_id)

        if not isinstance(channel, (discord.TextChannel, discord.Thread, discord.DMChannel)):
            return

        if session_id not in self._message_locks:
            self._message_locks[session_id] = asyncio.Lock()

        async with self._message_locks[session_id]:
            if session_id not in self._streaming_messages:
                msg = await channel.send(content=chunk.delta or "...")
                self._streaming_messages[session_id] = (msg, chunk.delta or "")
            else:
                msg, current_text = self._streaming_messages[session_id]
                new_text = current_text + (chunk.delta or "")

                if new_text != current_text and new_text.strip():
                    try:
                        await msg.edit(content=new_text)
                    except discord.HTTPException:
                        # Ignore rate limit errors for simplicity in this iteration
                        pass

                if chunk.is_final:
                    del self._streaming_messages[session_id]
                else:
                    self._streaming_messages[session_id] = (msg, new_text)
