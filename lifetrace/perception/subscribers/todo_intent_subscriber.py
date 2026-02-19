from __future__ import annotations

import asyncio
from contextlib import suppress
from typing import TYPE_CHECKING
from uuid import uuid4

from lifetrace.perception.models import PerceptionEvent, SourceType
from lifetrace.schemas.perception_todo_intent import TodoIntentContext, TodoIntentTimeWindow
from lifetrace.services.perception_todo_intent.dedupe import canonicalize_text
from lifetrace.services.perception_todo_intent.orchestrator import TodoIntentOrchestrator
from lifetrace.util.logging_config import get_logger
from lifetrace.util.time_utils import get_utc_now

if TYPE_CHECKING:
    from lifetrace.perception.stream import PerceptionStream

logger = get_logger()


class TodoIntentSubscriber:
    def __init__(self, stream: PerceptionStream, config: dict[str, object] | None = None):
        cfg = dict(config or {})
        self._stream = stream
        self._window_seconds = max(1, int(cfg.get("window_seconds", 20)))
        self._max_context_chars = max(128, int(cfg.get("max_context_chars", 2500)))
        self._queue_maxsize = max(1, int(cfg.get("internal_queue_maxsize", 200)))

        self._queue: asyncio.Queue[PerceptionEvent] = asyncio.Queue(maxsize=self._queue_maxsize)
        self._window_events: list[PerceptionEvent] = []
        self._window_seen: set[tuple[str, str]] = set()
        self._force_flush = False

        self._orchestrator = TodoIntentOrchestrator(cfg)
        self._worker_task: asyncio.Task[None] | None = None
        self._started = False
        self._stopped = True
        self._last_flush_at = get_utc_now()
        self._stream_callback = self.on_event
        self._stats: dict[str, int] = {
            "enqueued_total": 0,
            "dropped_incoming_total": 0,
            "dropped_existing_total": 0,
            "intra_window_dedupe_drop_total": 0,
            "processed_context_total": 0,
            "pre_gate_dedupe_hit_total": 0,
            "gate_passed_context_total": 0,
            "gate_blocked_context_total": 0,
            "created_total": 0,
            "updated_total": 0,
            "queued_review_total": 0,
            "skipped_total": 0,
        }

    async def start(self) -> None:
        if self._started:
            return
        self._stopped = False
        self._stream.subscribe(self._stream_callback)
        self._worker_task = asyncio.create_task(self._worker_loop(), name="todo_intent_worker")
        self._started = True
        logger.info("todo intent subscriber started")

    async def stop(self) -> None:
        if not self._started:
            return
        self._stopped = True
        self._stream.unsubscribe(self._stream_callback)
        if self._worker_task is not None:
            self._worker_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._worker_task
        self._worker_task = None
        self._started = False
        logger.info("todo intent subscriber stopped")

    async def on_event(self, event: PerceptionEvent) -> None:
        if self._stopped:
            return
        self._enqueue_event(event)

    def get_stats(self) -> dict[str, object]:
        return {
            **self._stats,
            "queue_len": self._queue.qsize(),
            "queue_maxsize": self._queue_maxsize,
            "window_event_count": len(self._window_events),
            "window_seconds": self._window_seconds,
            "max_context_chars": self._max_context_chars,
        }

    def _enqueue_event(self, event: PerceptionEvent) -> None:
        try:
            self._queue.put_nowait(event)
            self._stats["enqueued_total"] += 1
            return
        except asyncio.QueueFull:
            pass

        if self._try_replace_lower_priority(event):
            self._stats["enqueued_total"] += 1
            return
        self._stats["dropped_incoming_total"] += 1

    def _try_replace_lower_priority(self, incoming: PerceptionEvent) -> bool:
        pending = self._queue._queue
        if not pending:
            return False

        lowest_priority = min(event.priority for event in pending)
        if incoming.priority < lowest_priority:
            return False

        for idx, existing in enumerate(pending):
            if existing.priority == lowest_priority:
                del pending[idx]
                self._stats["dropped_existing_total"] += 1
                break

        try:
            self._queue.put_nowait(incoming)
            return True
        except asyncio.QueueFull:
            return False

    async def _worker_loop(self) -> None:
        try:
            while True:
                timeout = self._next_wait_timeout()
                event = await self._poll_event(timeout)
                if event is not None:
                    self._ingest_event(event)
                    self._queue.task_done()
                if self._should_flush():
                    await self._flush_window()
        finally:
            if self._window_events:
                with suppress(Exception):
                    await self._flush_window()

    def _next_wait_timeout(self) -> float:
        if not self._window_events:
            return 1.0
        elapsed = (get_utc_now() - self._last_flush_at).total_seconds()
        return max(0.1, float(self._window_seconds) - elapsed)

    async def _poll_event(self, timeout: float) -> PerceptionEvent | None:
        try:
            return await asyncio.wait_for(self._queue.get(), timeout=timeout)
        except TimeoutError:
            return None

    def _ingest_event(self, event: PerceptionEvent) -> None:
        if not self._should_accept_event(event):
            return

        dedupe_key = (event.source.value, canonicalize_text(event.content_text))
        if dedupe_key in self._window_seen:
            self._stats["intra_window_dedupe_drop_total"] += 1
            return

        self._window_events.append(event)
        self._window_seen.add(dedupe_key)

        if event.source == SourceType.USER_INPUT or (
            self._estimate_window_chars() >= self._max_context_chars
        ):
            self._force_flush = True

    def _should_accept_event(self, event: PerceptionEvent) -> bool:
        text = (event.content_text or "").strip()
        if not text:
            return False
        if event.source not in set(SourceType):
            return False
        return bool(canonicalize_text(text))

    def _estimate_window_chars(self) -> int:
        total = 0
        for event in self._window_events:
            total += (
                len(self._source_label(event.source)) + 1 + len((event.content_text or "").strip())
            )
        return total

    def _should_flush(self) -> bool:
        if not self._window_events:
            return False
        if self._force_flush:
            return True
        elapsed = (get_utc_now() - self._last_flush_at).total_seconds()
        return elapsed >= float(self._window_seconds)

    async def _flush_window(self) -> None:
        if not self._window_events:
            self._force_flush = False
            self._last_flush_at = get_utc_now()
            return

        context = self._build_context(self._window_events)
        self._window_events = []
        self._window_seen.clear()
        self._force_flush = False
        self._last_flush_at = get_utc_now()

        result = await self._orchestrator.process_context(context)
        self._record_result_stats(result)

    def _record_result_stats(self, result: dict[str, object]) -> None:
        self._stats["processed_context_total"] += 1
        if bool(result.get("dedupe_hit")):
            self._stats["pre_gate_dedupe_hit_total"] += 1
            return
        if bool(result.get("gate_should_extract")):
            self._stats["gate_passed_context_total"] += 1
        else:
            self._stats["gate_blocked_context_total"] += 1

        integration_results = result.get("integration_results")
        if not isinstance(integration_results, list):
            return
        for item in integration_results:
            if not isinstance(item, dict):
                continue
            action = item.get("action")
            if action == "created":
                self._stats["created_total"] += 1
            elif action == "updated":
                self._stats["updated_total"] += 1
            elif action == "queued_review":
                self._stats["queued_review_total"] += 1
            elif action == "skipped":
                self._stats["skipped_total"] += 1

    def _build_context(self, events: list[PerceptionEvent]) -> TodoIntentContext:
        ordered_events = sorted(events, key=lambda item: item.sequence_id)
        lines = [
            (self._source_priority(event.source), self._line_for_event(event))
            for event in ordered_events
        ]
        merged_lines = self._truncate_lines(lines)
        metadata = self._build_metadata(ordered_events)

        return TodoIntentContext(
            context_id=str(uuid4()),
            events=ordered_events,
            merged_text="\n".join(merged_lines),
            time_window=TodoIntentTimeWindow(
                start=ordered_events[0].timestamp,
                end=ordered_events[-1].timestamp,
            ),
            source_set=sorted({event.source.value for event in ordered_events}),
            metadata=metadata,
        )

    def _truncate_lines(self, lines: list[tuple[int, str]]) -> list[str]:
        plain = [line for _, line in lines]
        if len("\n".join(plain)) <= self._max_context_chars:
            return plain

        keep = [True] * len(lines)
        for target_priority in (0, 1, 2):
            for idx in range(len(lines) - 1, -1, -1):
                if not keep[idx]:
                    continue
                priority, _ = lines[idx]
                if priority != target_priority:
                    continue
                keep[idx] = False
                merged = "\n".join(text for i, (_, text) in enumerate(lines) if keep[i])
                if merged and len(merged) <= self._max_context_chars:
                    return [text for i, (_, text) in enumerate(lines) if keep[i]]

        fallback = plain[-1] if plain else ""
        if len(fallback) > self._max_context_chars:
            return [fallback[: self._max_context_chars]]
        return [fallback] if fallback else []

    def _line_for_event(self, event: PerceptionEvent) -> str:
        return f"{self._source_label(event.source)} {(event.content_text or '').strip()}"

    def _source_label(self, source: SourceType) -> str:
        if source == SourceType.USER_INPUT:
            return "[INPUT]"
        if source in (SourceType.MIC_PC, SourceType.MIC_HARDWARE):
            return "[AUDIO]"
        return "[OCR]"

    def _source_priority(self, source: SourceType) -> int:
        if source == SourceType.USER_INPUT:
            return 2
        if source in (SourceType.MIC_PC, SourceType.MIC_HARDWARE):
            return 1
        return 0

    def _build_metadata(self, events: list[PerceptionEvent]) -> dict[str, object]:
        metadata: dict[str, object] = {"event_count": len(events)}
        for key in ("app", "app_name", "window", "window_title", "speaker"):
            value = self._latest_metadata_value(events, key)
            if value is None:
                continue
            metadata[key] = value
        return metadata

    def _latest_metadata_value(self, events: list[PerceptionEvent], key: str) -> str | None:
        for event in reversed(events):
            value = event.metadata.get(key)
            if value in (None, ""):
                continue
            return str(value)
        return None
