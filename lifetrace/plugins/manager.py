"""Backend plugin manager with builtin module compatibility."""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

from lifetrace.plugins.builtin.module_adapter import BuiltinModulePluginAdapter
from lifetrace.plugins.installer import InstallResult, PluginInstaller, UninstallResult
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
        self.installer = PluginInstaller()
        self.builtin_adapter = BuiltinModulePluginAdapter(installer=self.installer)

    def snapshot(self) -> PluginSnapshot:
        """Return combined snapshot for modules and plugins."""
        plugin_states = self.builtin_adapter.list_states()
        module_states = self.builtin_adapter.get_module_states()
        return PluginSnapshot(module_states=module_states, plugin_states=plugin_states)

    def list_plugins(self) -> dict[str, PluginState]:
        """List all plugin states."""
        plugins = dict(self.builtin_adapter.list_states())
        plugins.update(self.builtin_adapter.list_third_party_states())
        return plugins

    def register_all(self, app: FastAPI) -> list[str]:
        """Register all enabled plugins (mapped to enabled modules)."""
        return self.builtin_adapter.register(app)

    def register_subset(self, app: FastAPI, plugin_ids: list[str]) -> list[str]:
        """Register a subset of plugin ids (mapped to module ids in phase 1)."""
        return self.builtin_adapter.register_subset(app, plugin_ids)

    def list_installed_plugins(self) -> list[str]:
        """List installed third-party plugin ids."""
        return self.installer.list_installed_plugin_ids()

    def install_plugin_from_archive(
        self,
        plugin_id: str,
        archive_path: str,
        expected_sha256: str | None = None,
        force: bool = False,
    ) -> InstallResult:
        """Install plugin from local archive."""
        return self.installer.install_from_archive(
            plugin_id=plugin_id,
            archive_path=archive_path,
            expected_sha256=expected_sha256,
            force=force,
        )

    def uninstall_plugin(self, plugin_id: str) -> UninstallResult:
        """Uninstall plugin by id."""
        return self.installer.uninstall(plugin_id)

    def get_plugin_manifest(self, plugin_id: str) -> dict[str, object] | None:
        """Get installed plugin manifest if available."""
        return self.installer.read_manifest(plugin_id)


@lru_cache(maxsize=1)
def get_plugin_manager() -> PluginManager:
    """Return plugin manager singleton."""
    return PluginManager()
