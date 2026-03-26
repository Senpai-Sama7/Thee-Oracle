#!/usr/bin/env python3
"""
Model Router - Multi-LLM Support for Oracle Platform
Phase 1: Model Layer Implementation

Provides:
- ModelProvider protocol for unified LLM interface
- Adapters: Gemini, OpenAI (GPT-4o), Anthropic (Claude), Ollama
- ModelRouter with automatic failover chain
- Cost tracking and optimization
- Streaming support

Design follows the Oracle Platform v2 specification with these invariants:
- All providers return structured envelopes, never raise
- Failover is transparent to callers
- Streaming tokens preserve order
- Cost tracking is automatic and accurate
"""

from __future__ import annotations

import os
import time
import json
import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Literal, Protocol, runtime_checkable
from pathlib import Path
from collections import defaultdict

# Type imports for provider SDKs
from google import genai
from google.genai import types as genai_types

log = logging.getLogger("oracle.model_router")


# =============================================================================
# Data Models
# =============================================================================


@dataclass(frozen=True)
class GenerateConfig:
    """Configuration for text generation."""

    model_id: str
    temperature: float = 0.7
    max_tokens: int = 8192
    timeout: float = 60.0
    top_p: float | None = None
    stop_sequences: list[str] = field(default_factory=list)
    thinking_level: Literal["low", "medium", "high"] | None = None


@dataclass(frozen=True)
class ToolCall:
    """Represents a tool/function call from the model."""

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class TokenUsage:
    """Token usage statistics with cost calculation."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float | None = None

    def __add__(self, other: TokenUsage) -> TokenUsage:
        """Combine two usage statistics."""
        return TokenUsage(
            prompt_tokens=self.prompt_tokens + other.prompt_tokens,
            completion_tokens=self.completion_tokens + other.completion_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
            cost_usd=(self.cost_usd or 0) + (other.cost_usd or 0) if (self.cost_usd or other.cost_usd) else None,
        )


@dataclass(frozen=True)
class GenerateResponse:
    """Standard response envelope from any provider."""

    content: str
    tool_calls: list[ToolCall]
    usage: TokenUsage
    provider_id: str
    model_id: str
    latency_ms: float
    finish_reason: str | None = None
    error: str | None = None

    @classmethod
    def make_error(cls, provider_id: str, error_msg: str) -> GenerateResponse:
        """Create an error response."""
        return cls(
            content="",
            tool_calls=[],
            usage=TokenUsage(0, 0, 0, None),
            provider_id=provider_id,
            model_id="error",
            latency_ms=0.0,
            finish_reason=f"error: {error_msg}",
            error=error_msg,
        )

    @property
    def is_error(self) -> bool:
        """Check if this is an error response."""
        if self.error is not None:
            return True
        if self.finish_reason and "error" in self.finish_reason.lower():
            return True
        return False


@dataclass(frozen=True)
class StreamChunk:
    """Single token/chunk in a streaming response."""

    delta: str
    tool_call_delta: ToolCall | None = None
    is_final: bool = False
    provider_id: str = ""
    model_id: str = ""
    usage: TokenUsage | None = None  # Only present in final chunk
    finish_reason: str | None = None  # Only present in final chunk
    error: str | None = None

    @classmethod
    def final(
        cls,
        provider_id: str,
        model_id: str,
        usage: TokenUsage | None = None,
        finish_reason: str | None = None,
        error: str | None = None,
    ) -> StreamChunk:
        """Create a final chunk."""
        return cls(
            delta="",
            tool_call_delta=None,
            is_final=True,
            provider_id=provider_id,
            model_id=model_id,
            usage=usage,
            finish_reason=finish_reason or (f"error: {error}" if error else "stop"),
            error=error,
        )


@dataclass
class ProviderHealth:
    """Health status of a provider."""

    provider_id: str
    healthy: bool
    latency_ms: float
    error: str | None = None
    last_checked: float = field(default_factory=time.time)
    consecutive_failures: int = 0

    @property
    def is_healthy(self) -> bool:
        """Determine if provider should be used for requests."""
        if not self.healthy:
            return False
        # Temporarily mark unhealthy after 3 consecutive failures
        if self.consecutive_failures >= 3:
            return False
        return True


class ProviderError(Exception):
    """Exception raised when a provider fails."""

    def __init__(self, provider_id: str, message: str, retryable: bool = True, status_code: int | None = None):
        self.provider_id = provider_id
        self.message = message
        self.retryable = retryable
        self.status_code = status_code
        super().__init__(f"{provider_id}: {message}")


# =============================================================================
# Cost Tracking
# =============================================================================


class CostTracker:
    """Tracks token usage and costs across all providers."""

    # Pricing per 1K tokens (input, output) - updated periodically
    PRICING: dict[str, tuple[float, float]] = {
        # Gemini models
        "gemini-2.0-flash-exp": (0.0, 0.0),  # Free tier
        "gemini-2.0-flash": (0.000075, 0.0003),
        "gemini-2.5-pro-preview-05-06": (0.00125, 0.01),
        "gemini-1.5-pro": (0.00125, 0.005),
        "gemini-1.5-flash": (0.000075, 0.0003),
        # OpenAI models
        "gpt-4o": (0.0025, 0.01),
        "gpt-4o-mini": (0.00015, 0.0006),
        "gpt-4-turbo": (0.01, 0.03),
        # Anthropic models
        "claude-3-5-sonnet-20241022": (0.003, 0.015),
        "claude-3-opus-20240229": (0.015, 0.075),
        "claude-3-haiku-20240307": (0.00025, 0.00125),
        # Ollama models (local = free)
        "llama3": (0.0, 0.0),
        "llama3.1": (0.0, 0.0),
        "mistral": (0.0, 0.0),
        "codellama": (0.0, 0.0),
    }

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._total_usage: dict[str, TokenUsage] = defaultdict(lambda: TokenUsage(0, 0, 0, 0.0))
        self._session_usage: dict[str, TokenUsage] = defaultdict(lambda: TokenUsage(0, 0, 0, 0.0))

    def calculate_cost(self, model_id: str, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate cost in USD for a request."""
        # Try exact match, then prefix match
        pricing = self.PRICING.get(model_id)
        if pricing is None:
            for key, value in self.PRICING.items():
                if model_id.startswith(key):
                    pricing = value
                    break

        if pricing is None:
            return 0.0

        input_price, output_price = pricing
        cost = prompt_tokens / 1000 * input_price + completion_tokens / 1000 * output_price
        return round(cost, 6)

    async def record_usage(self, session_id: str, model_id: str, usage: TokenUsage) -> None:
        """Record usage for a request."""
        async with self._lock:
            # Calculate cost if not already set
            if usage.cost_usd is None:
                cost = self.calculate_cost(model_id, usage.prompt_tokens, usage.completion_tokens)
                usage = TokenUsage(
                    prompt_tokens=usage.prompt_tokens,
                    completion_tokens=usage.completion_tokens,
                    total_tokens=usage.total_tokens,
                    cost_usd=cost,
                )

            # Update totals
            self._total_usage[model_id] = self._total_usage[model_id] + usage
            self._session_usage[session_id] = self._session_usage[session_id] + usage

    def get_session_cost(self, session_id: str) -> float:
        """Get total cost for a session."""
        usage = self._session_usage.get(session_id)
        return usage.cost_usd if usage and usage.cost_usd else 0.0

    def get_total_cost(self) -> float:
        """Get total cost across all sessions."""
        return sum(u.cost_usd or 0 for u in self._total_usage.values())

    def get_stats(self) -> dict[str, Any]:
        """Get usage statistics."""
        return {
            "total_cost_usd": self.get_total_cost(),
            "by_model": {
                model: {
                    "prompt_tokens": u.prompt_tokens,
                    "completion_tokens": u.completion_tokens,
                    "total_tokens": u.total_tokens,
                    "cost_usd": u.cost_usd,
                }
                for model, u in self._total_usage.items()
            },
        }

    def reset(self) -> None:
        """Reset all tracking (useful for testing)."""
        self._total_usage.clear()
        self._session_usage.clear()


# Global cost tracker instance
_cost_tracker = CostTracker()


def get_cost_tracker() -> CostTracker:
    """Get the global cost tracker instance."""
    return _cost_tracker


# =============================================================================
# ModelProvider Protocol
# =============================================================================


@runtime_checkable
class ModelProvider(Protocol):
    """Protocol for LLM providers."""

    provider_id: str

    async def generate(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        config: GenerateConfig,
    ) -> GenerateResponse:
        """Generate a complete response."""
        ...

    def stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        config: GenerateConfig,
    ) -> AsyncIterator[StreamChunk]:
        """Stream response tokens."""
        ...

    async def health_check(self) -> ProviderHealth:
        """Check provider health."""
        ...


# =============================================================================
# Base Adapter
# =============================================================================


class BaseAdapter(ABC):
    """Base class for model adapters with common functionality."""

    def __init__(self, provider_id: str, model_id: str):
        self.provider_id = provider_id
        self.model_id = model_id
        self._health = ProviderHealth(provider_id=provider_id, healthy=True, latency_ms=0)

    @abstractmethod
    async def generate(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        config: GenerateConfig,
    ) -> GenerateResponse:
        """Generate a complete response."""
        pass

    @abstractmethod
    def stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        config: GenerateConfig,
    ) -> AsyncIterator[StreamChunk]:
        """Stream response tokens."""
        pass

    async def health_check(self) -> ProviderHealth:
        """Default health check - ping with minimal request."""
        start = time.time()
        try:
            # Try a minimal generation
            await self.generate(
                messages=[{"role": "user", "content": "Hi"}],
                tools=None,
                config=GenerateConfig(model_id=self.model_id, max_tokens=1),
            )
            latency = (time.time() - start) * 1000
            self._health = ProviderHealth(
                provider_id=self.provider_id, healthy=True, latency_ms=latency, last_checked=time.time()
            )
        except Exception as e:
            latency = (time.time() - start) * 1000
            self._health = ProviderHealth(
                provider_id=self.provider_id,
                healthy=False,
                latency_ms=latency,
                error=str(e),
                last_checked=time.time(),
                consecutive_failures=self._health.consecutive_failures + 1,
            )
        return self._health

    def _convert_messages_to_openai_format(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Convert internal message format to OpenAI format."""
        # Our format is already close to OpenAI format
        return messages

    def _convert_tools_to_openai_format(self, tools: list[dict[str, Any]] | None) -> list[dict[str, Any]] | None:
        """Convert tool definitions to OpenAI format."""
        if not tools:
            return None

        openai_tools = []
        for tool in tools:
            openai_tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool.get("name"),
                        "description": tool.get("description", ""),
                        "parameters": tool.get("parameters", {"type": "object"}),
                    },
                }
            )
        return openai_tools

    def _make_usage(self, prompt_tokens: int, completion_tokens: int, model_id: str) -> TokenUsage:
        """Create a TokenUsage with cost calculation."""
        total = prompt_tokens + completion_tokens
        cost = _cost_tracker.calculate_cost(model_id, prompt_tokens, completion_tokens)
        return TokenUsage(prompt_tokens, completion_tokens, total, cost)


# =============================================================================
# Gemini Adapter
# =============================================================================


class GeminiAdapter(BaseAdapter):
    """Adapter for Google Gemini models via Vertex AI."""

    def __init__(
        self,
        project_id: str,
        location: str,
        model_id: str,
    ):
        super().__init__("gemini", model_id)
        self.project_id = project_id
        self.location = location
        self._client: genai.Client | None = None

    def _get_client(self) -> genai.Client:
        """Lazy initialization of Gemini client."""
        if self._client is None:
            self._client = genai.Client(
                vertexai=True,
                project=self.project_id,
                location=self.location,
            )
        return self._client

    def _convert_messages_to_gemini_format(self, messages: list[dict[str, Any]]) -> list[genai_types.Content]:
        """Convert internal messages to Gemini SDK format."""
        contents = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            # Map roles
            if role == "assistant":
                role = "model"
            elif role == "tool":
                role = "user"  # Tool responses are user messages in Gemini

            parts = [genai_types.Part.from_text(text=content)]
            contents.append(genai_types.Content(role=role, parts=parts))

        return contents

    def _convert_tools_to_gemini_format(
        self, tools: list[dict[str, Any]] | None
    ) -> list[genai_types.FunctionDeclaration] | None:
        """Convert tool definitions to Gemini format."""
        if not tools:
            return None

        declarations = []
        for tool in tools:
            declarations.append(
                genai_types.FunctionDeclaration(
                    name=tool.get("name", ""),
                    description=tool.get("description", ""),
                    parameters=tool.get("parameters", {"type": "object"}),
                )
            )

        return declarations

    async def generate(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        config: GenerateConfig,
    ) -> GenerateResponse:
        """Generate using Gemini."""
        start_time = time.time()

        try:
            client = self._get_client()
            contents = self._convert_messages_to_gemini_format(messages)
            function_declarations = self._convert_tools_to_gemini_format(tools)

            # Build generation config
            generation_config = genai_types.GenerateContentConfig(
                temperature=config.temperature,
                max_output_tokens=config.max_tokens,
            )

            if function_declarations:
                generation_config.tools = [genai_types.Tool(function_declarations=function_declarations)]

            # Handle thinking level for supported models
            if config.thinking_level and "2.5" in config.model_id:
                # Map thinking level to ThinkingConfig enum
                level_map = {
                    "low": genai_types.ThinkingLevel.LOW,
                    "medium": genai_types.ThinkingLevel.MEDIUM,
                    "high": genai_types.ThinkingLevel.HIGH,
                }
                if config.thinking_level in level_map:
                    generation_config.thinking_config = genai_types.ThinkingConfig(
                        thinking_level=level_map[config.thinking_level], include_thoughts=True
                    )

            response = await asyncio.to_thread(
                client.models.generate_content,
                model=config.model_id,
                contents=contents,  # type: ignore[arg-type]
                config=generation_config,
            )

            latency = (time.time() - start_time) * 1000

            # Extract content and tool calls
            content = ""
            tool_calls: list[ToolCall] = []

            if (
                response.candidates
                and response.candidates[0].content
                and getattr(response.candidates[0].content, "parts", None)
            ):
                candidate = response.candidates[0]
                content_obj = candidate.content
                if content_obj and content_obj.parts:
                    for part in content_obj.parts:
                        if part.text:
                            content += str(part.text)
                        elif getattr(part, "function_call", None):
                            fc = part.function_call
                            if fc:
                                tool_calls.append(
                                    ToolCall(
                                        id=f"call_{len(tool_calls)}",
                                        name=str(fc.name),
                                        arguments=dict(fc.args) if getattr(fc, "args", None) else {},  # type: ignore[arg-type]
                                    )
                                )

            # Extract usage if available
            usage_meta = response.usage_metadata
            if usage_meta:
                usage = self._make_usage(
                    usage_meta.prompt_token_count or 0, usage_meta.candidates_token_count or 0, config.model_id
                )
            else:
                # Estimate usage if not provided
                usage = self._make_usage(
                    sum(len(m.get("content", "")) for m in messages) // 4, len(content) // 4, config.model_id
                )

            return GenerateResponse(
                content=content,
                tool_calls=tool_calls,
                usage=usage,
                provider_id=self.provider_id,
                model_id=config.model_id,
                latency_ms=latency,
                finish_reason=candidate.finish_reason.name if candidate.finish_reason else None,
            )

        except Exception as e:
            latency = (time.time() - start_time) * 1000
            raise ProviderError(self.provider_id, str(e), retryable=True, status_code=getattr(e, "code", None)) from e

    async def stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        config: GenerateConfig,
    ) -> AsyncIterator[StreamChunk]:
        """Stream response from Gemini."""
        try:
            client = self._get_client()
            contents = self._convert_messages_to_gemini_format(messages)
            function_declarations = self._convert_tools_to_gemini_format(tools)

            generation_config = genai_types.GenerateContentConfig(
                temperature=config.temperature,
                max_output_tokens=config.max_tokens,
            )

            if function_declarations:
                generation_config.tools = [genai_types.Tool(function_declarations=function_declarations)]

            # Stream the response
            stream = await asyncio.to_thread(
                client.models.generate_content_stream,
                model=config.model_id,
                contents=contents,  # type: ignore[arg-type]
                config=generation_config,
            )

            full_content = ""
            tool_calls: list[ToolCall] = []

            for chunk in stream:
                if getattr(chunk, "candidates", None) is None or not chunk.candidates:
                    continue

                candidate = chunk.candidates[0]
                delta = ""
                tool_delta = None

                parts = getattr(candidate.content, "parts", []) if getattr(candidate, "content", None) else []
                for part in parts:
                    if getattr(part, "text", None):
                        delta += str(part.text)
                        full_content += str(part.text)
                    elif getattr(part, "function_call", None):
                        tool_delta = ToolCall(
                            id=f"call_{len(tool_calls)}",
                            name=str(part.function_call.name),
                            arguments=dict(part.function_call.args)
                            if getattr(part.function_call, "args", None)
                            else {},
                        )
                        tool_calls.append(tool_delta)

                if delta or tool_delta:
                    yield StreamChunk(
                        delta=delta,
                        tool_call_delta=tool_delta,
                        is_final=False,
                        provider_id=self.provider_id,
                        model_id=config.model_id,
                    )

            # Final chunk
            usage = self._make_usage(
                sum(len(m.get("content", "")) for m in messages) // 4, len(full_content) // 4, config.model_id
            )

            yield StreamChunk.final(
                provider_id=self.provider_id, model_id=config.model_id, usage=usage, finish_reason="stop"
            )

        except Exception as e:
            yield StreamChunk.final(provider_id=self.provider_id, model_id=config.model_id, error=str(e))


# =============================================================================
# OpenAI Adapter
# =============================================================================


class OpenAIAdapter(BaseAdapter):
    """Adapter for OpenAI models (GPT-4o, GPT-4o-mini, etc.)."""

    def __init__(
        self,
        api_key: str,
        model_id: str,
        base_url: str | None = None,
    ):
        super().__init__("openai", model_id)
        self.api_key = api_key
        self.base_url = base_url or "https://api.openai.com/v1"
        self._client: Any | None = None

    def _get_client(self) -> Any:
        """Lazy initialization of OpenAI client."""
        if self._client is None:
            try:
                import openai

                self._client = openai.AsyncOpenAI(api_key=self.api_key, base_url=self.base_url, timeout=60.0)
            except ImportError as err:
                raise ProviderError(
                    self.provider_id, "openai package not installed. Run: pip install openai", retryable=False
                ) from err
        return self._client

    async def generate(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        config: GenerateConfig,
    ) -> GenerateResponse:
        """Generate using OpenAI."""
        start_time = time.time()

        try:
            client = self._get_client()

            # Build request
            request: dict[str, Any] = {
                "model": config.model_id,
                "messages": messages,
                "temperature": config.temperature,
                "max_tokens": config.max_tokens,
            }

            if tools:
                request["tools"] = self._convert_tools_to_openai_format(tools)
                request["tool_choice"] = "auto"

            if config.top_p is not None:
                request["top_p"] = config.top_p

            if config.stop_sequences:
                request["stop"] = config.stop_sequences

            response = await client.chat.completions.create(**request)

            latency = (time.time() - start_time) * 1000

            # Extract content and tool calls
            choice = response.choices[0]
            message = choice.message

            content = message.content or ""
            tool_calls = []

            if message.tool_calls:
                for tc in message.tool_calls:
                    tool_calls.append(
                        ToolCall(id=tc.id, name=tc.function.name, arguments=json.loads(tc.function.arguments))
                    )

            # Extract usage
            usage = TokenUsage(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
                cost_usd=_cost_tracker.calculate_cost(
                    config.model_id, response.usage.prompt_tokens, response.usage.completion_tokens
                ),
            )

            return GenerateResponse(
                content=content,
                tool_calls=tool_calls,
                usage=usage,
                provider_id=self.provider_id,
                model_id=config.model_id,
                latency_ms=latency,
                finish_reason=choice.finish_reason,
            )

        except Exception as e:
            latency = (time.time() - start_time) * 1000
            # Check for specific error types
            status_code = None
            retryable = True

            if hasattr(e, "status_code"):
                status_code = e.status_code
                if status_code in (401, 403):
                    retryable = False
                elif status_code == 429:
                    retryable = True

            raise ProviderError(self.provider_id, str(e), retryable=retryable, status_code=status_code) from e

    async def stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        config: GenerateConfig,
    ) -> AsyncIterator[StreamChunk]:
        """Stream response from OpenAI."""
        try:
            client = self._get_client()

            request: dict[str, Any] = {
                "model": config.model_id,
                "messages": messages,
                "temperature": config.temperature,
                "max_tokens": config.max_tokens,
                "stream": True,
            }

            if tools:
                request["tools"] = self._convert_tools_to_openai_format(tools)
                request["tool_choice"] = "auto"

            stream = await client.chat.completions.create(**request)

            full_content = ""
            tool_calls: dict[str, dict[str, Any]] = {}
            current_tool_call: dict[str, Any] | None = None

            async for chunk in stream:
                delta = chunk.choices[0].delta

                # Handle content delta
                if delta.content:
                    full_content += delta.content
                    yield StreamChunk(delta=delta.content, provider_id=self.provider_id, model_id=config.model_id)

                # Handle tool call deltas
                if delta.tool_calls:
                    for tc_delta in delta.tool_calls:
                        if tc_delta.id:
                            # New tool call
                            current_tool_call = {
                                "id": tc_delta.id,
                                "name": tc_delta.function.name or "",
                                "arguments": tc_delta.function.arguments or "",
                            }
                            tool_calls[tc_delta.id] = current_tool_call
                        elif current_tool_call and tc_delta.function:
                            # Accumulate arguments
                            if tc_delta.function.arguments:
                                current_tool_call["arguments"] += tc_delta.function.arguments

            # Build final tool calls
            final_tool_calls = []
            for tc_data in tool_calls.values():
                try:
                    args = json.loads(tc_data["arguments"]) if tc_data["arguments"] else {}
                except json.JSONDecodeError:
                    args = {}

                tool_call = ToolCall(id=tc_data["id"], name=tc_data["name"], arguments=args)
                final_tool_calls.append(tool_call)

                # Yield tool call as a chunk
                yield StreamChunk(
                    delta="", tool_call_delta=tool_call, provider_id=self.provider_id, model_id=config.model_id
                )

            # Final chunk with usage estimate
            usage = self._make_usage(
                sum(len(m.get("content", "")) for m in messages) // 4, len(full_content) // 4, config.model_id
            )

            yield StreamChunk.final(
                provider_id=self.provider_id, model_id=config.model_id, usage=usage, finish_reason="stop"
            )

        except Exception as e:
            yield StreamChunk.final(provider_id=self.provider_id, model_id=config.model_id, error=str(e))


# =============================================================================
# Anthropic Adapter
# =============================================================================


class AnthropicAdapter(BaseAdapter):
    """Adapter for Anthropic Claude models."""

    def __init__(
        self,
        api_key: str,
        model_id: str,
    ):
        super().__init__("anthropic", model_id)
        self.api_key = api_key
        self._client: Any | None = None

    def _get_client(self) -> Any:
        """Lazy initialization of Anthropic client."""
        if self._client is None:
            try:
                import anthropic

                self._client = anthropic.AsyncAnthropic(api_key=self.api_key, timeout=60.0)
            except ImportError as err:
                raise ProviderError(
                    self.provider_id, "anthropic package not installed. Run: pip install anthropic", retryable=False
                ) from err
        return self._client

    def _convert_tools_to_anthropic_format(self, tools: list[dict[str, Any]] | None) -> list[dict[str, Any]] | None:
        """Convert tool definitions to Anthropic format."""
        if not tools:
            return None

        anthropic_tools = []
        for tool in tools:
            anthropic_tools.append(
                {
                    "name": tool.get("name"),
                    "description": tool.get("description", ""),
                    "input_schema": tool.get("parameters", {"type": "object"}),
                }
            )
        return anthropic_tools

    async def generate(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        config: GenerateConfig,
    ) -> GenerateResponse:
        """Generate using Anthropic Claude."""
        start_time = time.time()

        try:
            client = self._get_client()

            # Separate system message if present
            system_message = None
            chat_messages = []

            for msg in messages:
                if msg.get("role") == "system":
                    system_message = msg.get("content", "")
                else:
                    chat_messages.append(msg)

            # Build request
            request: dict[str, Any] = {
                "model": config.model_id,
                "messages": chat_messages,
                "max_tokens": config.max_tokens,
                "temperature": config.temperature,
            }

            if system_message:
                request["system"] = system_message

            if tools:
                request["tools"] = self._convert_tools_to_anthropic_format(tools)

            if config.top_p is not None:
                request["top_p"] = config.top_p

            if config.stop_sequences:
                request["stop_sequences"] = config.stop_sequences

            response = await client.messages.create(**request)

            latency = (time.time() - start_time) * 1000

            # Extract content and tool calls
            content = ""
            tool_calls = []

            for block in response.content:
                if block.type == "text":
                    content += block.text
                elif block.type == "tool_use":
                    tool_calls.append(ToolCall(id=block.id, name=block.name, arguments=block.input))

            # Extract usage
            usage = TokenUsage(
                prompt_tokens=response.usage.input_tokens,
                completion_tokens=response.usage.output_tokens,
                total_tokens=response.usage.input_tokens + response.usage.output_tokens,
                cost_usd=_cost_tracker.calculate_cost(
                    config.model_id, response.usage.input_tokens, response.usage.output_tokens
                ),
            )

            return GenerateResponse(
                content=content,
                tool_calls=tool_calls,
                usage=usage,
                provider_id=self.provider_id,
                model_id=config.model_id,
                latency_ms=latency,
                finish_reason=response.stop_reason,
            )

        except Exception as e:
            latency = (time.time() - start_time) * 1000
            status_code = None
            retryable = True

            if hasattr(e, "status_code"):
                status_code = e.status_code
                if status_code in (401, 403):
                    retryable = False

            raise ProviderError(self.provider_id, str(e), retryable=retryable, status_code=status_code) from e

    async def stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        config: GenerateConfig,
    ) -> AsyncIterator[StreamChunk]:
        """Stream response from Claude."""
        try:
            client = self._get_client()

            # Separate system message
            system_message = None
            chat_messages = []

            for msg in messages:
                if msg.get("role") == "system":
                    system_message = msg.get("content", "")
                else:
                    chat_messages.append(msg)

            request: dict[str, Any] = {
                "model": config.model_id,
                "messages": chat_messages,
                "max_tokens": config.max_tokens,
                "temperature": config.temperature,
                "stream": True,
            }

            if system_message:
                request["system"] = system_message

            if tools:
                request["tools"] = self._convert_tools_to_anthropic_format(tools)

            stream = await client.messages.create(**request)

            full_content = ""
            current_tool_call: dict[str, Any] | None = None

            async for event in stream:
                if event.type == "content_block_delta":
                    delta = event.delta

                    if delta.type == "text_delta":
                        full_content += delta.text
                        yield StreamChunk(delta=delta.text, provider_id=self.provider_id, model_id=config.model_id)

                    elif delta.type == "input_json_delta":
                        # Tool call argument streaming
                        if current_tool_call:
                            current_tool_call["arguments"] += delta.partial_json

                elif event.type == "content_block_start":
                    if event.content_block.type == "tool_use":
                        current_tool_call = {
                            "id": event.content_block.id,
                            "name": event.content_block.name,
                            "arguments": "",
                        }

                elif event.type == "content_block_stop":
                    if current_tool_call:
                        # Finalize tool call
                        try:
                            args = json.loads(current_tool_call["arguments"]) if current_tool_call["arguments"] else {}
                        except json.JSONDecodeError:
                            args = {}

                        tool_call = ToolCall(id=current_tool_call["id"], name=current_tool_call["name"], arguments=args)

                        yield StreamChunk(
                            delta="", tool_call_delta=tool_call, provider_id=self.provider_id, model_id=config.model_id
                        )
                        current_tool_call = None

            # Final chunk
            usage = self._make_usage(
                sum(len(m.get("content", "")) for m in messages) // 4, len(full_content) // 4, config.model_id
            )

            yield StreamChunk.final(
                provider_id=self.provider_id, model_id=config.model_id, usage=usage, finish_reason="stop"
            )

        except Exception as e:
            yield StreamChunk.final(provider_id=self.provider_id, model_id=config.model_id, error=str(e))


# =============================================================================
# Ollama Adapter
# =============================================================================


class OllamaAdapter(BaseAdapter):
    """Adapter for local Ollama models."""

    def __init__(
        self,
        base_url: str,
        model_id: str,
    ):
        super().__init__("ollama", model_id)
        self.base_url = base_url.rstrip("/")
        self.model_id = model_id

    async def _make_request(self, endpoint: str, data: dict[str, Any]) -> dict[str, Any]:
        """Make HTTP request to Ollama API."""
        import aiohttp

        url = f"{self.base_url}/api/{endpoint}"

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data, timeout=aiohttp.ClientTimeout(total=60.0)) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise ProviderError(self.provider_id, f"HTTP {resp.status}: {text}", retryable=resp.status >= 500)
                result: dict[str, Any] = await resp.json()
                return result

    async def _make_stream_request(self, endpoint: str, data: dict[str, Any]) -> AsyncIterator[dict[str, Any]]:
        """Make streaming HTTP request to Ollama API."""
        import aiohttp

        url = f"{self.base_url}/api/{endpoint}"

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data, timeout=aiohttp.ClientTimeout(total=60.0)) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise ProviderError(self.provider_id, f"HTTP {resp.status}: {text}", retryable=resp.status >= 500)

                async for raw_line in resp.content:
                    stripped_line = raw_line.strip()
                    if stripped_line:
                        try:
                            yield json.loads(stripped_line)
                        except json.JSONDecodeError:
                            continue

    async def generate(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        config: GenerateConfig,
    ) -> GenerateResponse:
        """Generate using Ollama."""
        start_time = time.time()

        try:
            # Ollama uses similar format to OpenAI
            request_data: dict[str, Any] = {
                "model": self.model_id,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": config.temperature,
                    "num_predict": config.max_tokens,
                },
            }

            if config.top_p is not None:
                request_data["options"]["top_p"] = config.top_p

            if tools:
                # Ollama tool support varies by model
                request_data["tools"] = self._convert_tools_to_openai_format(tools)

            response = await self._make_request("chat", request_data)

            latency = (time.time() - start_time) * 1000

            # Extract response
            message = response.get("message", {})
            content = message.get("content", "")

            # Check for tool calls in response
            tool_calls: list[ToolCall] = []
            if "tool_calls" in message:
                for tc in message["tool_calls"]:
                    tool_calls.append(
                        ToolCall(
                            id=tc.get("id", f"call_{len(tool_calls)}"),
                            name=tc.get("function", {}).get("name", ""),
                            arguments=tc.get("function", {}).get("arguments", {}),
                        )
                    )

            # Ollama doesn't always provide usage, estimate
            prompt_tokens = response.get("prompt_eval_count", sum(len(m.get("content", "")) for m in messages) // 4)
            completion_tokens = response.get("eval_count", len(content) // 4)

            usage = self._make_usage(prompt_tokens, completion_tokens, self.model_id)

            return GenerateResponse(
                content=content,
                tool_calls=tool_calls,
                usage=usage,
                provider_id=self.provider_id,
                model_id=self.model_id,
                latency_ms=latency,
                finish_reason="stop" if not response.get("done_reason") else response.get("done_reason"),
            )

        except Exception as e:
            latency = (time.time() - start_time) * 1000
            if isinstance(e, ProviderError):
                raise
            raise ProviderError(self.provider_id, str(e), retryable=True) from e

    async def stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        config: GenerateConfig,
    ) -> AsyncIterator[StreamChunk]:
        """Stream response from Ollama."""
        try:
            request_data: dict[str, Any] = {
                "model": self.model_id,
                "messages": messages,
                "stream": True,
                "options": {
                    "temperature": config.temperature,
                    "num_predict": config.max_tokens,
                },
            }

            if config.top_p is not None:
                request_data["options"]["top_p"] = config.top_p

            full_content = ""

            async for chunk in self._make_stream_request("chat", request_data):
                if "message" in chunk:
                    message = chunk["message"]
                    content = message.get("content", "")
                    if content:
                        full_content += content
                        yield StreamChunk(delta=content, provider_id=self.provider_id, model_id=self.model_id)

                # Check if done
                if chunk.get("done"):
                    # Final chunk with usage
                    prompt_tokens = chunk.get(
                        "prompt_eval_count", sum(len(m.get("content", "")) for m in messages) // 4
                    )
                    completion_tokens = chunk.get("eval_count", len(full_content) // 4)

                    usage = self._make_usage(prompt_tokens, completion_tokens, self.model_id)

                    yield StreamChunk.final(
                        provider_id=self.provider_id,
                        model_id=self.model_id,
                        usage=usage,
                        finish_reason=chunk.get("done_reason", "stop"),
                    )

        except Exception as e:
            yield StreamChunk.final(provider_id=self.provider_id, model_id=self.model_id, error=str(e))

    async def health_check(self) -> ProviderHealth:
        """Check Ollama health by listing models."""
        start = time.time()

        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/api/tags", timeout=aiohttp.ClientTimeout(total=10.0)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        models = [m.get("name") for m in data.get("models", [])]

                        if self.model_id in models or f"{self.model_id}:latest" in models:
                            latency = (time.time() - start) * 1000
                            self._health = ProviderHealth(
                                provider_id=self.provider_id, healthy=True, latency_ms=latency, last_checked=time.time()
                            )
                        else:
                            self._health = ProviderHealth(
                                provider_id=self.provider_id,
                                healthy=False,
                                latency_ms=(time.time() - start) * 1000,
                                error=f"Model {self.model_id} not found",
                                last_checked=time.time(),
                                consecutive_failures=self._health.consecutive_failures + 1,
                            )
                    else:
                        self._health = ProviderHealth(
                            provider_id=self.provider_id,
                            healthy=False,
                            latency_ms=(time.time() - start) * 1000,
                            error=f"HTTP {resp.status}",
                            last_checked=time.time(),
                            consecutive_failures=self._health.consecutive_failures + 1,
                        )
        except Exception as e:
            self._health = ProviderHealth(
                provider_id=self.provider_id,
                healthy=False,
                latency_ms=(time.time() - start) * 1000,
                error=str(e),
                last_checked=time.time(),
                consecutive_failures=self._health.consecutive_failures + 1,
            )

        return self._health


# =============================================================================
# Model Router
# =============================================================================


class ModelRouter:
    """
    Routes requests to LLM providers with automatic failover.

    Features:
    - Priority-ordered provider chain
    - Automatic failover on ProviderError
    - Background health checks
    - Cost tracking integration
    - Streaming support
    """

    def __init__(self, chain: list[ModelProvider], health_interval: float = 30.0, session_id: str = "default"):
        self.chain = chain
        self.health_interval = health_interval
        self.session_id = session_id
        self._health_status: dict[str, ProviderHealth] = {}
        self._health_task: asyncio.Task[Any] | None = None
        self._shutdown_event = asyncio.Event()

        log.info(f"ModelRouter initialized with {len(chain)} providers: {[p.provider_id for p in chain]}")

    async def start(self) -> None:
        """Start background health check loop."""
        if self._health_task is None and self.chain:
            self._shutdown_event.clear()
            self._health_task = asyncio.create_task(self._health_loop())
            log.info("Health check loop started")

    async def stop(self) -> None:
        """Stop background health check loop."""
        if self._health_task:
            self._shutdown_event.set()
            try:
                await asyncio.wait_for(self._health_task, timeout=5.0)
            except asyncio.TimeoutError:
                self._health_task.cancel()
            self._health_task = None
            log.info("Health check loop stopped")

    async def _health_loop(self) -> None:
        """Background task for health checks."""
        while not self._shutdown_event.is_set():
            for provider in self.chain:
                try:
                    health = await asyncio.wait_for(provider.health_check(), timeout=10.0)
                    self._health_status[provider.provider_id] = health

                    # Reset consecutive failures on healthy check
                    if health.healthy and health.consecutive_failures > 0:
                        health.consecutive_failures = 0

                except asyncio.TimeoutError:
                    self._health_status[provider.provider_id] = ProviderHealth(
                        provider_id=provider.provider_id,
                        healthy=False,
                        latency_ms=10000,
                        error="Health check timeout",
                        consecutive_failures=self._health_status.get(
                            provider.provider_id, ProviderHealth(provider.provider_id, True, 0)
                        ).consecutive_failures
                        + 1,
                    )
                except Exception as e:
                    self._health_status[provider.provider_id] = ProviderHealth(
                        provider_id=provider.provider_id,
                        healthy=False,
                        latency_ms=0,
                        error=str(e),
                        consecutive_failures=self._health_status.get(
                            provider.provider_id, ProviderHealth(provider.provider_id, True, 0)
                        ).consecutive_failures
                        + 1,
                    )

            try:
                await asyncio.wait_for(self._shutdown_event.wait(), timeout=self.health_interval)
            except asyncio.TimeoutError:
                pass

    def _get_healthy_providers(self) -> list[ModelProvider]:
        """Get list of healthy providers in priority order."""
        healthy = []
        for provider in self.chain:
            health = self._health_status.get(provider.provider_id)
            if health is None or health.is_healthy:
                healthy.append(provider)
        return healthy

    async def generate(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        config: GenerateConfig | None = None,
    ) -> GenerateResponse:
        """
        Generate response with automatic failover.

        Iterates through provider chain until one succeeds.
        Returns error response if all providers fail.
        """
        if not self.chain:
            return GenerateResponse.make_error("router", "No providers configured")

        providers_tried: list[str] = []
        last_error: Exception | None = None

        # Try each provider in order
        for provider in self._get_healthy_providers():
            providers_tried.append(provider.provider_id)

            try:
                response = await provider.generate(
                    messages, tools, config or GenerateConfig(model_id=getattr(provider, "model_id", "unknown"))
                )

                # Record usage for cost tracking
                if response.usage:
                    await _cost_tracker.record_usage(self.session_id, response.model_id, response.usage)

                log.info(f"Successfully generated using {provider.provider_id} ({response.latency_ms:.0f}ms)")
                return response

            except ProviderError as e:
                log.warning(f"Provider {provider.provider_id} failed: {e.message}")
                last_error = e

                # Update health status
                current_health = self._health_status.get(provider.provider_id)
                if current_health:
                    current_health.consecutive_failures += 1

                # Non-retryable errors skip to next immediately
                if not e.retryable:
                    log.error(f"Non-retryable error from {provider.provider_id}, skipping")
                    continue

            except Exception as e:
                log.error(f"Unexpected error from {provider.provider_id}: {e}")
                last_error = e

        # All providers exhausted
        error_msg = str(last_error) if last_error else "All providers exhausted"
        log.error(f"All providers failed. Tried: {providers_tried}")

        return GenerateResponse.make_error("router", f"All providers exhausted: {error_msg}")

    async def stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        config: GenerateConfig | None = None,
    ) -> AsyncIterator[StreamChunk]:
        """
        Stream response with automatic failover.

        If a provider fails mid-stream, tries next provider.
        """
        if not self.chain:
            yield StreamChunk.final("router", "unknown", error="No providers configured")
            return

        has_yielded = False
        providers_tried = []

        for provider in self._get_healthy_providers():
            providers_tried.append(provider.provider_id)

            try:
                full_content = ""
                full_tool_calls = []

                async for chunk in provider.stream(
                    messages, tools, config or GenerateConfig(model_id=getattr(provider, "model_id", "unknown"))
                ):
                    if chunk.is_final:
                        # Check if final chunk indicates error
                        if chunk.error:
                            log.warning(f"Provider {provider.provider_id} stream returned error: {chunk.error}")
                            if has_yielded:
                                # Cannot safely failover mid-stream
                                yield chunk  # Send the error chunk
                                return
                            break  # Try next provider

                        # Record final usage
                        if chunk.usage:
                            await _cost_tracker.record_usage(self.session_id, chunk.model_id, chunk.usage)

                        # Yield final chunk from successful provider
                        yield chunk
                        log.info(f"Stream completed using {provider.provider_id}")
                        return
                    else:
                        # Accumulate to check for failover safety
                        full_content += chunk.delta
                        if chunk.tool_call_delta:
                            full_tool_calls.append(chunk.tool_call_delta)

                        has_yielded = True
                        yield chunk
                else:
                    # Stream completed normally (no break)
                    log.info(f"Stream completed using {provider.provider_id}")
                    return

                # If we get here, provider returned error final chunk - continue to next
                if has_yielded:
                    # Already failed after yielding, don't try next provider (avoid double messages)
                    return

            except Exception as e:
                log.warning(f"Provider {provider.provider_id} stream failed: {e}")

                # Update health status
                current_health = self._health_status.get(provider.provider_id)
                if current_health:
                    current_health.consecutive_failures += 1

                if has_yielded:
                    # Already yielded content, don't retry (user has already seen some of this)
                    log.error(f"Provider {provider.provider_id} failed mid-stream. Aborting to avoid double output.")
                    yield StreamChunk.final(
                        "router", provider.provider_id, error=f"Stream failed mid-response: {str(e)}"
                    )
                    return

                # Continue to next provider only if nothing was yielded
                continue

        # All providers exhausted
        log.error(f"All providers failed in stream. Tried: {providers_tried}")
        yield StreamChunk.final("router", "unknown", error=f"All providers exhausted. Tried: {providers_tried}")

    def get_chain_status(self) -> list[ProviderHealth]:
        """Get current health status of all providers."""
        return list(self._health_status.values())

    def get_cost_stats(self) -> dict[str, Any]:
        """Get cost statistics for current session."""
        return {
            "session_id": self.session_id,
            "session_cost_usd": _cost_tracker.get_session_cost(self.session_id),
            "total_cost_usd": _cost_tracker.get_total_cost(),
            "by_model": _cost_tracker.get_stats()["by_model"],
        }


# =============================================================================
# Factory Functions
# =============================================================================


def create_provider_from_config(config: dict[str, Any]) -> ModelProvider:
    """Create a provider from configuration dict."""
    provider_type = config.get("provider", "").lower()

    if provider_type == "gemini":
        return GeminiAdapter(
            project_id=config["project_id"], location=config.get("location", "us-central1"), model_id=config["model"]
        )

    elif provider_type == "openai":
        api_key = config.get("api_key") or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI adapter requires api_key or OPENAI_API_KEY env var")
        return OpenAIAdapter(api_key=api_key, model_id=config["model"], base_url=config.get("base_url"))

    elif provider_type == "anthropic":
        api_key = config.get("api_key") or os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("Anthropic adapter requires api_key or ANTHROPIC_API_KEY env var")
        return AnthropicAdapter(api_key=api_key, model_id=config["model"])

    elif provider_type == "ollama":
        return OllamaAdapter(base_url=config.get("base_url", "http://localhost:11434"), model_id=config["model"])

    else:
        raise ValueError(f"Unknown provider type: {provider_type}")


def create_router_from_config(config_path: Path | None = None, session_id: str = "default") -> ModelRouter:
    """
    Create a ModelRouter from YAML/JSON config file.

    Config format:
    ```yaml
    model_chain:
      - provider: gemini
        model: gemini-2.0-flash-exp
        project_id: ${GCP_PROJECT_ID}
        priority: 1
      - provider: openai
        model: gpt-4o
        api_key: ${OPENAI_API_KEY}
        priority: 2
    health_check_interval: 30
    ```
    """
    import yaml

    if config_path is None:
        config_path = Path("config/model_chain.yaml")

    chain: list[ModelProvider] = []

    if not config_path.exists():
        # Create default config with just Gemini
        log.warning(f"Config not found at {config_path}, using default Gemini config")

        # Try to create Gemini provider if credentials available
        project_id = os.environ.get("GCP_PROJECT_ID")
        if project_id:
            try:
                chain.append(
                    GeminiAdapter(
                        project_id=project_id,
                        location=os.environ.get("GCP_LOCATION", "us-central1"),
                        model_id=os.environ.get("ORACLE_MODEL_ID", "gemini-2.0-flash-exp"),
                    )
                )
            except Exception as e:
                log.warning(f"Failed to create default Gemini adapter: {e}")

        if not chain:
            log.error("No providers could be configured")

        return ModelRouter(chain, session_id=session_id)

    # Load config
    with open(config_path) as f:
        config = yaml.safe_load(f)

    # Resolve environment variables
    def resolve_env(value: Any) -> Any:
        if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
            env_var = value[2:-1]
            return os.environ.get(env_var, value)
        return value

    def resolve_dict(d: dict[str, Any]) -> dict[str, Any]:
        return {k: resolve_env(v) for k, v in d.items()}

    # Build provider chain
    chain = []
    for provider_config in config.get("model_chain", []):
        try:
            resolved = resolve_dict(provider_config)
            provider = create_provider_from_config(resolved)
            chain.append(provider)
            log.info(f"Added {provider.provider_id} to chain")
        except Exception as e:
            log.warning(f"Failed to create provider {provider_config.get('provider')}: {e}")

    # Sort by priority if specified
    chain.sort(key=lambda p: getattr(p, "priority", 99))

    health_interval = config.get("health_check_interval", 30.0)

    return ModelRouter(chain, health_interval, session_id)
