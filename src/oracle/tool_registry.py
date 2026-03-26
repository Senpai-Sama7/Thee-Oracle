#!/usr/bin/env python3
"""
Unified Tool Registry for Oracle Agent 5.0
Aggregates tools from built-in, MCP, and skill sources.

Implements Requirement 6 from MCP Skills Integration spec.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, cast

try:
    from google.genai import types

    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("google-genai not installed. Gemini types unavailable.")

from .mcp_registry import MCPRegistry
from .skill_loader import SkillLoader, SkillToolDef

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Aggregates tools from multiple sources and provides unified dispatch.

    Req 6: Unified registry for built-in, MCP, and skill tools.
    """

    def __init__(
        self,
        tool_executor: Any,  # ToolExecutor instance
        mcp_registry: Optional[MCPRegistry] = None,
        skill_loader: Optional[SkillLoader] = None,
    ) -> None:
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

        if GENAI_AVAILABLE:
            self._build_builtin_declarations()

    def _build_builtin_declarations(self) -> None:
        """Build FunctionDeclarations for the 4 built-in tools."""
        self._builtin_declarations = [
            types.FunctionDeclaration(
                name="shell_execute",
                description=(
                    "Execute a bash command on the local system. "
                    "Returns stdout, stderr, and exit code. "
                    "Use for system inspection, file management, and process control."
                ),
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "command": types.Schema(type=types.Type.STRING, description="Bash command string to execute")
                    },
                    required=["command"],
                ),
            ),
            types.FunctionDeclaration(
                name="vision_capture",
                description=(
                    "Capture the current desktop state as a PNG image. "
                    "Use to observe GUI application state or verify "
                    "the result of UI interactions."
                ),
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "reason": types.Schema(
                            type=types.Type.STRING, description="Reason for capturing screenshot (for logging)"
                        )
                    },
                ),
            ),
            types.FunctionDeclaration(
                name="file_system_ops",
                description=(
                    "Read, write, list, or delete files in the workspace. "
                    "Operations are sandboxed to the project root for safety."
                ),
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "operation": types.Schema(
                            type=types.Type.STRING,
                            enum=["read", "write", "list", "delete"],
                            description="File operation to perform",
                        ),
                        "path": types.Schema(
                            type=types.Type.STRING, description="File or directory path (relative to workspace)"
                        ),
                        "content": types.Schema(
                            type=types.Type.STRING, description="Content to write (for write operation)"
                        ),
                    },
                    required=["operation", "path"],
                ),
            ),
            types.FunctionDeclaration(
                name="http_fetch",
                description=(
                    "Make HTTP requests to external APIs or websites. Returns status code, headers, and truncated body."
                ),
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "url": types.Schema(type=types.Type.STRING, description="URL to fetch"),
                        "method": types.Schema(
                            type=types.Type.STRING,
                            enum=["GET", "POST", "PUT", "DELETE", "PATCH"],
                            description="HTTP method",
                        ),
                        "headers": types.Schema(type=types.Type.OBJECT, description="Optional request headers"),
                        "body": types.Schema(type=types.Type.STRING, description="Request body for POST/PUT"),
                    },
                    required=["url"],
                ),
            ),
        ]

    async def initialize(self) -> None:
        """Initialize MCP and skill registries."""
        builtin_names = cast(List[str], [d.name for d in self._builtin_declarations if d.name])

        if self.mcp_registry:
            self.mcp_registry.register_builtin_tools(builtin_names)
            await self.mcp_registry.build_registry()
            self._mcp_declarations = self.mcp_registry.get_function_declarations()

        if self.skill_loader:
            self.skill_loader.register_builtin_tools(builtin_names)
            skill_tools = self.skill_loader.load_all()
            self._skill_handlers = skill_tools
            self._skill_declarations = self._build_skill_declarations(skill_tools)
        else:
            self._skill_handlers = {}
            self._skill_declarations = []

        # Req 6.6: Log tool counts
        counts = self.tool_count()
        logger.info(
            f"ToolRegistry initialized: builtin={counts['builtin']}, mcp={counts['mcp']}, skill={counts['skill']}"
        )

    def _build_skill_declarations(self, skill_tools: Dict[str, SkillToolDef]) -> List[types.FunctionDeclaration]:
        """Build FunctionDeclarations from skill tools."""
        if not GENAI_AVAILABLE:
            return []

        declarations = []

        for tool_name, tool_def in skill_tools.items():
            declaration = types.FunctionDeclaration(
                name=tool_name, description=tool_def.description, parameters=self._dict_to_schema(tool_def.parameters)
            )
            declarations.append(declaration)

        return declarations

    def _dict_to_schema(self, params: Dict[str, Any]) -> types.Schema:
        """Convert dict parameters to Gemini Schema."""
        if not GENAI_AVAILABLE:
            return types.Schema(type=types.Type.OBJECT)

        # Simplified conversion - expand as needed
        properties = {}
        required = []

        for name, prop_def in params.items():
            if isinstance(prop_def, dict):
                prop_type = prop_def.get("type", "string")
                type_map = {
                    "string": types.Type.STRING,
                    "integer": types.Type.INTEGER,
                    "number": types.Type.NUMBER,
                    "boolean": types.Type.BOOLEAN,
                    "array": types.Type.ARRAY,
                    "object": types.Type.OBJECT,
                }
                schema = types.Schema(
                    type=type_map.get(prop_type.lower(), types.Type.STRING), description=prop_def.get("description", "")
                )
                if prop_def.get("enum"):
                    schema.enum = prop_def["enum"]
                properties[name] = schema

                if prop_def.get("required"):
                    required.append(name)
            else:
                properties[name] = types.Schema(type=types.Type.STRING)

        return types.Schema(type=types.Type.OBJECT, properties=properties, required=required)

    def get_function_declarations(self) -> List[types.FunctionDeclaration]:
        """
        Get all function declarations.

        Req 6.2, 6.3: Return merged list for model config.
        """
        return self._builtin_declarations + self._mcp_declarations + self._skill_declarations

    def get_skill_catalog(self) -> List[Dict[str, Any]]:
        """Return discovered skill metadata for prompt-time selection."""
        if not self.skill_loader:
            return []
        return self.skill_loader.get_catalog()

    def build_skill_prompt_context(self, prompt: str, max_skills: int = 3) -> str:
        """Build prompt-time skill context for the current request."""
        if not self.skill_loader:
            return ""
        return self.skill_loader.build_prompt_context(prompt, max_skills=max_skills)

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
        method = getattr(self.tool_executor, name, None)
        if not method:
            return {"success": False, "error": f"Tool method {name} not found"}

        if asyncio.iscoroutinefunction(method):
            res: Dict[str, Any] = await method(**args)
            return res
        else:
            res_sync: Dict[str, Any] = method(**args)
            return res_sync

    async def _dispatch_skill(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch to skill handler."""
        tool_def = self._skill_handlers[name]
        handler = tool_def.handler

        # Req 9.2: Log skill tool call
        logger.info(f"Skill tool call: {name} (args: {str(args)[:120]})")

        try:
            if asyncio.iscoroutinefunction(handler):
                result = await cast(Any, handler)(**args)
            else:
                result = cast(Any, handler)(**args)

            # Ensure Tool_Envelope format
            if isinstance(result, dict) and "success" in result:
                return cast(Dict[str, Any], result)
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
            "skill": len(self._skill_declarations),
        }

    def get_stats(self) -> Dict[str, Dict[str, int]]:
        """
        Get cumulative call statistics.

        Req 6.5: Track usage per tool.
        """
        return self._stats.copy()
