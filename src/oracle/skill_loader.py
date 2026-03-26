#!/usr/bin/env python3
"""
Skill Loader for Oracle Agent 5.0
Discovers, loads, and manages skills from Python modules.

Implements Requirements 4-5 from MCP Skills Integration spec.
"""

import asyncio
import importlib.util
import logging
import os
import sys
from dataclasses import dataclass, field
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
    parameters: Dict[str, Any] = field(default_factory=dict)
    handler: Optional[Callable[..., Any]] = None

    def __post_init__(self) -> None:
        if self.handler is None:
            raise ValueError("SkillToolDef.handler cannot be None")


class SkillModule:
    """Wrapper for loaded skill module."""

    def __init__(self, name: str, module: Any, file_path: Path) -> None:
        self.name = name
        self.module = module
        self.file_path = file_path
        self.tools: List[SkillToolDef] = []

    async def setup(self) -> None:
        """Call setup() if defined (Req 4.3)."""
        if hasattr(self.module, "setup"):
            setup_func = self.module.setup
            if asyncio.iscoroutinefunction(setup_func):
                await setup_func()
            else:
                setup_func()

    async def teardown(self) -> None:
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

    def __init__(self, skills_dir: Optional[str] = None) -> None:
        self.skills_dir = Path(str(skills_dir or os.getenv("ORACLE_SKILLS_DIR", "skills/")))
        self.skills: Dict[str, SkillModule] = {}
        self._builtin_tools: set[str] = set()

        # Req 5.2: Create directory if missing
        if not self.skills_dir.exists():
            self.skills_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created skills directory: {self.skills_dir}")

    def register_builtin_tools(self, tool_names: List[str]) -> None:
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
                                f"Skill tool '{validated_tool.name}' conflicts with built-in, renamed to '{tool_name}'"
                            )
                            validated_tool.name = tool_name

                        # Check for duplicate within this skill load
                        if tool_name in all_tools:
                            logger.warning(f"Duplicate tool name '{tool_name}' in skill '{skill_name}', skipping")
                            continue

                        skill_module.tools.append(validated_tool)
                        all_tools[tool_name] = validated_tool

                # Req 4.3: Call setup
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(skill_module.setup())
                except RuntimeError:
                    # No running loop, safely run synchronously
                    asyncio.run(skill_module.setup())

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
            resolved_file = file_path.resolve()
            resolved_skills_dir = self.skills_dir.resolve()

            # Security Hardening: Enforce strict path containment
            if not resolved_file.is_relative_to(resolved_skills_dir):
                logger.error(f"Security: Skill path {resolved_file} is outside skills directory {resolved_skills_dir}")
                return None

            # Security Hardening: Ensure file and directory permissions are safe
            # i.e., not world-writable (st_mode & 0o002 == 0)
            try:
                if resolved_file.stat().st_mode & 0o002:
                    logger.error(f"Security: Skill file {resolved_file} is world-writable, refusing to load.")
                    return None
                if resolved_skills_dir.stat().st_mode & 0o002:
                    logger.error(
                        f"Security: Skills directory {resolved_skills_dir} is world-writable, refusing to load."
                    )
                    return None
            except FileNotFoundError:
                logger.error("Security: Could not stat file/directory for permissions check.")
                return None

            spec = importlib.util.spec_from_file_location(name, resolved_file)
            if not spec or not spec.loader:
                logger.error(f"Cannot load spec for {resolved_file}")
                return None

            module = importlib.util.module_from_spec(spec)

            # Add skills directory to path for imports
            if str(resolved_skills_dir) not in sys.path:
                sys.path.insert(0, str(resolved_skills_dir))

            spec.loader.exec_module(module)

            return SkillModule(name, module, resolved_file)

        except Exception as e:
            logger.error(f"Error importing skill '{name}': {e}")
            return None

    def _validate_tool(self, skill_name: str, tool_def: Any) -> Optional[SkillToolDef]:
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
            elif isinstance(tool_def, SkillToolDef):
                # Already a valid SkillToolDef
                return tool_def
            else:
                # Try to extract from object attributes
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

            if not isinstance(parameters, dict):
                logger.error(f"Skill '{skill_name}': tool '{name}' missing valid 'parameters'")
                return None

            # Req 4.6: Validate handler is callable
            if not handler or not callable(handler):
                logger.error(f"Skill '{skill_name}': tool '{name}' missing callable 'handler'")
                return None

            return SkillToolDef(name=name, description=description, parameters=parameters, handler=handler)

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

    async def teardown_all(self) -> None:
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
        for _skill_name, skill in self.skills.items():
            for tool in skill.tools:
                tools.append((tool.name, tool))
        return tools
