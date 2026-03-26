import asyncio
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from src.oracle.interface_adapter import InterfaceBus, InboundMessage, OutboundMessage
from src.oracle.model_router import StreamChunk


class TelegramAdapter:
    adapter_id: str = "telegram"
    channel_type: str = "telegram"

    def __init__(self, token: str, interface_bus: InterfaceBus) -> None:
        self.token = token
        self.interface_bus = interface_bus
        self._app: Application | None = None  # type: ignore
        self._message_locks: dict[str, asyncio.Lock] = {}
        # Used to track the ID of the bot's message so we can edit it while streaming
        self._streaming_messages: dict[str, tuple[int, str]] = {}  # session_id -> (message_id, current_text)

    async def start(self) -> None:
        self._app = Application.builder().token(self.token).build()  # type: ignore
        self._app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message))  # type: ignore
        self._app.add_handler(CommandHandler("start", self._handle_message))  # type: ignore
        await self._app.initialize()  # type: ignore
        await self._app.start()  # type: ignore
        if self._app.updater:  # type: ignore
            await self._app.updater.start_polling()  # type: ignore

    async def stop(self) -> None:
        if self._app:
            if self._app.updater:  # type: ignore
                await self._app.updater.stop()  # type: ignore
            await self._app.stop()  # type: ignore
            await self._app.shutdown()  # type: ignore

    def _get_session_id(self, chat_id: int, thread_id: int | None) -> str:
        tid = thread_id if thread_id is not None else 0
        return f"{self.adapter_id}:{chat_id}:{tid}"

    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message or not update.effective_chat:
            return

        chat_id = update.effective_chat.id
        thread_id = update.message.message_thread_id
        session_id = self._get_session_id(chat_id, thread_id)

        text = update.message.text

        inbound = InboundMessage(
            session_id=session_id,
            channel_id=str(chat_id),
            user_id=str(update.message.from_user.id) if update.message.from_user else "unknown",
            text=text,
            attachments=[],
            timestamp=datetime.now().isoformat(),
            reply_to=str(update.message.reply_to_message.message_id) if update.message.reply_to_message else None,
        )

        await self.interface_bus.dispatch_inbound(inbound)

    async def send(self, session_id: str, message: OutboundMessage) -> None:
        if not self._app or not getattr(self._app, "bot", None):
            return

        parts = session_id.split(":")
        if len(parts) != 3 or parts[0] != self.adapter_id:
            return

        chat_id = int(parts[1])
        thread_id = int(parts[2]) if parts[2] != "0" else None

        await self._app.bot.send_message(  # type: ignore
            chat_id=chat_id,
            message_thread_id=thread_id,
            text=message.text,
            parse_mode="Markdown" if message.parse_mode == "markdown" else None,
        )

    async def stream_token(self, session_id: str, chunk: StreamChunk) -> None:
        if not self._app or not getattr(self._app, "bot", None):
            return

        parts = session_id.split(":")
        if len(parts) != 3 or parts[0] != self.adapter_id:
            return

        chat_id = int(parts[1])
        thread_id = int(parts[2]) if parts[2] != "0" else None

        if session_id not in self._message_locks:
            self._message_locks[session_id] = asyncio.Lock()

        async with self._message_locks[session_id]:
            if session_id not in self._streaming_messages:
                # Send the first chunk
                msg = await self._app.bot.send_message(  # type: ignore
                    chat_id=chat_id,
                    message_thread_id=thread_id,
                    text=chunk.delta or "...",
                )
                self._streaming_messages[session_id] = (msg.message_id, chunk.delta or "")
            else:
                msg_id, current_text = self._streaming_messages[session_id]
                new_text = current_text + (chunk.delta or "")

                # Update text in telegram
                if new_text != current_text and new_text.strip():
                    try:
                        await self._app.bot.edit_message_text(  # type: ignore
                            chat_id=chat_id, message_id=msg_id, text=new_text
                        )
                    except Exception:
                        pass

                if chunk.is_final:
                    del self._streaming_messages[session_id]
                else:
                    self._streaming_messages[session_id] = (msg_id, new_text)
