from __future__ import annotations

from datetime import UTC, datetime, timedelta

from lifetrace.perception.models import SourceType
from lifetrace.schemas.perception_todo_intent import TodoIntentContext
from lifetrace.services.perception_todo_intent import dedupe as dedupe_module
from lifetrace.services.perception_todo_intent.dedupe import PreGateDedupeCache


def _build_context(
    text: str,
    *,
    source_set: list[SourceType] | None = None,
    app_name: str = "Terminal",
    window_title: str = "tmux",
) -> TodoIntentContext:
    now = datetime(2026, 2, 19, 8, 0, tzinfo=UTC)
    return TodoIntentContext(
        context_id="ctx_test",
        event_ids=["e1"],
        merged_text=text,
        source_set=source_set or [SourceType.OCR_SCREEN],
        time_window_start=now,
        time_window_end=now,
        metadata={
            "app_name": app_name,
            "window_title": window_title,
            "speaker": "",
        },
    )


def test_pre_gate_dedupe_cache_respects_expiry(monkeypatch) -> None:
    cache = PreGateDedupeCache(ttl_seconds=2, max_cache_size=10)
    now_holder = {"now": datetime(2026, 2, 19, 0, 0, tzinfo=UTC)}
    monkeypatch.setattr(dedupe_module, "get_utc_now", lambda: now_holder["now"])

    context = _build_context("same text")
    is_hit, _ = cache.check_and_record(context)
    assert is_hit is False

    now_holder["now"] = now_holder["now"] + timedelta(seconds=1)
    is_hit, _ = cache.check_and_record(context)
    assert is_hit is True

    now_holder["now"] = now_holder["now"] + timedelta(seconds=2)
    is_hit, _ = cache.check_and_record(context)
    assert is_hit is False


def test_pre_gate_dedupe_cross_batch_containment_keeps_latest(monkeypatch) -> None:
    cache = PreGateDedupeCache(ttl_seconds=90, max_cache_size=10)
    now_holder = {"now": datetime(2026, 2, 23, 13, 0, tzinfo=UTC)}
    monkeypatch.setattr(dedupe_module, "get_utc_now", lambda: now_holder["now"])

    old_ctx = _build_context("实现意图识别模块功能")
    new_ctx = _build_context("实现意图识别模块功能 并补充测试用例")

    hit1, _ = cache.check_and_record(old_ctx)
    assert hit1 is False

    now_holder["now"] = now_holder["now"] + timedelta(seconds=1)
    hit2, key2 = cache.check_and_record(new_ctx)
    assert hit2 is False

    now_holder["now"] = now_holder["now"] + timedelta(seconds=1)
    hit3, key3 = cache.check_and_record(old_ctx)
    assert hit3 is True
    assert key3 == key2

    now_holder["now"] = now_holder["now"] + timedelta(seconds=1)
    hit4, key4 = cache.check_and_record(new_ctx)
    assert hit4 is True
    assert key4 == key2


def test_pre_gate_dedupe_same_text_different_anchor_not_deduped(monkeypatch) -> None:
    cache = PreGateDedupeCache(ttl_seconds=90, max_cache_size=10)
    now_holder = {"now": datetime(2026, 2, 23, 13, 0, tzinfo=UTC)}
    monkeypatch.setattr(dedupe_module, "get_utc_now", lambda: now_holder["now"])

    ctx_left = _build_context("准备提交PR", window_title="tmux-left")
    ctx_right = _build_context("准备提交PR", window_title="tmux-right")

    hit1, _ = cache.check_and_record(ctx_left)
    assert hit1 is False

    now_holder["now"] = now_holder["now"] + timedelta(seconds=1)
    hit2, _ = cache.check_and_record(ctx_right)
    assert hit2 is False
