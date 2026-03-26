#!/usr/bin/env python3
"""
MCP Client for Oracle Agent 5.0
Manages connections to external MCP servers and routes tool calls.

Implements Requirements 1-3 from MCP Skills Integration spec.
"""

import asyncio
import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)

# Try to import MCP library
try:
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    logger.warning("MCP library not installed. MCP features disabled.")

try:
    import yaml

    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    logger.warning("PyYAML not installed. Using JSON config fallback.")


@dataclass
class MCPServerConfig:
    """Configuration for a single MCP server."""

    name: str
    transport: str  # "stdio" or "sse"
    command: Optional[str] = None
    args: Optional[List[str]] = None
    url: Optional[str] = None
    env: Optional[Dict[str, str]] = None
    timeout: int = 30
    disabled: bool = False


class MCPClient:
    """
    Manages connections to MCP servers and routes tool calls.

    Key responsibilities:
    1. Load and validate MCP server configurations
    2. Connect to servers (stdio and SSE transports)
    3. Discover available tools from each server
    4. Route tool calls to appropriate server
    5. Handle timeouts, errors, and server failures
    """

    def __init__(self, config_path: str | None = None) -> None:
        if not MCP_AVAILABLE:
            raise RuntimeError("MCP library not installed. Install with: pip install mcp>=1.12.0")

        self.config_path = config_path or os.getenv("ORACLE_MCP_CONFIG", "config/mcp_servers.yaml")
        self.timeout = int(os.getenv("ORACLE_MCP_TIMEOUT", "30"))
        self.servers: Dict[str, MCPServerConfig] = {}
        self.sessions: Dict[str, ClientSession] = {}  # ClientSession instances
        self.processes: Dict[str, Any] = {}
        self._tools_by_server: Dict[str, List[Dict[str, Any]]] = {}
        self._unavailable_servers: Set[str] = set()

    async def initialize(self) -> None:
        """Load config and connect to all enabled servers."""
        if not self.config_path:
            logger.warning("No MCP config path provided")
            return
        self.servers = self._load_config(str(self.config_path))
        if self.servers:
            await self.connect_all()
        else:
            logger.info("No MCP servers configured")

    def _load_config(self, path: str) -> Dict[str, MCPServerConfig]:
        """
        Load MCP server configurations from YAML/JSON file.

        Req 1.1, 1.2, 1.5: Validate required fields, skip invalid/disabled entries.
        """
        servers: Dict[str, MCPServerConfig] = {}
        config_file = Path(path)

        if not config_file.exists():
            logger.warning(f"MCP config file not found: {path}. Starting with zero MCP servers.")
            # Create example config
            self._create_example_config(config_file)
            return servers

        try:
            with open(config_file) as f:
                if YAML_AVAILABLE:
                    config = yaml.safe_load(f)
                else:
                    # Fallback to JSON
                    config = json.load(f)

            if not config or "servers" not in config:
                logger.warning("MCP config has no 'servers' key. Starting with zero servers.")
                return servers

            for entry in config.get("servers", []):
                server_name = entry.get("name")

                # Req 1.5: Validate required fields
                if not server_name:
                    logger.error(f"Skipping MCP server entry without 'name': {entry}")
                    continue

                if entry.get("disabled"):
                    logger.info(f"Skipping disabled MCP server: {server_name}")
                    continue

                transport = entry.get("transport")
                if transport not in ("stdio", "sse"):
                    logger.error(f"Invalid transport '{transport}' for server '{server_name}'")
                    continue

                if transport == "stdio" and not entry.get("command"):
                    logger.error(f"Missing 'command' for stdio server '{server_name}'")
                    continue

                if transport == "sse" and not entry.get("url"):
                    logger.error(f"Missing 'url' for SSE server '{server_name}'")
                    continue

                # Req 1.7: Support environment variable overrides
                env = entry.get("env", {})
                env = {k: os.path.expandvars(v) for k, v in env.items()}

                servers[server_name] = MCPServerConfig(
                    name=server_name,
                    transport=transport,
                    command=entry.get("command"),
                    args=entry.get("args", []),
                    url=entry.get("url"),
                    env=env,
                    timeout=entry.get("timeout", self.timeout),
                    disabled=entry.get("disabled", False),
                )

        except Exception as e:
            logger.error(f"Error loading MCP config: {e}")

        return servers

    def _create_example_config(self, config_file: Path) -> None:
        """Create example MCP config file."""
        try:
            config_file.parent.mkdir(parents=True, exist_ok=True)
            example = {
                "servers": [
                    {
                        "name": "filesystem",
                        "transport": "stdio",
                        "command": "npx",
                        "args": ["-y", "@modelcontextprotocol/server-filesystem", "~/.oracle/workspace"],
                        "env": {},
                        "timeout": 30,
                        "disabled": False,
                    },
                    {
                        "name": "github",
                        "transport": "stdio",
                        "command": "npx",
                        "args": ["-y", "@modelcontextprotocol/server-github"],
                        "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}"},
                        "timeout": 30,
                        "disabled": True,
                    },
                ]
            }

            with open(config_file, "w") as f:
                if YAML_AVAILABLE:
                    yaml.dump(example, f, default_flow_style=False)
                else:
                    json.dump(example, f, indent=2)

            logger.info(f"Created example MCP config: {config_file}")
        except Exception as e:
            logger.error(f"Failed to create example config: {e}")

    async def connect_all(self) -> None:
        """
        Connect to all configured MCP servers.

        Req 1.3: stdio transport via subprocess
        Req 1.4: SSE transport via HTTP
        Req 1.6: Handle server failures gracefully
        """
        for server_name, config in self.servers.items():
            try:
                if config.transport == "stdio":
                    await self._connect_stdio(server_name, config)
                else:
                    await self._connect_sse(server_name, config)
            except Exception as e:
                logger.error(f"Failed to connect MCP server '{server_name}': {e}")
                self._unavailable_servers.add(server_name)

    async def _connect_stdio(self, name: str, config: MCPServerConfig) -> None:
        """Connect to stdio-based MCP server."""
        logger.info(f"Connecting to stdio MCP server: {name}")

        # Prepare environment
        env = os.environ.copy()
        if config.env:
            env.update(config.env)

        if not config.command:
            logger.error(f"Cannot connect to stdio server {name}: missing command")
            return

        server_params = StdioServerParameters(command=config.command, args=config.args or [], env=env)

        # Req 1.3: Launch subprocess and connect
        try:
            # Note: stdio_client is async context manager
            read, write = await self._stdio_client_connect(server_params, name=name)

            session = ClientSession(read, write)
            await session.initialize()

            self.sessions[name] = session

            # Discover tools
            tools_response = await session.list_tools()
            self._tools_by_server[name] = [
                {"name": tool.name, "description": tool.description, "inputSchema": tool.inputSchema}
                for tool in tools_response.tools
            ]

            logger.info(f"Connected to '{name}' with {len(tools_response.tools)} tools")
        except Exception as e:
            logger.error(f"Failed to connect to stdio server '{name}': {e}")
            raise

    async def _stdio_client_connect(self, server_params: StdioServerParameters, name: str = "") -> Tuple[Any, Any]:
        """Helper to connect stdio client."""
        # Use the actual stdio_client context manager properly
        cm = stdio_client(server_params)
        read, write = await cm.__aenter__()
        # Store context manager for cleanup — keyed by server name to avoid collisions
        # when multiple servers share the same command binary (e.g., 'npx')
        self._stdio_contexts = getattr(self, "_stdio_contexts", {})
        key = name or server_params.command
        self._stdio_contexts[key] = cm
        return read, write

    async def _connect_sse(self, name: str, config: MCPServerConfig) -> None:
        """Connect to SSE-based MCP server."""
        logger.info(f"Connecting to SSE MCP server: {name} at {config.url}")

        try:
            # Req 1.4: Connect via SSE
            # Note: SSE client may not be available in all MCP versions
            try:
                from mcp.client.sse import sse_client

                if not config.url:
                    logger.error(f"Cannot connect to SSE server {name}: missing URL")
                    raise ValueError(f"Missing URL for SSE server {name}")

                cm = sse_client(config.url)
                read, write = await cm.__aenter__()

                # Store context manager for cleanup
                self._sse_contexts = getattr(self, "_sse_contexts", {})
                self._sse_contexts[name] = cm

                session = ClientSession(read, write)
                await session.initialize()

                self.sessions[name] = session

                # Discover tools
                tools_response = await session.list_tools()
                self._tools_by_server[name] = [
                    {"name": tool.name, "description": tool.description, "inputSchema": tool.inputSchema}
                    for tool in tools_response.tools
                ]

                logger.info(f"Connected to '{name}' with {len(tools_response.tools)} tools")
            except ImportError as err:
                logger.error(f"SSE client not available in MCP library for server '{name}'")
                raise RuntimeError("SSE transport requires mcp>=1.12.0") from err
        except Exception as e:
            logger.error(f"Failed to connect to SSE server '{name}': {e}")
            raise

    async def call_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call a tool on a specific MCP server.

        Req 3.1-3.6: Route calls, handle timeouts, errors, return Tool_Envelope.
        """
        # Check server availability
        if server_name in self._unavailable_servers:
            return {"success": False, "error": f"MCP server '{server_name}' is unavailable"}

        session = self.sessions.get(server_name)
        if not session:
            return {"success": False, "error": f"MCP server '{server_name}' not connected"}

        config = self.servers.get(server_name)
        timeout = config.timeout if config else self.timeout

        try:
            # Req 3.1: Call MCP tools/call
            result = await asyncio.wait_for(session.call_tool(tool_name, arguments), timeout=timeout)

            # Req 3.2: Convert to Tool_Envelope
            if result.isError:
                # Req 3.3: Handle isError
                return {"success": False, "error": result.content or "Tool execution failed"}
            else:
                return {"success": True, "result": result.content}

        except asyncio.TimeoutError:
            # Req 3.4: Handle timeout
            logger.error(f"MCP tool call timeout after {timeout}s: {server_name}.{tool_name}")
            return {"success": False, "error": f"Tool call timeout after {timeout} seconds"}
        except Exception as e:
            # Req 3.5: Never raise exceptions
            logger.error(f"MCP tool call error: {e}")
            return {"success": False, "error": str(e)}

    def get_all_tools(self) -> List[Tuple[str, str, Dict[str, Any]]]:
        """
        Get all tools from all connected servers.

        Returns: List of (server_name, tool_name, tool_definition) tuples.
        """
        tools = []
        for server_name, server_tools in self._tools_by_server.items():
            if server_name in self._unavailable_servers:
                continue
            for tool in server_tools:
                tools.append((server_name, tool["name"], tool))
        return tools

    def mark_server_unavailable(self, server_name: str) -> None:
        """
        Mark a server as unavailable (Req 1.6, 3.6).
        Removes its tools from the active registry.
        """
        logger.warning(f"Marking MCP server '{server_name}' as unavailable")
        self._unavailable_servers.add(server_name)
        if server_name in self._tools_by_server:
            del self._tools_by_server[server_name]

    async def shutdown(self) -> None:
        """Cleanly shut down all MCP connections."""
        logger.info("Shutting down MCP client")

        # Sessions are automatically closed when their respective transports' context managers exit below.
        pass

        # Close stdio contexts
        if hasattr(self, "_stdio_contexts"):
            for cmd, cm in self._stdio_contexts.items():
                try:
                    await cm.__aexit__(None, None, None)
                except Exception as e:
                    logger.warning(f"Error closing stdio context for '{cmd}': {e}")

        # Close SSE contexts
        if hasattr(self, "_sse_contexts"):
            for name, cm in self._sse_contexts.items():
                try:
                    await cm.__aexit__(None, None, None)
                except Exception as e:
                    logger.warning(f"Error closing SSE context for '{name}': {e}")

        self.sessions.clear()
        self._tools_by_server.clear()
