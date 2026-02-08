"""Plugin management APIs (phase 1 runtime visibility)."""

from __future__ import annotations

import json
import queue

from fastapi import APIRouter, Header, HTTPException, Query, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from lifetrace.plugins.error_codes import PluginApiError, PluginErrorCode
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


class TogglePluginRequest(BaseModel):
    """Toggle plugin enable/disable request payload."""

    plugin_id: str = Field(description="插件 ID")
    enabled: bool = Field(description="目标启用状态")


def _format_sse(event_name: str, event_id: str, data: dict[str, object]) -> str:
    payload = json.dumps(data, ensure_ascii=False)
    return f"id: {event_id}\nevent: {event_name}\ndata: {payload}\n\n"


def _raise_plugin_error(status_code: int, error: PluginApiError) -> None:
    raise HTTPException(status_code=status_code, detail=error.to_payload())


def _map_exception_to_api_error(exc: Exception) -> PluginApiError:
    message = str(exc)
    if isinstance(exc, PluginValidationError):
        validation_mappings: list[tuple[str, str]] = [
            ("插件 ID 非法", PluginErrorCode.INVALID_PLUGIN_ID),
            ("已安装", PluginErrorCode.ALREADY_INSTALLED),
            ("未安装", PluginErrorCode.NOT_INSTALLED),
            ("SHA-256 不匹配", PluginErrorCode.CHECKSUM_MISMATCH),
            ("缺少 expected_sha256", PluginErrorCode.MISSING_CHECKSUM),
            ("plugin.manifest.json", PluginErrorCode.MANIFEST_MISSING),
            ("仅支持 .zip", PluginErrorCode.ARCHIVE_INVALID),
            ("非法路径", PluginErrorCode.ARCHIVE_INVALID),
        ]
        matched_code = next(
            (code for pattern, code in validation_mappings if pattern in message),
            PluginErrorCode.VALIDATION_FAILED,
        )
        return PluginApiError(code=matched_code, message=message)
    if isinstance(exc, PluginInstallError):
        return PluginApiError(code=PluginErrorCode.INSTALL_FAILED, message=message)
    if isinstance(exc, ValueError):
        return PluginApiError(code=PluginErrorCode.ENABLE_NOT_ALLOWED, message=message)
    return PluginApiError(code=PluginErrorCode.INTERNAL_ERROR, message=message)


def _status_code_from_error_code(error_code: str) -> int:
    if error_code == PluginErrorCode.INTERNAL_ERROR:
        return 500
    return 400


def _raise_from_exception(exc: Exception) -> None:
    api_error = _map_exception_to_api_error(exc)
    status_code = _status_code_from_error_code(api_error.code)
    _raise_plugin_error(status_code, api_error)


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
        result, task_id = await run_in_threadpool(
            manager.install_plugin_from_archive,
            payload.plugin_id,
            payload.archive_path,
            payload.expected_sha256,
            payload.force,
        )
    except Exception as exc:
        _raise_from_exception(exc)
        return {}

    manifest = manager.get_plugin_manifest(payload.plugin_id)
    return {
        "plugin_id": result.plugin_id,
        "task_id": task_id,
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
        result, task_id = await run_in_threadpool(manager.uninstall_plugin, payload.plugin_id)
    except Exception as exc:
        _raise_from_exception(exc)
        return {}

    return {
        "plugin_id": result.plugin_id,
        "task_id": task_id,
        "success": result.success,
        "install_dir": result.install_dir,
        "message": result.message,
    }


@router.post("/toggle")
async def toggle_plugin(payload: TogglePluginRequest):
    """Enable or disable one plugin."""
    manager = get_plugin_manager()
    try:
        plugin = await run_in_threadpool(
            manager.set_plugin_enabled, payload.plugin_id, payload.enabled
        )
    except Exception as exc:
        _raise_from_exception(exc)
        return {}

    return {
        "plugin": {
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
    }


@router.get("/tasks")
async def list_plugin_tasks(
    plugin_id: str | None = Query(default=None, description="按插件 ID 过滤任务"),
    limit: int = Query(default=50, ge=1, le=200),
):
    """List persisted plugin install/uninstall tasks."""
    manager = get_plugin_manager()
    tasks = manager.list_task_history(plugin_id=plugin_id, limit=limit)
    return {"tasks": tasks}


@router.get("/tasks/{task_id}")
async def get_plugin_task(task_id: str):
    """Get one plugin task by id."""
    manager = get_plugin_manager()
    task = manager.get_task(task_id)
    if task is None:
        _raise_plugin_error(
            404,
            PluginApiError(
                code=PluginErrorCode.NOT_INSTALLED,
                message=f"任务不存在: {task_id}",
            ),
        )
    return task


@router.get("/events")
async def stream_plugin_events(
    request: Request,
    plugin_id: str | None = Query(default=None, description="按插件 ID 过滤事件"),
    task_id: str | None = Query(default=None, description="按任务 ID 过滤事件"),
    last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
):
    """Stream plugin lifecycle events as SSE."""
    manager = get_plugin_manager()
    subscriber_id, subscriber_queue, replay_events = manager.event_bus.subscribe(
        plugin_id=plugin_id,
        task_id=task_id,
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
