"""
email_worker/main.py — RabbitMQ consumer that sends emails via SMTP.

Architecture (design §5)
------------------------
Each message is treated as an orchestrator Task:
  id          = RabbitMQ message_id (or generated UUID)
  type        = "send_email"
  workflow_id = session_id from the originating personal agent request
  status      = PENDING → RUNNING → COMPLETED | FAILED | DEAD_LETTER

Retry strategy
--------------
- Up to MAX_RETRIES attempts with exponential backoff (2^n seconds, cap 60s)
- On final failure the message is nacked to the dead-letter exchange (DLX)
- All outcomes persisted to ResultStore for observability

Environment variables
---------------------
RABBITMQ_URL        amqp://admin:pass@host:5672/   (default: local dev creds)
EMAIL_QUEUE         queue to consume (default: email_tasks)
DLX_QUEUE           dead-letter queue name (default: email_tasks.dlq)
SMTP_HOST           SMTP server hostname
SMTP_PORT           SMTP port (default: 587)
SMTP_USER           SMTP username
SMTP_PASSWORD       SMTP password
SMTP_FROM           From address
SMTP_USE_TLS        true/false (default: true)
WORKER_DB           path to SQLite DB (default: data/personal_agent/agent_state.db)
MAX_RETRIES         per-message retry limit (default: 3)
PREFETCH_COUNT      RabbitMQ QoS prefetch (default: 1)
"""

from __future__ import annotations

import json
import logging
import os
import smtplib
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from orchestrator import ResultStore, Task

log = logging.getLogger("email_worker")
logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

RABBITMQ_URL = os.environ.get("RABBITMQ_URL", "amqp://admin:oracle_pass_2026@localhost:5672/")
EMAIL_QUEUE = os.environ.get("EMAIL_QUEUE", "email_tasks")
DLX_QUEUE = os.environ.get("DLX_QUEUE", "email_tasks.dlq")
WORKER_DB = os.environ.get("WORKER_DB", "data/personal_agent/agent_state.db")
MAX_RETRIES = int(os.environ.get("MAX_RETRIES", "3"))
PREFETCH_COUNT = int(os.environ.get("PREFETCH_COUNT", "1"))

SMTP_HOST = os.environ.get("SMTP_HOST", "localhost")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_FROM = os.environ.get("SMTP_FROM", "agent@example.com")
SMTP_USE_TLS = os.environ.get("SMTP_USE_TLS", "true").lower() == "true"


_conn = sqlite3.connect(WORKER_DB, check_same_thread=False)
_conn.execute("PRAGMA journal_mode=WAL")
_conn.execute("PRAGMA synchronous=NORMAL")
_conn.row_factory = sqlite3.Row
result_store = ResultStore(_conn)


class _TaskStore:
    """Minimal TaskStoreLike backed by ResultStore for email tasks."""

    def upsert(self, task: Task) -> None:
        result_store.store(
            f"task:{task.id}",
            {
                "id": task.id,
                "type": task.type,
                "status": task.status.value,
                "workflow_id": task.workflow_id,
                "payload": task.payload,
                "retry_count": task.retry_count,
                "error": task.error,
                "created_at": task.created_at,
                "started_at": task.started_at,
                "completed_at": task.completed_at,
            },
        )


task_store = _TaskStore()

# ---------------------------------------------------------------------------
# Email command model
# ---------------------------------------------------------------------------


@dataclass
class EmailCommand:
    id: str
    to: str
    subject: str
    body: str
    workflow_id: str | None = None
    submitted_at: float = field(default_factory=time.time)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EmailCommand":
        missing = [f for f in ("to", "subject", "body") if not data.get(f)]
        if missing:
            raise ValueError(f"EmailCommand missing required fields: {missing}")
        return cls(
            id=data.get("id") or str(uuid.uuid4()),
            to=data["to"],
            subject=data["subject"],
            body=data["body"],
            workflow_id=data.get("workflow_id") or data.get("session_id"),
            submitted_at=data.get("submitted_at", time.time()),
        )


# ---------------------------------------------------------------------------
# SMTP sender
# ---------------------------------------------------------------------------


def send_smtp(cmd: EmailCommand) -> None:
    """Send a single email via SMTP. Raises on any failure."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = cmd.subject
    msg["From"] = SMTP_FROM
    msg["To"] = cmd.to
    msg["Message-ID"] = f"<{cmd.id}@personal-agent>"
    msg.attach(MIMEText(cmd.body, "plain"))

    if SMTP_USE_TLS:
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15)
        server.ehlo()
        server.starttls()
    else:
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15)

    try:
        if SMTP_USER and SMTP_PASSWORD:
            server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_FROM, [cmd.to], msg.as_string())
        log.info("email_sent", extra={"id": cmd.id, "to": cmd.to, "subject": cmd.subject})
    finally:
        server.quit()


# ---------------------------------------------------------------------------
# Message handler
# ---------------------------------------------------------------------------


def on_message(ch: Any, method: Any, properties: Any, body: bytes) -> None:
    """
    RabbitMQ on_message callback.

    Flow:
      1. Parse body → EmailCommand (reject malformed messages immediately)
      2. Create Task, mark RUNNING, persist
      3. Attempt send_smtp with exponential backoff up to MAX_RETRIES
      4. On success: mark COMPLETED, ack
      5. On final failure: mark DEAD_LETTER, nack (routes to DLX)
    """
    # --- Parse ---
    try:
        data = json.loads(body)
        if data.get("type") != "email":
            log.warning("unknown_message_type", extra={"type": data.get("type")})
            ch.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
            return
        cmd = EmailCommand.from_dict(data)
    except (json.JSONDecodeError, ValueError) as exc:
        log.error("malformed_message", extra={"error": str(exc), "body": body[:200]})
        ch.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
        return

    # --- Create orchestrator Task ---
    task = Task(
        id=cmd.id,
        type="send_email",
        workflow_id=cmd.workflow_id,
        payload={"to": cmd.to, "subject": cmd.subject},
        max_retries=MAX_RETRIES,
    )
    task.mark_running()
    task_store.upsert(task)
    log.info("email_task_started", extra={"id": cmd.id, "to": cmd.to})

    # --- Retry loop ---
    last_error: str = ""
    for attempt in range(MAX_RETRIES + 1):
        try:
            send_smtp(cmd)
            task.mark_completed()
            task_store.upsert(task)
            ch.basic_ack(delivery_tag=method.delivery_tag)
            log.info("email_task_completed", extra={"id": cmd.id, "attempts": attempt + 1})
            return
        except Exception as exc:
            last_error = str(exc)
            task.retry_count = attempt + 1
            log.warning(
                "email_send_attempt_failed",
                extra={"id": cmd.id, "attempt": attempt + 1, "error": last_error},
            )
            if attempt < MAX_RETRIES:
                delay = task.next_retry_delay()
                log.info("email_retry_backoff", extra={"id": cmd.id, "delay_s": delay})
                time.sleep(delay)

    # --- Dead letter ---
    task.mark_dead_letter(last_error)
    task_store.upsert(task)
    log.error(
        "email_task_dead_lettered",
        extra={"id": cmd.id, "to": cmd.to, "error": last_error, "attempts": MAX_RETRIES + 1},
    )
    # nack without requeue — RabbitMQ routes to DLX if configured
    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


# ---------------------------------------------------------------------------
# Worker loop — self-healing connection with exponential backoff
# ---------------------------------------------------------------------------


def _declare_queues(ch: Any) -> None:
    """Declare main queue with DLX binding, and the dead-letter queue."""
    # Dead-letter queue (no TTL — messages stay until manually processed)
    ch.queue_declare(queue=DLX_QUEUE, durable=True)

    # Main queue — messages that exhaust retries route to DLX
    ch.queue_declare(
        queue=EMAIL_QUEUE,
        durable=True,
        arguments={
            "x-dead-letter-exchange": "",
            "x-dead-letter-routing-key": DLX_QUEUE,
        },
    )
    ch.basic_qos(prefetch_count=PREFETCH_COUNT)
    ch.basic_consume(queue=EMAIL_QUEUE, on_message_callback=on_message)


def start_worker() -> None:
    """
    Self-healing consumer loop.
    Reconnects on AMQP errors with exponential backoff (2s → 64s).
    Exits cleanly on KeyboardInterrupt.
    """
    import pika  # type: ignore[import]
    from pika.exceptions import AMQPConnectionError, ConnectionClosedByBroker

    retry_count = 0
    max_reconnect = 10

    while True:
        try:
            log.info("connecting_to_rabbitmq", extra={"url": RABBITMQ_URL.split("@")[-1]})
            params = pika.URLParameters(RABBITMQ_URL)
            params.heartbeat = 600
            params.blocked_connection_timeout = 30
            connection = pika.BlockingConnection(params)
            channel = connection.channel()
            _declare_queues(channel)
            retry_count = 0  # reset on successful connect
            log.info("email_worker_ready", extra={"queue": EMAIL_QUEUE})
            channel.start_consuming()

        except KeyboardInterrupt:
            log.info("email_worker_shutdown")
            break

        except (AMQPConnectionError, ConnectionClosedByBroker) as exc:
            retry_count += 1
            if retry_count > max_reconnect:
                log.error("email_worker_max_reconnects_exceeded", extra={"error": str(exc)})
                break
            delay = min(2**retry_count, 64)
            log.warning(
                "rabbitmq_reconnect",
                extra={"attempt": retry_count, "delay_s": delay, "error": str(exc)},
            )
            time.sleep(delay)

        except Exception as exc:
            retry_count += 1
            delay = min(2**retry_count, 64)
            log.error("email_worker_unexpected_error", extra={"error": str(exc), "delay_s": delay})
            time.sleep(delay)


if __name__ == "__main__":
    start_worker()
