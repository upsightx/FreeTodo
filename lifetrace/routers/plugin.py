"""Plugin management APIs (phase 1 runtime visibility)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from lifetrace.plugins.installer import PluginInstallError, PluginValidationError
from lifetrace.plugins.manager import get_plugin_manager

router = APIRouter(prefix="/api/plugins", tags=["plugins"])


class InstallPluginRequest(BaseModel):
    """Install plugin request payload."""

    plugin_id: str = Field(description="插件 ID")
    archive_path: str = Field(description="本地插件 zip 包路径")
    expected_sha256: str | None = Field(default=None, description="可选 SHA-256 校验值")
    force: bool = Field(default=False, description="已安装时是否强制覆盖")


class UninstallPluginRequest(BaseModel):
    """Uninstall plugin request payload."""

    plugin_id: str = Field(description="插件 ID")


@router.get("")
async def list_plugins():
    """List backend plugins and runtime states."""
    manager = get_plugin_manager()
    plugins = manager.list_plugins()
    return {
        "plugins": [
            {
                "id": plugin.id,
                "name": plugin.name,
                "version": plugin.version,
                "kind": plugin.kind,
                "source": plugin.source,
                "enabled": plugin.enabled,
                "installed": plugin.installed,
                "available": plugin.available,
                "status": plugin.status,
                "missing_deps": plugin.missing_deps,
            }
            for plugin in plugins.values()
        ],
        "installed_third_party": manager.list_installed_plugins(),
    }


@router.post("/install")
async def install_plugin(payload: InstallPluginRequest):
    """Install plugin from local archive with validation checks."""
    manager = get_plugin_manager()
    try:
        result = manager.install_plugin_from_archive(
            plugin_id=payload.plugin_id,
            archive_path=payload.archive_path,
            expected_sha256=payload.expected_sha256,
            force=payload.force,
        )
    except PluginValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PluginInstallError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"插件安装失败: {exc}") from exc

    manifest = manager.get_plugin_manifest(payload.plugin_id)
    return {
        "plugin_id": result.plugin_id,
        "success": result.success,
        "install_dir": result.install_dir,
        "checksum": result.checksum,
        "message": result.message,
        "manifest": manifest,
    }


@router.post("/uninstall")
async def uninstall_plugin(payload: UninstallPluginRequest):
    """Uninstall plugin by plugin id."""
    manager = get_plugin_manager()
    try:
        result = manager.uninstall_plugin(payload.plugin_id)
    except PluginValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PluginInstallError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"插件卸载失败: {exc}") from exc

    return {
        "plugin_id": result.plugin_id,
        "success": result.success,
        "install_dir": result.install_dir,
        "message": result.message,
    }
