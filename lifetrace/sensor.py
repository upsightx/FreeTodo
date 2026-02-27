"""LifeTrace Sensor — lightweight perception daemon.

Run on the sensing PC to capture screen / proactive-OCR data and forward
PerceptionEvents to the remote Center node via HTTP POST.

Usage:
    python -m lifetrace.sensor --center-url https://xxx.cpolar.top --node-id MY-PC
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import platform

import httpx
import numpy as np

from lifetrace.perception.models import Modality, PerceptionEvent, SourceType
from lifetrace.util.logging_config import get_logger
from lifetrace.util.time_utils import get_utc_now

logger = get_logger()

# ---------------------------------------------------------------------------
# Lazy singletons for heavy components (created on first use)
# ---------------------------------------------------------------------------

_window_capture = None
_app_router = None
_roi_extractor = None
_ocr_engine = None


def _mss_grab_in_thread() -> np.ndarray | None:
    """Capture primary monitor inside the calling thread.

    mss uses thread-local Win32 DC handles, so we must create and
    close the instance within the same thread.
    """
    import mss  # noqa: PLC0415

    try:
        with mss.mss() as sct:
            monitor = sct.monitors[1]
            shot = sct.grab(monitor)
            arr = np.array(shot)
            if arr.shape[2] == BGRA_CHANNELS:
                arr = arr[:, :, :3]
            return arr[:, :, ::-1].copy()
    except Exception as exc:
        logger.error(f"mss screenshot failed: {exc}")
        return None


def _get_window_capture():
    global _window_capture  # noqa: PLW0603
    if _window_capture is None:
        from lifetrace.jobs.proactive_ocr.capture import WindowCapture  # noqa: PLC0415

        _window_capture = WindowCapture(fps=1.0)
    return _window_capture


def _get_app_router():
    global _app_router  # noqa: PLW0603
    if _app_router is None:
        from lifetrace.jobs.proactive_ocr.router import AppRouter  # noqa: PLC0415

        _app_router = AppRouter()
    return _app_router


def _get_roi_extractor():
    global _roi_extractor  # noqa: PLW0603
    if _roi_extractor is None:
        from lifetrace.jobs.proactive_ocr.roi import get_roi_extractor  # noqa: PLC0415

        _roi_extractor = get_roi_extractor()
    return _roi_extractor


def _get_ocr_engine():
    global _ocr_engine  # noqa: PLW0603
    if _ocr_engine is None:
        from lifetrace.jobs.proactive_ocr.ocr_engine import get_ocr_engine  # noqa: PLC0415
        from lifetrace.util.settings import settings  # noqa: PLC0415

        _ocr_engine = get_ocr_engine(
            backend=settings.get("jobs.proactive_ocr.ocr_backend", "auto"),
            det_limit_side_len=settings.get("jobs.proactive_ocr.det_limit_side_len", 960),
            resize_max_side=settings.get("jobs.proactive_ocr.resize_max_side", 0),
            rec_batch_num=settings.get("jobs.proactive_ocr.rec_batch_num", 8),
            use_cls=settings.get("jobs.proactive_ocr.use_cls", False),
            winrt_lang=settings.get("jobs.proactive_ocr.winrt_lang", "zh-Hans-CN"),
        )
    return _ocr_engine


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

BGRA_CHANNELS = 4
_MIN_OCR_CONFIDENCE = 0.8
_MIN_TEXT_LEN = 5
_BLANK_IMAGE_STD_THRESHOLD = 5.0
_MIN_ROI_AREA_RATIO = 0.10


def _text_hash(text: str) -> str:
    return hashlib.md5(text.encode(), usedforsecurity=False).hexdigest()


# ---------------------------------------------------------------------------
# SensorDaemon
# ---------------------------------------------------------------------------


class SensorDaemon:
    """轻量感知守护进程，采集本地屏幕/OCR 数据并转发到 Center。"""

    def __init__(self, center_url: str, node_id: str):
        self.center_url = center_url.rstrip("/")
        self.node_id = node_id
        self.client = httpx.AsyncClient(timeout=30)

        self._last_screenshot_hash: str = ""
        self._last_proactive_hash: str = ""
        self._consecutive_post_failures: int = 0
        self._max_backoff: float = 120.0

    # ------------------------------------------------------------------
    # Network helpers
    # ------------------------------------------------------------------

    async def post_event(self, event: PerceptionEvent) -> None:
        event.metadata["node_id"] = self.node_id
        url = f"{self.center_url}/api/perception/ingest"
        resp = await self.client.post(url, json=event.model_dump(mode="json"))
        resp.raise_for_status()
        self._consecutive_post_failures = 0

    async def post_batch(self, events: list[PerceptionEvent]) -> None:
        if not events:
            return
        for e in events:
            e.metadata["node_id"] = self.node_id
        url = f"{self.center_url}/api/perception/ingest/batch"
        payload = {
            "node_id": self.node_id,
            "events": [e.model_dump(mode="json") for e in events],
        }
        resp = await self.client.post(url, json=payload)
        resp.raise_for_status()
        self._consecutive_post_failures = 0

    async def _safe_post(self, event: PerceptionEvent) -> bool:
        try:
            await self.post_event(event)
            return True
        except Exception as exc:
            self._consecutive_post_failures += 1
            logger.warning(f"POST 失败 (连续 {self._consecutive_post_failures}): {exc}")
            return False

    def _post_backoff(self) -> float:
        if self._consecutive_post_failures <= 1:
            return 0
        return min(2 ** (self._consecutive_post_failures - 1), self._max_backoff)

    # ------------------------------------------------------------------
    # Screenshot + OCR cycle
    # ------------------------------------------------------------------

    async def run_screenshot_ocr_cycle(self) -> None:
        """截取主屏幕 → OCR → 生成 PerceptionEvent → POST 到 Center。"""
        image = await asyncio.to_thread(_mss_grab_in_thread)
        if image is None:
            return

        engine = _get_ocr_engine()
        ocr_result = await asyncio.to_thread(engine.ocr, image)

        valid_lines = [ln for ln in ocr_result.lines if ln.score >= _MIN_OCR_CONFIDENCE]
        if not valid_lines:
            logger.debug("截屏 OCR: 无有效文本")
            return

        text = "\n".join(ln.text for ln in valid_lines)
        if len(text) < _MIN_TEXT_LEN:
            return

        h = _text_hash(text)
        if h == self._last_screenshot_hash:
            logger.debug("截屏 OCR: 文本未变化，跳过")
            return
        self._last_screenshot_hash = h

        event = PerceptionEvent(
            timestamp=get_utc_now(),
            source=SourceType.OCR_SCREEN,
            modality=Modality.TEXT,
            content_text=text,
            metadata={
                "ocr_lines": len(valid_lines),
                "ocr_latency_ms": round(ocr_result.latency_ms, 1),
            },
        )
        ok = await self._safe_post(event)
        if ok:
            logger.info(f"截屏 OCR → Center: {len(valid_lines)} 行, {len(text)} 字符")

    # ------------------------------------------------------------------
    # Proactive OCR cycle (WeChat / Feishu)
    # ------------------------------------------------------------------

    async def _capture_target_window(self):
        """检测并截取前台目标窗口，返回 (frame, image_to_ocr, app_type, window) 或 None。"""
        capture = _get_window_capture()
        router = _get_app_router()

        window = await asyncio.to_thread(capture.get_foreground_window)
        if window is None:
            return None

        from lifetrace.jobs.proactive_ocr.models import AppType  # noqa: PLC0415

        app_type, _reason = router.identify_app(window)
        if app_type == AppType.UNKNOWN or window.is_minimized:
            return None

        frame = await asyncio.to_thread(capture.capture_window, window)
        if frame is None:
            logger.debug(f"主动 OCR: 窗口截取失败 ({app_type.value})")
            return None

        img_std = float(np.std(frame.data))
        if img_std < _BLANK_IMAGE_STD_THRESHOLD:
            logger.debug("主动 OCR: 截图疑似空白，跳过")
            return None

        image_to_ocr = await self._apply_roi(frame, app_type)
        if image_to_ocr is None:
            return None

        return frame, image_to_ocr, app_type, window

    async def _apply_roi(self, frame, app_type) -> np.ndarray | None:
        roi_extractor = _get_roi_extractor()
        roi_result = await asyncio.to_thread(
            roi_extractor.extract_with_details, frame.data, app_type
        )
        if roi_result is None:
            return None
        if roi_result:
            roi_area = roi_result.width * roi_result.height
            full_area = frame.width * frame.height
            if full_area > 0 and roi_area / full_area >= _MIN_ROI_AREA_RATIO:
                return roi_result.image
        return frame.data

    async def run_proactive_ocr_cycle(self) -> None:
        """检测前台微信/飞书 → 截取窗口 → ROI → OCR → POST。"""
        result = await self._capture_target_window()
        if result is None:
            return
        _frame, image_to_ocr, app_type, window = result

        engine = _get_ocr_engine()
        ocr_result = await asyncio.to_thread(engine.ocr, image_to_ocr)

        valid_lines = [ln for ln in ocr_result.lines if ln.score >= _MIN_OCR_CONFIDENCE]
        if not valid_lines:
            return

        text = "\n".join(ln.text for ln in valid_lines)
        if len(text) < _MIN_TEXT_LEN:
            return

        h = _text_hash(text)
        if h == self._last_proactive_hash:
            return
        self._last_proactive_hash = h

        event = PerceptionEvent(
            timestamp=get_utc_now(),
            source=SourceType.OCR_PROACTIVE,
            modality=Modality.TEXT,
            content_text=text,
            metadata={
                "app_name": app_type.value,
                "window_title": window.title[:100],
                "ocr_lines": len(valid_lines),
                "ocr_latency_ms": round(ocr_result.latency_ms, 1),
            },
        )
        ok = await self._safe_post(event)
        if ok:
            logger.info(
                f"主动 OCR ({app_type.value}) → Center: {len(valid_lines)} 行, {len(text)} 字符"
            )

    # ------------------------------------------------------------------
    # Heartbeat
    # ------------------------------------------------------------------

    async def heartbeat(self) -> None:
        url = f"{self.center_url}/api/health"
        try:
            resp = await self.client.get(url)
            resp.raise_for_status()
            logger.debug("Heartbeat OK")
        except Exception as exc:
            logger.warning(f"Heartbeat failed: {exc}")

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    async def run(self, screenshot_interval: float, proactive_ocr_interval: float) -> None:
        logger.info(
            f"Sensor 事件循环启动 "
            f"(截屏间隔={screenshot_interval}s, 主动OCR间隔={proactive_ocr_interval}s)"
        )

        async def screenshot_loop() -> None:
            while True:
                try:
                    await self.run_screenshot_ocr_cycle()
                except Exception as exc:
                    logger.error(f"截屏 OCR 异常: {exc}", exc_info=True)
                backoff = self._post_backoff()
                await asyncio.sleep(screenshot_interval + backoff)

        async def proactive_ocr_loop() -> None:
            while True:
                try:
                    await self.run_proactive_ocr_cycle()
                except Exception as exc:
                    logger.error(f"主动 OCR 异常: {exc}", exc_info=True)
                backoff = self._post_backoff()
                await asyncio.sleep(proactive_ocr_interval + backoff)

        async def heartbeat_loop() -> None:
            while True:
                await self.heartbeat()
                await asyncio.sleep(30)

        await asyncio.gather(
            screenshot_loop(),
            proactive_ocr_loop(),
            heartbeat_loop(),
        )

    async def close(self) -> None:
        await self.client.aclose()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="LifeTrace Sensor 感知守护进程")
    parser.add_argument(
        "--center-url",
        required=True,
        help="Center 节点地址，如 https://xxx.cpolar.top",
    )
    parser.add_argument(
        "--node-id",
        default=platform.node(),
        help="节点 ID（默认主机名）",
    )
    parser.add_argument(
        "--screenshot-interval",
        type=float,
        default=10.0,
        help="截屏 OCR 间隔（秒，默认 10）",
    )
    parser.add_argument(
        "--proactive-ocr-interval",
        type=float,
        default=1.0,
        help="主动 OCR 间隔（秒，默认 1）",
    )
    parser.add_argument(
        "--no-screenshot",
        action="store_true",
        help="禁用截屏 OCR（只运行主动 OCR + 心跳）",
    )
    parser.add_argument(
        "--no-proactive-ocr",
        action="store_true",
        help="禁用主动 OCR（只运行截屏 + 心跳）",
    )
    return parser.parse_args()


def _make_loop(coro_fn, interval_fn):
    """Create an infinite retry loop coroutine."""

    async def _loop() -> None:
        while True:
            try:
                await coro_fn()
            except Exception as exc:
                logger.error(f"{coro_fn.__name__} 异常: {exc}", exc_info=True)
            await asyncio.sleep(interval_fn())

    return _loop


async def _run(args: argparse.Namespace) -> None:
    daemon = SensorDaemon(center_url=args.center_url, node_id=args.node_id)
    logger.info(f"Sensor 启动: node_id={args.node_id}, center={args.center_url}")

    tasks: list[asyncio.Task] = []

    if not args.no_screenshot:
        loop_fn = _make_loop(
            daemon.run_screenshot_ocr_cycle,
            lambda: args.screenshot_interval + daemon._post_backoff(),
        )
        tasks.append(asyncio.create_task(loop_fn()))
    else:
        logger.info("截屏 OCR 已禁用 (--no-screenshot)")

    if not args.no_proactive_ocr:
        loop_fn = _make_loop(
            daemon.run_proactive_ocr_cycle,
            lambda: args.proactive_ocr_interval + daemon._post_backoff(),
        )
        tasks.append(asyncio.create_task(loop_fn()))
    else:
        logger.info("主动 OCR 已禁用 (--no-proactive-ocr)")

    async def heartbeat_loop() -> None:
        while True:
            await daemon.heartbeat()
            await asyncio.sleep(30)

    tasks.append(asyncio.create_task(heartbeat_loop()))

    try:
        await asyncio.gather(*tasks)
    finally:
        await daemon.close()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(_run(args))
