from __future__ import annotations

import hashlib
import re
from collections import OrderedDict
from typing import TYPE_CHECKING

from lifetrace.util.time_utils import get_utc_now

if TYPE_CHECKING:
    from lifetrace.schemas.perception_todo_intent import TodoIntentContext


_NON_WORD_RE = re.compile(r"[^\w\s]", re.UNICODE)
_MULTI_SPACE_RE = re.compile(r"\s+")


def _normalize_text(text: str) -> str:
    normalized = _NON_WORD_RE.sub(" ", (text or "").lower())
    normalized = _MULTI_SPACE_RE.sub(" ", normalized).strip()
    return normalized


class PreGateDedupeCache:
    """In-memory dedupe cache for TodoIntent pre-gate filtering."""

    def __init__(
        self,
        *,
        ttl_seconds: int = 90,
        max_cache_size: int = 5000,
    ):
        self._ttl_seconds = max(1, int(ttl_seconds))
        self._max_cache_size = max(1, int(max_cache_size))
        self._cache: OrderedDict[str, float] = OrderedDict()
        self._hit_count = 0
        self._miss_count = 0

    def _build_key(self, context: TodoIntentContext) -> str:
        canonical_text = _normalize_text(context.merged_text)
        anchor = "|".join(
            [
                str(context.metadata.get("app_name") or ""),
                str(context.metadata.get("window_title") or ""),
                str(context.metadata.get("speaker") or ""),
            ]
        )
        raw = f"{canonical_text}|{anchor}"
        return hashlib.sha1(raw.encode("utf-8"), usedforsecurity=False).hexdigest()

    def _evict_expired(self, now_ts: float) -> None:
        for key, expires_at in list(self._cache.items()):
            if expires_at <= now_ts:
                self._cache.pop(key, None)

    def _evict_overflow(self) -> None:
        while len(self._cache) > self._max_cache_size:
            self._cache.popitem(last=False)

    def check_and_record(self, context: TodoIntentContext) -> tuple[bool, str]:
        now_ts = get_utc_now().timestamp()
        self._evict_expired(now_ts)
        dedupe_key = self._build_key(context)
        expires_at = self._cache.get(dedupe_key)
        if expires_at and expires_at > now_ts:
            self._hit_count += 1
            self._cache.move_to_end(dedupe_key, last=True)
            return True, dedupe_key

        self._miss_count += 1
        self._cache[dedupe_key] = now_ts + self._ttl_seconds
        self._cache.move_to_end(dedupe_key, last=True)
        self._evict_overflow()
        return False, dedupe_key

    def stats(self) -> dict[str, int]:
        return {
            "size": len(self._cache),
            "hit_count": self._hit_count,
            "miss_count": self._miss_count,
        }
