#!/usr/bin/env python3
"""
Skill Loader for Oracle Agent 5.0
Discovers, loads, and manages legacy Python skills and Claude-style SKILL.md packages.
"""

from __future__ import annotations

import asyncio
import importlib.util
import logging
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

try:
    import yaml
except ImportError:  # pragma: no cover - optional dependency
    yaml = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

_STOP_WORDS = {
    "and",
    "are",
    "for",
    "from",
    "into",
    "that",
    "the",
    "this",
    "use",
    "with",
    "when",
}
_MAX_SKILL_SUMMARY_REFERENCES = 3
_MAX_SELECTED_SKILLS = 3
_MAX_SKILL_INSTRUCTION_CHARS = 3000
_MAX_TOTAL_PROMPT_CONTEXT_CHARS = 9000


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


@dataclass
class SkillFrontmatter:
    """Frontmatter metadata parsed from SKILL.md."""

    name: str
    description: str
    triggers: List[str] = field(default_factory=list)
    entrypoint: Optional[str] = None
    allowed_tools: List[str] = field(default_factory=list)


@dataclass
class SkillResources:
    """Supporting files bundled with a skill package."""

    scripts: List[str] = field(default_factory=list)
    references: List[str] = field(default_factory=list)
    assets: List[str] = field(default_factory=list)


class SkillModule:
    """Wrapper for a loaded skill module or an instruction-only skill package."""

    def __init__(
        self,
        name: str,
        module: Any,
        file_path: Path,
        *,
        root_path: Optional[Path] = None,
        source_type: str = "legacy_module",
        manifest_path: Optional[Path] = None,
        frontmatter: Optional[SkillFrontmatter] = None,
        instructions: str = "",
        resources: Optional[SkillResources] = None,
    ) -> None:
        self.name = name
        self.module = module
        self.file_path = file_path
        self.root_path = root_path or file_path.parent
        self.source_type = source_type
        self.manifest_path = manifest_path
        self.frontmatter = frontmatter
        self.instructions = instructions.strip()
        self.resources = resources or SkillResources()
        self.tools: List[SkillToolDef] = []

    async def setup(self) -> None:
        """Call setup() if defined."""
        if self.module is None or not hasattr(self.module, "setup"):
            return
        setup_func = self.module.setup
        if asyncio.iscoroutinefunction(setup_func):
            await setup_func()
        else:
            setup_func()

    async def teardown(self) -> None:
        """Call teardown() if defined."""
        if self.module is None or not hasattr(self.module, "teardown"):
            return
        teardown_func = self.module.teardown
        try:
            if asyncio.iscoroutinefunction(teardown_func):
                await teardown_func()
            else:
                teardown_func()
        except Exception as exc:
            logger.error("Error in teardown for skill '%s': %s", self.name, exc)

    @property
    def description(self) -> str:
        if self.frontmatter:
            return self.frontmatter.description
        description = getattr(self.module, "SKILL_DESCRIPTION", None) if self.module is not None else None
        if isinstance(description, str) and description.strip():
            return description.strip()
        if self.tools:
            tool_names = ", ".join(tool.name for tool in self.tools[:5])
            suffix = "..." if len(self.tools) > 5 else ""
            return f"Legacy Python skill exposing tools: {tool_names}{suffix}"
        return "Legacy skill package"

    @property
    def triggers(self) -> List[str]:
        if self.frontmatter:
            return self.frontmatter.triggers
        return []

    @property
    def allowed_tools(self) -> List[str]:
        if self.frontmatter:
            return self.frontmatter.allowed_tools
        return []

    def tool_names(self) -> List[str]:
        return [tool.name for tool in self.tools]

    def catalog_entry(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "source_type": self.source_type,
            "triggers": list(self.triggers),
            "allowed_tools": list(self.allowed_tools),
            "tool_names": self.tool_names(),
            "root_path": str(self.root_path),
            "manifest_path": str(self.manifest_path) if self.manifest_path else None,
            "resources": {
                "scripts": list(self.resources.scripts),
                "references": list(self.resources.references),
                "assets": list(self.resources.assets),
            },
        }


class SkillLoader:
    """
    Discovers, loads, and manages skills from Python modules and SKILL.md packages.

    Supported formats:
    - Legacy flat Python modules in skills/*.py exposing TOOLS
    - Claude-style skill folders in skills/<skill-name>/SKILL.md with optional skill.py or __init__.py
    """

    def __init__(self, skills_dir: Optional[str] = None) -> None:
        self.skills_dir = Path(str(skills_dir or os.getenv("ORACLE_SKILLS_DIR", "skills/")))
        self.skills: Dict[str, SkillModule] = {}
        self._builtin_tools: set[str] = set()

        if not self.skills_dir.exists():
            self.skills_dir.mkdir(parents=True, exist_ok=True)
            logger.info("Created skills directory: %s", self.skills_dir)

    def register_builtin_tools(self, tool_names: List[str]) -> None:
        """Register built-in tool names to detect conflicts."""
        self._builtin_tools = set(tool_names)

    def load_all(self) -> Dict[str, SkillToolDef]:
        """Load all legacy and package skills from the skills directory."""
        self.skills = {}
        all_tools: Dict[str, SkillToolDef] = {}

        for py_file in sorted(self.skills_dir.glob("*.py")):
            if py_file.name == "__init__.py":
                continue
            skill_module = self._load_legacy_skill(py_file)
            if not skill_module:
                continue
            self._register_skill(skill_module, all_tools)

        for skill_dir in self._iter_skill_dirs():
            skill_module = self._load_skill_package(skill_dir)
            if not skill_module:
                continue
            self._register_skill(skill_module, all_tools)

        logger.info("SkillLoader: %d skills, %d tools loaded", len(self.skills), len(all_tools))
        return all_tools

    def _iter_skill_dirs(self) -> List[Path]:
        skill_dirs: List[Path] = []
        for child in sorted(self.skills_dir.iterdir()):
            if not child.is_dir():
                continue
            if child.name.startswith(".") or child.name.startswith("__"):
                continue
            if (child / "SKILL.md").exists():
                skill_dirs.append(child)
        return skill_dirs

    def _register_skill(self, skill_module: SkillModule, all_tools: Dict[str, SkillToolDef]) -> None:
        if skill_module.name in self.skills:
            logger.warning("Duplicate skill name '%s', skipping", skill_module.name)
            return

        tool_defs = self._extract_skill_tools(skill_module)

        for tool_def in tool_defs:
            tool_name = tool_def.name
            if tool_name in self._builtin_tools:
                tool_name = f"{skill_module.name}__{tool_name}"
                logger.warning(
                    "Skill tool '%s' conflicts with built-in, renamed to '%s'",
                    tool_def.name,
                    tool_name,
                )
                tool_def.name = tool_name

            if tool_name in all_tools:
                logger.warning("Duplicate tool name '%s' in skill '%s', skipping", tool_name, skill_module.name)
                continue

            skill_module.tools.append(tool_def)
            all_tools[tool_name] = tool_def

        self._setup_skill(skill_module)
        self.skills[skill_module.name] = skill_module
        logger.info(
            "Loaded skill '%s' (%s) with %d tools",
            skill_module.name,
            skill_module.source_type,
            len(skill_module.tools),
        )

    def _setup_skill(self, skill_module: SkillModule) -> None:
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(skill_module.setup())
        except RuntimeError:
            asyncio.run(skill_module.setup())

    def _extract_skill_tools(self, skill_module: SkillModule) -> List[SkillToolDef]:
        if skill_module.module is None or not hasattr(skill_module.module, "TOOLS"):
            return []

        tools_attr = skill_module.module.TOOLS
        if not isinstance(tools_attr, (list, tuple)):
            logger.error("Skill '%s': TOOLS must be a list", skill_module.name)
            return []

        tools: List[SkillToolDef] = []
        for tool_def in tools_attr:
            validated_tool = self._validate_tool(skill_module.name, tool_def)
            if validated_tool:
                tools.append(validated_tool)
        return tools

    def _load_legacy_skill(self, file_path: Path) -> Optional[SkillModule]:
        skill_name = file_path.stem
        if not self._validate_skill_path(file_path, self.skills_dir.resolve()):
            return None
        module = self._import_python_module(skill_name, file_path, [self.skills_dir])
        if module is None:
            return None
        resolved_name = getattr(module, "SKILL_NAME", skill_name)
        if not isinstance(resolved_name, str) or not resolved_name.strip():
            resolved_name = skill_name
        return SkillModule(
            name=resolved_name.strip(),
            module=module,
            file_path=file_path.resolve(),
            root_path=self.skills_dir.resolve(),
            source_type="legacy_module",
        )

    def _load_skill_package(self, skill_dir: Path) -> Optional[SkillModule]:
        resolved_skill_dir = skill_dir.resolve()
        if not self._validate_skill_path(resolved_skill_dir, self.skills_dir.resolve(), expect_directory=True):
            return None
        manifest_path = skill_dir / "SKILL.md"
        if not self._validate_skill_path(manifest_path, resolved_skill_dir):
            return None
        try:
            frontmatter, instructions = self._load_skill_manifest(manifest_path)
        except ValueError as exc:
            logger.error("Failed to load skill package '%s': %s", skill_dir.name, exc)
            return None

        entrypoint = self._resolve_skill_entrypoint(skill_dir, frontmatter)
        module = None
        file_path = manifest_path.resolve()

        if entrypoint is not None:
            module_name = self._normalize_module_name(frontmatter.name)
            module = self._import_python_module(module_name, entrypoint, [self.skills_dir, skill_dir])
            if module is None:
                logger.error("Failed to import skill entrypoint for '%s'", frontmatter.name)
                return None
            file_path = entrypoint.resolve()

        return SkillModule(
            name=frontmatter.name,
            module=module,
            file_path=file_path,
            root_path=skill_dir.resolve(),
            source_type="skill_package",
            manifest_path=manifest_path.resolve(),
            frontmatter=frontmatter,
            instructions=instructions,
            resources=self._discover_supporting_files(skill_dir),
        )

    def _load_skill_manifest(self, manifest_path: Path) -> tuple[SkillFrontmatter, str]:
        text = manifest_path.read_text(encoding="utf-8")
        raw_frontmatter, body = self._parse_frontmatter(text)
        return self._normalize_frontmatter(raw_frontmatter), body.strip()

    def _parse_frontmatter(self, text: str) -> tuple[Dict[str, Any], str]:
        lines = text.splitlines()
        if not lines or lines[0].strip() != "---":
            raise ValueError("SKILL.md must start with YAML frontmatter delimited by '---'")

        closing_idx = None
        for idx in range(1, len(lines)):
            if lines[idx].strip() == "---":
                closing_idx = idx
                break

        if closing_idx is None:
            raise ValueError("SKILL.md frontmatter is missing a closing '---'")

        frontmatter_text = "\n".join(lines[1:closing_idx]).strip()
        body = "\n".join(lines[closing_idx + 1 :])

        if not frontmatter_text:
            raise ValueError("SKILL.md frontmatter cannot be empty")

        if yaml is not None:
            parsed = yaml.safe_load(frontmatter_text)
            if not isinstance(parsed, dict):
                raise ValueError("SKILL.md frontmatter must parse to a mapping")
            return dict(parsed), body

        return self._parse_frontmatter_fallback(frontmatter_text), body

    def _parse_frontmatter_fallback(self, frontmatter_text: str) -> Dict[str, Any]:
        data: Dict[str, Any] = {}
        current_list_key: Optional[str] = None

        for raw_line in frontmatter_text.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            if line.startswith("- "):
                if current_list_key is None:
                    raise ValueError("List item found before a list key in SKILL.md frontmatter")
                data.setdefault(current_list_key, [])
                if not isinstance(data[current_list_key], list):
                    raise ValueError(f"Frontmatter key '{current_list_key}' was not initialized as a list")
                data[current_list_key].append(line[2:].strip().strip("'\""))
                continue

            if ":" not in line:
                raise ValueError(f"Unsupported frontmatter line: {raw_line}")

            key, raw_value = line.split(":", 1)
            key = key.strip()
            value = raw_value.strip()

            if not value:
                data[key] = []
                current_list_key = key
                continue

            data[key] = value.strip("'\"")
            current_list_key = None

        return data

    def _normalize_frontmatter(self, data: Dict[str, Any]) -> SkillFrontmatter:
        name = data.get("name")
        description = data.get("description")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Frontmatter field 'name' is required")
        if not isinstance(description, str) or not description.strip():
            raise ValueError("Frontmatter field 'description' is required")

        triggers = self._coerce_string_list(data.get("triggers"))
        allowed_tools = self._coerce_string_list(data.get("allowed-tools", data.get("allowed_tools")))
        entrypoint = data.get("entrypoint")
        if entrypoint is not None and (not isinstance(entrypoint, str) or not entrypoint.strip()):
            raise ValueError("Frontmatter field 'entrypoint' must be a non-empty string when present")

        return SkillFrontmatter(
            name=name.strip(),
            description=description.strip(),
            triggers=triggers,
            entrypoint=entrypoint.strip() if isinstance(entrypoint, str) else None,
            allowed_tools=allowed_tools,
        )

    def _coerce_string_list(self, value: Any) -> List[str]:
        if value is None:
            return []
        if isinstance(value, str):
            stripped = value.strip()
            return [stripped] if stripped else []
        if isinstance(value, list):
            result: List[str] = []
            for item in value:
                if isinstance(item, str):
                    stripped = item.strip()
                    if stripped:
                        result.append(stripped)
            return result
        return []

    def _resolve_skill_entrypoint(self, skill_dir: Path, frontmatter: SkillFrontmatter) -> Optional[Path]:
        candidate_names: List[str] = []
        if frontmatter.entrypoint:
            candidate_names.append(frontmatter.entrypoint)
        candidate_names.extend(["skill.py", "__init__.py"])

        seen: set[str] = set()
        for candidate_name in candidate_names:
            if candidate_name in seen:
                continue
            seen.add(candidate_name)
            candidate = (skill_dir / candidate_name).resolve()
            if not candidate.exists():
                continue
            if not candidate.is_relative_to(skill_dir.resolve()):
                raise ValueError(f"Skill entrypoint escapes skill directory: {candidate_name}")
            if not self._validate_skill_path(candidate, skill_dir.resolve()):
                raise ValueError(f"Skill entrypoint failed validation: {candidate_name}")
            return candidate
        return None

    def _discover_supporting_files(self, skill_dir: Path) -> SkillResources:
        resources = SkillResources()
        for directory_name, target in (
            ("scripts", resources.scripts),
            ("references", resources.references),
            ("assets", resources.assets),
        ):
            resource_dir = skill_dir / directory_name
            if not resource_dir.exists():
                continue
            if not self._validate_skill_path(resource_dir, skill_dir.resolve(), expect_directory=True):
                logger.warning("Skipping unsafe skill resource directory: %s", resource_dir)
                continue
            for file_path in sorted(path for path in resource_dir.rglob("*") if path.is_file()):
                resolved_file = file_path.resolve()
                if not resolved_file.is_relative_to(skill_dir.resolve()):
                    logger.warning("Skipping resource outside skill directory: %s", resolved_file)
                    continue
                if not self._validate_skill_path(resolved_file, skill_dir.resolve()):
                    logger.warning("Skipping unsafe skill resource file: %s", resolved_file)
                    continue
                target.append(str(file_path.relative_to(skill_dir)))
        return resources

    def _normalize_module_name(self, skill_name: str) -> str:
        normalized = re.sub(r"[^a-zA-Z0-9_]+", "_", skill_name).strip("_")
        return f"oracle_skill_{normalized or 'skill'}"

    def _import_python_module(self, name: str, file_path: Path, extra_paths: List[Path]) -> Any | None:
        try:
            resolved_file = file_path.resolve()
            resolved_skills_dir = self.skills_dir.resolve()
            if not self._validate_skill_path(resolved_file, resolved_skills_dir):
                return None

            spec = importlib.util.spec_from_file_location(name, resolved_file)
            if not spec or not spec.loader:
                logger.error("Cannot load spec for %s", resolved_file)
                return None

            module = importlib.util.module_from_spec(spec)
            for extra_path in extra_paths:
                resolved_extra = extra_path.resolve()
                if str(resolved_extra) not in sys.path:
                    sys.path.insert(0, str(resolved_extra))
            spec.loader.exec_module(module)
            return module
        except Exception as exc:
            logger.error("Error importing skill '%s': %s", name, exc)
            return None

    def _validate_skill_path(self, path: Path, root_dir: Path, *, expect_directory: bool = False) -> bool:
        try:
            resolved_path = path.resolve()
            resolved_root = root_dir.resolve()
            if not resolved_path.is_relative_to(resolved_root):
                logger.error("Security: Skill path %s is outside allowed root %s", resolved_path, resolved_root)
                return False

            target_stat = resolved_path.stat()
            root_stat = resolved_root.stat()
            if target_stat.st_mode & 0o002:
                logger.error("Security: Skill path %s is world-writable, refusing to load.", resolved_path)
                return False
            if root_stat.st_mode & 0o002:
                logger.error("Security: Skills root %s is world-writable, refusing to load.", resolved_root)
                return False
            if expect_directory and not resolved_path.is_dir():
                logger.error("Security: Expected directory for skill path %s", resolved_path)
                return False
            if not expect_directory and not resolved_path.is_file():
                logger.error("Security: Expected file for skill path %s", resolved_path)
                return False
            return True
        except FileNotFoundError:
            logger.error("Security: Could not stat skill path %s for validation.", path)
            return False

    def _validate_tool(self, skill_name: str, tool_def: Any) -> Optional[SkillToolDef]:
        """Validate a SkillToolDef."""
        try:
            if isinstance(tool_def, dict):
                name = tool_def.get("name")
                description = tool_def.get("description")
                parameters = tool_def.get("parameters", {})
                handler = tool_def.get("handler")
            elif isinstance(tool_def, SkillToolDef):
                return tool_def
            else:
                name = getattr(tool_def, "name", None)
                description = getattr(tool_def, "description", None)
                parameters = getattr(tool_def, "parameters", {})
                handler = getattr(tool_def, "handler", None)

            if not name or not isinstance(name, str):
                logger.error("Skill '%s': tool missing valid 'name'", skill_name)
                return None
            if not description or not isinstance(description, str):
                logger.error("Skill '%s': tool '%s' missing valid 'description'", skill_name, name)
                return None
            if not isinstance(parameters, dict):
                logger.error("Skill '%s': tool '%s' missing valid 'parameters'", skill_name, name)
                return None
            if not handler or not callable(handler):
                logger.error("Skill '%s': tool '%s' missing callable 'handler'", skill_name, name)
                return None

            return SkillToolDef(name=name, description=description, parameters=parameters, handler=handler)
        except Exception as exc:
            logger.error("Error validating tool in skill '%s': %s", skill_name, exc)
            return None

    def get_catalog(self) -> List[Dict[str, Any]]:
        """Return the current discovered skill catalog."""
        return [self.skills[name].catalog_entry() for name in sorted(self.skills)]

    def select_for_prompt(self, prompt: str, limit: int = 3) -> List[SkillModule]:
        """Select the most relevant skills for a prompt using lightweight lexical matching."""
        scored: List[Tuple[int, str, SkillModule]] = []
        for skill in self.skills.values():
            score = self._score_skill_match(skill, prompt)
            if score > 0:
                scored.append((score, skill.name, skill))

        scored.sort(key=lambda item: (-item[0], item[1]))
        return [skill for _score, _name, skill in scored[:limit]]

    def build_prompt_context(self, prompt: str, max_skills: int = 3) -> str:
        """Build a compact system-instruction block describing discovered and selected skills."""
        if not self.skills:
            return ""

        selected_skills = self.select_for_prompt(prompt, limit=min(max_skills, _MAX_SELECTED_SKILLS))
        lines = [
            "Repository-local skills are available in this workspace.",
            "Treat a skill as a specialized operating procedure.",
            "Only follow a skill when the current request matches its description or triggers.",
            "",
            "Available skills:",
        ]

        for skill in sorted(self.skills.values(), key=lambda item: item.name):
            summary = f"- {skill.name}: {skill.description}"
            if skill.triggers:
                summary += f" Triggers: {', '.join(skill.triggers)}."
            if skill.tool_names():
                summary += f" Tools: {', '.join(skill.tool_names())}."
            if skill.resources.references:
                summary += f" References: {', '.join(skill.resources.references[:_MAX_SKILL_SUMMARY_REFERENCES])}."
            lines.append(summary)

        if not selected_skills:
            return "\n".join(lines)

        lines.extend(["", "Selected skill instructions for this request:"])
        for skill in selected_skills:
            lines.extend(["", f"## {skill.name}", skill.description])
            if skill.allowed_tools:
                lines.append(f"Preferred existing tools: {', '.join(skill.allowed_tools)}")
            if skill.instructions:
                instructions = skill.instructions
                if len(instructions) > _MAX_SKILL_INSTRUCTION_CHARS:
                    instructions = (
                        instructions[:_MAX_SKILL_INSTRUCTION_CHARS].rstrip() + "\n\n[skill instructions truncated]"
                    )
                lines.append(instructions)
            if skill.resources.scripts or skill.resources.references or skill.resources.assets:
                lines.append("Supporting files available:")
                for label, resources in (
                    ("scripts", skill.resources.scripts),
                    ("references", skill.resources.references),
                    ("assets", skill.resources.assets),
                ):
                    if resources:
                        lines.append(f"- {label}: {', '.join(resources)}")
        context = "\n".join(lines)
        if len(context) > _MAX_TOTAL_PROMPT_CONTEXT_CHARS:
            context = context[:_MAX_TOTAL_PROMPT_CONTEXT_CHARS].rstrip() + "\n\n[prompt skill context truncated]"
        return context

    def _score_skill_match(self, skill: SkillModule, prompt: str) -> int:
        prompt_lower = prompt.lower()
        prompt_terms = self._tokenize(prompt)

        score = 0
        if skill.name.lower() in prompt_lower:
            score += 12

        for trigger in skill.triggers:
            trigger_lower = trigger.lower()
            if trigger_lower and trigger_lower in prompt_lower:
                score += 10 + len(trigger_lower.split())

        metadata_terms = self._tokenize(" ".join([skill.name, skill.description, *skill.triggers, *skill.tool_names()]))
        score += len(prompt_terms & metadata_terms)

        return score

    def _tokenize(self, text: str) -> set[str]:
        return {
            token
            for token in re.findall(r"[a-z0-9][a-z0-9_-]{1,}", text.lower())
            if len(token) > 2 and token not in _STOP_WORDS
        }

    def reload(self) -> Dict[str, SkillToolDef]:
        """Reload skills from directory."""
        logger.info("Reloading skills...")
        for skill in self.skills.values():
            try:
                asyncio.create_task(skill.teardown())
            except RuntimeError:
                asyncio.run(skill.teardown())
        return self.load_all()

    async def teardown_all(self) -> None:
        """Call teardown on all loaded skills."""
        logger.info("Tearing down all skills")
        for skill_name, skill in self.skills.items():
            try:
                await skill.teardown()
            except Exception as exc:
                logger.error("Error tearing down skill '%s': %s", skill_name, exc)

    def get_tools(self) -> List[Tuple[str, SkillToolDef]]:
        """Get all loaded tools."""
        tools: List[Tuple[str, SkillToolDef]] = []
        for skill in self.skills.values():
            for tool in skill.tools:
                tools.append((tool.name, tool))
        return tools
