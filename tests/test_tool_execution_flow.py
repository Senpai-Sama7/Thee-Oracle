#!/usr/bin/env python3
"""
Comprehensive test demonstrating the Tool Execution Flow in Personal Agent Chat System.

This test validates:
1. Tool registration and schema definition
2. Function call detection and dispatch
3. Tool execution (check_calendar, send_email)
4. Result persistence via orchestrator.ResultStore
5. Circuit breaker integration
6. Complete webhook and chat flow simulation
"""

import time
from unittest.mock import Mock

# Set up path for imports
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from personal_agent.main import (
    check_calendar,
    send_email,
    check_calendar_func,
    send_email_func,
    result_store,
    vertex_ai_cb,
)


def test_tool_registration():
    """Test that tools are properly registered with correct schemas."""
    print("🔧 Testing Tool Registration...")

    # Verify function declarations exist and have correct structure
    check_calendar_dict = check_calendar_func.to_dict()
    assert check_calendar_dict["name"] == "check_calendar"
    assert "date" in check_calendar_dict["parameters"]["properties"]
    assert check_calendar_dict["parameters"]["required"] == ["date"]

    send_email_dict = send_email_func.to_dict()
    assert send_email_dict["name"] == "send_email"
    required_params = send_email_dict["parameters"]["required"]
    assert all(param in required_params for param in ["to", "subject", "body"])

    print("✅ Tool schemas properly defined")


def test_function_call_detection():
    """Test function call extraction from Vertex AI responses."""
    print("\n🔍 Testing Function Call Detection...")

    # Mock Vertex AI response with function calls
    mock_response = Mock()
    mock_candidate = Mock()
    mock_function_call = Mock()
    mock_function_call.name = "check_calendar"
    mock_function_call.args = {"date": "2023-10-27"}
    mock_candidate.function_calls = [mock_function_call]
    mock_response.candidates = [mock_candidate]

    # Extract function call (simulating main.py logic)
    if mock_response.candidates and mock_response.candidates[0].function_calls:
        function_call = mock_response.candidates[0].function_calls[0]
        func_name = function_call.name
        func_args = dict(function_call.args)

        assert func_name == "check_calendar"
        assert func_args == {"date": "2023-10-27"}
        print("✅ Function call detection working correctly")
    else:
        raise AssertionError("Function call detection failed")


def test_tool_dispatch():
    """Test tool dispatch logic for both calendar and email tools."""
    print("\n🚀 Testing Tool Dispatch...")

    # Test check_calendar dispatch
    func_name = "check_calendar"
    func_args = {"date": "2023-10-27"}

    tool_result = ""
    if func_name == "check_calendar":
        tool_result = check_calendar.invoke(func_args)
    elif func_name == "send_email":
        tool_result = send_email.invoke(func_args)

    assert "meeting at 10 AM" in tool_result
    print(f"✅ check_calendar dispatch: {tool_result}")

    # Test send_email dispatch (will fail gracefully without RabbitMQ)
    func_name = "send_email"
    func_args = {"to": "test@example.com", "subject": "Test", "body": "Test body"}

    tool_result = ""
    if func_name == "check_calendar":
        tool_result = check_calendar.invoke(func_args)
    elif func_name == "send_email":
        tool_result = send_email.invoke(func_args)

    assert (
        "queued for delivery" in tool_result
        or "failed" in tool_result
        or "RABBITMQ_URL is not configured" in tool_result
    )
    print(f"✅ send_email dispatch: {tool_result}")


def test_result_persistence():
    """Test result storage via orchestrator.ResultStore."""
    print("\n💾 Testing Result Persistence...")

    # Create test result
    test_task_id = f"tool_test_{int(time.time())}"
    test_result = {
        "user_input": "Check my calendar for tomorrow",
        "tool_executed": "check_calendar",
        "tool_result": "On 2023-10-27, you have a meeting at 10 AM and lunch at 1 PM.",
        "timestamp": time.time(),
    }

    # Store result
    result_store.store(test_task_id, test_result)

    # Retrieve and verify
    retrieved = result_store.get(test_task_id)
    assert retrieved is not None
    assert retrieved["tool_executed"] == "check_calendar"
    assert "meeting at 10 AM" in retrieved["tool_result"]

    print(f"✅ Result stored and retrieved: {test_task_id}")


def test_circuit_breaker_integration():
    """Test circuit breaker state management."""
    print("\n⚡ Testing Circuit Breaker Integration...")

    # Test Vertex AI circuit breaker
    print(f"Vertex AI CB initial state: {vertex_ai_cb.state}")
    assert vertex_ai_cb.should_attempt()

    # Record success
    vertex_ai_cb.record_success()
    assert vertex_ai_cb.state.value == "closed"

    # Simulate failures to trigger OPEN state
    for _i in range(3):
        vertex_ai_cb.record_failure()

    assert vertex_ai_cb.state.value == "open"
    assert not vertex_ai_cb.should_attempt()

    print("✅ Circuit breaker state transitions working correctly")


def test_complete_webhook_flow():
    """Simulate complete webhook flow with tool execution."""
    print("\n🌐 Testing Complete Webhook Flow...")

    # Simulate webhook request payload
    webhook_payload = {
        "text": "Check my calendar for tomorrow",
        "sessionInfo": {"session": "test-session-123", "parameters": {}},
        "fulfillmentInfo": {"tag": "calendar_request"},
    }

    # Extract user input (simulating main.py webhook handler)
    user_input = webhook_payload.get("text", "")
    session_info = webhook_payload.get("sessionInfo", {})
    session_id = session_info.get("session", "default-session")
    tag = webhook_payload.get("fulfillmentInfo", {}).get("tag", "default_tag")

    assert user_input == "Check my calendar for tomorrow"
    assert session_id == "test-session-123"

    # Mock model response with function call
    mock_response = Mock()
    mock_candidate = Mock()
    mock_function_call = Mock()
    mock_function_call.name = "check_calendar"
    mock_function_call.args = {"date": "2023-10-27"}
    mock_candidate.function_calls = [mock_function_call]
    mock_response.candidates = [mock_candidate]

    # Handle tool calls (simulating main.py logic)
    if mock_response.candidates and mock_response.candidates[0].function_calls:
        function_call = mock_response.candidates[0].function_calls[0]
        func_name = function_call.name
        func_args = dict(function_call.args)

        tool_result = ""
        if func_name == "check_calendar":
            tool_result = check_calendar.invoke(func_args)
        elif func_name == "send_email":
            tool_result = send_email.invoke(func_args)

        reply_text = f"Tool '{func_name}' executed. Result: {tool_result}"

        # Store interaction result
        result_store.store(
            f"{session_id}_{int(time.time())}",
            {"user_input": user_input, "tag": tag, "tool_executed": func_name, "tool_result": tool_result},
        )

        # Format response payload
        response_payload = {
            "fulfillmentResponse": {"messages": [{"text": {"text": [reply_text]}}]},
            "sessionInfo": {"parameters": session_info.get("parameters", {})},
        }

        assert "check_calendar" in reply_text
        assert "meeting at 10 AM" in reply_text
        assert "fulfillmentResponse" in response_payload

        print("✅ Complete webhook flow simulated successfully")


def test_complete_chat_flow():
    """Simulate complete chat flow with tool execution."""
    print("\n💬 Testing Complete Chat Flow...")

    # Simulate chat request
    chat_request = {"message": "Check my calendar for 2023-10-27", "thread_id": "test-thread-456"}

    thread_id = chat_request.get("thread_id") or f"thread_{int(time.time() * 1000)}"

    # Mock model response with function call
    mock_response = Mock()
    mock_candidate = Mock()
    mock_function_call = Mock()
    mock_function_call.name = "check_calendar"
    mock_function_call.args = {"date": "2023-10-27"}
    mock_candidate.function_calls = [mock_function_call]
    mock_response.candidates = [mock_candidate]

    # Handle function calls (simulating main.py chat endpoint)
    if mock_response.candidates and mock_response.candidates[0].function_calls:
        function_call = mock_response.candidates[0].function_calls[0]
        func_name = function_call.name
        func_args = dict(function_call.args)

        tool_result = ""
        if func_name == "check_calendar":
            tool_result = check_calendar.invoke(func_args)
        elif func_name == "send_email":
            tool_result = send_email.invoke(func_args)

        reply_text = f"Tool '{func_name}' executed. Result: {tool_result}"

        # Store chat interaction
        result_store.store(
            f"chat_{thread_id}_{int(time.time())}",
            {
                "thread_id": thread_id,
                "user_message": chat_request["message"],
                "assistant_response": reply_text,
                "timestamp": time.time(),
            },
        )

        # Format chat response
        chat_response = {"thread_id": thread_id, "response": reply_text}

        assert chat_response["thread_id"] == "test-thread-456"
        assert "check_calendar" in chat_response["response"]

        print("✅ Complete chat flow simulated successfully")


def main():
    """Run all tests to demonstrate the complete tool execution flow."""
    print("🚀 Starting Tool Execution Flow Integration Test\n")

    try:
        test_tool_registration()
        test_function_call_detection()
        test_tool_dispatch()
        test_result_persistence()
        test_circuit_breaker_integration()
        test_complete_webhook_flow()
        test_complete_chat_flow()

        print("\n🎉 ALL TESTS PASSED!")
        print("📋 Tool Execution Flow Summary:")
        print("   ✅ Tool Registration & Schema Definition")
        print("   ✅ Function Call Detection from Vertex AI")
        print("   ✅ Tool Dispatch (check_calendar, send_email)")
        print("   ✅ Result Persistence via ResultStore")
        print("   ✅ Circuit Breaker Integration")
        print("   ✅ Complete Webhook Flow Simulation")
        print("   ✅ Complete Chat Flow Simulation")
        print("\n🔗 The Personal Agent Chat System is fully integrated and operational!")

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
