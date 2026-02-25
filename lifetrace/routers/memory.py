"""Memory REST API — read, search and compress personal memory files."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Query

from lifetrace.memory.manager import try_get_memory_manager

router = APIRouter(prefix="/api/memory", tags=["memory"])


def _require_manager():
    mgr = try_get_memory_manager()
    if mgr is None:
        raise HTTPException(status_code=503, detail="Memory module not initialized")
    return mgr


@router.get("/today")
async def get_today_memory():
    mgr = _require_manager()
    today = datetime.now(tz=UTC).strftime("%Y-%m-%d")
    content = mgr.reader.read_by_date(today)
    return {"date": today, "content": content}


@router.get("/date/{date_str}")
async def get_memory_by_date(date_str: str):
    mgr = _require_manager()
    content = mgr.reader.read_by_date(date_str)
    return {"date": date_str, "content": content}


@router.get("/raw/{date_str}")
async def get_raw_memory(date_str: str):
    mgr = _require_manager()
    content = mgr.reader.get_raw_content(date_str)
    return {"date": date_str, "content": content}


@router.get("/search")
async def search_memory(
    keyword: str = Query(..., min_length=1),
    days: int = Query(default=7, ge=1, le=365),
    max_results: int = Query(default=10, ge=1, le=50),
):
    mgr = _require_manager()
    results = mgr.reader.search_keyword(keyword, days=days, max_results=max_results)
    return {
        "keyword": keyword,
        "days": days,
        "count": len(results),
        "results": [r.model_dump() for r in results],
    }


@router.get("/dates")
async def list_memory_dates():
    mgr = _require_manager()
    dates = mgr.reader.list_available_dates()
    return {"count": len(dates), "dates": dates}


@router.get("/status")
async def get_memory_status():
    mgr = _require_manager()
    return mgr.get_status()


@router.post("/compress/{date_str}")
async def trigger_compress(date_str: str):
    mgr = _require_manager()
    if mgr.compressor is None:
        raise HTTPException(status_code=503, detail="Compressor not available (LLM not configured)")
    path = await mgr.compressor.compress_day(date_str)
    return {
        "date": date_str,
        "compressed": path is not None,
        "path": str(path) if path else None,
    }
