from __future__ import annotations

from typing import TYPE_CHECKING

from lifetrace.perception.models import Modality, PerceptionEvent, SourceType
from lifetrace.util.time_utils import get_utc_now

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable


class OCRAdapter:
    def __init__(self, publisher: Callable[[PerceptionEvent], Awaitable[None]]):
        self._publish = publisher

    async def on_screen_ocr(
        self, text: str, screenshot_path: str, metadata: dict | None = None
    ) -> None:
        content = (text or "").strip()
        if not content:
            return

        event = PerceptionEvent(
            timestamp=get_utc_now(),
            source=SourceType.OCR_SCREEN,
            modality=Modality.IMAGE,
            content_text=content,
            content_raw=screenshot_path,
            metadata=metadata or {},
            priority=1,
        )
        await self._publish(event)

    async def on_proactive_ocr(self, text: str, metadata: dict | None = None) -> None:
        content = (text or "").strip()
        if not content:
            return

        event = PerceptionEvent(
            timestamp=get_utc_now(),
            source=SourceType.OCR_PROACTIVE,
            modality=Modality.TEXT,
            content_text=content,
            metadata=metadata or {},
            priority=1,
        )
        await self._publish(event)
