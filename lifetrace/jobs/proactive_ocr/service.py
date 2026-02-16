"""
Proactive OCR Service
主动检测并处理 WeChat/Feishu 窗口的 OCR 服务
"""

import hashlib
import sys
import threading
import time
from functools import lru_cache
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from lifetrace.llm.todo_extraction_service import todo_extraction_service
from lifetrace.storage import ocr_mgr, screenshot_mgr
from lifetrace.util.logging_config import get_logger
from lifetrace.util.path_utils import get_screenshots_dir
from lifetrace.util.settings import settings
from lifetrace.util.utils import ensure_dir

from .capture import get_capture
from .models import AppType
from .ocr_engine import get_ocr_engine
from .roi import get_roi_extractor
from .router import get_router

logger = get_logger()


class ProactiveOCRService:
    """Proactive OCR 服务"""

    def __init__(self):
        self.is_running = False
        self._monitor_thread: threading.Thread | None = None
        self._stop_event = threading.Event()

        # 从配置读取参数
        self.interval = settings.get("jobs.proactive_ocr.interval", 1.0)
        self.ocr_backend = settings.get("jobs.proactive_ocr.ocr_backend", "auto")
        self.winrt_lang = settings.get("jobs.proactive_ocr.winrt_lang", "zh-Hans-CN")
        self.use_roi = settings.get("jobs.proactive_ocr.use_roi", True)
        self.resize_max_side = settings.get("jobs.proactive_ocr.resize_max_side", 800)
        self.det_limit_side_len = settings.get("jobs.proactive_ocr.det_limit_side_len", 640)
        self.rec_batch_num = settings.get("jobs.proactive_ocr.rec_batch_num", 8)
        self.use_cls = settings.get("jobs.proactive_ocr.use_cls", False)
        self.min_confidence = settings.get("jobs.proactive_ocr.min_confidence", 0.8)

        # 初始化组件
        self.router = get_router()
        self.capture = get_capture(fps=1.0 / self.interval)
        self.roi_extractor = get_roi_extractor()
        self.ocr_engine = get_ocr_engine(
            backend=self.ocr_backend,
            det_limit_side_len=self.det_limit_side_len,
            resize_max_side=self.resize_max_side,
            rec_batch_num=self.rec_batch_num,
            use_cls=self.use_cls,
            winrt_lang=self.winrt_lang,
        )

        # 统计信息
        self.stats = {
            "total_captures": 0,
            "successful_ocrs": 0,
            "failed_captures": 0,
            "last_capture_time": None,
        }

        logger.info(
            f"ProactiveOCR: Service initialized (interval={self.interval}s, "
            f"use_roi={self.use_roi}, resize_max_side={self.resize_max_side})"
        )

    def start(self):
        """启动监控服务"""
        if self.is_running:
            logger.warning("ProactiveOCR: Service is already running")
            return

        self.is_running = True
        self._stop_event.clear()
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop, daemon=True, name="ProactiveOCRMonitor"
        )
        self._monitor_thread.start()
        logger.info(
            f"ProactiveOCR: Service started (interval={self.interval}s, "
            f"apps=['wechat', 'feishu'], platform={sys.platform})"
        )

    def stop(self):
        """停止监控服务"""
        if not self.is_running:
            return

        self.is_running = False
        self._stop_event.set()

        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=5.0)

        logger.info("ProactiveOCR: Service stopped")

    def _monitor_loop(self):
        """监控循环"""
        while self.is_running and not self._stop_event.is_set():
            try:
                self.run_once()
            except Exception as e:
                logger.error(f"ProactiveOCR: Error in monitor loop: {e}", exc_info=True)

            # 等待间隔时间
            self._stop_event.wait(self.interval)

    def run_once(self) -> dict[str, Any] | None:
        """
        执行一次检测和处理

        Returns:
            处理结果字典，如果未检测到目标窗口返回 None
        """
        # 获取前台窗口（跨平台）
        window = self.capture.get_foreground_window()
        if not window:
            return None

        # 检查是否为目标应用
        app_type, _reason = self.router.identify_app(window)
        if app_type == AppType.UNKNOWN:
            return None

        logger.info(
            f"ProactiveOCR: Detected foreground window: hwnd={window.hwnd}, "
            f'app={app_type.value}, title="{window.title[:50]}"'
        )

        # 检查窗口是否最小化
        if window.is_minimized:
            logger.debug("ProactiveOCR: Window is minimized, skipping capture")
            return None

        logger.debug(f"ProactiveOCR: Window size: {window.rect.width}x{window.rect.height}")

        # 捕获窗口截图
        timings = {}
        t0 = time.perf_counter()
        frame = self.capture.capture_window(window)
        timings["capture"] = (time.perf_counter() - t0) * 1000

        if frame is None:
            logger.error("ProactiveOCR: Capture window failed")
            self.stats["failed_captures"] += 1
            return None

        logger.info(
            f"ProactiveOCR: Capture completed in {timings['capture']:.0f}ms "
            f"({frame.width}x{frame.height})"
        )

        # 检测空白/全黑图像（PrintWindow 偶尔返回空白帧）
        img_std = float(np.std(frame.data))
        if img_std < 5.0:
            logger.warning(
                f"ProactiveOCR: Captured image appears blank/uniform "
                f"(std={img_std:.1f}), skipping OCR"
            )
            self.stats["failed_captures"] += 1
            return None

        # ROI 裁切
        image_to_ocr = frame.data
        theme = None
        roi_result = None

        if self.use_roi:
            t0 = time.perf_counter()
            roi_result = self.roi_extractor.extract_with_details(frame.data, app_type)
            timings["roi"] = (time.perf_counter() - t0) * 1000

            if roi_result:
                # 安全网：如果 ROI 区域面积不到原图的 10%，说明裁切可能出错，回退全图
                roi_area = roi_result.width * roi_result.height
                full_area = frame.width * frame.height
                min_area_ratio = 0.10

                if full_area > 0 and roi_area / full_area < min_area_ratio:
                    logger.warning(
                        f"ProactiveOCR: ROI too small ({roi_result.width}x{roi_result.height}, "
                        f"{roi_area / full_area:.1%} of full image), falling back to full image"
                    )
                    roi_result = None  # 丢弃异常的 ROI
                else:
                    image_to_ocr = roi_result.image
                    theme = roi_result.theme
                    logger.info(
                        f"ProactiveOCR: ROI extracted - theme={theme}, "
                        f"region={roi_result.width}x{roi_result.height} "
                        f"(from x={roi_result.x}, y={roi_result.y}), "
                        f"time={timings['roi']:.1f}ms"
                    )

        # 执行 OCR 识别
        ocr_h, ocr_w = image_to_ocr.shape[:2]
        logger.info(
            f"ProactiveOCR: OCR input {ocr_w}x{ocr_h} "
            f"(resize_max_side={self.resize_max_side}, det_limit={self.det_limit_side_len})"
        )
        t0 = time.perf_counter()
        ocr_result = self.ocr_engine.ocr(image_to_ocr)
        timings["ocr_total"] = (time.perf_counter() - t0) * 1000

        logger.info(
            f"ProactiveOCR: OCR completed in {timings['ocr_total']:.0f}ms "
            f"(det={ocr_result.det_time_ms:.0f}ms, "
            f"cls={ocr_result.cls_time_ms:.0f}ms, "
            f"rec={ocr_result.rec_time_ms:.0f}ms)"
        )

        # 过滤低置信度结果
        valid_lines = [line for line in ocr_result.lines if line.score >= self.min_confidence]
        logger.info(
            f"ProactiveOCR: Found {len(valid_lines)} text blocks "
            f"(confidence >={self.min_confidence})"
        )

        if len(valid_lines) > 0:
            # 提取文本内容
            text_content = "\n".join([line.text for line in valid_lines])
            logger.debug(f"ProactiveOCR: Text preview: {text_content[:100]}...")

            # 保存截图和 OCR 结果到数据库
            screenshot_id = self._save_to_database(
                frame,
                window,
                app_type,
                text_content,
                ocr_result,
                valid_lines,
                roi_image=roi_result.image if roi_result else None,
                ocr_input_image=image_to_ocr,
            )

            if screenshot_id:
                self.stats["successful_ocrs"] += 1
                logger.info(
                    f"ProactiveOCR: Saved screenshot_id={screenshot_id}, "
                    f"ocr_result with {len(valid_lines)} lines"
                )

        self.stats["total_captures"] += 1
        self.stats["last_capture_time"] = time.time()

        total_time = sum(timings.values())
        logger.debug(f"ProactiveOCR: Total time: {total_time:.0f}ms")

        return {
            "app_type": app_type.value,
            "window_title": window.title,
            "text_lines": len(valid_lines),
            "timings": timings,
        }

    @staticmethod
    def _draw_ocr_visualization(
        image: np.ndarray,
        valid_lines: list,
    ) -> Image.Image:
        """在图像上绘制 OCR 识别结果的边界框和文本标注

        Args:
            image: OCR 输入图像 (numpy array, RGB)
            valid_lines: 通过置信度过滤后的 OcrLine 列表

        Returns:
            带有边界框标注的 PIL Image
        """
        vis_img = Image.fromarray(image.copy())
        draw = ImageDraw.Draw(vis_img)

        # 尝试加载字体（回退到默认字体）
        font = None
        font_small = None
        try:
            # Windows 系统常见中文字体
            for font_name in [
                "msyh.ttc",  # 微软雅黑
                "simhei.ttf",  # 黑体
                "simsun.ttc",  # 宋体
                "arial.ttf",  # Arial
            ]:
                try:
                    font = ImageFont.truetype(font_name, 14)
                    font_small = ImageFont.truetype(font_name, 11)
                    break
                except OSError:
                    continue
        except Exception:
            pass

        if font is None:
            font = ImageFont.load_default()
            font_small = font

        for line in valid_lines:
            bbox = line.bbox_px
            x1, y1 = bbox.x, bbox.y
            x2, y2 = bbox.x + bbox.width, bbox.y + bbox.height

            # 根据置信度选择颜色：高置信度绿色，中等黄色，低置信度红色
            if line.score >= 0.95:
                box_color = (0, 200, 0)  # 绿色
            elif line.score >= 0.85:
                box_color = (0, 160, 255)  # 蓝色
            else:
                box_color = (255, 140, 0)  # 橙色

            # 画边界框
            draw.rectangle([x1, y1, x2, y2], outline=box_color, width=2)

            # 画标签背景（置信度 + 文本预览）
            score_text = f"{line.score:.2f}"
            label = f"{score_text} {line.text[:20]}"
            label_bbox = draw.textbbox((0, 0), label, font=font_small)
            label_w = label_bbox[2] - label_bbox[0] + 6
            label_h = label_bbox[3] - label_bbox[1] + 4

            # 标签放在框的上方，如果空间不够就放下方
            label_y = y1 - label_h - 2
            if label_y < 0:
                label_y = y2 + 2

            draw.rectangle(
                [x1, label_y, x1 + label_w, label_y + label_h],
                fill=box_color,
            )
            draw.text(
                (x1 + 3, label_y + 2),
                label,
                fill=(255, 255, 255),
                font=font_small,
            )

        return vis_img

    def _save_to_database(
        self,
        frame,
        window,
        app_type: AppType,
        text_content: str,
        ocr_result,
        valid_lines,
        roi_image=None,
        ocr_input_image=None,
    ) -> int | None:
        """保存截图和 OCR 结果到数据库"""
        try:
            # 保存图像文件
            screenshots_dir = get_screenshots_dir()
            ensure_dir(str(screenshots_dir))

            # 生成文件名
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"proactive_{app_type.value}_{timestamp}_{frame.capture_id}.png"
            file_path = str(screenshots_dir / filename)

            # 保存原始图像（PIL Image）
            img = Image.fromarray(frame.data)
            img.save(file_path)

            # 保存 ROI 裁切后的图像
            if roi_image is not None:
                roi_filename = f"proactive_{app_type.value}_{timestamp}_{frame.capture_id}_roi.png"
                roi_file_path = str(screenshots_dir / roi_filename)
                roi_img = Image.fromarray(roi_image)
                roi_img.save(roi_file_path)
                logger.debug(f"ProactiveOCR: ROI image saved to {roi_file_path}")

            # 保存 OCR 可视化图像（在 OCR 输入图像上画框）
            if ocr_input_image is not None and valid_lines:
                try:
                    vis_img = self._draw_ocr_visualization(ocr_input_image, valid_lines)
                    vis_filename = (
                        f"proactive_{app_type.value}_{timestamp}_{frame.capture_id}_ocr.png"
                    )
                    vis_file_path = str(screenshots_dir / vis_filename)
                    vis_img.save(vis_file_path)
                    logger.debug(
                        f"ProactiveOCR: OCR visualization saved to {vis_file_path} "
                        f"({len(valid_lines)} boxes)"
                    )
                except Exception as e:
                    logger.warning(f"ProactiveOCR: Failed to save OCR visualization: {e}")

            # 计算文件哈希
            with open(file_path, "rb") as f:
                file_hash = hashlib.md5(f.read(), usedforsecurity=False).hexdigest()

            # 添加截图记录
            screenshot_id = screenshot_mgr.add_screenshot(
                file_path=file_path,
                file_hash=file_hash,
                width=frame.width,
                height=frame.height,
                metadata={
                    "screen_id": 0,
                    "app_name": app_type.value,
                    "window_title": window.title,
                    "proactive_ocr": True,
                    "hwnd": window.hwnd,
                    "pid": window.pid,
                },
            )

            if not screenshot_id:
                logger.error("ProactiveOCR: Failed to save screenshot to database")
                return None

            # 计算平均置信度
            avg_confidence = (
                sum(line.score for line in valid_lines) / len(valid_lines) if valid_lines else 0.0
            )

            # 添加 OCR 结果
            ocr_result_id = ocr_mgr.add_ocr_result(
                screenshot_id=screenshot_id,
                text_content=text_content,
                confidence=avg_confidence,
                language="ch",
                processing_time=ocr_result.latency_ms / 1000.0,
            )

            if ocr_result_id:
                logger.debug(f"ProactiveOCR: Saved OCR result_id={ocr_result_id}")

                # Publish to Perception Stream (best-effort, threadsafe).
                try:
                    from lifetrace.perception.manager import (  # noqa: PLC0415
                        try_get_perception_manager,
                    )

                    mgr = try_get_perception_manager()
                    if mgr is not None and screenshot_id:
                        mgr.try_publish_proactive_ocr_threadsafe(
                            text_content,
                            content_raw=f"/api/screenshots/{screenshot_id}/image",
                            metadata={
                                "source": "proactive_ocr",
                                "screenshot_id": screenshot_id,
                                "ocr_result_id": ocr_result_id,
                                "app_name": app_type.value,
                                "window_title": window.title,
                                "confidence": avg_confidence,
                                "hwnd": window.hwnd,
                                "pid": window.pid,
                            },
                        )
                except Exception as exc:
                    logger.debug(f"Perception publish skipped: {exc}")

                # 自动触发基于 OCR 文本的待办提取
                # 同时检查 proactive_ocr 自身开关和全局自动待办检测开关
                try:
                    auto_extract = settings.get(
                        "jobs.proactive_ocr.params.auto_extract_todos", False
                    )
                    global_auto_todo = settings.get("jobs.auto_todo_detection.enabled", False)
                    min_text_length = settings.get(
                        "jobs.proactive_ocr.params.min_text_length",
                        10,
                    )
                    should_extract = (auto_extract or global_auto_todo) and len(
                        (text_content or "").strip()
                    ) >= min_text_length
                    if should_extract:
                        logger.info(
                            "ProactiveOCR: auto_extract_todos 开启，开始基于 OCR 文本提取待办"
                        )
                        # 我们仅调用提取逻辑，不在此处直接写 todo，结果由上层或日志查看
                        extraction_result = todo_extraction_service.extract_todos_from_ocr_text(
                            ocr_result_id=ocr_result_id,
                            text_content=text_content,
                            app_name=app_type.value,
                            window_title=window.title,
                        )

                        if extraction_result.get("skipped"):
                            logger.info(
                                "ProactiveOCR: OCR 文本待办提取已跳过 - "
                                f"reason={extraction_result.get('reason')}, "
                                f"ocr_result_id={extraction_result.get('ocr_result_id')}"
                            )
                        else:
                            todos_count = len(extraction_result.get("todos") or [])
                            error_message = extraction_result.get("error_message")
                            created_count = extraction_result.get("created_count")
                            if error_message:
                                logger.warning(
                                    "ProactiveOCR: OCR 文本待办提取完成但存在错误 - "
                                    f"error={error_message}, "
                                    f"ocr_result_id={extraction_result.get('ocr_result_id')}, "
                                    f"todos_count={todos_count}, "
                                    f"created_count={created_count}"
                                )
                            else:
                                logger.info(
                                    "ProactiveOCR: OCR 文本待办提取完成 - "
                                    f"ocr_result_id={extraction_result.get('ocr_result_id')}, "
                                    f"todos_count={todos_count}, "
                                    f"created_count={created_count}"
                                )
                except Exception as e:
                    logger.error(f"ProactiveOCR: 自动待办提取失败（已忽略）: {e}", exc_info=True)

                return screenshot_id

            return None

        except Exception as e:
            logger.error(f"ProactiveOCR: Failed to save to database: {e}", exc_info=True)
            return None

    def get_status(self) -> dict[str, Any]:
        """获取服务状态"""
        return {
            "is_running": self.is_running,
            "interval": self.interval,
            "use_roi": self.use_roi,
            "platform": sys.platform,
            "stats": self.stats.copy(),
        }


# 单例实例


@lru_cache(maxsize=1)
def get_proactive_ocr_service() -> ProactiveOCRService:
    """获取 Proactive OCR 服务单例"""
    return ProactiveOCRService()
