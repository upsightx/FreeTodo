"""Adapter that exposes existing backend modules as builtin plugins."""

from __future__ import annotations

from dataclasses import replace

from lifetrace.core import module_registry
from lifetrace.plugins.base import BackendPlugin
from lifetrace.plugins.models import PluginKind, PluginState, PluginStatus


class BuiltinModulePluginAdapter(BackendPlugin):
    """Bridge from module registry to plugin runtime."""

    id = "builtin-modules"
    name = "Builtin Modules"
    version = "1.0.0"
    source = "builtin"

    def __init__(self):
        self._module_states = module_registry.get_module_states()

    def refresh(self) -> None:
        """Refresh module states from current settings."""
        self._module_states = module_registry.get_module_states()

    def list_states(self) -> dict[str, PluginState]:
        self.refresh()
        result: dict[str, PluginState] = {}
        for module in module_registry.MODULES:
            module_state = self._module_states[module.id]
            if module_state.enabled and module_state.available:
                status = PluginStatus.ENABLED
            elif not module_state.enabled:
                status = PluginStatus.DISABLED
            else:
                status = PluginStatus.UNAVAILABLE

            result[module.id] = PluginState(
                id=module.id,
                name=module.id,
                version="builtin",
                kind=PluginKind.BACKEND,
                source="builtin:module",
                enabled=module_state.enabled,
                installed=True,
                available=module_state.available,
                status=status,
                missing_deps=list(module_state.missing_deps),
            )
        return result

    def register(self, app):
        self.refresh()
        module_registry.log_module_summary(self._module_states)
        enabled_ids = module_registry.get_enabled_module_ids(self._module_states)
        return module_registry.register_modules(app, enabled_ids, states=self._module_states)

    def register_subset(self, app, module_ids: list[str]) -> list[str]:
        """Register a subset of modules using latest states."""
        self.refresh()
        return module_registry.register_modules(app, module_ids, states=self._module_states)

    def get_module_states(self) -> dict[str, module_registry.ModuleState]:
        """Return current module states."""
        return {k: replace(v) for k, v in self._module_states.items()}
