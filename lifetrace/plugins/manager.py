"""Backend plugin manager with builtin module compatibility."""

from __future__ import annotations

import re
from functools import lru_cache
from typing import TYPE_CHECKING

from lifetrace.plugins.builtin.module_adapter import BuiltinModulePluginAdapter
from lifetrace.plugins.error_codes import PluginErrorCode
from lifetrace.plugins.events import PluginEventBus
from lifetrace.plugins.history import PluginTaskHistoryStore
from lifetrace.plugins.installer import InstallResult, PluginInstaller, UninstallResult
from lifetrace.plugins.models import PluginSnapshot, PluginState
from lifetrace.util.settings import settings

if TYPE_CHECKING:
    from fastapi import FastAPI

PLUGIN_ERROR_CODE_PATTERNS: list[tuple[str, str]] = [
    ("插件 ID 非法", PluginErrorCode.INVALID_PLUGIN_ID),
    ("已安装", PluginErrorCode.ALREADY_INSTALLED),
    ("未安装", PluginErrorCode.NOT_INSTALLED),
    ("SHA-256 不匹配", PluginErrorCode.CHECKSUM_MISMATCH),
    ("缺少 expected_sha256", PluginErrorCode.MISSING_CHECKSUM),
    ("plugin.manifest.json", PluginErrorCode.MANIFEST_MISSING),
    ("仅支持 .zip", PluginErrorCode.ARCHIVE_INVALID),
    ("非法路径", PluginErrorCode.ARCHIVE_INVALID),
]


class PluginManager:
    """Runtime plugin manager.

    Phase 1 goal:
    - expose existing backend modules through unified plugin view
    - keep startup behavior backward-compatible
    """

    def __init__(self):
        self.installer = PluginInstaller()
        self.event_bus = PluginEventBus()
        self.history_store = PluginTaskHistoryStore()
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
    ) -> tuple[InstallResult, str]:
        """Install plugin from local archive."""
        task = self.history_store.create_task(
            plugin_id=plugin_id,
            action="install",
            status="running",
            progress=0,
            message="开始安装插件",
            details={"archive_path": archive_path, "force": force},
        )

        def on_event(
            stage: str,
            status: str,
            message: str,
            progress: int | None,
            details: dict[str, object] | None,
        ) -> None:
            task_status = "running"
            error_code: str | None = None
            if status == "success":
                task_status = "success"
            elif status == "failed":
                task_status = "failed"
                error_code = self.infer_error_code(message)

            self.history_store.update_task(
                task_id=task.task_id,
                status=task_status,
                message=message,
                progress=progress,
                error_code=error_code,
                details=details,
            )
            self.event_bus.publish(
                plugin_id=plugin_id,
                action="install",
                task_id=task.task_id,
                stage=stage,
                status=status,
                message=message,
                progress=progress,
                details=details,
            )

        result = self.installer.install_from_archive(
            plugin_id=plugin_id,
            archive_path=archive_path,
            expected_sha256=expected_sha256,
            force=force,
            on_event=on_event,
        )
        return result, task.task_id

    def uninstall_plugin(self, plugin_id: str) -> tuple[UninstallResult, str]:
        """Uninstall plugin by id."""
        task = self.history_store.create_task(
            plugin_id=plugin_id,
            action="uninstall",
            status="running",
            progress=0,
            message="开始卸载插件",
            details={},
        )

        def on_event(
            stage: str,
            status: str,
            message: str,
            progress: int | None,
            details: dict[str, object] | None,
        ) -> None:
            task_status = "running"
            error_code: str | None = None
            if status == "success":
                task_status = "success"
            elif status == "failed":
                task_status = "failed"
                error_code = self.infer_error_code(message)

            self.history_store.update_task(
                task_id=task.task_id,
                status=task_status,
                message=message,
                progress=progress,
                error_code=error_code,
                details=details,
            )
            self.event_bus.publish(
                plugin_id=plugin_id,
                action="uninstall",
                task_id=task.task_id,
                stage=stage,
                status=status,
                message=message,
                progress=progress,
                details=details,
            )

        result = self.installer.uninstall_with_events(plugin_id, on_event=on_event)
        return result, task.task_id

    def set_plugin_enabled(self, plugin_id: str, enabled: bool) -> PluginState:
        """Enable/disable one plugin in persisted settings."""
        plugin = self.list_plugins().get(plugin_id)
        if not plugin:
            raise ValueError(f"插件 {plugin_id} 不存在")

        if plugin.source == "builtin:module":
            self._set_builtin_module_enabled(plugin_id, enabled)
        elif plugin.source == "third_party":
            self.builtin_adapter.set_third_party_enabled(plugin_id, enabled)
        else:
            raise ValueError(f"插件 {plugin_id} 暂不支持启停")

        updated = self.list_plugins().get(plugin_id)
        if updated is None:
            raise RuntimeError(f"插件状态刷新失败: {plugin_id}")
        return updated

    def _set_builtin_module_enabled(self, module_id: str, enabled: bool) -> None:
        enabled_modules = {
            str(item)
            for item in settings.get("backend_modules.enabled", [])
            if str(item) != module_id
        }
        disabled_modules = {
            str(item)
            for item in settings.get("backend_modules.disabled", [])
            if str(item) != module_id
        }
        was_allow_all = not enabled_modules

        if enabled:
            disabled_modules.discard(module_id)
            if not was_allow_all:
                enabled_modules.add(module_id)
        else:
            disabled_modules.add(module_id)
            enabled_modules.discard(module_id)

        settings.set("backend_modules.enabled", sorted(enabled_modules))
        settings.set("backend_modules.disabled", sorted(disabled_modules))

    def list_task_history(
        self,
        *,
        plugin_id: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, object]]:
        """Return plugin task history payloads."""
        records = self.history_store.list_tasks(plugin_id=plugin_id, limit=limit)
        return [record.to_payload() for record in records]

    def get_task(self, task_id: str) -> dict[str, object] | None:
        """Get one plugin task payload by id."""
        task = self.history_store.get_task(task_id)
        if not task:
            return None
        return task.to_payload()

    def infer_error_code(self, message: str) -> str:
        """Infer error code from installer message."""
        normalized = message.strip()
        for pattern, error_code in PLUGIN_ERROR_CODE_PATTERNS:
            if re.search(pattern, normalized):
                return error_code
        return PluginErrorCode.INTERNAL_ERROR

    def get_plugin_manifest(self, plugin_id: str) -> dict[str, object] | None:
        """Get installed plugin manifest if available."""
        return self.installer.read_manifest(plugin_id)


@lru_cache(maxsize=1)
def get_plugin_manager() -> PluginManager:
    """Return plugin manager singleton."""
    return PluginManager()
