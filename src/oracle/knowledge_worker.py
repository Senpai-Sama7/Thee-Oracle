import pika
import json
import os
import subprocess
import urllib.request
import time
from typing import Any, Dict, cast
from pika.exceptions import AMQPConnectionError, ConnectionClosedByBroker


def load_env() -> Dict[str, str]:
    """Parses the local .env file for GCP project and Discovery Engine IDs."""
    env = {}
    try:
        with open(".env") as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    k, v = line.strip().split("=", 1)
                    env[k] = v.strip('"')
    except FileNotFoundError:
        print("[!] Error: .env file not found in Project Root.")
    return env


def get_token() -> str:
    """Retrieves an active OAuth2 access token via gcloud ADC."""
    return subprocess.check_output(["gcloud", "auth", "print-access-token"], text=True).strip()


def discovery_engine_search(query: str) -> Dict[str, Any]:
    """Executes a semantic search against the provisioned Discovery Engine Data Store."""
    env = load_env()
    url = f"https://discoveryengine.googleapis.com/v1/projects/{env['GCP_PROJECT_NUMBER']}/locations/global/collections/default_collection/engines/{env['DISCOVERY_ENGINE_ID']}/servingConfigs/default_search:search"

    headers = {
        "Authorization": f"Bearer {get_token()}",
        "Content-Type": "application/json",
        "X-Goog-User-Project": env["GCP_PROJECT_ID"],
    }

    # Payload configured for basic retrieval; summarySpec can be added for LLM answers
    payload = json.dumps({"query": query, "pageSize": 3}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode("utf-8"))
            return cast(Dict[str, Any], result)
    except Exception as e:
        return {"error": str(e)}


def on_request(ch: Any, method: Any, props: Any, body: bytes) -> None:
    """Enhanced callback with comprehensive error handling and poison pill protection."""
    try:
        request = json.loads(body)
        query = request.get("query")
        print(f"[*] Processing Knowledge Request: {query}")

        # Validate request structure
        if not query or not isinstance(query, str):
            print(f"[!] Invalid request format: {request}")
            # Reject malformed request to prevent processing errors
            ch.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
            return

        # Execute the RAG lookup from Memory
        result = discovery_engine_search(query)

        # Validate result before sending
        if not isinstance(result, dict):
            print(f"[!] Invalid result format: {type(result)}")
            result = {"error": "Internal processing error", "query": query}

        # Dispatch result back to unique callback queue defined by requester
        ch.basic_publish(
            exchange="",
            routing_key=props.reply_to,
            properties=pika.BasicProperties(correlation_id=props.correlation_id),
            body=json.dumps(result),
        )

        # Acknowledge completion to clear task from RabbitMQ
        ch.basic_ack(delivery_tag=method.delivery_tag)
        print("[+] Task Complete. Result Sent.")

    except json.JSONDecodeError as e:
        print(f"[!] JSON decode error: {e}")
        # Send error response but still acknowledge to prevent requeue
        error_response = {"error": f"JSON decode error: {e}", "query": "unknown"}
        ch.basic_publish(
            exchange="",
            routing_key=props.reply_to,
            properties=pika.BasicProperties(correlation_id=props.correlation_id),
            body=json.dumps(error_response),
        )
        ch.basic_ack(delivery_tag=method.delivery_tag)

    except Exception as e:
        print(f"[!] Critical processing error: {e}")
        # Always acknowledge to prevent infinite requeue loops
        ch.basic_ack(delivery_tag=method.delivery_tag)


def start_worker() -> None:
    """Self-Healing Connection Loop with comprehensive error recovery."""
    retry_count = 0
    max_retries = 10
    base_delay = 2  # Start with 2 seconds, exponential backoff

    while True:
        try:
            print(f"[*] Establishing Nervous System Connection (RabbitMQ) - Attempt {retry_count + 1}")

            # Load credentials from environment (never hardcode)
            env = load_env()
            rmq_host = os.environ.get("RABBITMQ_HOST", env.get("RABBITMQ_HOST", "localhost"))
            rmq_user = os.environ.get("RABBITMQ_USER", env.get("RABBITMQ_USER", "guest"))
            rmq_pass = os.environ.get("RABBITMQ_PASS", env.get("RABBITMQ_PASS", "guest"))

            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=rmq_host,
                    credentials=pika.PlainCredentials(rmq_user, rmq_pass),
                    heartbeat=600,  # Extended heartbeat for long LLM operations
                    blocked_connection_timeout=30,  # Quick failure detection
                    connection_attempts=3,  # Connection retry attempts
                    retry_delay=base_delay * (2 ** min(retry_count, 5)),  # Exponential backoff
                )
            )
            channel = connection.channel()

            # Declare durable task queue with enhanced parameters
            channel.queue_declare(queue="knowledge_requests", durable=True)
            channel.basic_qos(prefetch_count=1)  # Fair dispatch and credit protection

            # Set up consumer with enhanced error handling
            channel.basic_consume(queue="knowledge_requests", on_message_callback=on_request)

            print("[*] Knowledge Worker LIVE. Awaiting requests...")
            print(f"[*] Connection parameters: heartbeat=600s, retry_delay={base_delay * (2 ** min(retry_count, 5))}s")

            # Start consuming with blocking mode
            channel.start_consuming()

        except (AMQPConnectionError, ConnectionClosedByBroker) as e:
            retry_count += 1
            if retry_count >= max_retries:
                print(f"[!] CRITICAL: Max retries ({max_retries}) reached. Manual intervention required.")
                print(f"[!] Last error: {e}")
                time.sleep(30)  # Wait before final exit attempt
                if retry_count >= max_retries + 2:
                    print("[!] FATAL: Unable to recover connection. Exiting.")
                    break
            else:
                delay = base_delay * (2 ** min(retry_count, 5))
                print(f"[!] Connection lost. Retrying in {delay}s... (Attempt {retry_count + 1}/{max_retries})")
                print(f"[!] Error details: {e}")
                time.sleep(delay)

        except KeyboardInterrupt:
            print("\n[!] Graceful shutdown requested by user")
            break
        except Exception as e:
            print(f"[!] Unexpected error: {e}")
            retry_count += 1
            if retry_count < max_retries:
                print(f"[!] Retrying in 5s... (Attempt {retry_count + 1}/{max_retries})")
                time.sleep(5)
            else:
                print("[!] FATAL: Unexpected critical error. Exiting.")
                break


if __name__ == "__main__":
    start_worker()
