import os
import json
import sqlite3
import pika
import time
import logging

# Configure Logging
logger = logging.getLogger(__name__)

# Constants (mirroring main.py environment)
RABBITMQ_HOST = os.environ.get("RABBITMQ_HOST", "localhost")
RABBITMQ_QUEUE = os.environ.get("RABBITMQ_QUEUE", "task_queue")
DB_PATH = os.environ.get("AGENT_DB_PATH", "agent_state.db")


def check_calendar(date: str) -> str:
    """Check the user's calendar for a specific date."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Ensure table exists (idempotent)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS calendar (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                event TEXT NOT NULL
            )
        """)

        cursor.execute("SELECT event FROM calendar WHERE date = ?", (date,))
        rows = cursor.fetchall()
        conn.close()

        if rows:
            events = [row[0] for row in rows]
            return f"Events on {date}: " + ", ".join(events)
        return f"No events scheduled for {date}."
    except Exception as e:
        logger.error(f"Failed to access calendar database: {e}")
        return f"Error accessing calendar: {e}"


def send_email(to: str, subject: str, body: str) -> str:
    """Send an email to a recipient via RabbitMQ queue."""
    logger.info("Skill Call: send_email", extra={"to": to, "subject": subject})
    message = json.dumps({"type": "email", "to": to, "subject": subject, "body": body})

    params = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        heartbeat=600,
        blocked_connection_timeout=5.0,
        socket_timeout=5.0,
    )

    last_error: Exception | None = None
    for attempt in range(3):
        try:
            connection = pika.BlockingConnection(params)
            channel = connection.channel()
            channel.queue_declare(queue=RABBITMQ_QUEUE, durable=True)
            channel.basic_publish(
                exchange="",
                routing_key=RABBITMQ_QUEUE,
                body=message,
                properties=pika.BasicProperties(delivery_mode=2),
            )
            connection.close()
            logger.info(
                "Email queued via RabbitMQ",
                extra={"to": to, "subject": subject, "attempt": attempt + 1},
            )
            return f"Email to {to} has been queued for delivery."
        except Exception as exc:
            last_error = exc
            logger.error(
                "RabbitMQ publish failed",
                extra={"error": str(exc), "attempt": attempt + 1},
            )
            time.sleep(0.5)

    return f"Failed to queue email after retries. Error: {last_error}"


# Oracle 5.0 Skill Definition Structure
TOOLS = [
    {
        "name": "check_calendar",
        "description": "Check the user's calendar for a specific date.",
        "parameters": {
            "type": "object",
            "properties": {"date": {"type": "string", "description": "The date to check (YYYY-MM-DD)"}},
            "required": ["date"],
        },
        "handler": check_calendar,
    },
    {
        "name": "send_email",
        "description": "Send an email to a recipient.",
        "parameters": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Recipient email address"},
                "subject": {"type": "string", "description": "Email subject"},
                "body": {"type": "string", "description": "Email body"},
            },
            "required": ["to", "subject", "body"],
        },
        "handler": send_email,
    },
]
