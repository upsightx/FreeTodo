from __future__ import annotations

from datetime import datetime  # noqa: TC003 — Pydantic needs this at runtime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class MemoryLevel(str, Enum):
    RAW = "raw"
    EVENT = "event"
    ACTIVITY = "activity"
    SUMMARY = "summary"
    ENTITY = "entity"


class MemoryEntry(BaseModel):
    """Single memory record (in-memory representation)."""

    timestamp: datetime
    source: str
    speaker: str | None = None
    app: str | None = None
    target: str | None = None
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class EventSummary(BaseModel):
    """L1 event summary produced by compressor."""

    title: str
    time_start: datetime
    time_end: datetime | None = None
    participants: list[str] = Field(default_factory=list)
    source: str
    summary: str
    action_items: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class MemorySearchResult(BaseModel):
    """Search result item."""

    level: MemoryLevel
    date: str
    snippet: str
    file_path: str | None = None
    relevance_hint: str | None = None
