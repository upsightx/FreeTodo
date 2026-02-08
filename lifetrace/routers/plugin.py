"""Plugin management APIs (phase 1 runtime visibility)."""

from __future__ import annotations

import json
import queue

from fastapi import APIRouter, Header, HTTPException, Query, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
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


def _format_sse(event_name: str, event_id: str, data: dict[str, object]) -> str:
    payload = json.dumps(data, ensure_ascii=False)
    return f"id: {event_id}\nevent: {event_name}\ndata: {payload}\n\n"


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
        result = await run_in_threadpool(
            manager.install_plugin_from_archive,
            payload.plugin_id,
            payload.archive_path,
            payload.expected_sha256,
            payload.force,
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
        result = await run_in_threadpool(manager.uninstall_plugin, payload.plugin_id)
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


@router.get("/events")
async def stream_plugin_events(
    request: Request,
    plugin_id: str | None = Query(default=None, description="按插件 ID 过滤事件"),
    last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
):
    """Stream plugin lifecycle events as SSE."""
    manager = get_plugin_manager()
    subscriber_id, subscriber_queue, replay_events = manager.event_bus.subscribe(
        plugin_id=plugin_id,
        last_event_id=last_event_id,
    )

    async def event_generator():
        try:
            for replay_event in replay_events:
                yield _format_sse(
                    event_name="plugin_event",
                    event_id=replay_event.event_id,
                    data=replay_event.to_payload(),
                )

            while True:
                if await request.is_disconnected():
                    break
                try:
                    next_event = await run_in_threadpool(subscriber_queue.get, True, 1.0)
                except queue.Empty:
                    yield ": keep-alive\n\n"
                    continue

                yield _format_sse(
                    event_name="plugin_event",
                    event_id=next_event.event_id,
                    data=next_event.to_payload(),
                )
        finally:
            manager.event_bus.unsubscribe(subscriber_id)

    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers=headers,
    )
