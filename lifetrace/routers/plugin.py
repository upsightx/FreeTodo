"""Plugin management APIs (phase 1 runtime visibility)."""

from __future__ import annotations

from fastapi import APIRouter

from lifetrace.plugins.manager import get_plugin_manager

router = APIRouter(prefix="/api/plugins", tags=["plugins"])


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
        ]
    }
