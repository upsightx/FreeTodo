"""
屏幕录制器 - 负责截图和相关处理
"""

import argparse
import os
import time
from datetime import datetime
from functools import lru_cache

import mss
from PIL import Image

from lifetrace.storage import event_mgr, screenshot_mgr
from lifetrace.util.logging_config import get_logger
from lifetrace.util.path_utils import get_screenshots_dir
from lifetrace.util.settings import settings
from lifetrace.util.utils import ensure_dir, get_active_window_info, get_active_window_screen

from .recorder_blacklist import get_blacklist_reason, log_blacklist_config
from .recorder_capture import (
    ScreenshotCapture,
    extract_screen_id_from_path,
    get_unprocessed_files,
    process_screenshot_event,
)
from .recorder_config import UNKNOWN_APP, UNKNOWN_WINDOW, with_timeout

logger = get_logger()


class ScreenRecorder:
    """屏幕录制器"""

    def __init__(self):
        self.screenshots_dir = str(get_screenshots_dir())
        self.interval = settings.get("jobs.recorder.interval")
        self.screens = self._get_screen_list()

        # 超时配置
        self.file_io_timeout = settings.get("jobs.recorder.params.file_io_timeout")
        self.db_timeout = settings.get("jobs.recorder.params.db_timeout")
        self.window_info_timeout = settings.get("jobs.recorder.params.window_info_timeout")

        # 初始化截图捕获器
        self.capture = ScreenshotCapture(
            screenshots_dir=self.screenshots_dir,
            file_io_timeout=self.file_io_timeout,
            db_timeout=self.db_timeout,
            deduplicate=settings.get("jobs.recorder.params.deduplicate"),
            hash_threshold=settings.get("jobs.recorder.params.hash_threshold"),
        )

        # 初始化截图目录
        ensure_dir(self.screenshots_dir)

        logger.info(
            f"超时配置 - 文件I/O: {self.file_io_timeout}s, "
            f"数据库: {self.db_timeout}s, "
            f"窗口信息: {self.window_info_timeout}s"
        )

        logger.info(f"屏幕录制器初始化完成，监控屏幕: {self.screens}")

        # 打印黑名单配置信息
        log_blacklist_config()

        # 启动时扫描未处理的文件
        self._scan_unprocessed_files()

    def _get_window_info(self) -> tuple[str, str]:
        """获取当前活动窗口信息"""

        @with_timeout(timeout_seconds=self.window_info_timeout, operation_name="获取窗口信息")
        def _do_get_window_info():
            return get_active_window_info()

        try:
            result = _do_get_window_info()
            if result is not None:
                app_name, window_title = result
                app_name = app_name or UNKNOWN_APP
                window_title = window_title or UNKNOWN_WINDOW
                return (app_name, window_title)
            return (UNKNOWN_APP, UNKNOWN_WINDOW)
        except Exception as e:
            logger.error(f"获取窗口信息失败: {e}")
            return (UNKNOWN_APP, UNKNOWN_WINDOW)

    def _get_screen_list(self) -> list[int]:
        """获取要截图的屏幕列表"""
        screens_config = settings.get("jobs.recorder.params.screens")
        logger.debug(f"屏幕配置: {screens_config}")
        with mss.mss() as sct:
            monitor_count = len(sct.monitors) - 1

            if screens_config == "all":
                return list(range(1, monitor_count + 1))
            elif isinstance(screens_config, list):
                return [s for s in screens_config if 1 <= s <= monitor_count]
            else:
                return [1] if monitor_count > 0 else []

    def _capture_screen(
        self,
        screen_id: int,
        app_name: str | None = None,
        window_title: str | None = None,
    ) -> tuple[str | None, str]:
        """截取指定屏幕

        Returns:
            (file_path, status) - file_path为截图路径，status为状态: 'success', 'skipped', 'failed'
        """
        try:
            screenshot, file_path, timestamp = self.capture.grab_and_prepare_screenshot(screen_id)
            if not screenshot:
                return None, "failed"

            # 优化：先从内存计算图像哈希，避免不必要的磁盘I/O
            image_hash = self.capture.calculate_image_hash_from_memory(screenshot)
            if not image_hash:
                filename = os.path.basename(file_path)
                logger.error(f"[窗口 {screen_id}] 计算图像哈希失败，跳过: {filename}")
                return None, "failed"

            # 检查是否重复
            if self.capture.is_duplicate(screen_id, image_hash):
                filename = os.path.basename(file_path)
                logger.debug(f"[窗口 {screen_id}] 检测到重复截图，跳过保存: {filename}")
                return None, "skipped"

            # 更新哈希记录并保存截图
            self.capture.last_hashes[screen_id] = image_hash
            if not self.capture.save_screenshot(screenshot, file_path):
                filename = os.path.basename(file_path)
                logger.error(f"[窗口 {screen_id}] 保存截图失败: {filename}")
                return None, "failed"

            # 获取窗口信息和保存到数据库
            app_name, window_title = self._ensure_window_info(app_name, window_title)
            self._save_screenshot_metadata(file_path, screen_id, app_name, window_title, timestamp)

            return file_path, "success"

        except Exception as e:
            logger.error(f"[窗口 {screen_id}] 截图失败: {e}")
            return None, "failed"

    def _ensure_window_info(
        self,
        app_name: str | None,
        window_title: str | None,
    ) -> tuple[str, str]:
        """确保有窗口信息，如果没有则获取"""
        if app_name is None or window_title is None:
            return self._get_window_info()
        return app_name, window_title

    def _save_screenshot_metadata(
        self, file_path: str, screen_id: int, app_name: str, window_title: str, timestamp: datetime
    ):
        """保存截图的元数据到数据库"""
        filename = os.path.basename(file_path)

        width, height = self.capture.get_image_size(file_path)
        file_hash = self.capture.calculate_file_hash(file_path)
        if not file_hash:
            logger.warning(f"[窗口 {screen_id}] 计算文件哈希失败，使用空值: {filename}")
            file_hash = ""

        screenshot_id = self.capture.save_to_database(
            file_path, file_hash, width, height, screen_id, app_name, window_title
        )

        if screenshot_id:
            logger.debug(f"[窗口 {screen_id}] 截图记录已保存到数据库: {screenshot_id}")
            process_screenshot_event(screenshot_id, app_name, window_title, timestamp)
        else:
            logger.warning(f"[窗口 {screen_id}] 数据库保存失败，但文件已保存: {filename}")

        file_size = os.path.getsize(file_path)
        file_size_kb = file_size / 1024
        logger.info(f"[窗口 {screen_id}] 截图保存: {filename} ({file_size_kb:.2f} KB) - {app_name}")

    def _close_active_event_on_blacklist(self):
        """当应用进入黑名单时关闭活跃事件"""
        try:
            event_mgr.close_active_event()
            logger.info("已关闭上一个活跃事件")
        except Exception as e:
            logger.error(f"关闭活跃事件失败: {e}")

    def capture_all_screens(self) -> list[str]:
        """只截取活跃窗口所在的屏幕"""
        captured_files = []

        app_name, window_title = self._get_window_info()
        active_screen_id = get_active_window_screen()

        if active_screen_id is None:
            logger.warning("无法获取活跃窗口所在的屏幕，跳过截图")
            return captured_files

        if active_screen_id not in self.screens:
            logger.info(f"⏭️  活跃窗口在屏幕 {active_screen_id}，但该屏幕未在配置中启用，跳过截图")
            return captured_files

        blacklist_reason = get_blacklist_reason(app_name, window_title)
        is_blacklisted = bool(blacklist_reason)

        if is_blacklisted:
            logger.info(f"⏭️  {blacklist_reason}（跳过截图）")
            self._close_active_event_on_blacklist()
            return captured_files

        logger.info(
            f"📸 准备截图 - 屏幕: {active_screen_id}, 应用: {app_name}, 窗口: {window_title}"
        )

        file_path, status = self._capture_screen(active_screen_id, app_name, window_title)
        if file_path:
            captured_files.append(file_path)

        if status == "success":
            logger.info(f"截图成功 - 屏幕: {active_screen_id}")
        elif status == "skipped":
            logger.info(f"截图跳过 - 屏幕: {active_screen_id}")
        elif status == "failed":
            logger.warning(f"截图失败 - 屏幕: {active_screen_id}")

        return captured_files

    def execute_capture(self):
        """执行一次截图任务（用于调度器调用）

        Returns:
            捕获的文件列表
        """
        try:
            captured_files = self.capture_all_screens()
            if captured_files:
                logger.info(f"✅ 本次截取了 {len(captured_files)} 张截图")
            else:
                logger.info("⏭️  本次未截取截图（窗口被跳过或重复）")
            return captured_files
        except Exception as e:
            logger.error(f"执行截图任务失败: {e}")
            return []

    def start_recording(self):
        """开始录制（传统模式，独立运行）"""
        logger.info("开始屏幕录制...")

        try:
            while True:
                start_time = time.time()

                captured_files = self.capture_all_screens()

                if captured_files:
                    logger.debug(f"本次截取了 {len(captured_files)} 张截图")

                elapsed = time.time() - start_time
                sleep_time = max(0, self.interval - elapsed)

                if sleep_time > 0:
                    time.sleep(sleep_time)
                else:
                    logger.warning(f"截图处理时间 ({elapsed:.2f}s) 超过间隔时间 ({self.interval}s)")

        except KeyboardInterrupt:
            logger.error("收到停止信号，结束录制")
            self._print_final_stats()
        except Exception as e:
            logger.error(f"录制过程中发生错误: {e}")
            self._print_final_stats()
            raise
        finally:
            pass

    def _process_single_file(self, file_path: str) -> bool:
        """处理单个未处理的截图文件，返回是否成功"""
        if not os.path.exists(file_path):
            return False

        file_stats = os.stat(file_path)
        if file_stats.st_size == 0:
            logger.warning(f"文件为空，跳过: {file_path}")
            return False

        try:
            with Image.open(file_path) as img:
                width, height = img.size
        except Exception as e:
            logger.error(f"无法处理图像文件 {file_path}: {e}")
            return False

        screen_id = extract_screen_id_from_path(file_path)

        file_hash = self.capture.calculate_file_hash(file_path)
        if not file_hash:
            filename = os.path.basename(file_path)
            logger.warning(f"[窗口 {screen_id}] 计算文件哈希失败，使用空值: {filename}")
            file_hash = ""

        app_name, window_title = self._get_window_info()

        screenshot_id = screenshot_mgr.add_screenshot(
            file_path=file_path,
            file_hash=file_hash,
            width=width,
            height=height,
            metadata={
                "screen_id": screen_id,
                "app_name": app_name,
                "window_title": window_title,
            },
        )

        if screenshot_id:
            filename = os.path.basename(file_path)
            logger.debug(f"[窗口 {screen_id}] 已处理未处理文件: {filename} (ID: {screenshot_id})")
            return True

        logger.warning(f"[窗口 {screen_id}] 添加截图记录失败: {file_path}")
        return False

    def _scan_unprocessed_files(self):
        """扫描并处理未处理的截图文件"""
        if not os.path.exists(self.screenshots_dir):
            logger.info("截图目录不存在，跳过扫描")
            return

        logger.info(f"扫描现有截图文件: {self.screenshots_dir}")

        unprocessed_files = get_unprocessed_files(self.screenshots_dir)

        if not unprocessed_files:
            logger.info("未发现未处理的截图文件")
            return

        logger.info(f"发现 {len(unprocessed_files)} 个未处理文件，开始处理...")

        processed_count = 0
        for file_path in unprocessed_files:
            try:
                if self._process_single_file(file_path):
                    processed_count += 1
            except Exception as e:
                logger.error(f"处理文件失败 {file_path}: {e}")

        logger.info(
            f"未处理文件扫描完成，成功处理 {processed_count}/{len(unprocessed_files)} 个文件"
        )

    def _print_final_stats(self):
        """输出最终统计信息"""
        logger.info("录制会话结束")


# 全局录制器实例（用于调度器任务）


@lru_cache(maxsize=1)
def get_recorder_instance() -> ScreenRecorder:
    """获取全局录制器实例

    Returns:
        ScreenRecorder 实例
    """
    return ScreenRecorder()


def execute_capture_task():
    """执行截图任务（供调度器调用的可序列化函数）

    这是一个模块级别的函数，可以被 APScheduler 序列化到数据库中
    """
    try:
        logger.info("🔄 开始执行录制器任务")
        recorder = get_recorder_instance()
        captured_files = recorder.execute_capture()
        return len(captured_files)
    except Exception as e:
        logger.error(f"执行录制器任务失败: {e}", exc_info=True)
        return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LifeTrace Screen Recorder")
    parser.add_argument("--config", help="配置文件路径")
    parser.add_argument("--interval", type=int, help="截图间隔（秒）")
    parser.add_argument("--screens", help='要截图的屏幕，用逗号分隔或使用"all"')
    parser.add_argument("--debug", action="store_true", help="启用调试日志")

    args = parser.parse_args()

    if args.interval:
        settings.set("jobs.recorder.interval", args.interval)

    if args.screens:
        if args.screens.lower() == "all":
            settings.set("jobs.recorder.params.screens", "all")
        else:
            screens = [int(s.strip()) for s in args.screens.split(",")]
            settings.set("jobs.recorder.params.screens", screens)

    recorder = ScreenRecorder()
    recorder.start_recording()
