#!/usr/bin/env python3
"""
MCP Registry for Oracle Agent 5.0
Translates MCP tools to Gemini FunctionDeclarations and routes calls.

Implements Requirements 2 and 3 from MCP Skills Integration spec.
"""

import logging
from typing import Any, Dict, List, Tuple

try:
    from google.genai import types

    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("google-genai not installed. Gemini types unavailable.")

from .mcp_client import MCPClient

logger = logging.getLogger(__name__)


class MCPRegistry:
    """
    Translates MCP tools to Gemini FunctionDeclarations and routes calls.

    Req 2: Tool discovery and schema translation
    Req 3: Tool invocation routing
    """

    def __init__(self, mcp_client: MCPClient):
        if not GENAI_AVAILABLE:
            raise RuntimeError("google-genai required for MCPRegistry")

        self.mcp_client = mcp_client
        self._tool_map: Dict[str, Tuple[str, str]] = {}  # registered_name -> (server, original_name)
        self._declarations: List[types.FunctionDeclaration] = []
        self._builtin_tools: set[str] = set()  # To detect conflicts

    def register_builtin_tools(self, tool_names: List[str]) -> None:
        """Register built-in tool names to detect conflicts."""
        self._builtin_tools = set(tool_names)

    async def build_registry(self) -> None:
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
                logger.warning(f"MCP tool '{tool_name}' conflicts with built-in, renamed to '{registered_name}'")
            elif registered_name in self._tool_map:
                # Additional conflict with another MCP tool
                registered_name = f"{server_name}__{tool_name}"
                logger.warning(f"MCP tool name collision, renamed to '{registered_name}'")

            # Store mapping for dispatch
            self._tool_map[registered_name] = (server_name, tool_name)

            # Req 2.2: Translate schema to FunctionDeclaration
            declaration = self._translate_tool(registered_name, tool_def)
            self._declarations.append(declaration)

        logger.info(f"MCP Registry: {len(self._declarations)} tools registered")

    def _translate_tool(self, registered_name: str, tool_def: Dict[str, Any]) -> types.FunctionDeclaration:
        """
        Translate MCP tool definition to Gemini FunctionDeclaration.

        Req 2.2, 2.5, 10: Schema translation with fallback descriptions.
        """
        original_name = tool_def.get("name", registered_name)
        description = str(tool_def.get("description", ""))

        # Req 2.5: Fallback description
        if not description:
            description = f"Tool {original_name} from MCP server"

        # Req 10: Translate JSON Schema to Gemini parameters
        input_schema = tool_def.get("inputSchema", {})
        parameters = self._translate_schema(input_schema)

        return types.FunctionDeclaration(name=registered_name, description=description, parameters=parameters)

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
                logger.warning(f"JSON Schema keyword '{keyword}' not supported, will be omitted")

        schema_kwargs: Dict[str, Any] = {}

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
        if "properties" in json_schema and json_schema.get("type") == "object":
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
            return {"success": False, "error": f"Unknown MCP tool: {tool_name}"}

        server_name, original_tool_name = self._tool_map[tool_name]

        # Req 9.1: Log structured tool call
        logger.info(f"MCP tool call: {tool_name} on {server_name} (args: {str(arguments)[:120]})")

        # Route to MCP client
        return await self.mcp_client.call_tool(server_name, original_tool_name, arguments)
