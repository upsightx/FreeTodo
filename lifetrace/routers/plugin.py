"""插件管理 API 路由 - 提供可选插件的查询、安装和卸载接口。"""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from lifetrace.services.plugin_manager import media_crawler_plugin
from lifetrace.util.logging_config import get_logger

logger = get_logger()

router = APIRouter(prefix="/api/plugins", tags=["plugins"])

# ==============================================================================
# MediaCrawler 插件
# ==============================================================================


@router.get("/media-crawler/status")
async def get_media_crawler_status():
    """获取 MediaCrawler 插件的安装状态。

    Returns:
        插件状态信息，包括是否安装、版本、模式等。
    """
    try:
        status = media_crawler_plugin.get_status()
        return {"success": True, **status}
    except Exception as e:
        logger.error(f"获取插件状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取插件状态失败: {e}") from e


@router.post("/media-crawler/install")
async def install_media_crawler(
    version: str | None = None,
    download_url: str | None = None,
):
    """安装 MediaCrawler 插件（流式返回安装进度）。

    安装过程包括：下载 → 解压 → 安装依赖。
    通过 NDJSON（每行一个 JSON 对象）流式返回每个阶段的进度。

    Args:
        version: 要安装的版本号（默认为最新版）。
        download_url: 自定义下载 URL（可选，覆盖默认地址）。
    """
    if media_crawler_plugin.is_installed():
        installed_version = media_crawler_plugin.get_installed_version()
        target_version = version or media_crawler_plugin.LATEST_VERSION
        if installed_version == target_version:
            return {
                "success": True,
                "message": f"插件已安装 (v{installed_version})，无需重复安装",
                "already_installed": True,
            }

    progress = await media_crawler_plugin.download_and_install(
        version=version,
        download_url=download_url,
    )

    async def stream_progress():
        async for step in progress.run():
            yield json.dumps(step, ensure_ascii=False) + "\n"

    return StreamingResponse(
        stream_progress(),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "Access-Control-Allow-Origin": "*",
        },
    )


@router.post("/media-crawler/uninstall")
async def uninstall_media_crawler():
    """卸载 MediaCrawler 插件（删除插件安装目录）。"""
    if not media_crawler_plugin.is_installed():
        return {
            "success": True,
            "message": "插件未安装，无需卸载",
        }

    try:
        success = await media_crawler_plugin.uninstall()
        if success:
            return {"success": True, "message": "插件已成功卸载"}
        raise HTTPException(status_code=500, detail="卸载失败，请查看日志")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"卸载插件失败: {e}")
        raise HTTPException(status_code=500, detail=f"卸载插件失败: {e}") from e


# ==============================================================================
# 通用插件列表（目前只有 media-crawler）
# ==============================================================================


@router.get("/list")
async def list_plugins():
    """列出所有可用的插件及其状态。"""
    try:
        return {
            "success": True,
            "plugins": [
                media_crawler_plugin.get_status(),
            ],
        }
    except Exception as e:
        logger.error(f"获取插件列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取插件列表失败: {e}") from e
