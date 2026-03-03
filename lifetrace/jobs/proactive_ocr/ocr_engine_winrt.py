"""
WinRT OCR 引擎封装模块
基于 Windows.Media.Ocr 的系统级 OCR 实现，专为 GUI 屏幕文字优化。
速度比 RapidOCR 快 20-40 倍，仅支持 Windows 10/11。
"""

import asyncio
import time
from typing import Any

import numpy as np

from lifetrace.util.logging_config import get_logger

from .models import BBox, OcrLine, OcrRawResult

logger = get_logger()

IMAGE_NDIM_GRAY = 2
IMAGE_CHANNEL_RGBA = 4
IMAGE_CHANNEL_RGB = 3

try:
    import winocr

    WINOCR_AVAILABLE = True
except ImportError:
    winocr = None
    WINOCR_AVAILABLE = False
    logger.info("winocr not available, WinRT OCR backend disabled")

try:
    import cv2
except ImportError:
    cv2 = None

try:
    from winrt.windows.globalization import Language
    from winrt.windows.media.ocr import OcrEngine as WinOcrEngine
except Exception:
    Language = None
    WinOcrEngine = None


class WinRtOcrEngine:
    """基于 Windows.Media.Ocr 的 OCR 引擎封装"""

    def __init__(
        self,
        lang: str = "zh-Hans-CN",
        resize_max_side: int = 0,
    ):
        """
        初始化 WinRT OCR 引擎

        Args:
            lang: OCR 语言代码（zh-Hans-CN 简体中文，en 英文，ja 日文等）
            resize_max_side: 预缩放最大边长，0 表示不缩放
        """
        if not WINOCR_AVAILABLE:
            raise ImportError("winocr not available. Install with: uv add winocr")

        self.lang = lang
        self.resize_max_side = resize_max_side

        # 验证语言是否支持
        try:
            if (
                WinOcrEngine is not None
                and Language is not None
                and not WinOcrEngine.is_language_supported(Language(lang))
            ):
                logger.warning(
                    f"WinRT OCR: language '{lang}' not supported, "
                    f"falling back to 'zh-Hans-CN'. "
                    f"Install via: Settings > Time & Language > Language"
                )
                self.lang = "zh-Hans-CN"
        except Exception as e:
            logger.warning(f"WinRT OCR: language check failed: {e}")

        logger.info(f"WinRT OCR engine initialized (lang={self.lang})")

    def _resize_image(self, image: np.ndarray, max_side: int) -> tuple:
        """等比例缩小图像"""
        if cv2 is None:
            return image, 1.0

        h, w = image.shape[:2]
        max_dim = max(h, w)

        if max_dim <= max_side:
            return image, 1.0

        scale = max_side / max_dim
        new_w = int(w * scale)
        new_h = int(h * scale)

        resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
        return resized, scale

    def _rgb_to_rgba(self, image: np.ndarray) -> np.ndarray:
        """将 RGB 图像转换为 RGBA 格式"""
        if image.ndim == IMAGE_NDIM_GRAY:
            # 灰度图
            rgba = np.zeros((*image.shape, 4), dtype=np.uint8)
            rgba[:, :, 0] = image
            rgba[:, :, 1] = image
            rgba[:, :, 2] = image
            rgba[:, :, 3] = 255
            return rgba
        elif image.shape[2] == IMAGE_CHANNEL_RGBA:
            return image
        elif image.shape[2] == IMAGE_CHANNEL_RGB:
            rgba = np.zeros((image.shape[0], image.shape[1], 4), dtype=np.uint8)
            rgba[:, :, :3] = image
            rgba[:, :, 3] = 255
            return rgba
        return image

    def ocr(self, image: np.ndarray) -> OcrRawResult:
        """
        对图像执行 OCR 识别

        Args:
            image: 输入图像，numpy 数组，RGB 格式

        Returns:
            OcrRawResult: OCR 识别结果
        """
        start_time = time.time()

        # 预缩放图像
        scale = 1.0
        if self.resize_max_side > 0:
            image, scale = self._resize_image(image, self.resize_max_side)

        # 转换 RGB → RGBA（WinRT 要求 RGBA8 格式）
        rgba_image = self._rgb_to_rgba(image)
        h, w = rgba_image.shape[:2]

        # 调用 WinRT OCR（同步方式，在线程中安全使用）
        try:
            result = self._recognize_sync(rgba_image.tobytes(), w, h)
        except Exception as e:
            logger.error(f"WinRT OCR failed: {e}")
            return OcrRawResult(
                lines=[],
                engine="winrt",
                latency_ms=(time.time() - start_time) * 1000,
            )

        latency_ms = (time.time() - start_time) * 1000

        # 解析结果
        lines = []
        if result and "lines" in result:
            for line_data in result["lines"]:
                text = line_data.get("text", "")
                if not text.strip():
                    continue

                # 提取 bounding rect
                # WinRT 返回的是 {x, y, width, height} 格式
                rect = line_data.get("bounding_rect", {})
                x = int(float(rect.get("x", 0)) / scale)
                y = int(float(rect.get("y", 0)) / scale)
                width = int(float(rect.get("width", 0)) / scale)
                height = int(float(rect.get("height", 0)) / scale)

                bbox = BBox(x=x, y=y, width=width, height=height)

                # WinRT 不提供行级置信度，从 words 中计算平均
                word_confidences = []
                for word in line_data.get("words", []):
                    # picklify 后是 dict
                    conf = word.get("confidence", None)
                    if conf is not None:
                        word_confidences.append(float(conf))

                avg_confidence = (
                    sum(word_confidences) / len(word_confidences)
                    if word_confidences
                    else 0.95  # WinRT 准确率高，默认给 0.95
                )

                lines.append(OcrLine(text=text, score=avg_confidence, bbox_px=bbox))

        return OcrRawResult(
            lines=lines,
            engine="winrt",
            latency_ms=latency_ms,
            det_time_ms=0,
            rec_time_ms=latency_ms,
            cls_time_ms=0,
            model_version="windows-media-ocr",
            device="cpu",
        )

    def _recognize_sync(self, image_bytes: bytes, width: int, height: int) -> dict[str, Any]:
        """同步调用 WinRT OCR"""
        # 在新的事件循环中运行异步调用
        # 这在普通线程中是安全的
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(self._recognize_async(image_bytes, width, height))
            return result
        finally:
            loop.close()

    async def _recognize_async(self, image_bytes: bytes, width: int, height: int) -> dict[str, Any]:
        """异步调用 WinRT OCR"""
        if winocr is None:
            raise RuntimeError("winocr backend unavailable")
        awaitable = winocr.recognize_bytes(image_bytes, width, height, lang=self.lang)
        result = await awaitable
        pickled = winocr.picklify(result)
        if not isinstance(pickled, dict):
            raise RuntimeError("winocr returned unexpected result type")
        return pickled

    def ocr_simple(self, image: np.ndarray) -> list[tuple[str, float]]:
        """简化版 OCR，只返回文本和置信度"""
        result = self.ocr(image)
        return [(line.text, line.score) for line in result.lines]
