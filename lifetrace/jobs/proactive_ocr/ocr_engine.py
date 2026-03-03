"""
OCR引擎封装模块
基于 RapidOCR (ONNX Runtime) 的轻量级OCR实现
"""

import platform
import re
import time
from typing import Protocol

import numpy as np

from lifetrace.util.logging_config import get_logger

from .models import BBox, OcrLine, OcrRawResult
from .ocr_engine_winrt import WINOCR_AVAILABLE, WinRtOcrEngine

logger = get_logger()

ELAPSE_COMPONENTS = 3


try:
    from rapidocr_onnxruntime import RapidOCR

    RAPIDOCR_AVAILABLE = True
except ImportError:
    RapidOCR = None
    RAPIDOCR_AVAILABLE = False
    logger.error("rapidocr-onnxruntime not available")

try:
    import cv2

    CV2_AVAILABLE = True
except ImportError:
    cv2 = None
    CV2_AVAILABLE = False
    logger.warning("opencv-python not available, image resizing disabled")


class OcrEngine:
    """OCR引擎封装类"""

    def __init__(
        self,
        det_limit_side_len: int = 640,
        det_limit_type: str = "max",
        rec_batch_num: int = 8,
        use_gpu: bool = False,
        resize_max_side: int = 0,  # 预缩放最大边长，0表示不缩放
        use_cls: bool = False,  # 是否启用方向分类（聊天场景不需要）
    ):
        """
        初始化OCR引擎

        Args:
            det_limit_side_len: 检测输入图像的边长限制，减小可降低内存占用
            det_limit_type: 边长限制类型，"max"限制最大边，"min"限制最小边
            rec_batch_num: 识别批次大小，增大可提升速度（推荐6~8）
            use_gpu: 是否使用GPU（需要安装CUDA版本onnxruntime）
            resize_max_side: 输入图像预缩放的最大边长，0表示不缩放
            use_cls: 是否启用方向分类，关闭可省50~200ms
        """
        if not RAPIDOCR_AVAILABLE:
            raise ImportError(
                "rapidocr-onnxruntime not available. Install with: uv add rapidocr-onnxruntime"
            )
        if RapidOCR is None:
            raise ImportError("RapidOCR backend is not available")

        # 配置参数
        init_params = {
            "det_limit_side_len": det_limit_side_len,
            "det_limit_type": det_limit_type,
            "rec_batch_num": rec_batch_num,
        }

        # GPU配置
        if use_gpu:
            init_params["use_cuda"] = True

        self.engine = RapidOCR(**init_params)

        self.det_limit_side_len = det_limit_side_len
        self.det_limit_type = det_limit_type
        self.rec_batch_num = rec_batch_num
        self.resize_max_side = resize_max_side
        self.use_cls = use_cls

    def _resize_image(self, image: np.ndarray, max_side: int) -> tuple:
        """
        等比例缩小图像

        Returns:
            (缩放后图像, 缩放比例)
        """
        if not CV2_AVAILABLE:
            logger.warning("OpenCV not available, skipping image resize")
            return image, 1.0
        if cv2 is None:
            logger.warning("OpenCV not available, skipping image resize")
            return image, 1.0

        cv2_local = cv2

        h, w = image.shape[:2]
        max_dim = max(h, w)

        if max_dim <= max_side:
            return image, 1.0

        scale = max_side / max_dim
        new_w = int(w * scale)
        new_h = int(h * scale)

        resized = cv2_local.resize(image, (new_w, new_h), interpolation=cv2_local.INTER_AREA)
        return resized, scale

    def ocr(self, image: np.ndarray) -> OcrRawResult:
        """
        对图像执行OCR识别

        Args:
            image: 输入图像，numpy数组，RGB格式

        Returns:
            OcrRawResult: OCR识别结果
        """
        start_time = time.time()

        # 预缩放图像
        scale = 1.0
        if self.resize_max_side > 0:
            image, scale = self._resize_image(image, self.resize_max_side)

        # 执行OCR（use_cls=False 跳过方向分类以加速）
        result, elapse = self.engine(image, use_cls=self.use_cls)

        latency_ms = (time.time() - start_time) * 1000

        det_time_ms, rec_time_ms, cls_time_ms = self._parse_elapse(elapse)

        # 解析结果
        lines = []
        if result:
            for item in result:
                # item格式: [bbox, text, score]
                # bbox格式: [[x1,y1], [x2,y1], [x2,y2], [x1,y2]]
                bbox_points = item[0]
                text = item[1]
                score = item[2]

                # 转换bbox为BBox格式（考虑缩放）
                x_coords = [float(p[0]) for p in bbox_points]
                y_coords = [float(p[1]) for p in bbox_points]
                x_min = int(min(x_coords) / scale)
                y_min = int(min(y_coords) / scale)
                x_max = int(max(x_coords) / scale)
                y_max = int(max(y_coords) / scale)

                bbox = BBox(
                    x=x_min,
                    y=y_min,
                    width=x_max - x_min,
                    height=y_max - y_min,
                )

                lines.append(OcrLine(text=text, score=float(score), bbox_px=bbox))

        return OcrRawResult(
            lines=lines,
            engine="rapidocr-onnxruntime",
            latency_ms=latency_ms,
            det_time_ms=det_time_ms,
            rec_time_ms=rec_time_ms,
            cls_time_ms=cls_time_ms,
            model_version="1.4.4",
            device="cpu",
        )

    @staticmethod
    def _parse_elapse(elapse: object) -> tuple[float, float, float]:
        det_time_ms = 0.0
        rec_time_ms = 0.0
        cls_time_ms = 0.0
        if not elapse:
            return det_time_ms, rec_time_ms, cls_time_ms

        # elapse 格式随 RapidOCR 版本不同而不同：
        # - v1.4.x: [det_time, cls_time, rec_time] (秒)
        # - 旧版本: str 或 dict
        if isinstance(elapse, list | tuple) and len(elapse) >= ELAPSE_COMPONENTS:
            det_time_ms = float(elapse[0]) * 1000
            cls_time_ms = float(elapse[1]) * 1000
            rec_time_ms = float(elapse[2]) * 1000
        elif isinstance(elapse, str):
            det_match = re.search(r"det[:\s]+(\d+\.?\d*)s?", elapse)
            rec_match = re.search(r"rec[:\s]+(\d+\.?\d*)s?", elapse)
            cls_match = re.search(r"cls[:\s]+(\d+\.?\d*)s?", elapse)
            if det_match:
                det_time_ms = float(det_match.group(1)) * 1000
            if rec_match:
                rec_time_ms = float(rec_match.group(1)) * 1000
            if cls_match:
                cls_time_ms = float(cls_match.group(1)) * 1000
        elif isinstance(elapse, dict):
            det_time_ms = float(elapse.get("det", 0)) * 1000
            rec_time_ms = float(elapse.get("rec", 0)) * 1000
            cls_time_ms = float(elapse.get("cls", 0)) * 1000
        return det_time_ms, rec_time_ms, cls_time_ms

    def ocr_simple(self, image: np.ndarray) -> list[tuple[str, float]]:
        """
        简化版OCR，只返回文本和置信度

        Args:
            image: 输入图像

        Returns:
            [(text, score), ...] 文本和置信度列表
        """
        result = self.ocr(image)
        return [(line.text, line.score) for line in result.lines]


# 单例实例（支持多后端）
class OcrBackend(Protocol):
    def ocr(self, image: np.ndarray) -> OcrRawResult: ...

    def ocr_simple(self, image: np.ndarray) -> list[tuple[str, float]]: ...


_engine_state: dict[str, OcrBackend | None] = {"instance": None}


def get_ocr_engine(
    backend: str = "auto",
    det_limit_side_len: int = 640,
    det_limit_type: str = "max",
    rec_batch_num: int = 8,
    resize_max_side: int = 0,
    use_cls: bool = False,
    winrt_lang: str = "zh-Hans-CN",
) -> OcrBackend:
    """
    获取 OCR 引擎单例

    Args:
        backend: OCR 后端选择
            - "auto": 自动选择（Windows 优先 WinRT，其他用 RapidOCR）
            - "winrt": 强制使用 WinRT（仅 Windows）
            - "rapidocr": 强制使用 RapidOCR（跨平台）
        det_limit_side_len: RapidOCR 检测边长限制
        det_limit_type: RapidOCR 边长限制类型
        rec_batch_num: RapidOCR 识别批次大小
        resize_max_side: 图像预缩放最大边长
        use_cls: RapidOCR 是否启用方向分类
        winrt_lang: WinRT OCR 语言代码
    """
    instance = _engine_state["instance"]
    if instance is not None:
        return instance

    # 选择后端
    chosen_backend = _resolve_backend(backend)

    if chosen_backend == "winrt":
        instance = WinRtOcrEngine(
            lang=winrt_lang,
            resize_max_side=resize_max_side,
        )
        logger.info("OCR backend: WinRT (Windows.Media.Ocr)")
    else:
        instance = OcrEngine(
            det_limit_side_len=det_limit_side_len,
            det_limit_type=det_limit_type,
            rec_batch_num=rec_batch_num,
            resize_max_side=resize_max_side,
            use_cls=use_cls,
        )
        logger.info("OCR backend: RapidOCR (ONNX Runtime)")

    _engine_state["instance"] = instance
    return instance


def _resolve_backend(backend: str) -> str:
    """
    解析 OCR 后端选择

    Args:
        backend: "auto", "winrt", "rapidocr"

    Returns:
        实际使用的后端名称
    """
    if backend == "rapidocr":
        return "rapidocr"

    if backend == "winrt":
        if WINOCR_AVAILABLE:
            return "winrt"
        logger.warning("WinRT OCR requested but not available, falling back to RapidOCR")
        return "rapidocr"

    # auto: Windows 上优先 WinRT
    if backend == "auto":
        if platform.system() == "Windows" and WINOCR_AVAILABLE:
            return "winrt"
        return "rapidocr"

    logger.warning(f"Unknown OCR backend '{backend}', falling back to RapidOCR")
    return "rapidocr"
