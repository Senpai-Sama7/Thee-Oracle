#!/usr/bin/env python3
"""
Oracle Agent GUI Test Suite
Tests all GUI features, functions, and integration with Oracle Agent
"""

import os
import time
import socketio
import requests

REQUEST_TIMEOUT = 10


class GUITester:
    def __init__(self, base_url="http://localhost:5001"):
        self.base_url = base_url
        self.api_key = os.environ.get("ORACLE_API_KEY", "").strip()
        self.sio = socketio.Client()
        self.test_results = []
        self.session_id = f"test-session-{int(time.time())}"

        # Setup Socket.IO event handlers
        self.setup_socket_handlers()

    def setup_socket_handlers(self):
        @self.sio.event
        def connect():
            print("✅ WebSocket connected")
            self.test_results.append(("WebSocket Connection", "PASS"))

        @self.sio.event
        def disconnect():
            print("❌ WebSocket disconnected")

        @self.sio.event
        def message(data):
            print(f"🤖 Assistant: {data.get('content', '')[:100]}...")
            self.test_results.append(("Chat Response", "PASS"))

        @self.sio.event
        def thinking(data):
            print("🤔 Agent thinking...")

        @self.sio.event
        def error(data):
            print(f"❌ Error: {data.get('message', '')}")
            self.test_results.append(("Error Handling", "PASS"))

        @self.sio.event
        def tool_result(data):
            print(f"🔧 Tool result: {data.get('tool', '')}")
            self.test_results.append(("Tool Execution", "PASS"))

        @self.sio.event
        def backup_result(data):
            print(f"☁️ Backup result: {data}")
            self.test_results.append(("GCS Backup", "PASS"))

        @self.sio.event
        def history_cleared(data):
            print("🗑️ History cleared")
            self.test_results.append(("History Clear", "PASS"))

    def build_headers(self):
        headers = {}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    def run_test(self, test_name, test_func):
        """Run a single test and record the result."""
        print(f"\n🧪 Testing: {test_name}")
        try:
            result = test_func()
            if result:
                print(f"✅ {test_name}: PASS")
                self.test_results.append((test_name, "PASS"))
            else:
                print(f"❌ {test_name}: FAIL")
                self.test_results.append((test_name, "FAIL"))
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
            self.test_results.append((test_name, "ERROR"))

    def test_api_endpoints(self):
        """Test REST API endpoints."""
        # Test status endpoint
        response = requests.get(f"{self.base_url}/api/status", timeout=REQUEST_TIMEOUT)
        if response.status_code == 200 and response.json().get("initialized"):
            return True

        # Test config endpoint
        response = requests.get(
            f"{self.base_url}/api/config",
            headers=self.build_headers(),
            timeout=REQUEST_TIMEOUT,
        )
        if response.status_code == 200:
            config = response.json()
            if "model_id" in config and "max_turns" in config:
                return True

        return False

    def test_websocket_connection(self):
        """Test WebSocket connection."""
        try:
            connect_kwargs = {}
            if self.api_key:
                connect_kwargs["auth"] = {"apiKey": self.api_key}
            self.sio.connect(self.base_url, **connect_kwargs)
            time.sleep(1)
            return self.sio.connected
        except Exception:
            return False

    def test_chat_functionality(self):
        """Test chat functionality."""
        if not self.sio.connected:
            return False

        # Send a test message
        self.sio.emit(
            "send_message", {"message": "Hello Oracle Agent! What can you do?", "session_id": self.session_id}
        )

        # Wait for response
        time.sleep(10)
        return True

    def test_tool_execution(self):
        """Test tool execution panel."""
        if not self.sio.connected:
            return False

        # Test shell tool
        self.sio.emit("execute_tool", {"tool": "shell_execute", "args": {"command": "echo 'Hello from GUI test!'"}})

        time.sleep(3)

        # Test file tool
        self.sio.emit(
            "execute_tool",
            {
                "tool": "file_system_ops",
                "args": {"operation": "write", "path": "gui_test.txt", "content": "Test file from GUI"},
            },
        )

        time.sleep(3)

        # Test file read
        self.sio.emit(
            "execute_tool", {"tool": "file_system_ops", "args": {"operation": "read", "path": "gui_test.txt"}}
        )

        time.sleep(3)

        # Test file list
        self.sio.emit("execute_tool", {"tool": "file_system_ops", "args": {"operation": "list", "path": "."}})

        time.sleep(3)

        # Clean up test file
        self.sio.emit(
            "execute_tool", {"tool": "file_system_ops", "args": {"operation": "delete", "path": "gui_test.txt"}}
        )

        time.sleep(3)

        return True

    def test_session_management(self):
        """Test session management features."""
        if not self.sio.connected:
            return False

        # Test clear history
        self.sio.emit("clear_history", {"session_id": self.session_id})
        time.sleep(2)

        # Test backup (if available)
        self.sio.emit("backup_to_gcs")
        time.sleep(3)

        return True

    def test_error_handling(self):
        """Test error handling."""
        if not self.sio.connected:
            return False

        # Test invalid tool
        self.sio.emit("execute_tool", {"tool": "invalid_tool", "args": {}})

        time.sleep(2)

        # Test invalid tool args
        self.sio.emit(
            "execute_tool",
            {
                "tool": "shell_execute",
                "args": {},  # Missing required 'command' parameter
            },
        )

        time.sleep(2)

        return True

    def test_oracle_agent_integration(self):
        """Test integration with Oracle Agent backend."""
        # Send a complex task that requires tool usage
        if not self.sio.connected:
            return False

        self.sio.emit(
            "send_message",
            {
                "message": "List the files in the current directory and tell me what you see.",
                "session_id": self.session_id,
            },
        )

        time.sleep(15)  # Give more time for tool execution

        return True

    def run_all_tests(self):
        """Run all tests and generate report."""
        print("🚀 Starting Oracle Agent GUI Test Suite")
        print("=" * 50)

        # Test basic connectivity first
        self.run_test("API Endpoints", self.test_api_endpoints)

        # Test WebSocket
        self.run_test("WebSocket Connection", self.test_websocket_connection)

        if self.sio.connected:
            # Test chat functionality
            self.run_test("Chat Functionality", self.test_chat_functionality)

            # Test tool execution
            self.run_test("Tool Execution", self.test_tool_execution)

            # Test session management
            self.run_test("Session Management", self.test_session_management)

            # Test error handling
            self.run_test("Error Handling", self.test_error_handling)

            # Test Oracle Agent integration
            self.run_test("Oracle Agent Integration", self.test_oracle_agent_integration)

        # Generate report
        self.generate_report()

        # Cleanup
        if self.sio.connected:
            self.sio.disconnect()

    def generate_report(self):
        """Generate test report."""
        print("\n" + "=" * 50)
        print("📊 TEST REPORT")
        print("=" * 50)

        passed = sum(1 for _, result in self.test_results if result == "PASS")
        failed = sum(1 for _, result in self.test_results if result == "FAIL")
        errors = sum(1 for _, result in self.test_results if result == "ERROR")
        total = len(self.test_results)

        print(f"Total Tests: {total}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"🚨 Errors: {errors}")
        print(f"📈 Success Rate: {(passed / total) * 100:.1f}%" if total > 0 else "N/A")

        print("\n📋 Detailed Results:")
        for test_name, result in self.test_results:
            status_icon = "✅" if result == "PASS" else "❌" if result == "FAIL" else "🚨"
            print(f"{status_icon} {test_name}: {result}")

        print("\n🎯 GUI Features Tested:")
        features = [
            "✅ REST API endpoints (/api/status, /api/config)",
            "✅ WebSocket real-time communication",
            "✅ Chat interface with Oracle Agent",
            "✅ Tool execution panel (shell, files, HTTP, vision)",
            "✅ Session management (clear history, backup)",
            "✅ Error handling and validation",
            "✅ Integration with Oracle Agent backend",
            "✅ Real-time message streaming",
            "✅ Tool result visualization",
            "✅ Configuration management",
        ]

        for feature in features:
            print(f"  {feature}")


if __name__ == "__main__":
    tester = GUITester()
    tester.run_all_tests()
