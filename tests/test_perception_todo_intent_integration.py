from __future__ import annotations

from datetime import UTC, datetime, timedelta

import lifetrace.services.perception_todo_intent.integration as integration_module
from lifetrace.schemas.perception_todo_intent import (
    ExtractedTodoCandidate,
    TodoIntentContext,
    TodoIntentTimeWindow,
)
from lifetrace.services.perception_todo_intent.integration import TodoIntentIntegration

_UPDATED_TODO_ID = 7
_CREATED_TODO_ID = 101


class _FakeTodoMgr:
    def __init__(self):
        self.created: list[dict[str, object]] = []
        self.updated: list[tuple[int, dict[str, object]]] = []
        self.active_rows: list[dict[str, object]] = []
        self.draft_rows: list[dict[str, object]] = []

    def list_todos(self, *, limit: int, offset: int, status: str | None = None):  # noqa: ARG002
        if status == "active":
            return self.active_rows
        if status == "draft":
            return self.draft_rows
        return []

    def create_todo(self, **kwargs):
        self.created.append(kwargs)
        return _CREATED_TODO_ID

    def update_todo(self, todo_id: int, **kwargs):
        self.updated.append((todo_id, kwargs))
        return True


def _build_context() -> TodoIntentContext:
    now = datetime(2026, 2, 19, 12, 0, tzinfo=UTC)
    return TodoIntentContext(
        context_id="ctx-1",
        events=[],
        merged_text="",
        time_window=TodoIntentTimeWindow(start=now, end=now + timedelta(seconds=10)),
        source_set=[],
        metadata={},
    )


def test_integration_updates_existing_todo(monkeypatch) -> None:
    fake_mgr = _FakeTodoMgr()
    fake_mgr.active_rows = [
        {
            "id": _UPDATED_TODO_ID,
            "name": "Send proposal",
            "description": "old",
            "user_notes": "",
            "priority": "none",
            "tags": ["work"],
            "due": datetime(2026, 2, 20, 7, 0, tzinfo=UTC),
        }
    ]
    monkeypatch.setattr(integration_module, "todo_mgr", fake_mgr)

    integration = TodoIntentIntegration(
        mode="active",
        config={
            "create_confidence_threshold": 0.7,
            "update_confidence_threshold": 0.75,
            "update_time_tolerance_seconds": 7200,
        },
    )
    candidate = ExtractedTodoCandidate(
        name="Send proposal",
        description="to Alice",
        due=datetime(2026, 2, 20, 7, 30, tzinfo=UTC),
        priority="high",
        tags=["client"],
        confidence=0.9,
        source_text="I will send proposal to Alice tomorrow morning.",
        source_event_ids=["e1"],
    )

    results = integration.integrate(context=_build_context(), candidates=[candidate])

    assert results[0].action == "updated"
    assert fake_mgr.created == []
    assert fake_mgr.updated
    assert fake_mgr.updated[0][0] == _UPDATED_TODO_ID


def test_integration_updates_existing_with_naive_due(monkeypatch) -> None:
    fake_mgr = _FakeTodoMgr()
    fake_mgr.active_rows = [
        {
            "id": _UPDATED_TODO_ID,
            "name": "Send proposal",
            "description": "old",
            "user_notes": "",
            "priority": "none",
            "tags": ["work"],
            "due": "2026-02-20T07:00:00",
        }
    ]
    monkeypatch.setattr(integration_module, "todo_mgr", fake_mgr)

    integration = TodoIntentIntegration(
        mode="active",
        config={
            "create_confidence_threshold": 0.7,
            "update_confidence_threshold": 0.75,
            "update_time_tolerance_seconds": 7200,
        },
    )
    candidate = ExtractedTodoCandidate(
        name="Send proposal",
        due=datetime(2026, 2, 20, 7, 30, tzinfo=UTC),
        confidence=0.9,
        source_text="send proposal at 7:30",
    )

    results = integration.integrate(context=_build_context(), candidates=[candidate])

    assert results[0].action == "updated"
    assert fake_mgr.updated
    assert fake_mgr.created == []


def test_integration_creates_when_no_existing_match(monkeypatch) -> None:
    fake_mgr = _FakeTodoMgr()
    monkeypatch.setattr(integration_module, "todo_mgr", fake_mgr)

    integration = TodoIntentIntegration(mode="draft", config={})
    candidate = ExtractedTodoCandidate(
        name="Prepare weekly report",
        confidence=0.8,
        source_text="Prepare weekly report tomorrow.",
    )

    results = integration.integrate(context=_build_context(), candidates=[candidate])

    assert results[0].action == "created"
    assert results[0].todo_id == _CREATED_TODO_ID
    assert fake_mgr.created
    assert fake_mgr.updated == []


def test_integration_review_queue_mode(monkeypatch) -> None:
    fake_mgr = _FakeTodoMgr()
    monkeypatch.setattr(integration_module, "todo_mgr", fake_mgr)

    integration = TodoIntentIntegration(mode="review_queue", config={})
    candidate = ExtractedTodoCandidate(
        name="Book meeting room",
        confidence=0.9,
        source_text="book room",
    )

    results = integration.integrate(context=_build_context(), candidates=[candidate])

    assert results[0].action == "queued_review"
    assert fake_mgr.created == []
    assert fake_mgr.updated == []
