import logging
from unittest.mock import AsyncMock, MagicMock

import pytest

from interfaces.messaging.discord_adapter import DiscordAdapter
from interfaces.messaging.slack_adapter import SlackAdapter
from interfaces.messaging.telegram_adapter import TelegramAdapter
from src.oracle.interface_adapter import InterfaceBus, OutboundMessage
from src.oracle.model_router import StreamChunk


@pytest.mark.asyncio
async def test_telegram_adapter_send(mocker):
    bus = InterfaceBus()
    adapter = TelegramAdapter("fake_token", bus)

    mock_app = MagicMock()
    mock_app.bot.send_message = AsyncMock()
    adapter._app = mock_app

    msg = OutboundMessage(session_id="telegram:123:456", text="Hello")
    await adapter.send("telegram:123:456", msg)

    mock_app.bot.send_message.assert_called_once_with(
        chat_id=123, message_thread_id=456, text="Hello", parse_mode="Markdown"
    )


@pytest.mark.asyncio
async def test_telegram_adapter_stream(mocker):
    bus = InterfaceBus()
    adapter = TelegramAdapter("fake_token", bus)

    mock_app = MagicMock()
    mock_send = AsyncMock()
    mock_send.return_value.message_id = 999
    mock_app.bot.send_message = mock_send
    mock_app.bot.edit_message_text = AsyncMock()
    adapter._app = mock_app

    chunk1 = StreamChunk(delta="Hello")
    await adapter.stream_token("telegram:123:0", chunk1)

    mock_app.bot.send_message.assert_called_once_with(chat_id=123, message_thread_id=None, text="Hello")

    chunk2 = StreamChunk(delta=" World", is_final=True)
    await adapter.stream_token("telegram:123:0", chunk2)

    mock_app.bot.edit_message_text.assert_called_once_with(chat_id=123, message_id=999, text="Hello World")


@pytest.mark.asyncio
async def test_telegram_adapter_logs_stream_update_failures(caplog):
    bus = InterfaceBus()
    adapter = TelegramAdapter("fake_token", bus)

    mock_app = MagicMock()
    mock_send = AsyncMock()
    mock_send.return_value.message_id = 999
    mock_app.bot.send_message = mock_send
    mock_app.bot.edit_message_text = AsyncMock(side_effect=RuntimeError("rate limited"))
    adapter._app = mock_app

    await adapter.stream_token("telegram:123:0", StreamChunk(delta="Hello"))

    with caplog.at_level(logging.WARNING):
        await adapter.stream_token("telegram:123:0", StreamChunk(delta=" World", is_final=True))

    assert "Telegram streaming update failed" in caplog.text
    assert "telegram:123:0" not in adapter._streaming_messages


@pytest.mark.asyncio
async def test_discord_adapter_send(mocker):
    bus = InterfaceBus()
    adapter = DiscordAdapter("fake_token", bus)

    mock_channel = MagicMock()
    mock_channel.send = AsyncMock()

    # Mock discord TextChannel check
    import discord

    mock_channel.__class__ = discord.TextChannel

    adapter.client.get_channel = MagicMock(return_value=mock_channel)

    msg = OutboundMessage(session_id="discord:123:0", text="Hello Discord")
    await adapter.send("discord:123:0", msg)

    mock_channel.send.assert_called_once_with(content="Hello Discord")


@pytest.mark.asyncio
async def test_slack_adapter_send(mocker):
    bus = InterfaceBus()
    adapter = SlackAdapter("bot", "app", bus)

    adapter.app.client.chat_postMessage = AsyncMock()

    msg = OutboundMessage(session_id="slack:C123:T456", text="Hello Slack")
    await adapter.send("slack:C123:T456", msg)

    adapter.app.client.chat_postMessage.assert_called_once_with(channel="C123", thread_ts="T456", text="Hello Slack")


@pytest.mark.asyncio
async def test_slack_adapter_stream_update_failure_is_nonfatal(mocker):
    bus = InterfaceBus()
    adapter = SlackAdapter("bot", "app", bus)

    adapter.app.client.chat_postMessage = AsyncMock(return_value={"ts": "123.456"})
    adapter.app.client.chat_update = AsyncMock(side_effect=RuntimeError("rate limited"))

    await adapter.stream_token("slack:C123:0", StreamChunk(delta="Hello"))
    await adapter.stream_token("slack:C123:0", StreamChunk(delta=" world", is_final=True))

    adapter.app.client.chat_update.assert_called_once_with(channel="C123", ts="123.456", text="Hello world")
    assert "slack:C123:0" not in adapter._streaming_messages


@pytest.mark.asyncio
async def test_telegram_adapter_stream_update_failure_is_nonfatal(mocker):
    bus = InterfaceBus()
    adapter = TelegramAdapter("fake_token", bus)

    mock_app = MagicMock()
    mock_send = AsyncMock()
    mock_send.return_value.message_id = 999
    mock_app.bot.send_message = mock_send
    mock_app.bot.edit_message_text = AsyncMock(side_effect=RuntimeError("edit failed"))
    adapter._app = mock_app

    await adapter.stream_token("telegram:123:0", StreamChunk(delta="Hello"))
    await adapter.stream_token("telegram:123:0", StreamChunk(delta=" world", is_final=True))

    mock_app.bot.edit_message_text.assert_called_once_with(chat_id=123, message_id=999, text="Hello world")
    assert "telegram:123:0" not in adapter._streaming_messages


@pytest.mark.asyncio
async def test_slack_adapter_logs_stream_update_failures(caplog):
    bus = InterfaceBus()
    adapter = SlackAdapter("bot", "app", bus)

    adapter.app.client.chat_postMessage = AsyncMock(return_value={"ts": "100.200"})
    adapter.app.client.chat_update = AsyncMock(side_effect=RuntimeError("rate limited"))

    await adapter.stream_token("slack:C123:0", StreamChunk(delta="Hello"))

    with caplog.at_level(logging.WARNING):
        await adapter.stream_token("slack:C123:0", StreamChunk(delta=" World", is_final=True))

    assert "Slack streaming update failed" in caplog.text
    assert "slack:C123:0" not in adapter._streaming_messages
