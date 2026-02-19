from __future__ import annotations

from datetime import UTC, datetime, timedelta

from lifetrace.perception.models import Modality, PerceptionEvent, SourceType
from lifetrace.perception.subscribers.todo_intent_subscriber import TodoIntentSubscriber
from lifetrace.services.perception_todo_intent.dedupe import TTLDedupeCache


class _FakeStream:
    def subscribe(self, callback):
        _ = callback

    def unsubscribe(self, callback):
        _ = callback


def _build_event(
    *,
    sequence_id: int,
    source: SourceType,
    text: str,
    ts: datetime,
) -> PerceptionEvent:
    return PerceptionEvent(
        sequence_id=sequence_id,
        timestamp=ts,
        source=source,
        modality=Modality.TEXT,
        content_text=text,
        metadata={},
        priority=0,
    )


def test_ttl_dedupe_cache_respects_expiry() -> None:
    cache = TTLDedupeCache(ttl_seconds=2, max_size=10)
    now = datetime(2026, 2, 19, 0, 0, tzinfo=UTC)

    assert cache.check_and_mark("k1", now=now) is False
    assert cache.check_and_mark("k1", now=now + timedelta(seconds=1)) is True
    assert cache.check_and_mark("k1", now=now + timedelta(seconds=3)) is False


def test_build_context_preserves_high_priority_sources_when_truncating() -> None:
    subscriber = TodoIntentSubscriber(
        _FakeStream(),
        {
            "window_seconds": 20,
            "max_context_chars": 95,
            "internal_queue_maxsize": 10,
            "enabled": False,
        },
    )
    base = datetime(2026, 2, 19, 8, 0, tzinfo=UTC)
    events = [
        _build_event(
            sequence_id=1,
            source=SourceType.OCR_SCREEN,
            text="Long OCR content with repeated words and extra details.",
            ts=base,
        ),
        _build_event(
            sequence_id=2,
            source=SourceType.MIC_PC,
            text="Need to send the proposal before tomorrow noon.",
            ts=base + timedelta(seconds=1),
        ),
        _build_event(
            sequence_id=3,
            source=SourceType.USER_INPUT,
            text="Remember this proposal follow-up.",
            ts=base + timedelta(seconds=2),
        ),
    ]

    context = subscriber._build_context(events)

    assert "[INPUT]" in context.merged_text
    assert "[AUDIO]" in context.merged_text
    assert "[OCR]" not in context.merged_text


def test_user_input_event_sets_force_flush() -> None:
    subscriber = TodoIntentSubscriber(
        _FakeStream(),
        {
            "window_seconds": 60,
            "max_context_chars": 1000,
            "internal_queue_maxsize": 10,
            "enabled": False,
        },
    )
    event = _build_event(
        sequence_id=1,
        source=SourceType.USER_INPUT,
        text="记一下明天开会",
        ts=datetime(2026, 2, 19, 9, 0, tzinfo=UTC),
    )

    subscriber._ingest_event(event)

    assert subscriber._force_flush is True
    assert subscriber._should_flush() is True
