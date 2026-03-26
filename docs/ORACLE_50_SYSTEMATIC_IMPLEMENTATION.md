# Oracle 5.0 - Systematic Implementation Plan
## Integrating MCP Skills, Model Router, Multi-Agent, and Interfaces

**Based on:**
- `.kiro/specs/mcp-skills-integration/requirements.md`
- `.kiro/specs/oracle-platform-v2/design.md`
- `.kiro/specs/mcp-skills-integration/tasks.md`

---

## 🎯 Implementation Strategy

### Phase Dependencies

```
Phase 0: MCP + Skills (Foundation)
    ↓
Phase 1: Model Router (Multi-LLM)
    ↓
Phase 2: Multi-Agent Orchestration
    ↓
Phase 3: Interface Layer (TUI/GUI/Messaging)
    ↓
Phase 4: Knowledge + Embeddings
    ↓
Phase 5: Browser + Skills Ecosystem
    ↓
Phase 6: Mobile + Production
```

**Current Status:** Phase 0 is ~70% complete (tasks marked with [~])

---

## 📋 Phase 0: Complete MCP + Skills Foundation

### Week 1: Finalize MCP Client & Registry

#### Day 1-2: Complete MCP Client Implementation

**File:** `src/oracle/mcp_client.py`

```python
"""
MCP Client for connecting to external MCP servers.
Implements Requirements 1-3 from MCP Skills Integration spec.
"""

import asyncio
import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client

logger = logging.getLogger(__name__)


@dataclass
class MCPServerConfig:
    """Configuration for a single MCP server."""
    name: str
    transport: str  # "stdio" or "sse"
    command: Optional[str] = None
    args: List[str] = None
    url: Optional[str] = None
    env: Dict[str, str] = None
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
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or os.getenv(
            "ORACLE_MCP_CONFIG", 
            "config/mcp_servers.yaml"
        )
        self.timeout = int(os.getenv("ORACLE_MCP_TIMEOUT", "30"))
        self.servers: Dict[str, MCPServerConfig] = {}
        self.sessions: Dict[str, ClientSession] = {}
        self.processes: Dict[str, asyncio.subprocess.Process] = {}
        self._tools_by_server: Dict[str, List[Dict]] = {}
        self._unavailable_servers: set = set()
        
    async def initialize(self):
        """Load config and connect to all enabled servers."""
        self.servers = self._load_config(self.config_path)
        await self.connect_all()
        
    def _load_config(self, path: str) -> Dict[str, MCPServerConfig]:
        """
        Load MCP server configurations from YAML file.
        
        Req 1.1, 1.2, 1.5: Validate required fields, skip invalid/disabled entries.
        """
        servers = {}
        config_file = Path(path)
        
        if not config_file.exists():
            logger.warning(f"MCP config file not found: {path}. Starting with zero MCP servers.")
            return servers
            
        try:
            with open(config_file) as f:
                config = yaml.safe_load(f)
                
            if not config or "servers" not in config:
                logger.warning("MCP config has no 'servers' key. Starting with zero servers.")
                return servers
                
            for entry in config["servers"]:
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
                    disabled=entry.get("disabled", False)
                )
                
        except yaml.YAMLError as e:
            logger.error(f"Failed to parse MCP config: {e}")
        except Exception as e:
            logger.error(f"Error loading MCP config: {e}")
            
        return servers
        
    async def connect_all(self):
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
                
    async def _connect_stdio(self, name: str, config: MCPServerConfig):
        """Connect to stdio-based MCP server."""
        logger.info(f"Connecting to stdio MCP server: {name}")
        
        # Prepare environment
        env = os.environ.copy()
        env.update(config.env or {})
        
        server_params = StdioServerParameters(
            command=config.command,
            args=config.args or [],
            env=env
        )
        
        # Req 1.3: Launch subprocess and connect
        transport = await stdio_client(server_params)
        read, write = transport
        
        session = ClientSession(read, write)
        await session.initialize()
        
        self.sessions[name] = session
        
        # Discover tools
        tools_response = await session.list_tools()
        self._tools_by_server[name] = tools_response.tools
        
        logger.info(f"Connected to '{name}' with {len(tools_response.tools)} tools")
        
    async def _connect_sse(self, name: str, config: MCPServerConfig):
        """Connect to SSE-based MCP server."""
        logger.info(f"Connecting to SSE MCP server: {name} at {config.url}")
        
        # Req 1.4: Connect via SSE
        streams = await sse_client(config.url)
        read, write = streams
        
        session = ClientSession(read, write)
        await session.initialize()
        
        self.sessions[name] = session
        
        # Discover tools
        tools_response = await session.list_tools()
        self._tools_by_server[name] = tools_response.tools
        
        logger.info(f"Connected to '{name}' with {len(tools_response.tools)} tools")
        
    async def call_tool(
        self, 
        server_name: str, 
        tool_name: str, 
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Call a tool on a specific MCP server.
        
        Req 3.1-3.6: Route calls, handle timeouts, errors, return Tool_Envelope.
        """
        # Check server availability
        if server_name in self._unavailable_servers:
            return {
                "success": False,
                "error": f"MCP server '{server_name}' is unavailable"
            }
            
        session = self.sessions.get(server_name)
        if not session:
            return {
                "success": False,
                "error": f"MCP server '{server_name}' not connected"
            }
            
        config = self.servers.get(server_name)
        timeout = config.timeout if config else self.timeout
        
        try:
            # Req 3.1: Call MCP tools/call
            result = await asyncio.wait_for(
                session.call_tool(tool_name, arguments),
                timeout=timeout
            )
            
            # Req 3.2: Convert to Tool_Envelope
            if result.isError:
                # Req 3.3: Handle isError
                return {
                    "success": False,
                    "error": result.content or "Tool execution failed"
                }
            else:
                return {
                    "success": True,
                    "result": result.content
                }
                
        except asyncio.TimeoutError:
            # Req 3.4: Handle timeout
            logger.error(f"MCP tool call timeout after {timeout}s: {server_name}.{tool_name}")
            return {
                "success": False,
                "error": f"Tool call timeout after {timeout} seconds"
            }
        except Exception as e:
            # Req 3.5: Never raise exceptions
            logger.error(f"MCP tool call error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
            
    def get_all_tools(self) -> List[Tuple[str, str, Dict]]:
        """
        Get all tools from all connected servers.
        
        Returns: List of (server_name, tool_name, tool_definition) tuples.
        """
        tools = []
        for server_name, server_tools in self._tools_by_server.items():
            if server_name in self._unavailable_servers:
                continue
            for tool in server_tools:
                tools.append((server_name, tool.name, tool))
        return tools
        
    def mark_server_unavailable(self, server_name: str):
        """
        Mark a server as unavailable (Req 1.6, 3.6).
        Removes its tools from the active registry.
        """
        logger.warning(f"Marking MCP server '{server_name}' as unavailable")
        self._unavailable_servers.add(server_name)
        if server_name in self._tools_by_server:
            del self._tools_by_server[server_name]
            
    async def shutdown(self):
        """Cleanly shut down all MCP connections."""
        logger.info("Shutting down MCP client")
        
        for name, session in self.sessions.items():
            try:
                await session.close()
            except Exception as e:
                logger.warning(f"Error closing session '{name}': {e}")
                
        # Terminate subprocesses
        for name, process in self.processes.items():
            if process.returncode is None:
                try:
                    process.terminate()
                    await asyncio.wait_for(process.wait(), timeout=5.0)
                except Exception:
                    process.kill()
```

#### Day 3-4: Implement MCP Registry

**File:** `src/oracle/mcp_registry.py`

```python
"""
MCP Registry for tool discovery, schema translation, and dispatch.
Implements Requirements 2 and 3 from MCP Skills Integration spec.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from google.genai import types

from .mcp_client import MCPClient

logger = logging.getLogger(__name__)


class MCPRegistry:
    """
    Translates MCP tools to Gemini FunctionDeclarations and routes calls.
    
    Req 2: Tool discovery and schema translation
    Req 3: Tool invocation routing
    """
    
    def __init__(self, mcp_client: MCPClient):
        self.mcp_client = mcp_client
        self._tool_map: Dict[str, Tuple[str, str]] = {}  # registered_name -> (server, original_name)
        self._declarations: List[types.FunctionDeclaration] = []
        self._builtin_tools: set = set()  # To detect conflicts
        
    def register_builtin_tools(self, tool_names: List[str]):
        """Register built-in tool names to detect conflicts."""
        self._builtin_tools = set(tool_names)
        
    async def build_registry(self):
        """
        Discover all MCP tools and build FunctionDeclarations.
        
        Req 2.1-2.6: Translate schemas, handle conflicts, store mappings.
        """
        self._tool_map = {}
        self._declarations = []
        
        tools = self.mcp_client.get_all_tools()
        
        for server_name, tool_name, tool_def in tools:
            # Req 2.3: Handle name conflicts
            registered_name = tool_name
            if tool_name in self._builtin_tools:
                registered_name = f"{server_name}__{tool_name}"
                logger.warning(
                    f"MCP tool '{tool_name}' conflicts with built-in, "
                    f"renamed to '{registered_name}'"
                )
            elif registered_name in self._tool_map:
                # Additional conflict with another MCP tool
                registered_name = f"{server_name}__{tool_name}"
                logger.warning(
                    f"MCP tool name collision, renamed to '{registered_name}'"
                )
                
            # Store mapping for dispatch
            self._tool_map[registered_name] = (server_name, tool_name)
            
            # Req 2.2: Translate schema to FunctionDeclaration
            declaration = self._translate_tool(registered_name, tool_def)
            self._declarations.append(declaration)
            
        logger.info(f"MCP Registry: {len(self._declarations)} tools registered")
        
    def _translate_tool(
        self, 
        registered_name: str, 
        tool_def: Any
    ) -> types.FunctionDeclaration:
        """
        Translate MCP tool definition to Gemini FunctionDeclaration.
        
        Req 2.2, 2.5, 10: Schema translation with fallback descriptions.
        """
        original_name = tool_def.name
        description = tool_def.description
        
        # Req 2.5: Fallback description
        if not description:
            description = f"Tool {original_name} from MCP server"
            
        # Req 10: Translate JSON Schema to Gemini parameters
        parameters = self._translate_schema(tool_def.inputSchema)
        
        return types.FunctionDeclaration(
            name=registered_name,
            description=description,
            parameters=parameters
        )
        
    def _translate_schema(self, json_schema: Dict[str, Any]) -> types.Schema:
        """
        Translate JSON Schema to Gemini Schema.
        
        Req 10: Support type, description, properties, required, enum, items.
        Log warnings for unsupported keywords.
        """
        if not json_schema:
            return types.Schema(type=types.Type.OBJECT)
            
        # Check for unsupported keywords
        unsupported = ["$ref", "allOf", "anyOf", "oneOf", "not", "additionalProperties"]
        for keyword in unsupported:
            if keyword in json_schema:
                logger.warning(
                    f"JSON Schema keyword '{keyword}' not supported, "
                    f"will be omitted"
                )
                
        schema_kwargs = {}
        
        # Map type (Req 10.1)
        type_map = {
            "string": types.Type.STRING,
            "integer": types.Type.INTEGER,
            "number": types.Type.NUMBER,
            "boolean": types.Type.BOOLEAN,
            "array": types.Type.ARRAY,
            "object": types.Type.OBJECT,
        }
        
        json_type = json_schema.get("type", "object")
        if isinstance(json_type, list):
            # Handle union types (e.g., ["string", "null"]) - use first non-null
            json_type = next((t for t in json_type if t != "null"), "string")
            
        schema_kwargs["type"] = type_map.get(json_type, types.Type.OBJECT)
        
        # Description
        if "description" in json_schema:
            schema_kwargs["description"] = json_schema["description"]
            
        # Enum (Req 10.1)
        if "enum" in json_schema:
            schema_kwargs["enum"] = json_schema["enum"]
            
        # Properties for objects (Req 10.2 - nested objects)
        if "properties" in json_schema and json_schema["type"] == "object":
            properties = {}
            for prop_name, prop_schema in json_schema["properties"].items():
                properties[prop_name] = self._translate_schema(prop_schema)
            schema_kwargs["properties"] = properties
            
        # Required fields
        if "required" in json_schema:
            schema_kwargs["required"] = json_schema["required"]
            
        # Items for arrays (Req 10.3)
        if "items" in json_schema and json_schema.get("type") == "array":
            schema_kwargs["items"] = self._translate_schema(json_schema["items"])
            
        return types.Schema(**schema_kwargs)
        
    def get_function_declarations(self) -> List[types.FunctionDeclaration]:
        """
        Get all FunctionDeclarations for registered MCP tools.
        
        Req 2.4: Return declarations for injection into model config.
        """
        return self._declarations
        
    async def dispatch(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Route tool call to appropriate MCP server.
        
        Req 3.1: Dispatch to correct MCP server.
        """
        if tool_name not in self._tool_map:
            return {
                "success": False,
                "error": f"Unknown MCP tool: {tool_name}"
            }
            
        server_name, original_tool_name = self._tool_map[tool_name]
        
        # Req 9.1: Log structured tool call
        logger.info(
            f"MCP tool call: {tool_name} on {server_name} "
            f"(args: {str(arguments)[:120]})"
        )
        
        # Route to MCP client
        return await self.mcp_client.call_tool(
            server_name, 
            original_tool_name, 
            arguments
        )
```

#### Day 5-6: Complete Skill Loader

**File:** `src/oracle/skill_loader.py`

```python
"""
Skill Loader for dynamic tool registration from Python modules.
Implements Requirements 4-5 from MCP Skills Integration spec.
"""

import asyncio
import importlib.util
import inspect
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class SkillToolDef:
    """
    Definition of a tool provided by a skill.
    
    Req 4.1, 4.2: Skill tool definition with name, description, parameters, handler.
    """
    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Callable[..., Any]


class SkillModule:
    """Wrapper for loaded skill module."""
    
    def __init__(self, name: str, module: Any, file_path: Path):
        self.name = name
        self.module = module
        self.file_path = file_path
        self.tools: List[SkillToolDef] = []
        
    async def setup(self):
        """Call setup() if defined (Req 4.3)."""
        if hasattr(self.module, "setup"):
            setup_func = self.module.setup
            if asyncio.iscoroutinefunction(setup_func):
                await setup_func()
            else:
                setup_func()
                
    async def teardown(self):
        """Call teardown() if defined (Req 4.4, 5.5)."""
        if hasattr(self.module, "teardown"):
            teardown_func = self.module.teardown
            try:
                if asyncio.iscoroutinefunction(teardown_func):
                    await teardown_func()
                else:
                    teardown_func()
            except Exception as e:
                logger.error(f"Error in teardown for skill '{self.name}': {e}")
                # Req 5.5: Log error without stopping other teardowns


class SkillLoader:
    """
    Discovers, loads, and manages skills from Python modules.
    
    Req 4: Skill definition and lifecycle
    Req 5: Skill discovery and loading
    """
    
    def __init__(self, skills_dir: Optional[str] = None):
        self.skills_dir = Path(skills_dir or os.getenv("ORACLE_SKILLS_DIR", "skills/"))
        self.skills: Dict[str, SkillModule] = {}
        self._builtin_tools: set = set()
        
        # Req 5.2: Create directory if missing
        if not self.skills_dir.exists():
            self.skills_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created skills directory: {self.skills_dir}")
            
    def register_builtin_tools(self, tool_names: List[str]):
        """Register built-in tool names to detect conflicts."""
        self._builtin_tools = set(tool_names)
        
    def load_all(self) -> Dict[str, SkillToolDef]:
        """
        Load all skills from the skills directory.
        
        Req 5.1, 5.3, 5.5: Scan, import, validate, and register skills.
        """
        self.skills = {}
        all_tools: Dict[str, SkillToolDef] = {}
        
        # Req 5.3: Scan for .py files
        py_files = list(self.skills_dir.glob("*.py"))
        
        for py_file in py_files:
            skill_name = py_file.stem
            
            try:
                skill_module = self._load_skill_module(skill_name, py_file)
                
                if not skill_module:
                    continue
                    
                # Req 4.1, 5.3: Validate TOOLS attribute
                if not hasattr(skill_module.module, "TOOLS"):
                    logger.debug(f"Skipping {py_file.name}: no TOOLS attribute")
                    continue
                    
                tools_attr = skill_module.module.TOOLS
                
                if not isinstance(tools_attr, (list, tuple)):
                    logger.error(f"Skill '{skill_name}': TOOLS must be a list")
                    continue
                    
                # Process each tool
                for tool_def in tools_attr:
                    validated_tool = self._validate_tool(skill_name, tool_def)
                    
                    if validated_tool:
                        # Req 5.7: Handle name conflicts
                        tool_name = validated_tool.name
                        
                        if tool_name in self._builtin_tools:
                            tool_name = f"{skill_name}__{tool_name}"
                            logger.warning(
                                f"Skill tool '{validated_tool.name}' conflicts with built-in, "
                                f"renamed to '{tool_name}'"
                            )
                            validated_tool.name = tool_name
                            
                        skill_module.tools.append(validated_tool)
                        all_tools[tool_name] = validated_tool
                        
                # Req 4.3: Call setup
                asyncio.create_task(skill_module.setup())
                
                self.skills[skill_name] = skill_module
                logger.info(f"Loaded skill '{skill_name}' with {len(skill_module.tools)} tools")
                
            except Exception as e:
                # Req 4.5, 5.5: Log error and continue loading other skills
                logger.error(f"Failed to load skill '{skill_name}': {e}")
                continue
                
        logger.info(f"SkillLoader: {len(self.skills)} skills, {len(all_tools)} tools loaded")
        return all_tools
        
    def _load_skill_module(self, name: str, file_path: Path) -> Optional[SkillModule]:
        """Import a skill Python module."""
        try:
            spec = importlib.util.spec_from_file_location(name, file_path)
            if not spec or not spec.loader:
                logger.error(f"Cannot load spec for {file_path}")
                return None
                
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            return SkillModule(name, module, file_path)
            
        except Exception as e:
            logger.error(f"Error importing skill '{name}': {e}")
            return None
            
    def _validate_tool(
        self, 
        skill_name: str, 
        tool_def: Any
    ) -> Optional[SkillToolDef]:
        """
        Validate a SkillToolDef.
        
        Req 4.6: Validate fields and handler.
        """
        try:
            # Handle both dataclass and dict formats
            if isinstance(tool_def, dict):
                name = tool_def.get("name")
                description = tool_def.get("description")
                parameters = tool_def.get("parameters", {})
                handler = tool_def.get("handler")
            else:
                # Assume dataclass
                name = getattr(tool_def, "name", None)
                description = getattr(tool_def, "description", None)
                parameters = getattr(tool_def, "parameters", {})
                handler = getattr(tool_def, "handler", None)
                
            # Validate required fields
            if not name or not isinstance(name, str):
                logger.error(f"Skill '{skill_name}': tool missing valid 'name'")
                return None
                
            if not description or not isinstance(description, str):
                logger.error(f"Skill '{skill_name}': tool '{name}' missing valid 'description'")
                return None
                
            if not parameters or not isinstance(parameters, dict):
                logger.error(f"Skill '{skill_name}': tool '{name}' missing valid 'parameters'")
                return None
                
            # Req 4.6: Validate handler is callable
            if not handler or not callable(handler):
                logger.error(f"Skill '{skill_name}': tool '{name}' missing callable 'handler'")
                return None
                
            return SkillToolDef(
                name=name,
                description=description,
                parameters=parameters,
                handler=handler
            )
            
        except Exception as e:
            logger.error(f"Error validating tool in skill '{skill_name}': {e}")
            return None
            
    def reload(self) -> Dict[str, SkillToolDef]:
        """
        Reload skills from directory.
        
        Req 5.6: Re-scan and re-import changed modules.
        """
        logger.info("Reloading skills...")
        
        # Teardown existing skills
        for skill in self.skills.values():
            asyncio.create_task(skill.teardown())
            
        # Clear and reload
        return self.load_all()
        
    async def teardown_all(self):
        """
        Call teardown on all loaded skills.
        
        Req 5.5: Clean shutdown.
        """
        logger.info("Tearing down all skills")
        
        for skill_name, skill in self.skills.items():
            try:
                await skill.teardown()
            except Exception as e:
                logger.error(f"Error tearing down skill '{skill_name}': {e}")
                
    def get_tools(self) -> List[Tuple[str, SkillToolDef]]:
        """Get all loaded tools."""
        tools = []
        for skill_name, skill in self.skills.items():
            for tool in skill.tools:
                tools.append((tool.name, tool))
        return tools
```

---

### Week 2: Tool Registry & Integration

#### Day 7-8: Implement Tool Registry

**File:** `src/oracle/tool_registry.py`

```python
"""
Unified Tool Registry aggregating built-in, MCP, and skill tools.
Implements Requirement 6 from MCP Skills Integration spec.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from google.genai import types

from .mcp_registry import MCPRegistry
from .skill_loader import SkillLoader, SkillToolDef
from .agent_system import ToolExecutor

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Aggregates tools from multiple sources and provides unified dispatch.
    
    Req 6: Unified registry for built-in, MCP, and skill tools.
    """
    
    def __init__(
        self,
        tool_executor: ToolExecutor,
        mcp_registry: Optional[MCPRegistry] = None,
        skill_loader: Optional[SkillLoader] = None
    ):
        self.tool_executor = tool_executor
        self.mcp_registry = mcp_registry
        self.skill_loader = skill_loader
        
        # Tool storage
        self._builtin_declarations: List[types.FunctionDeclaration] = []
        self._mcp_declarations: List[types.FunctionDeclaration] = []
        self._skill_declarations: List[types.FunctionDeclaration] = []
        
        # Skill tool handlers
        self._skill_handlers: Dict[str, SkillToolDef] = {}
        
        # Statistics
        self._stats: Dict[str, Dict[str, int]] = {}
        
        self._build_builtin_declarations()
        
    def _build_builtin_declarations(self):
        """Build FunctionDeclarations for the 4 built-in tools."""
        self._builtin_declarations = [
            types.FunctionDeclaration(
                name="shell_execute",
                description="Execute a shell command",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "command": types.Schema(type=types.Type.STRING)
                    },
                    required=["command"]
                )
            ),
            types.FunctionDeclaration(
                name="vision_capture",
                description="Capture a screenshot",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "reason": types.Schema(type=types.Type.STRING)
                    }
                )
            ),
            types.FunctionDeclaration(
                name="file_system_ops",
                description="Read, write, list, or delete files",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "operation": types.Schema(type=types.Type.STRING),
                        "path": types.Schema(type=types.Type.STRING),
                        "content": types.Schema(type=types.Type.STRING)
                    },
                    required=["operation", "path"]
                )
            ),
            types.FunctionDeclaration(
                name="http_fetch",
                description="Make HTTP requests",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "url": types.Schema(type=types.Type.STRING),
                        "method": types.Schema(type=types.Type.STRING),
                        "headers": types.Schema(type=types.Type.OBJECT),
                        "body": types.Schema(type=types.Type.STRING)
                    },
                    required=["url"]
                )
            )
        ]
        
    async def initialize(self):
        """Initialize MCP and skill registries."""
        builtin_names = [d.name for d in self._builtin_declarations]
        
        if self.mcp_registry:
            self.mcp_registry.register_builtin_tools(builtin_names)
            await self.mcp_registry.build_registry()
            self._mcp_declarations = self.mcp_registry.get_function_declarations()
            
        if self.skill_loader:
            self.skill_loader.register_builtin_tools(builtin_names)
            skill_tools = self.skill_loader.load_all()
            self._skill_handlers = skill_tools
            self._skill_declarations = self._build_skill_declarations(skill_tools)
            
        # Req 6.6: Log tool counts
        counts = self.tool_count()
        logger.info(
            f"ToolRegistry initialized: "
            f"builtin={counts['builtin']}, "
            f"mcp={counts['mcp']}, "
            f"skill={counts['skill']}"
        )
        
    def _build_skill_declarations(
        self, 
        skill_tools: Dict[str, SkillToolDef]
    ) -> List[types.FunctionDeclaration]:
        """Build FunctionDeclarations from skill tools."""
        declarations = []
        
        for tool_name, tool_def in skill_tools.items():
            declaration = types.FunctionDeclaration(
                name=tool_name,
                description=tool_def.description,
                parameters=self._dict_to_schema(tool_def.parameters)
            )
            declarations.append(declaration)
            
        return declarations
        
    def _dict_to_schema(self, params: Dict[str, Any]) -> types.Schema:
        """Convert dict parameters to Gemini Schema."""
        # Simplified conversion - expand as needed
        properties = {}
        required = []
        
        for name, prop_def in params.items():
            if isinstance(prop_def, dict):
                prop_type = prop_def.get("type", "string")
                schema = types.Schema(
                    type=getattr(types.Type, prop_type.upper(), types.Type.STRING),
                    description=prop_def.get("description", "")
                )
                if prop_def.get("enum"):
                    schema.enum = prop_def["enum"]
                properties[name] = schema
                
                if prop_def.get("required"):
                    required.append(name)
            else:
                properties[name] = types.Schema(type=types.Type.STRING)
                
        return types.Schema(
            type=types.Type.OBJECT,
            properties=properties,
            required=required
        )
        
    def get_function_declarations(self) -> List[types.FunctionDeclaration]:
        """
        Get all function declarations.
        
        Req 6.2, 6.3: Return merged list for model config.
        """
        return (
            self._builtin_declarations +
            self._mcp_declarations +
            self._skill_declarations
        )
        
    async def dispatch(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Route tool call to appropriate handler.
        
        Req 6.4: Unified dispatch with exception handling.
        """
        # Track stats
        if name not in self._stats:
            self._stats[name] = {"calls": 0, "failures": 0}
        self._stats[name]["calls"] += 1
        
        try:
            # Built-in tools
            if name in ["shell_execute", "vision_capture", "file_system_ops", "http_fetch"]:
                return await self._dispatch_builtin(name, args)
                
            # MCP tools
            if self.mcp_registry and name in [d.name for d in self._mcp_declarations]:
                return await self.mcp_registry.dispatch(name, args)
                
            # Skill tools
            if name in self._skill_handlers:
                return await self._dispatch_skill(name, args)
                
            # Unknown tool
            return {"success": False, "error": f"Unknown tool: {name}"}
            
        except Exception as e:
            # Req 6.4: Never raise exceptions
            self._stats[name]["failures"] += 1
            logger.error(f"Tool dispatch error for '{name}': {e}")
            return {"success": False, "error": str(e)}
            
    async def _dispatch_builtin(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch to built-in tool executor."""
        method = getattr(self.tool_executor, name)
        
        if asyncio.iscoroutinefunction(method):
            return await method(**args)
        else:
            return method(**args)
            
    async def _dispatch_skill(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch to skill handler."""
        tool_def = self._skill_handlers[name]
        handler = tool_def.handler
        
        # Req 9.2: Log skill tool call
        logger.info(f"Skill tool call: {name} (args: {str(args)[:120]})")
        
        try:
            if asyncio.iscoroutinefunction(handler):
                result = await handler(**args)
            else:
                result = handler(**args)
                
            # Ensure Tool_Envelope format
            if isinstance(result, dict) and "success" in result:
                return result
            else:
                return {"success": True, "result": result}
                
        except Exception as e:
            logger.error(f"Skill tool '{name}' error: {e}")
            return {"success": False, "error": str(e)}
            
    def tool_count(self) -> Dict[str, int]:
        """
        Get tool counts by source.
        
        Req 6.5: Observability counts.
        """
        return {
            "builtin": len(self._builtin_declarations),
            "mcp": len(self._mcp_declarations),
            "skill": len(self._skill_declarations)
        }
        
    def get_stats(self) -> Dict[str, Dict[str, int]]:
        """
        Get cumulative call statistics.
        
        Req 6.5: Track usage per tool.
        """
        return self._stats.copy()
```

#### Day 9-10: Integrate with OracleAgent

**Modify:** `src/oracle/agent_system.py`

```python
"""
Modifications to OracleAgent for ToolRegistry integration.
Implements Requirement 7 from MCP Skills Integration spec.
"""

# Add to imports
from .mcp_client import MCPClient
from .mcp_registry import MCPRegistry
from .skill_loader import SkillLoader
from .tool_registry import ToolRegistry


class OracleAgent:
    """
    Enhanced OracleAgent with MCP and Skill support.
    
    Req 7: Integration of ToolRegistry into existing agent.
    """
    
    def __init__(self, config: Optional[OracleConfig] = None):
        self.config = config or OracleConfig()
        
        # Existing components
        self.persistence = PersistenceLayer(self.config.db_path)
        self.tool_executor = ToolExecutor(
            self.config.project_root,
            self.config.shell_timeout,
            self.config.http_timeout
        )
        
        # Req 7.1: Initialize new components
        self.mcp_client = MCPClient()
        self.mcp_registry = MCPRegistry(self.mcp_client)
        self.skill_loader = SkillLoader()
        
        self._tool_registry = ToolRegistry(
            tool_executor=self.tool_executor,
            mcp_registry=self.mcp_registry,
            skill_loader=self.skill_loader
        )
        
        # Initialize async components
        asyncio.run(self._async_init())
        
    async def _async_init(self):
        """Async initialization."""
        await self.mcp_client.initialize()
        await self._tool_registry.initialize()
        
    async def close(self):
        """
        Clean shutdown.
        
        Req 7.5: Shutdown MCP and skills.
        """
        await self.mcp_client.shutdown()
        await self.skill_loader.teardown_all()
        
    def _build_config(self) -> types.GenerateContentConfig:
        """
        Build model config with tool declarations.
        
        Req 7.2: Use ToolRegistry for function declarations.
        """
        declarations = self._tool_registry.get_function_declarations()
        
        return types.GenerateContentConfig(
            temperature=0.7,
            tools=[types.Tool(function_declarations=declarations)]
        )
        
    async def _dispatch(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Dispatch tool call via ToolRegistry.
        
        Req 7.3: Delegate to ToolRegistry.
        Req 7.4: Built-in tools remain functional.
        """
        return await self._tool_registry.dispatch(name, args)
```

---

## 📅 Phases 1-6: Implementation Roadmap

### Phase 1: Model Router (Weeks 3-4)

**Goal:** Multi-LLM support with failover and streaming

**Key Components:**
```python
# src/oracle/model_router.py

class ModelRouter:
    """Route requests to best available LLM provider."""
    
class GeminiAdapter(ModelProvider): ...
class AnthropicAdapter(ModelProvider): ...
class OpenAIAdapter(ModelProvider): ...
class OllamaAdapter(ModelProvider): ...
```

**Deliverables:**
- [ ] ModelProvider protocol
- [ ] 4 provider adapters
- [ ] Failover chain with health checks
- [ ] Streaming support
- [ ] Cost tracking

### Phase 2: Multi-Agent (Weeks 5-6)

**Goal:** Agent graph orchestration with A2A protocol

**Key Components:**
```python
# src/oracle/agent_graph.py

class AgentGraph:
    """DAG orchestrator for multi-agent workflows."""
    
class WorkflowEngine:
    """Execute workflows with conditional branching."""
    
class A2AProtocol:
    """Agent-to-agent communication."""
```

**Deliverables:**
- [ ] AgentNode base class
- [ ] Agent graph with DAG validation
- [ ] Workflow engine with fan-out/fan-in
- [ ] A2A protocol implementation
- [ ] Conditional branching

### Phase 3: Interface Layer (Weeks 7-9)

**Goal:** TUI, GUI, and messaging adapters

**Key Components:**
```python
# src/oracle/interfaces/

class InterfaceAdapter(Protocol): ...
class InterfaceBus:
    """Route messages between interfaces and agents."""
    
# TUI
tui/app.py          # Textual interface
tui/components.py   # Chat, logs, metrics

# GUI
gui/main_window.py  # PyQt6 interface
gui/system_tray.py  # Quick actions

# Messaging
messaging/telegram_adapter.py
messaging/discord_adapter.py
messaging/slack_adapter.py
messaging/whatsapp_adapter.py
messaging/signal_adapter.py
messaging/teams_adapter.py
```

**Deliverables:**
- [ ] TUI with streaming support
- [ ] GUI with system tray
- [ ] 6 messaging adapters
- [ ] Session isolation per channel
- [ ] Mobile node bridge

### Phase 4: Knowledge Layer (Weeks 10-11)

**Goal:** Vector embeddings and Markdown vault

**Key Components:**
```python
# src/oracle/knowledge/

class VectorStore:
    """ChromaDB/Pinecone vector storage."""
    
class MarkdownVault:
    """Git-friendly Markdown persistence."""
    
class KnowledgeGraph:
    """Entity and relationship storage."""
```

**Deliverables:**
- [ ] Embedding providers (local + cloud)
- [ ] ChromaDB integration
- [ ] Semantic search
- [ ] Markdown vault with Git
- [ ] Knowledge graph

### Phase 5: Browser + Skills Ecosystem (Weeks 12-13)

**Goal:** CDP browser control and community skills

**Key Components:**
```python
# src/oracle/browser/

class BrowserAgent:
    """Playwright-based browser automation."""
    
# src/oracle/skills/

class SkillRegistry:
    """Community skill registry."""
    
class SkillSandbox:
    """Isolated skill execution."""
```

**Deliverables:**
- [ ] Browser automation (Playwright)
- [ ] Skill registry with search/install
- [ ] Skill sandboxing
- [ ] CDP tools integration

### Phase 6: Mobile + Production (Weeks 14-15)

**Goal:** Mobile apps and production features

**Key Components:**
```python
# src/oracle/mobile/

class MobileNode:
    """WebSocket bridge for iOS/Android."""
    
class HeartbeatScheduler:
    """Proactive task checking."""
```

**Deliverables:**
- [ ] iOS companion app
- [ ] Android companion app
- [ ] Heartbeat scheduler
- [ ] RBAC system
- [ ] Production hardening

---

## 🧪 Testing Strategy

### Property-Based Tests (Hypothesis)

```python
# tests/test_tool_registry_properties.py

from hypothesis import given, settings, strategies as st

class TestToolRegistryProperties:
    """Property-based tests for ToolRegistry."""
    
    @settings(max_examples=100)
    @given(
        tool_name=st.text(min_size=1, max_size=50),
        args=st.dictionaries(st.text(), st.one_of(st.text(), st.integers()))
    )
    def test_dispatch_never_raises(self, tool_name, args):
        """Property 10: Dispatch always returns dict with success key."""
        registry = create_test_registry()
        result = asyncio.run(registry.dispatch(tool_name, args))
        
        assert isinstance(result, dict)
        assert "success" in result
        
    @settings(max_examples=50)
    @given(
        builtin_count=st.integers(min_value=4, max_value=4),
        mcp_count=st.integers(min_value=0, max_value=10),
        skill_count=st.integers(min_value=0, max_value=10)
    )
    def test_tool_count_consistency(self, builtin_count, mcp_count, skill_count):
        """Property 12: Sum of counts equals total declarations."""
        registry = create_test_registry_with_counts(
            builtin_count, mcp_count, skill_count
        )
        
        counts = registry.tool_count()
        declarations = registry.get_function_declarations()
        
        assert sum(counts.values()) == len(declarations)
```

---

## 📊 Success Criteria

| Phase | Criteria | Measurement |
|-------|----------|-------------|
| 0 | MCP + Skills integrated | All 10 requirements pass tests |
| 1 | 4+ LLM providers | Failover <5s, streaming works |
| 2 | Multi-agent workflows | 3+ agents, conditional branching |
| 3 | 3 interfaces working | TUI, GUI, 2+ messaging platforms |
| 4 | Semantic search | 90%+ recall accuracy |
| 5 | Browser automation | Full CDP control, 100+ skills |
| 6 | Mobile apps | iOS + Android published |

---

*Integration Plan Version: 5.0.0*  
*Based on Kiro Specifications*  
*Last Updated: 2026-03-15*
