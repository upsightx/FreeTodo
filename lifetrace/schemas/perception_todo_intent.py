from __future__ import annotations

from typing import Literal

from pydantic import AwareDatetime, BaseModel, Field


class TodoIntentTimeWindow(BaseModel):
    start: AwareDatetime
    end: AwareDatetime


class TodoIntentContext(BaseModel):
    context_id: str
    events: list[object]
    merged_text: str
    time_window: TodoIntentTimeWindow
    source_set: list[str] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)


class IntentGateDecision(BaseModel):
    should_extract: bool
    reason: str = "unknown"
    data: dict[str, object] | None = None


class ExtractedTodoCandidate(BaseModel):
    name: str
    description: str | None = None
    start_time: AwareDatetime | None = None
    due: AwareDatetime | None = None
    deadline: AwareDatetime | None = None
    time_zone: str | None = None
    priority: str = "none"
    tags: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    source_text: str = ""
    source_event_ids: list[str] = Field(default_factory=list)
    dedupe_key: str | None = None


class TodoIntegrationResult(BaseModel):
    action: Literal["created", "updated", "skipped", "queued_review"]
    todo_id: int | None = None
    dedupe_key: str | None = None
    reason: str | None = None
