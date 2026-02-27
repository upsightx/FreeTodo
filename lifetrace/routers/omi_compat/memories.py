"""Omi-compatible memory API.

Maps omi's ``/v3/memories`` to LifeTrace's Memory system.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from lifetrace.routers.omi_compat.auth import verify_token
from lifetrace.util.logging_config import get_logger

logger = get_logger()

router = APIRouter(tags=["omi-memories"])


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class OmiMemory(BaseModel):
    id: str
    content: str
    category: str = "core"
    created_at: str
    updated_at: str | None = None
    reviewed: bool = False
    user_review: bool | None = None
    visibility: str = "private"


class CreateMemoryRequest(BaseModel):
    content: str
    category: str = "core"
    visibility: str = "private"


class EditMemoryRequest(BaseModel):
    value: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _iso(dt: datetime | None) -> str:
    if dt is None:
        return datetime.now(tz=UTC).isoformat()
    return dt.isoformat() if dt.tzinfo else dt.replace(tzinfo=UTC).isoformat()


def _row_to_omi(row: dict[str, Any]) -> OmiMemory:
    ts = row.get("created_at") or row.get("timestamp")
    ts_str = _iso(ts) if isinstance(ts, datetime) else str(ts) if ts else _iso(None)
    return OmiMemory(
        id=str(row.get("memory_id", row.get("id", ""))),
        content=row.get("content", ""),
        category=row.get("category", "core"),
        created_at=ts_str,
        updated_at=ts_str,
        reviewed=bool(row.get("reviewed", False)),
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/v3/memories", response_model=list[OmiMemory])
async def list_memories(
    limit: int = 100,
    offset: int = 0,
    uid: str = Depends(verify_token),
):
    try:
        from lifetrace.memory.reader import MemoryReader

        reader = MemoryReader()
        rows = reader.list_memories(limit=limit, offset=offset)
        return [_row_to_omi(r) for r in rows]
    except Exception as e:
        logger.error(f"[omi-compat] list_memories error: {e}")
        return []


@router.post("/v3/memories", response_model=OmiMemory)
async def create_memory(
    body: CreateMemoryRequest,
    uid: str = Depends(verify_token),
):
    try:
        from lifetrace.memory.writer import MemoryWriter

        writer = MemoryWriter()
        mem = writer.create_memory(content=body.content, category=body.category)
        return _row_to_omi(mem)
    except Exception as e:
        logger.error(f"[omi-compat] create_memory error: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.delete("/v3/memories/{memory_id}")
async def delete_memory(
    memory_id: str,
    uid: str = Depends(verify_token),
):
    try:
        from lifetrace.memory.writer import MemoryWriter

        writer = MemoryWriter()
        writer.delete_memory(memory_id)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"[omi-compat] delete_memory error: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.patch("/v3/memories/{memory_id}")
async def edit_memory(
    memory_id: str,
    body: EditMemoryRequest,
    uid: str = Depends(verify_token),
):
    try:
        from lifetrace.memory.writer import MemoryWriter

        writer = MemoryWriter()
        writer.update_memory(memory_id, content=body.value)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"[omi-compat] edit_memory error: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.delete("/v3/memories")
async def delete_all_memories(
    uid: str = Depends(verify_token),
):
    """Bulk delete – omi App sends this on "clear all"."""
    try:
        from lifetrace.memory.writer import MemoryWriter

        writer = MemoryWriter()
        writer.delete_all_memories()
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"[omi-compat] delete_all_memories error: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from None
