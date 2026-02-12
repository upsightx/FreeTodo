from __future__ import annotations

from typing import TYPE_CHECKING

from lifetrace.perception.models import Modality, PerceptionEvent, SourceType
from lifetrace.util.time_utils import get_utc_now

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable


class InputAdapter:
    def __init__(self, publisher: Callable[[PerceptionEvent], Awaitable[None]]):
        self._publish = publisher

    async def on_user_input(self, text: str, metadata: dict | None = None) -> None:
        content = (text or "").strip()
        if not content:
            return

        event = PerceptionEvent(
            timestamp=get_utc_now(),
            source=SourceType.USER_INPUT,
            modality=Modality.TEXT,
            content_text=content,
            metadata=metadata or {},
            priority=3,
        )
        await self._publish(event)
