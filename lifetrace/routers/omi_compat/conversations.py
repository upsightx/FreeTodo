"""Omi-compatible conversation (memory/event) API.

Maps omi's ``/v1/conversations`` endpoints to LifeTrace's internal
Event + Memory systems.
"""

from __future__ import annotations

import functools
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from lifetrace.routers.omi_compat.auth import verify_token
from lifetrace.util.logging_config import get_logger

logger = get_logger()

router = APIRouter(tags=["omi-conversations"])


@functools.lru_cache(maxsize=1)
def _get_event_repo():
    """Lazy-init a cached SqlEventRepository."""
    from lifetrace.repositories.sql_event_repository import SqlEventRepository
    from lifetrace.storage.database_base import DatabaseBase

    return SqlEventRepository(DatabaseBase())


# ---------------------------------------------------------------------------
# Pydantic models (omi-compatible response shapes)
# ---------------------------------------------------------------------------


class TranscriptSegment(BaseModel):
    id: int = 0
    text: str = ""
    speaker_id: str = "SPEAKER_00"
    is_user: bool = True
    person_id: str | None = None
    start: float = 0.0
    end: float = 0.0


class ActionItem(BaseModel):
    description: str = ""
    completed: bool = False


class Structured(BaseModel):
    title: str = ""
    overview: str = ""
    emoji: str = ""
    action_items: list[ActionItem] = Field(default_factory=list)
    events: list[dict] = Field(default_factory=list)


class Geolocation(BaseModel):
    latitude: float = 0.0
    longitude: float = 0.0
    address: str | None = None


class OmiConversation(BaseModel):
    """Trimmed omi Conversation model for list/detail responses."""

    id: str
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None
    status: str = "completed"
    structured: Structured = Field(default_factory=Structured)
    transcript_segments: list[TranscriptSegment] = Field(default_factory=list)
    geolocation: Geolocation | None = None
    source: str = "omi"
    visibility: str = "private"
    discarded: bool = False
    deleted: bool = False
    starred: bool = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _iso(dt: datetime | None) -> str:
    if dt is None:
        return datetime.now(tz=UTC).isoformat()
    return dt.isoformat() if dt.tzinfo else dt.replace(tzinfo=UTC).isoformat()


def _event_to_conversation(row: dict[str, Any]) -> OmiConversation:
    """Convert a LifeTrace Event dict into an omi-compatible Conversation."""
    meta = row.get("metadata") or {}
    segments_raw = meta.get("segments", [])
    segments = [TranscriptSegment(**s) if isinstance(s, dict) else s for s in segments_raw]

    structured_raw = meta.get("structured")
    structured = (
        Structured(**structured_raw)
        if isinstance(structured_raw, dict)
        else Structured(
            title=row.get("title", ""),
            overview=row.get("content", ""),
        )
    )

    ts = row.get("timestamp") or row.get("created_at")
    ts_str = _iso(ts) if isinstance(ts, datetime) else str(ts) if ts else _iso(None)

    return OmiConversation(
        id=str(row.get("event_id", row.get("id", ""))),
        created_at=ts_str,
        started_at=ts_str,
        finished_at=ts_str,
        status="completed",
        structured=structured,
        transcript_segments=segments,
        source=row.get("source", "omi"),
        starred=bool(row.get("starred", False)),
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/v1/conversations", response_model=list[OmiConversation])
async def list_conversations(
    limit: int = 100,
    offset: int = 0,
    statuses: str | None = "processing,completed",
    uid: str = Depends(verify_token),
):
    """Return conversations (mapped from LifeTrace Events)."""
    try:
        repo = _get_event_repo()
        rows = repo.list_events(
            limit=limit,
            offset=offset,
            start_date=None,
            end_date=None,
            app_name=None,
        )
        return [_event_to_conversation(r) for r in rows]
    except Exception as e:
        logger.error(f"[omi-compat] list_conversations error: {e}")
        return []


@router.get("/v1/conversations/{conversation_id}", response_model=OmiConversation)
async def get_conversation(
    conversation_id: str,
    uid: str = Depends(verify_token),
):
    try:
        repo = _get_event_repo()
        row = repo.get_summary(int(conversation_id))
        if row is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return _event_to_conversation(row)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[omi-compat] get_conversation error: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.delete("/v1/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    uid: str = Depends(verify_token),
):
    # Event deletion not implemented yet; return ok to avoid 404
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Sub-resource stubs (action-items, segments, etc.)
# ---------------------------------------------------------------------------


@router.get("/v1/conversations/{conversation_id}/action-items")
async def conversation_action_items(
    conversation_id: str,
    uid: str = Depends(verify_token),
):
    return []


@router.get("/v1/conversations/{conversation_id}/segments/text")
async def conversation_segments_text(
    conversation_id: str,
    uid: str = Depends(verify_token),
):
    return ""


@router.get("/v1/conversations/{conversation_id}/transcripts")
async def conversation_transcripts(
    conversation_id: str,
    uid: str = Depends(verify_token),
):
    return []


@router.get("/v1/conversations/{conversation_id}/events")
async def conversation_events(
    conversation_id: str,
    uid: str = Depends(verify_token),
):
    return []


@router.get("/v1/conversations/{conversation_id}/suggested-apps")
async def conversation_suggested_apps(
    conversation_id: str,
    uid: str = Depends(verify_token),
):
    return []


@router.post("/v1/conversations/search")
async def search_conversations(uid: str = Depends(verify_token)):
    return []


@router.post("/v1/conversations")
async def create_conversation(uid: str = Depends(verify_token)):
    return {"id": "", "status": "created"}
