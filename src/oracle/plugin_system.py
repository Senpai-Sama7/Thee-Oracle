"""
Oracle Agent Plugin System
"""

from __future__ import annotations

import importlib.util
from enum import Enum
from pathlib import Path
from types import ModuleType
from typing import Any, Protocol, cast


class PluginType(Enum):
    TOOL = "tool"
    SKILL = "skill"
    INTEGRATION = "integration"


class PluginStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"


class PluginInstance(Protocol):
    name: str
    version: str
    description: str
    type: str

    def initialize(self) -> None: ...
    def cleanup(self) -> None: ...


class Plugin:
    def __init__(self, plugin_id: str, metadata: dict[str, str]) -> None:
        self.id = plugin_id
        self.metadata = metadata
        self.status = PluginStatus.INACTIVE
        self.instance: PluginInstance | None = None
        self.config: dict[str, Any] = {}

    def initialize(self, config: dict[str, Any] | None = None) -> None:
        """Initialize plugin."""
        self.config = config or {}
        if self.instance and hasattr(self.instance, "initialize"):
            self.instance.initialize()
        self.status = PluginStatus.ACTIVE

    def cleanup(self) -> None:
        """Cleanup plugin."""
        if self.instance and hasattr(self.instance, "cleanup"):
            self.instance.cleanup()
        self.status = PluginStatus.INACTIVE


class PluginManager:
    def __init__(self, plugin_dir: str = "plugins") -> None:
        self.plugin_dir = Path(plugin_dir)
        self.plugin_dir_resolved = self.plugin_dir.resolve()
        self.plugins: dict[str, Plugin] = {}
        self.plugin_dir.mkdir(exist_ok=True)

    def discover_plugins(self) -> list[str]:
        """Discover available plugins."""
        plugins: list[str] = []
        for plugin_file in self.plugin_dir.glob("*.py"):
            if plugin_file.name.startswith("__"):
                continue
            plugins.append(plugin_file.stem)
        return plugins

    def load_plugin(self, plugin_id: str) -> bool:
        """Load a plugin."""
        try:
            if Path(plugin_id).name != plugin_id or plugin_id in {".", ".."}:
                return False

            plugin_file = (self.plugin_dir / f"{plugin_id}.py").resolve()
            if self.plugin_dir_resolved not in plugin_file.parents:
                return False
            if not plugin_file.exists() or not plugin_file.is_file():
                return False

            spec = importlib.util.spec_from_file_location(plugin_id, plugin_file)
            if spec is None or spec.loader is None:
                return False

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            plugin_instance = self._build_plugin_instance(module)
            if plugin_instance is None:
                return False

            plugin = Plugin(
                plugin_id,
                {
                    "name": getattr(plugin_instance, "name", plugin_id),
                    "version": getattr(plugin_instance, "version", "1.0.0"),
                    "description": getattr(plugin_instance, "description", ""),
                    "type": getattr(plugin_instance, "type", PluginType.TOOL.value),
                },
            )
            plugin.instance = plugin_instance
            plugin.initialize()

            self.plugins[plugin_id] = plugin
            return True
        except Exception as e:
            print(f"Error loading plugin {plugin_id}: {e}")
            return False

    @staticmethod
    def _build_plugin_instance(module: ModuleType) -> PluginInstance | None:
        """Construct a plugin instance from the module if supported."""
        plugin_class = getattr(module, "Plugin", None)
        if plugin_class is None:
            return None
        instance = plugin_class()
        return cast(PluginInstance, instance)

    def unload_plugin(self, plugin_id: str) -> bool:
        """Unload a plugin."""
        plugin = self.plugins.get(plugin_id)
        if plugin:
            plugin.cleanup()
            del self.plugins[plugin_id]
            return True
        return False

    def get_plugin(self, plugin_id: str) -> Plugin | None:
        """Get plugin by ID."""
        return self.plugins.get(plugin_id)

    def list_plugins(self) -> list[dict[str, str]]:
        """List all plugins."""
        return [
            {
                "id": plugin.id,
                "name": plugin.metadata["name"],
                "version": plugin.metadata["version"],
                "status": plugin.status.value,
                "type": plugin.metadata["type"],
            }
            for plugin in self.plugins.values()
        ]

    def get_active_plugins(self) -> list[Plugin]:
        """Get active plugins."""
        return [plugin for plugin in self.plugins.values() if plugin.status == PluginStatus.ACTIVE]


class ExamplePlugin:
    name = "Example Plugin"
    version = "1.0.0"
    description = "An example plugin"
    type = "tool"

    def __init__(self) -> None:
        self.initialized = False

    def initialize(self) -> None:
        self.initialized = True

    def execute(self, task: dict[str, Any]) -> dict[str, Any]:
        return {"result": "Example plugin executed", "task": task}

    def cleanup(self) -> None:
        self.initialized = False
