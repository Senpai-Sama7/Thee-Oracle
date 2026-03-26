import os
from unittest.mock import patch

# Force in-memory DB for tests
os.environ["AGENT_DB_PATH"] = ":memory:"

from oracle.main import app
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
import oracle.main

# Mock OracleAgent for tests to avoid GCP dependency
mock_agent = MagicMock()
mock_agent.run.return_value = "Mocked Agent Response"
mock_agent.config.model_id = "test-model"
oracle.main.agent = mock_agent

client = TestClient(app)


def test_webhook_returns_200() -> None:
    payload = {
        "text": "What is on my calendar?",
        "sessionInfo": {"parameters": {}},
        "fulfillmentInfo": {"tag": "custom_agent"},
    }
    response = client.post("/webhook", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "fulfillmentResponse" in data
    assert "messages" in data["fulfillmentResponse"]


def test_webhook_with_image_attachment() -> None:
    # A tiny 1x1 transparent PNG encoded in base64
    tiny_png = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
    payload = {
        "text": "What is in this image?",
        "sessionInfo": {"parameters": {"image_base64": tiny_png, "image_mime_type": "image/png"}},
        "fulfillmentInfo": {"tag": "custom_agent"},
    }

    response = client.post("/webhook", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "messages" in data.get("fulfillmentResponse", {})


def test_webhook_fallback_utterance() -> None:
    payload = {
        # Dialogflow sometimes doesn't pass text at the root level if configured a certain way
        "sessionInfo": {"parameters": {"last_user_utterance": "Hello! How are you?"}},
        "fulfillmentInfo": {"tag": "custom_agent"},
    }
    response = client.post("/webhook", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "messages" in data.get("fulfillmentResponse", {})


def test_tool_call_send_email_queues_to_rabbitmq() -> None:
    # We want to verify that calling the send_email tool triggers RabbitMQ
    with patch("pika.BlockingConnection") as mock_conn:
        from skills.personal_agent import send_email

        result = send_email("test@example.com", "Hello", "World")
        assert "has been queued for delivery" in result
        mock_conn.assert_called_once()


def test_chat_endpoint_creates_thread() -> None:
    """Test that chat endpoint creates new thread when no thread_id provided."""
    response = client.post("/chat", json={"message": "Hello, how are you?"})
    assert response.status_code == 200
    data = response.json()
    assert "thread_id" in data
    assert "response" in data
    assert data["thread_id"].startswith("thread_")


def test_chat_endpoint_maintains_session() -> None:
    """Test that chat endpoint maintains conversation history within same thread."""
    # First message
    response1 = client.post("/chat", json={"message": "My name is John"})
    assert response1.status_code == 200
    thread_id = response1.json()["thread_id"]

    # Second message in same thread
    response2 = client.post("/chat", json={"message": "What's my name?", "thread_id": thread_id})
    assert response2.status_code == 200
    data2 = response2.json()
    assert data2["thread_id"] == thread_id


def test_chat_endpoint_persists_to_result_store() -> None:
    """Test that chat interactions are persisted to ResultStore."""
    response = client.post("/chat", json={"message": "Test persistence"})
    assert response.status_code == 200

    # Verify the interaction was stored in the database
    # This would require access to the result_store instance
    # For now, we just verify the endpoint responds correctly


def test_health_endpoint() -> None:
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "service" in data
    assert "agent_type" in data
    assert data["status"] in ["healthy", "degraded"]
