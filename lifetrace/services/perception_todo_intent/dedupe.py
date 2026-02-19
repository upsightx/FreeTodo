from __future__ import annotations

import hashlib
import re
from collections import OrderedDict
from dataclasses import dataclass

from lifetrace.util.time_utils import get_utc_now

_PUNCT_RE = re.compile(r"[^\w\s\u4e00-\u9fff]")
_SPACE_RE = re.compile(r"\s+")


def canonicalize_text(text: str) -> str:
    normalized = (text or "").strip().lower()
    if not normalized:
        return ""
    normalized = _PUNCT_RE.sub(" ", normalized)
    normalized = _SPACE_RE.sub(" ", normalized)
    return normalized.strip()


def build_context_anchor(metadata: dict[str, object] | None) -> str:
    if not metadata:
        return ""

    parts: list[str] = []
    for key in ("app", "app_name", "window", "window_title", "speaker"):
        value = metadata.get(key)
        if value in (None, ""):
            continue
        parts.append(str(value).strip().lower())
    return "|".join(parts)


def build_exact_key(
    *,
    canonical_text: str,
    context_anchor: str,
    event_time: object,
    bucket_seconds: int = 10,
) -> str:
    timestamp_fn = getattr(event_time, "timestamp", None)
    event_ts = float(timestamp_fn()) if callable(timestamp_fn) else get_utc_now().timestamp()
    bucket = int(event_ts) // max(1, int(bucket_seconds))
    raw = f"{canonical_text}|{context_anchor}|{bucket}"
    return hashlib.md5(raw.encode("utf-8"), usedforsecurity=False).hexdigest()


@dataclass
class DedupeCacheEntry:
    expire_at_ts: float
    first_event_id: str | None
    hits: int = 0


class TTLDedupeCache:
    def __init__(self, *, ttl_seconds: int, max_size: int = 5000):
        self._ttl_seconds = max(1, int(ttl_seconds))
        self._max_size = max(1, int(max_size))
        self._store: OrderedDict[str, DedupeCacheEntry] = OrderedDict()

    def __len__(self) -> int:
        return len(self._store)

    def check_and_mark(
        self,
        key: str,
        *,
        first_event_id: str | None = None,
        now: object | None = None,
    ) -> bool:
        timestamp_fn = getattr(now, "timestamp", None)
        now_ts = float(timestamp_fn()) if callable(timestamp_fn) else get_utc_now().timestamp()
        self._evict_expired_and_oversized(now_ts)

        existing = self._store.get(key)
        if existing and existing.expire_at_ts > now_ts:
            existing.hits += 1
            self._store.move_to_end(key, last=True)
            return True

        self._store[key] = DedupeCacheEntry(
            expire_at_ts=now_ts + float(self._ttl_seconds),
            first_event_id=first_event_id,
            hits=0,
        )
        self._store.move_to_end(key, last=True)
        self._evict_expired_and_oversized(now_ts)
        return False

    def _evict_expired_and_oversized(self, now_ts: float) -> None:
        expired_keys = [k for k, v in self._store.items() if v.expire_at_ts <= now_ts]
        for key in expired_keys:
            self._store.pop(key, None)

        while len(self._store) > self._max_size:
            self._store.popitem(last=False)
