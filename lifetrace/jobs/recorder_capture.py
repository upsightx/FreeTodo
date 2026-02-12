"""
屏幕录制器截图捕获模块
包含截图捕获、保存和数据库操作
"""

import hashlib
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import imagehash
import mss
from mss import tools as mss_tools
from PIL import Image

from lifetrace.storage import event_mgr, screenshot_mgr
from lifetrace.util.logging_config import get_logger
from lifetrace.util.time_utils import get_utc_now
from lifetrace.util.utils import get_screenshot_filename

from .recorder_config import UNKNOWN_APP, UNKNOWN_WINDOW, with_timeout

logger = get_logger()


class ScreenshotCapture:
    """截图捕获类，处理截图的捕获、保存和数据库操作"""

    def __init__(
        self,
        screenshots_dir: str,
        file_io_timeout: float,
        db_timeout: float,
        deduplicate: bool,
        hash_threshold: int,
    ):
        self.screenshots_dir = screenshots_dir
        self.file_io_timeout = file_io_timeout
        self.db_timeout = db_timeout
        self.deduplicate = deduplicate
        self.hash_threshold = hash_threshold
        self.last_hashes = {}

    def save_screenshot(self, screenshot, file_path: str) -> bool:
        """保存截图到文件"""

        @with_timeout(timeout_seconds=self.file_io_timeout, operation_name="保存截图文件")
        def _do_save():
            mss_tools.to_png(screenshot.rgb, screenshot.size, output=file_path)
            return True

        try:
            result = _do_save()
            return result if result is not None else False
        except Exception as e:
            logger.error(f"保存截图失败 {file_path}: {e}")
            return False

    def get_image_size(self, file_path: str) -> tuple:
        """获取图像尺寸"""

        @with_timeout(timeout_seconds=self.file_io_timeout, operation_name="读取图像尺寸")
        def _do_get_size():
            with Image.open(file_path) as img:
                return img.size

        try:
            result = _do_get_size()
            return result if result is not None else (0, 0)
        except Exception as e:
            logger.error(f"读取图像尺寸失败 {file_path}: {e}")
            return (0, 0)

    def calculate_file_hash(self, file_path: str) -> str:
        """计算文件MD5哈希"""

        @with_timeout(timeout_seconds=self.file_io_timeout, operation_name="计算文件哈希")
        def _do_calculate_hash():
            with open(file_path, "rb") as f:
                return hashlib.md5(f.read(), usedforsecurity=False).hexdigest()

        try:
            result = _do_calculate_hash()
            return result if result is not None else ""
        except Exception as e:
            logger.error(f"计算文件哈希失败 {file_path}: {e}")
            return ""

    def calculate_image_hash(self, image_path: str) -> str:
        """计算图像感知哈希值"""

        @with_timeout(timeout_seconds=self.file_io_timeout, operation_name="计算图像哈希")
        def _do_calculate_hash():
            with Image.open(image_path) as img:
                return str(imagehash.phash(img))

        try:
            result = _do_calculate_hash()
            return result if result is not None else ""
        except Exception as e:
            logger.error(f"计算图像哈希失败 {image_path}: {e}")
            return ""

    def calculate_image_hash_from_memory(self, screenshot) -> str:
        """直接从内存中的截图计算图像感知哈希值"""

        @with_timeout(timeout_seconds=self.file_io_timeout, operation_name="从内存计算图像哈希")
        def _do_calculate_hash():
            img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
            return str(imagehash.phash(img))

        try:
            result = _do_calculate_hash()
            return result if result is not None else ""
        except Exception as e:
            logger.error(f"从内存计算图像哈希失败: {e}")
            return ""

    def is_duplicate(self, screen_id: int, image_hash: str) -> bool:
        """检查是否为重复图像"""
        if not self.deduplicate:
            return False

        if screen_id not in self.last_hashes:
            return False

        last_hash = self.last_hashes[screen_id]
        try:
            current = imagehash.hex_to_hash(image_hash)
            previous = imagehash.hex_to_hash(last_hash)
            distance = current - previous

            is_dup = distance <= self.hash_threshold

            if is_dup:
                logger.info(f"[窗口 {screen_id}] 跳过重复截图")

            return is_dup
        except Exception as e:
            logger.error(f"比较图像哈希失败: {e}")
            return False

    def save_to_database(
        self,
        file_path: str,
        file_hash: str,
        width: int,
        height: int,
        screen_id: int,
        app_name: str,
        window_title: str,
    ) -> int | None:
        """保存截图信息到数据库"""

        @with_timeout(timeout_seconds=self.db_timeout, operation_name="数据库操作")
        def _do_save_to_db():
            screenshot_id = screenshot_mgr.add_screenshot(
                file_path=file_path,
                file_hash=file_hash,
                width=width,
                height=height,
                metadata={
                    "screen_id": screen_id,
                    "app_name": app_name or UNKNOWN_APP,
                    "window_title": window_title or UNKNOWN_WINDOW,
                    "event_id": None,
                },
            )
            return screenshot_id

        try:
            result = _do_save_to_db()
            return result
        except Exception as e:
            logger.error(f"保存截图记录到数据库失败: {e}")
            return None

    def grab_and_prepare_screenshot(self, screen_id: int) -> tuple[Any | None, str, datetime]:
        """抓取屏幕并准备截图文件路径"""
        with mss.mss() as sct:
            if screen_id >= len(sct.monitors):
                logger.warning(f"[窗口 {screen_id}] 屏幕ID不存在")
                return None, "", get_utc_now()

            monitor = sct.monitors[screen_id]
            screenshot = sct.grab(monitor)
            timestamp = get_utc_now()
            filename = get_screenshot_filename(screen_id, timestamp)
            file_path = os.path.join(self.screenshots_dir, filename)
            return screenshot, file_path, timestamp


def process_screenshot_event(
    screenshot_id: int,
    app_name: str,
    window_title: str,
    timestamp: datetime,
):
    """处理截图事件：将截图关联到事件

    Args:
        screenshot_id: 截图ID
        app_name: 应用名称
        window_title: 窗口标题
        timestamp: 截图时间
    """
    try:
        event_id = event_mgr.get_or_create_event(
            app_name=app_name,
            window_title=window_title,
            timestamp=timestamp,
        )

        if event_id:
            success = event_mgr.add_screenshot_to_event(screenshot_id, event_id)
            if success:
                logger.info(
                    f"📎 截图 {screenshot_id} 已添加到事件 {event_id} [{app_name} - {window_title}]"
                )
            else:
                logger.warning(f"⚠️  截图 {screenshot_id} 添加到事件失败")
        else:
            logger.warning(f"⚠️  获取或创建事件失败，截图ID: {screenshot_id}")

    except Exception as e:
        logger.error(f"处理截图事件失败: {e}", exc_info=True)


def get_unprocessed_files(screenshots_dir: str) -> list[str]:
    """获取所有未处理的截图文件列表"""
    screenshot_files = []
    for file_path in Path(screenshots_dir).glob("*.png"):
        if file_path.is_file():
            screenshot_files.append(str(file_path))

    unprocessed_files = []
    for file_path in screenshot_files:
        screenshot = screenshot_mgr.get_screenshot_by_path(file_path)
        if not screenshot:
            unprocessed_files.append(file_path)

    return unprocessed_files


def extract_screen_id_from_path(file_path: str) -> int:
    """从文件名提取屏幕ID"""
    min_filename_parts = 2

    try:
        filename = os.path.basename(file_path)
        if filename.startswith("screen_"):
            parts = filename.split("_")
            if len(parts) >= min_filename_parts:
                return int(parts[1])
    except (ValueError, IndexError):
        pass
    return 0
