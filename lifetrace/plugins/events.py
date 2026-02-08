"""Plugin lifecycle event bus for SSE streaming."""

from __future__ import annotations

import queue
import threading
import uuid
from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass
class PluginLifecycleEvent:
    """Lifecycle event emitted during plugin operations."""

    event_id: str
    plugin_id: str
    action: str
    task_id: str | None
    stage: str
    status: str
    message: str
    progress: int | None
    timestamp: str
    details: dict[str, object]

    def to_payload(self) -> dict[str, object]:
        """Serialize event for API response and SSE payload."""
        return {
            "eventId": self.event_id,
            "pluginId": self.plugin_id,
            "action": self.action,
            "taskId": self.task_id,
            "stage": self.stage,
            "status": self.status,
            "message": self.message,
            "progress": self.progress,
            "timestamp": self.timestamp,
            "details": self.details,
        }


@dataclass
class _Subscriber:
    subscriber_id: str
    queue: queue.Queue[PluginLifecycleEvent]
    plugin_id: str | None
    task_id: str | None


class PluginEventBus:
    """In-memory plugin event bus with bounded history."""

    def __init__(self, history_limit: int = 300, queue_size: int = 200) -> None:
        self._history_limit = history_limit
        self._queue_size = queue_size
        self._history: deque[PluginLifecycleEvent] = deque(maxlen=history_limit)
        self._subscribers: dict[str, _Subscriber] = {}
        self._lock = threading.Lock()

    # ruff: noqa: PLR0913
    def publish(
        self,
        *,
        plugin_id: str,
        action: str,
        task_id: str | None,
        stage: str,
        status: str,
        message: str,
        progress: int | None = None,
        details: dict[str, object] | None = None,
    ) -> PluginLifecycleEvent:
        """Publish one plugin lifecycle event."""
        event = PluginLifecycleEvent(
            event_id=uuid.uuid4().hex,
            plugin_id=plugin_id,
            action=action,
            task_id=task_id,
            stage=stage,
            status=status,
            message=message,
            progress=progress,
            timestamp=datetime.now(tz=UTC).isoformat(),
            details=details or {},
        )
        with self._lock:
            self._history.append(event)
            subscribers = list(self._subscribers.values())

        for subscriber in subscribers:
            if subscriber.plugin_id and subscriber.plugin_id != plugin_id:
                continue
            if subscriber.task_id and subscriber.task_id != task_id:
                continue
            self._publish_to_queue(subscriber.queue, event)

        return event

    def subscribe(
        self,
        *,
        plugin_id: str | None = None,
        task_id: str | None = None,
        last_event_id: str | None = None,
    ) -> tuple[str, queue.Queue[PluginLifecycleEvent], list[PluginLifecycleEvent]]:
        """Subscribe to future events and return replay events."""
        subscriber_id = uuid.uuid4().hex
        subscriber_queue: queue.Queue[PluginLifecycleEvent] = queue.Queue(maxsize=self._queue_size)
        with self._lock:
            replay = self._build_replay_events(
                plugin_id=plugin_id,
                task_id=task_id,
                last_event_id=last_event_id,
            )
            self._subscribers[subscriber_id] = _Subscriber(
                subscriber_id=subscriber_id,
                queue=subscriber_queue,
                plugin_id=plugin_id,
                task_id=task_id,
            )
        return subscriber_id, subscriber_queue, replay

    def unsubscribe(self, subscriber_id: str) -> None:
        """Remove one subscriber."""
        with self._lock:
            self._subscribers.pop(subscriber_id, None)

    def _build_replay_events(
        self,
        *,
        plugin_id: str | None,
        task_id: str | None,
        last_event_id: str | None,
    ) -> list[PluginLifecycleEvent]:
        history = list(self._history)
        if plugin_id:
            history = [event for event in history if event.plugin_id == plugin_id]
        if task_id:
            history = [event for event in history if event.task_id == task_id]
        if not last_event_id:
            return history

        start_index = 0
        for index, event in enumerate(history):
            if event.event_id == last_event_id:
                start_index = index + 1
                break
        return history[start_index:]

    def _publish_to_queue(
        self,
        subscriber_queue: queue.Queue[PluginLifecycleEvent],
        event: PluginLifecycleEvent,
    ) -> None:
        try:
            subscriber_queue.put_nowait(event)
        except queue.Full:
            try:
                subscriber_queue.get_nowait()
            except queue.Empty:
                return
            try:
                subscriber_queue.put_nowait(event)
            except queue.Full:
                return
