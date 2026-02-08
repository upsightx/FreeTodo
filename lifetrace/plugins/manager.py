"""Backend plugin manager with builtin module compatibility."""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

from lifetrace.plugins.builtin.module_adapter import BuiltinModulePluginAdapter
from lifetrace.plugins.models import PluginSnapshot, PluginState

if TYPE_CHECKING:
    from fastapi import FastAPI


class PluginManager:
    """Runtime plugin manager.

    Phase 1 goal:
    - expose existing backend modules through unified plugin view
    - keep startup behavior backward-compatible
    """

    def __init__(self):
        self.builtin_adapter = BuiltinModulePluginAdapter()

    def snapshot(self) -> PluginSnapshot:
        """Return combined snapshot for modules and plugins."""
        plugin_states = self.builtin_adapter.list_states()
        module_states = self.builtin_adapter.get_module_states()
        return PluginSnapshot(module_states=module_states, plugin_states=plugin_states)

    def list_plugins(self) -> dict[str, PluginState]:
        """List all plugin states."""
        return self.builtin_adapter.list_states()

    def register_all(self, app: FastAPI) -> list[str]:
        """Register all enabled plugins (mapped to enabled modules)."""
        return self.builtin_adapter.register(app)

    def register_subset(self, app: FastAPI, plugin_ids: list[str]) -> list[str]:
        """Register a subset of plugin ids (mapped to module ids in phase 1)."""
        return self.builtin_adapter.register_subset(app, plugin_ids)


@lru_cache(maxsize=1)
def get_plugin_manager() -> PluginManager:
    """Return plugin manager singleton."""
    return PluginManager()
