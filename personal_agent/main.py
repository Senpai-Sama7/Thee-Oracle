"""
personal_agent/main.py — FastAPI service fronting Vertex AI Gemini.

Endpoints
---------
POST /webhook   Dialogflow CX / Agent Builder fulfillment
POST /chat      Direct conversational endpoint
GET  /health    Liveness probe
GET  /metrics   Prometheus text metrics

Integrations
------------
- Vertex AI Gemini (google-genai SDK) with AsyncTokenBucket rate limiting
- CircuitBreaker + CircuitBreakerStore for Gemini and RabbitMQ calls
- ResultStore for interaction persistence (SQLite WAL)
- RabbitMQ publish for async email side-effects
- image_base64 support on /webhook and /chat
"""

from __future__ import annotations

import base64
import json
import logging
import os
import sqlite3
import time
import uuid
from dataclasses import dataclass
from typing import Any

from orchestrator import (
    AsyncTokenBucket,
    CircuitBreaker,
    CircuitBreakerStore,
    MetricsRegistry,
    PrometheusExporter,
    ResultStore,
    wrap_with_circuit_breaker,
)

log = logging.getLogger("personal_agent")

# ---------------------------------------------------------------------------
# Persistence — SQLite WAL, single shared connection
# ---------------------------------------------------------------------------

_db_path = os.environ.get("PERSONAL_AGENT_DB", "data/personal_agent/agent_state.db")
_conn = sqlite3.connect(_db_path, check_same_thread=False)
_conn.execute("PRAGMA journal_mode=WAL")
_conn.execute("PRAGMA synchronous=NORMAL")
_conn.row_factory = sqlite3.Row

result_store = ResultStore(_conn)
cb_store = CircuitBreakerStore(_conn)

# ---------------------------------------------------------------------------
# Rate limiter — 10 req/s burst of 20 for Gemini calls
# ---------------------------------------------------------------------------

_gemini_rate = float(os.environ.get("GEMINI_RATE", "10"))
_gemini_burst = float(os.environ.get("GEMINI_BURST", "20"))
gemini_bucket = AsyncTokenBucket(rate=_gemini_rate, capacity=_gemini_burst)

# ---------------------------------------------------------------------------
# Circuit breakers
# ---------------------------------------------------------------------------

vertex_ai_cb = CircuitBreaker(
    task_type="gemini_generate",
    failure_threshold=3,
    recovery_timeout_s=60.0,
    success_threshold=2,
)
rabbitmq_cb = CircuitBreaker(
    task_type="rabbitmq_publish",
    failure_threshold=5,
    recovery_timeout_s=30.0,
    success_threshold=2,
)

# Restore persisted state so breakers survive restarts
cb_store.restore_into(vertex_ai_cb)
cb_store.restore_into(rabbitmq_cb)

# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

metrics = MetricsRegistry()
_exporter = PrometheusExporter(namespace="personal_agent")


# ---------------------------------------------------------------------------
# Tool declarations — SDK-independent shim
# ---------------------------------------------------------------------------


@dataclass
class _Param:
    name: str
    type: str
    description: str
    required: bool = True


class _FunctionDeclaration:
    """Mirrors the Vertex AI FunctionDeclaration interface for test portability."""

    def __init__(self, name: str, description: str, parameters: list[_Param]) -> None:
        self.name = name
        self.description = description
        self._parameters = parameters

    def to_dict(self) -> dict[str, Any]:
        props: dict[str, Any] = {}
        required: list[str] = []
        for p in self._parameters:
            props[p.name] = {"type": p.type, "description": p.description}
            if p.required:
                required.append(p.name)
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {"type": "object", "properties": props, "required": required},
        }


check_calendar_func = _FunctionDeclaration(
    name="check_calendar",
    description="Check the user's calendar for a given date and return scheduled events.",
    parameters=[_Param("date", "string", "Date to check in YYYY-MM-DD format")],
)

send_email_func = _FunctionDeclaration(
    name="send_email",
    description="Send an email to a recipient via the async email worker.",
    parameters=[
        _Param("to", "string", "Recipient email address"),
        _Param("subject", "string", "Email subject line"),
        _Param("body", "string", "Email body text"),
    ],
)

# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------


class _Tool:
    def __init__(self, fn: Any) -> None:
        self._fn = fn

    def invoke(self, args: dict[str, Any]) -> str:
        return self._fn(**args)


def _init_calendar_db():
    import sqlite3
    import datetime
    from pathlib import Path

    db_path = Path("data/calendar.db")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                description TEXT NOT NULL
            )
        """)
        cur = conn.execute("SELECT COUNT(*) FROM events")
        if cur.fetchone()[0] == 0:
            today = datetime.date.today().strftime("%Y-%m-%d")
            conn.execute(
                "INSERT INTO events (date, time, description) VALUES (?, ?, ?)", (today, "10:00", "Project Sync")
            )
            conn.execute(
                "INSERT INTO events (date, time, description) VALUES (?, ?, ?)", (today, "13:00", "Lunch with Team")
            )
            conn.execute(
                "INSERT INTO events (date, time, description) VALUES (?, ?, ?)", ("2023-10-27", "10 AM", "meeting")
            )
            conn.execute(
                "INSERT INTO events (date, time, description) VALUES (?, ?, ?)", ("2023-10-27", "1 PM", "lunch")
            )
            conn.commit()


_init_calendar_db()


def _check_calendar_impl(date: str) -> str:
    try:
        import sqlite3
        from pathlib import Path

        db_path = Path("data/calendar.db")
        if not db_path.exists():
            return f"On {date}, you have no events scheduled."
        with sqlite3.connect(db_path) as conn:
            cur = conn.execute("SELECT time, description FROM events WHERE date = ? ORDER BY time", (date,))
            events = cur.fetchall()

        if not events:
            return f"On {date}, you have no events scheduled."

        schedule = " and ".join([f"a {desc} at {time}" for time, desc in events])
        return f"On {date}, you have {schedule}."
    except Exception as e:
        log.error(f"Failed to access calendar database: {e}")
        return f"Error accessing calendar: {e}"


def _send_email_impl(to: str, subject: str, body: str) -> str:
    """Publish to RabbitMQ email_tasks queue, guarded by rabbitmq_cb."""
    try:
        import pika  # type: ignore[import]

        url = os.environ.get("RABBITMQ_URL", "amqp://admin:oracle_pass_2026@localhost:5672/")

        def _publish() -> str:
            conn = pika.BlockingConnection(pika.URLParameters(url))
            ch = conn.channel()
            ch.queue_declare(queue="email_tasks", durable=True)
            msg_id = str(uuid.uuid4())
            ch.basic_publish(
                exchange="",
                routing_key="email_tasks",
                body=json.dumps(
                    {
                        "type": "email",
                        "id": msg_id,
                        "to": to,
                        "subject": subject,
                        "body": body,
                        "submitted_at": time.time(),
                    }
                ),
                properties=pika.BasicProperties(
                    delivery_mode=2,
                    message_id=msg_id,
                    content_type="application/json",
                ),
            )
            conn.close()
            rabbitmq_cb.record_success()
            cb_store.save(rabbitmq_cb)
            return f"Email to {to!r} queued for delivery (id={msg_id})."

        if not rabbitmq_cb.should_attempt():
            return "Email queuing unavailable (circuit open). Will retry later."
        return _publish()

    except Exception as exc:
        rabbitmq_cb.record_failure()
        cb_store.save(rabbitmq_cb)
        log.error("rabbitmq_publish_failed", extra={"error": str(exc)})
        return f"Email send failed: {exc}"


check_calendar = _Tool(_check_calendar_impl)
send_email = _Tool(_send_email_impl)


# ---------------------------------------------------------------------------
# Core LLM dispatch
# ---------------------------------------------------------------------------


def _dispatch_tool(name: str, args: dict[str, Any]) -> str:
    if name == "check_calendar":
        return check_calendar.invoke(args)
    if name == "send_email":
        return send_email.invoke(args)
    return f"Unknown tool: {name!r}"


def _persist_interaction(
    session_id: str,
    user_input: str,
    tag: str,
    tool_name: str | None,
    result: str,
    has_image: bool = False,
) -> str:
    task_id = f"{session_id}_{int(time.time() * 1000)}"
    result_store.store(
        task_id,
        {
            "session_id": session_id,
            "user_input": user_input,
            "tag": tag,
            "tool_executed": tool_name,
            "result": result,
            "has_image": has_image,
            "timestamp": time.time(),
        },
    )
    metrics.inc("interactions_total", labels={"tag": tag, "tool": tool_name or "none"})
    return task_id


async def _call_gemini(
    user_input: str,
    image_b64: str | None = None,
) -> Any:
    """
    Call Vertex AI Gemini with rate limiting and circuit breaking.
    Returns the raw SDK response object.
    Raises RuntimeError if circuit is open or rate limit exceeded.
    """
    from google import genai  # type: ignore[import]
    from google.genai import types  # type: ignore[import]

    # Rate limit — raises RateLimitError after 5s wait
    await gemini_bucket.acquire(timeout_s=5.0)

    project = os.environ.get("GCP_PROJECT_ID", "")
    location = os.environ.get("GCP_LOCATION", "us-central1")
    model_id = os.environ.get("PERSONAL_AGENT_MODEL", "gemini-2.0-flash-exp")

    client = genai.Client(vertexai=True, project=project, location=location)

    tools = [
        types.Tool(
            function_declarations=[
                types.FunctionDeclaration(**check_calendar_func.to_dict()),
                types.FunctionDeclaration(**send_email_func.to_dict()),
            ]
        )
    ]

    # Build content parts — text + optional image
    parts: list[Any] = [types.Part.from_text(text=user_input)]
    if image_b64:
        image_bytes = base64.b64decode(image_b64)
        parts.append(types.Part.from_bytes(data=image_bytes, mime_type="image/png"))

    contents = [types.Content(role="user", parts=parts)]

    async def _generate() -> Any:
        return client.models.generate_content(
            model=model_id,
            contents=contents,
            config=types.GenerateContentConfig(tools=tools),
        )

    return await wrap_with_circuit_breaker(vertex_ai_cb, _generate, store=cb_store)


async def handle_input(
    user_input: str,
    session_id: str,
    tag: str = "default",
    image_b64: str | None = None,
) -> str:
    """
    Main entry point for both /webhook and /chat.
    Returns the reply string to send back to the caller.
    """
    start = time.monotonic()
    has_image = image_b64 is not None

    try:
        response = await _call_gemini(user_input, image_b64)
        elapsed = time.monotonic() - start
        metrics.observe("gemini_latency_seconds", elapsed)

        # Tool call path
        if response.candidates and response.candidates[0].function_calls:
            fc = response.candidates[0].function_calls[0]
            tool_result = _dispatch_tool(fc.name, dict(fc.args))
            _persist_interaction(session_id, user_input, tag, fc.name, tool_result, has_image)
            metrics.record_task_latency(elapsed, status="tool_call")
            return f"Tool '{fc.name}' executed. Result: {tool_result}"

        # Plain text path
        text = response.text or ""
        _persist_interaction(session_id, user_input, tag, None, text, has_image)
        metrics.record_task_latency(elapsed, status="text")
        return text

    except Exception as exc:
        elapsed = time.monotonic() - start
        metrics.inc("errors_total", labels={"tag": tag})
        log.error("handle_input_error", extra={"session_id": session_id, "error": str(exc)})
        # User-safe message; full detail is in logs
        return "I'm having trouble processing that right now. Please try again shortly."


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

try:
    from fastapi import FastAPI, Request, HTTPException
    from fastapi.responses import JSONResponse, PlainTextResponse

    app = FastAPI(title="Personal Agent", version="1.0.0")

    @app.get("/health")
    async def health() -> JSONResponse:
        return JSONResponse(
            {
                "status": "ok",
                "vertex_ai_cb": vertex_ai_cb.state.value,
                "rabbitmq_cb": rabbitmq_cb.state.value,
                "gemini_tokens_available": round(gemini_bucket.available, 2),
            }
        )

    @app.get("/metrics")
    async def prometheus_metrics() -> PlainTextResponse:
        return PlainTextResponse(_exporter.export(metrics), media_type="text/plain; version=0.0.4")

    @app.post("/webhook")
    async def webhook(request: Request) -> JSONResponse:
        """Dialogflow CX / Agent Builder fulfillment endpoint."""
        body = await request.json()
        user_input: str = body.get("text", "")
        session_info: dict[str, Any] = body.get("sessionInfo", {})
        session_id: str = session_info.get("session") or f"session_{uuid.uuid4().hex[:8]}"
        tag: str = body.get("fulfillmentInfo", {}).get("tag", "default")
        image_b64: str | None = body.get("image_base64")

        if not user_input:
            raise HTTPException(status_code=400, detail="'text' field is required")

        reply = await handle_input(user_input, session_id, tag, image_b64)

        return JSONResponse(
            {
                "fulfillmentResponse": {"messages": [{"text": {"text": [reply]}}]},
                "sessionInfo": {"parameters": session_info.get("parameters", {})},
            }
        )

    @app.post("/chat")
    async def chat(request: Request) -> JSONResponse:
        """Direct conversational endpoint."""
        body = await request.json()
        message: str = body.get("message", "")
        thread_id: str = body.get("thread_id") or f"thread_{uuid.uuid4().hex[:8]}"
        image_b64: str | None = body.get("image_base64")

        if not message:
            raise HTTPException(status_code=400, detail="'message' field is required")

        reply = await handle_input(message, thread_id, "chat", image_b64)
        return JSONResponse({"thread_id": thread_id, "response": reply})

except ImportError:
    app = None  # type: ignore[assignment]
    log.warning("FastAPI not installed — HTTP endpoints unavailable")


# ---------------------------------------------------------------------------
# Standalone entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn  # type: ignore[import]

    uvicorn.run(
        "personal_agent.main:app",
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", "8000")),
        reload=os.environ.get("RELOAD", "false").lower() == "true",
    )
