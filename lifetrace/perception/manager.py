from __future__ import annotations

import asyncio
import threading
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from lifetrace.perception.adapters.audio_adapter import AudioAdapter
from lifetrace.perception.adapters.input_adapter import InputAdapter
from lifetrace.perception.adapters.ocr_adapter import OCRAdapter
from lifetrace.perception.models import SourceType
from lifetrace.perception.stream import PerceptionStream
from lifetrace.util.time_utils import get_utc_now

if TYPE_CHECKING:
    from lifetrace.perception.models import PerceptionEvent


class PerceptionStreamManager:
    """Manage a PerceptionStream instance and its enabled adapters."""

    def __init__(self, config: dict | None = None):
        config = dict(config or {})
        self.stream = PerceptionStream(
            window_seconds=int(config.get("window_seconds", 300)),
            max_pending_events=int(config.get("max_pending_events", 1000)),
        )
        self._config = config
        self._adapters: dict[str, object] = {}
        self._status_online_window_seconds = max(
            1, int(config.get("status_online_window_seconds", 60))
        )
        self._enabled_sources = self._build_enabled_sources()
        self._status_lock = threading.Lock()
        self._last_seen: dict[SourceType, datetime] = {}
        self._loop: asyncio.AbstractEventLoop | None = None
        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            self._loop = None

    async def start(self) -> None:
        await self.stream.start()

        if self._config.get("audio_enabled", True):
            source_str = str(self._config.get("audio_source", SourceType.MIC_PC.value))
            try:
                source = SourceType(source_str)
            except ValueError:
                source = SourceType.MIC_PC
            self._adapters["audio"] = AudioAdapter(self.publish_event, source=source)

        if self._config.get("ocr_enabled", False):
            self._adapters["ocr"] = OCRAdapter(self.publish_event)

        if self._config.get("input_enabled", False):
            self._adapters["input"] = InputAdapter(self.publish_event)

    async def stop(self) -> None:
        self._adapters.clear()
        await self.stream.stop()

    def is_ocr_enabled(self) -> bool:
        return isinstance(self._adapters.get("ocr"), OCRAdapter)

    def is_input_enabled(self) -> bool:
        return isinstance(self._adapters.get("input"), InputAdapter)

    def record_seen(self, source: SourceType) -> None:
        with self._status_lock:
            self._last_seen[source] = get_utc_now()

    async def publish_event(self, event: PerceptionEvent) -> None:
        self.record_seen(event.source)
        await self.stream.publish(event)

    def publish_event_threadsafe(self, event: PerceptionEvent) -> None:
        loop = self._loop
        if loop is None or not loop.is_running():
            return
        self.record_seen(event.source)
        asyncio.run_coroutine_threadsafe(self.stream.publish(event), loop)

    def get_status(self) -> dict[str, object]:
        status: dict[str, dict[str, object]] = {
            st.value: {
                "enabled": self._enabled_sources.get(st, False),
                "online": False,
                "last_seen": None,
            }
            for st in SourceType
        }

        now = get_utc_now()
        with self._status_lock:
            last_seen = dict(self._last_seen)

        seen_window = timedelta(seconds=self._status_online_window_seconds)
        for st, when in last_seen.items():
            status_entry = status[st.value]
            status_entry["last_seen"] = when.isoformat()
            if now - when <= seen_window:
                status_entry["online"] = True

        status["_stream"] = self.stream.get_queue_stats()
        return status

    def _build_enabled_sources(self) -> dict[SourceType, bool]:
        enabled_sources: dict[SourceType, bool] = dict.fromkeys(SourceType, False)

        if self._config.get("audio_enabled", True):
            enabled_sources[SourceType.MIC_PC] = True
            enabled_sources[SourceType.MIC_HARDWARE] = True
            source_str = str(self._config.get("audio_source", SourceType.MIC_PC.value))
            try:
                enabled_sources[SourceType(source_str)] = True
            except ValueError:
                enabled_sources[SourceType.MIC_PC] = True

        if self._config.get("ocr_enabled", False):
            enabled_sources[SourceType.OCR_SCREEN] = True
            enabled_sources[SourceType.OCR_PROACTIVE] = True

        if self._config.get("input_enabled", False):
            enabled_sources[SourceType.USER_INPUT] = True

        return enabled_sources

    def get_audio_adapter(self) -> AudioAdapter | None:
        adapter = self._adapters.get("audio")
        return adapter if isinstance(adapter, AudioAdapter) else None

    def get_input_adapter(self) -> InputAdapter | None:
        adapter = self._adapters.get("input")
        return adapter if isinstance(adapter, InputAdapter) else None

    def get_ocr_adapter(self) -> OCRAdapter | None:
        adapter = self._adapters.get("ocr")
        return adapter if isinstance(adapter, OCRAdapter) else None


_manager: PerceptionStreamManager | None = None


async def init_perception_manager(config: dict | None = None) -> PerceptionStreamManager:
    global _manager  # noqa: PLW0603
    if _manager is None:
        _manager = PerceptionStreamManager(config=config)
        await _manager.start()
    return _manager


async def shutdown_perception_manager() -> None:
    global _manager  # noqa: PLW0603
    if _manager is None:
        return
    await _manager.stop()
    _manager = None


def try_get_perception_manager() -> PerceptionStreamManager | None:
    return _manager


def get_perception_manager() -> PerceptionStreamManager:
    if _manager is None:
        raise RuntimeError(
            "PerceptionStreamManager is not initialized. Call init_perception_manager() at startup."
        )
    return _manager


def try_get_perception_stream() -> PerceptionStream | None:
    mgr = try_get_perception_manager()
    return mgr.stream if mgr is not None else None


def get_perception_stream() -> PerceptionStream:
    return get_perception_manager().stream
