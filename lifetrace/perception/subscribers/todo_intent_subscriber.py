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

    @staticmethod
    def _modality_sort_key(modality: str) -> int:
        order = {
            "audio": 0,
            "image": 1,
            "text": 2,
        }
        return order.get(modality, 99)

    def __init__(
        self,
        *,
        orchestrator: TodoIntentOrchestrator,
        queue_maxsize: int = 200,
        max_recent_records: int = 200,
        aggregation_window_seconds: float = 20.0,
        max_events_per_context: int = 32,
        enabled: bool = True,
    ):
        self._orchestrator = orchestrator
        self._enabled = bool(enabled)
        self._aggregation_window_seconds = max(0.0, float(aggregation_window_seconds))
        self._max_events_per_context = max(1, int(max_events_per_context))
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
            "TodoIntentSubscriber started: queue_maxsize=%s aggregation_window_seconds=%s",
            self._queue.maxsize,
            self._aggregation_window_seconds,
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

    @staticmethod
    def _dedupe_events_within_batch(events: list[PerceptionEvent]) -> list[PerceptionEvent]:
        seen: set[tuple[str, str]] = set()
        deduped: list[PerceptionEvent] = []
        for event in events:
            text = " ".join((event.content_text or "").strip().lower().split())
            if not text:
                continue
            key = (event.source.value, text)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(event)
        return deduped

    async def _collect_batch(self, first_event: PerceptionEvent) -> list[PerceptionEvent]:
        if self._aggregation_window_seconds <= 0:
            return [first_event]

        loop = asyncio.get_running_loop()
        started_at = loop.time()
        batch = [first_event]

        while len(batch) < self._max_events_per_context:
            elapsed = loop.time() - started_at
            remaining = self._aggregation_window_seconds - elapsed
            if remaining <= 0:
                break

            try:
                event = await asyncio.wait_for(self._queue.get(), timeout=remaining)
            except TimeoutError:
                break
            batch.append(event)

        deduped_batch = self._dedupe_events_within_batch(batch)
        return deduped_batch or [first_event]

    @staticmethod
    def _resolve_error_code(exc: Exception) -> str:
        message = " ".join(str(exc).strip().split())
        if message:
            return message[:120]
        return f"orchestrator_{exc.__class__.__name__.lower()}"

    @staticmethod
    def _build_failed_record(
        events: list[PerceptionEvent],
        *,
        error_code: str = "orchestrator_error",
    ) -> TodoIntentProcessingRecord:
        ordered = list(events)
        first_event = ordered[0]
        event_ids = [event.event_id for event in ordered]
        source_set: list = []
        seen_sources = set()
        for event in ordered:
            if event.source in seen_sources:
                continue
            seen_sources.add(event.source)
            source_set.append(event.source)
        merged_text = "\n".join(
            (event.content_text or "").strip()
            for event in ordered
            if (event.content_text or "").strip()
        )
        time_window_start = min(event.timestamp for event in ordered)
        time_window_end = max(event.timestamp for event in ordered)
        metadata = dict(ordered[-1].metadata or {})
        metadata["batch_size"] = len(ordered)
        event_refs = [
            {
                "event_id": event.event_id,
                "source": event.source.value,
                "modality": event.modality.value,
                "sequence_id": int(event.sequence_id),
                "timestamp": event.timestamp.isoformat(),
            }
            for event in ordered
        ]
        event_refs.sort(
            key=lambda item: (
                TodoIntentSubscriber._modality_sort_key(str(item.get("modality", ""))),
                int(item.get("sequence_id", 0)),
                str(item.get("timestamp", "")),
                str(item.get("event_id", "")),
            )
        )
        metadata["event_refs"] = event_refs

        return TodoIntentProcessingRecord(
            record_id=f"tir_{uuid4().hex}",
            context_id=f"ctx_err_{uuid4().hex}",
            status=TodoIntentProcessingStatus.FAILED,
            created_at=get_utc_now(),
            event_ids=event_ids,
            source_set=source_set,
            merged_text=merged_text or (first_event.content_text or "").strip(),
            time_window_start=time_window_start,
            time_window_end=time_window_end,
            metadata=metadata,
            error=error_code,
        )

    async def _worker_loop(self) -> None:
        while True:
            event = await self._queue.get()
            batch = await self._collect_batch(event)
            try:
                if len(batch) == 1:
                    record = await self._orchestrator.process_event(batch[0])
                else:
                    context = self._orchestrator.build_context_from_events(batch)
                    record = await self._orchestrator.process_context(context)
                await self._publish_record(record)
                self._processed_total += len(batch)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self._failed_total += len(batch)
                fallback = self._build_failed_record(
                    batch,
                    error_code=self._resolve_error_code(exc),
                )
                await self._publish_record(fallback)
                logger.exception(
                    "TodoIntentSubscriber worker failed for event=%s batch_size=%s",
                    event.event_id,
                    len(batch),
                )

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
