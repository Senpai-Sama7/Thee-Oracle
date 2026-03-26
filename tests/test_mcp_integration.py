#!/usr/bin/env python3
"""
Tests for MCP + Skills Integration (Oracle 5.0 Phase 0)
"""

import asyncio
import json
import sys
from pathlib import Path

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from oracle.skill_loader import SkillLoader, SkillToolDef


class TestSkillLoader:
    """Test SkillLoader functionality."""

    def test_skill_discovery(self, tmp_path):
        """Test that skills are discovered from directory."""
        # Create a test skill file
        skill_content = """
SKILL_NAME = "test_skill"

def test_handler():
    return {"success": True, "result": "test"}

TOOLS = [
    {
        "name": "test_tool",
        "description": "A test tool",
        "parameters": {},
        "handler": test_handler
    }
]
"""
        skill_file = tmp_path / "test_skill.py"
        skill_file.write_text(skill_content)

        # Load skills
        loader = SkillLoader(str(tmp_path))
        tools = loader.load_all()

        assert "test_tool" in tools
        assert tools["test_tool"].name == "test_tool"
        assert tools["test_tool"].description == "A test tool"

    def test_skill_validation(self, tmp_path):
        """Test that invalid skills are rejected."""
        # Create an invalid skill (missing handler)
        skill_content = """
TOOLS = [
    {
        "name": "invalid_tool",
        "description": "Missing handler"
    }
]
"""
        skill_file = tmp_path / "invalid_skill.py"
        skill_file.write_text(skill_content)

        loader = SkillLoader(str(tmp_path))
        tools = loader.load_all()

        # Should be empty (invalid skill skipped)
        assert len(tools) == 0

    def test_builtin_conflict_resolution(self, tmp_path):
        """Test that built-in conflicts are resolved with prefixing."""
        skill_content = """
SKILL_NAME = "conflict_skill"

def handler():
    return {"success": True}

TOOLS = [
    {
        "name": "shell_execute",  # Conflicts with built-in
        "description": "Conflicting tool",
        "parameters": {},
        "handler": handler
    }
]
"""
        skill_file = tmp_path / "conflict_skill.py"
        skill_file.write_text(skill_content)

        loader = SkillLoader(str(tmp_path))
        loader.register_builtin_tools(["shell_execute", "vision_capture"])
        tools = loader.load_all()

        # Should be prefixed
        assert "conflict_skill__shell_execute" in tools
        assert "shell_execute" not in tools

    def test_skill_tool_execution(self, tmp_path):
        """Test that skill tools execute correctly."""
        skill_content = """
SKILL_NAME = "exec_skill"

def echo_handler(message: str):
    return {"success": True, "result": message}

TOOLS = [
    {
        "name": "echo",
        "description": "Echoes the input",
        "parameters": {"message": {"type": "string"}},
        "handler": echo_handler
    }
]
"""
        skill_file = tmp_path / "exec_skill.py"
        skill_file.write_text(skill_content)

        loader = SkillLoader(str(tmp_path))
        tools = loader.load_all()

        # Execute the tool
        result = tools["echo"].handler("Hello World")
        assert result["success"] is True
        assert result["result"] == "Hello World"


class TestSkillToolDef:
    """Test SkillToolDef dataclass."""

    def test_valid_tool_def(self):
        """Test valid tool definition creation."""

        def handler():
            return {"success": True}

        tool = SkillToolDef(name="test", description="Test tool", parameters={}, handler=handler)

        assert tool.name == "test"
        assert callable(tool.handler)

    def test_invalid_tool_def_no_handler(self):
        """Test that tool definition without handler fails."""
        with pytest.raises(ValueError, match="handler cannot be None"):
            SkillToolDef(name="test", description="Test tool", parameters={}, handler=None)


class TestMCPConfig:
    """Test MCP configuration loading."""

    def test_config_loading_yaml(self, tmp_path):
        """Test YAML config loading."""
        pytest.importorskip("yaml")

        config_content = """
servers:
  - name: test_server
    transport: stdio
    command: echo
    args: ["test"]
    timeout: 30
    disabled: false
"""
        config_file = tmp_path / "mcp_servers.yaml"
        config_file.write_text(config_content)

        from oracle.mcp_client import MCPClient

        client = MCPClient(str(config_file))
        servers = client._load_config(str(config_file))

        assert "test_server" in servers
        assert servers["test_server"].transport == "stdio"
        assert servers["test_server"].command == "echo"

    def test_config_loading_json(self, tmp_path):
        """Test JSON config loading."""
        config = {
            "servers": [
                {
                    "name": "json_server",
                    "transport": "sse",
                    "url": "http://localhost:3000",
                    "timeout": 60,
                    "disabled": False,
                }
            ]
        }

        config_file = tmp_path / "mcp_servers.json"
        config_file.write_text(json.dumps(config))

        from oracle.mcp_client import MCPClient

        client = MCPClient(str(config_file))
        servers = client._load_config(str(config_file))

        assert "json_server" in servers
        assert servers["json_server"].transport == "sse"
        assert servers["json_server"].url == "http://localhost:3000"

    def test_missing_config_file(self, tmp_path):
        """Test handling of missing config file."""
        from oracle.mcp_client import MCPClient

        client = MCPClient(str(tmp_path / "nonexistent.yaml"))
        servers = client._load_config(str(tmp_path / "nonexistent.yaml"))

        assert len(servers) == 0

    def test_disabled_server_skipped(self, tmp_path):
        """Test that disabled servers are skipped."""
        config = {
            "servers": [
                {"name": "enabled_server", "transport": "stdio", "command": "echo", "disabled": False},
                {"name": "disabled_server", "transport": "stdio", "command": "echo", "disabled": True},
            ]
        }

        config_file = tmp_path / "mcp_servers.json"
        config_file.write_text(json.dumps(config))

        from oracle.mcp_client import MCPClient

        client = MCPClient(str(config_file))
        servers = client._load_config(str(config_file))

        assert "enabled_server" in servers
        assert "disabled_server" not in servers


class TestToolRegistry:
    """Test ToolRegistry functionality."""

    @pytest.fixture
    def mock_tool_executor(self):
        """Create a mock ToolExecutor."""

        class MockToolExecutor:
            def shell_execute(self, command):
                return {"success": True, "stdout": command}

            def vision_capture(self, reason):
                return {"success": True, "path": "/tmp/screenshot.png"}

            def file_system_ops(self, operation, path, content=None):
                return {"success": True}

            def http_fetch(self, url, method="GET", headers=None):
                return {"success": True, "content": "<html></html>"}

        return MockToolExecutor()

    def test_tool_count(self, mock_tool_executor):
        """Test that tool counts are accurate."""
        pytest.importorskip("google.genai")

        from oracle.tool_registry import ToolRegistry

        registry = ToolRegistry(mock_tool_executor)
        # Note: initialize() not called, so only built-ins exist

        counts = registry.tool_count()
        assert counts["builtin"] == 4
        assert counts["mcp"] == 0
        assert counts["skill"] == 0

    def test_builtin_tools_present(self, mock_tool_executor):
        """Test that built-in tools are always present."""
        pytest.importorskip("google.genai")

        from oracle.tool_registry import ToolRegistry

        registry = ToolRegistry(mock_tool_executor)
        declarations = registry.get_function_declarations()

        tool_names = [d.name for d in declarations]
        assert "shell_execute" in tool_names
        assert "vision_capture" in tool_names
        assert "file_system_ops" in tool_names
        assert "http_fetch" in tool_names

    def test_dispatch_builtin(self, mock_tool_executor):
        """Test dispatch to built-in tools."""
        pytest.importorskip("google.genai")

        from oracle.tool_registry import ToolRegistry

        registry = ToolRegistry(mock_tool_executor)

        result = asyncio.run(registry.dispatch("shell_execute", {"command": "ls"}))

        assert result["success"] is True
        assert result["stdout"] == "ls"

    def test_dispatch_unknown_tool(self, mock_tool_executor):
        """Test dispatch to unknown tool returns error."""
        pytest.importorskip("google.genai")

        from oracle.tool_registry import ToolRegistry

        registry = ToolRegistry(mock_tool_executor)

        result = asyncio.run(registry.dispatch("unknown_tool", {}))

        assert result["success"] is False
        assert "Unknown tool" in result["error"]

    def test_dispatch_never_raises(self, mock_tool_executor):
        """Test that dispatch never raises exceptions."""
        pytest.importorskip("google.genai")

        from oracle.tool_registry import ToolRegistry

        registry = ToolRegistry(mock_tool_executor)

        # Should not raise even for invalid input
        result = asyncio.run(registry.dispatch("shell_execute", {}))  # Missing required arg

        # Should return error envelope, not raise
        assert isinstance(result, dict)
        assert "success" in result


class TestIntegration:
    """Integration tests."""

    def test_end_to_end_skill_execution(self, tmp_path):
        """Test full skill loading and execution flow."""
        # Create a skill
        skill_content = """
SKILL_NAME = "integration_skill"

def multiply(a: int, b: int):
    return {"success": True, "result": a * b}

TOOLS = [
    {
        "name": "multiply",
        "description": "Multiply two numbers",
        "parameters": {
            "a": {"type": "integer"},
            "b": {"type": "integer"}
        },
        "handler": multiply
    }
]
"""
        skill_file = tmp_path / "integration_skill.py"
        skill_file.write_text(skill_content)

        # Load and execute
        loader = SkillLoader(str(tmp_path))
        tools = loader.load_all()

        assert "multiply" in tools

        result = tools["multiply"].handler(5, 3)
        assert result["success"] is True
        assert result["result"] == 15


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
