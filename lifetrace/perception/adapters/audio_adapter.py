from __future__ import annotations

from typing import TYPE_CHECKING

from lifetrace.perception.models import Modality, PerceptionEvent, SourceType
from lifetrace.util.time_utils import get_utc_now

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable


class AudioAdapter:
    def __init__(
        self,
        publisher: Callable[[PerceptionEvent], Awaitable[None]],
        source: SourceType = SourceType.MIC_PC,
    ):
        self._publish = publisher
        self._source = source

    @property
    def source(self) -> SourceType:
        return self._source

    async def on_transcription(self, text: str, metadata: dict | None = None) -> None:
        content = (text or "").strip()
        if not content:
            return

        event = PerceptionEvent(
            timestamp=get_utc_now(),
            source=self._source,
            modality=Modality.AUDIO,
            content_text=content,
            metadata=metadata or {},
            priority=2,
        )
        await self._publish(event)
