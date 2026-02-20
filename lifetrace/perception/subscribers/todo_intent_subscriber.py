from __future__ import annotations

import asyncio
from collections import deque
from contextlib import suppress
from typing import TYPE_CHECKING
from uuid import uuid4

from lifetrace.schemas.perception_todo_intent import (
    TodoIntentProcessingRecord,
    TodoIntentProcessingStatus,
    TodoIntentSubscriberStatusResponse,
)
from lifetrace.util.logging_config import get_logger
from lifetrace.util.time_utils import get_utc_now

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from lifetrace.perception.models import PerceptionEvent
    from lifetrace.services.perception_todo_intent.orchestrator import TodoIntentOrchestrator

logger = get_logger()


class TodoIntentSubscriber:
    """PerceptionStream subscriber with internal queue + worker loop."""

    def __init__(
        self,
        *,
        orchestrator: TodoIntentOrchestrator,
        queue_maxsize: int = 200,
        max_recent_records: int = 200,
        enabled: bool = True,
    ):
        self._orchestrator = orchestrator
        self._enabled = bool(enabled)
        self._queue: asyncio.Queue[PerceptionEvent] = asyncio.Queue(
            maxsize=max(1, int(queue_maxsize))
        )
        self._recent_records: deque[TodoIntentProcessingRecord] = deque(
            maxlen=max(1, int(max_recent_records))
        )
        self._record_subscribers: list[Callable[[TodoIntentProcessingRecord], Awaitable[None]]] = []
        self._worker_task: asyncio.Task[None] | None = None
        self._enqueued_total = 0
        self._dropped_total = 0
        self._processed_total = 0
        self._failed_total = 0

    async def start(self, stream) -> None:
        if not self._enabled:
            return
        if self._worker_task is not None and not self._worker_task.done():
            return
        stream.subscribe(self.on_event)
        self._worker_task = asyncio.create_task(self._worker_loop())
        logger.info(
            "TodoIntentSubscriber started: queue_maxsize=%s",
            self._queue.maxsize,
        )

    async def stop(self, stream) -> None:
        stream.unsubscribe(self.on_event)
        task = self._worker_task
        self._worker_task = None
        if task is None:
            return
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task

    async def on_event(self, event: PerceptionEvent) -> None:
        if not self._enabled:
            return
        if not (event.content_text or "").strip():
            return
        try:
            self._queue.put_nowait(event)
            self._enqueued_total += 1
        except asyncio.QueueFull:
            self._dropped_total += 1

    def subscribe_records(
        self,
        callback: Callable[[TodoIntentProcessingRecord], Awaitable[None]],
    ) -> None:
        if callback not in self._record_subscribers:
            self._record_subscribers.append(callback)

    def unsubscribe_records(
        self,
        callback: Callable[[TodoIntentProcessingRecord], Awaitable[None]],
    ) -> None:
        self._record_subscribers = [cb for cb in self._record_subscribers if cb is not callback]

    def get_recent_records(self, count: int = 50) -> list[TodoIntentProcessingRecord]:
        safe_count = max(1, int(count))
        return list(self._recent_records)[-safe_count:]

    async def _publish_record(self, record: TodoIntentProcessingRecord) -> None:
        self._recent_records.append(record)
        subscribers = list(self._record_subscribers)
        if not subscribers:
            return
        await asyncio.gather(*(cb(record) for cb in subscribers), return_exceptions=True)

    async def _worker_loop(self) -> None:
        while True:
            event = await self._queue.get()
            try:
                record = await self._orchestrator.process_event(event)
                await self._publish_record(record)
                self._processed_total += 1
            except asyncio.CancelledError:
                raise
            except Exception:
                self._failed_total += 1
                fallback = TodoIntentProcessingRecord(
                    record_id=f"tir_{uuid4().hex}",
                    context_id=f"ctx_err_{uuid4().hex}",
                    status=TodoIntentProcessingStatus.FAILED,
                    created_at=get_utc_now(),
                    event_ids=[event.event_id],
                    source_set=[event.source],
                    merged_text=(event.content_text or "").strip(),
                    time_window_start=event.timestamp,
                    time_window_end=event.timestamp,
                    metadata=dict(event.metadata or {}),
                    error="orchestrator_error",
                )
                await self._publish_record(fallback)
                logger.exception("TodoIntentSubscriber worker failed for event=%s", event.event_id)

    def get_status(self) -> TodoIntentSubscriberStatusResponse:
        return TodoIntentSubscriberStatusResponse(
            enabled=self._enabled,
            running=self._worker_task is not None and not self._worker_task.done(),
            queue_size=self._queue.qsize(),
            queue_maxsize=self._queue.maxsize,
            enqueued_total=self._enqueued_total,
            dropped_total=self._dropped_total,
            processed_total=self._processed_total,
            failed_total=self._failed_total,
            orchestrator=self._orchestrator.get_stats(),
        )
