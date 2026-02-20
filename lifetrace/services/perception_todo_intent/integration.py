from __future__ import annotations

import hashlib
import re
from collections import OrderedDict

from lifetrace.schemas.perception_todo_intent import (
    ExtractedTodoCandidate,
    IntegrationAction,
    IntentGateDecision,
    TodoIntegrationResult,
    TodoIntentContext,
)
from lifetrace.util.time_utils import get_utc_now

_NON_WORD_RE = re.compile(r"[^\w\s]", re.UNICODE)
_MULTI_SPACE_RE = re.compile(r"\s+")


class TodoIntentIntegrationService:
    """In-memory integration for preview mode (no DB write)."""

    def __init__(
        self,
        *,
        dedupe_window_seconds: int = 600,
        max_cache_size: int = 5000,
    ):
        self._dedupe_window_seconds = max(1, int(dedupe_window_seconds))
        self._max_cache_size = max(1, int(max_cache_size))
        self._cache: OrderedDict[str, float] = OrderedDict()

    @staticmethod
    def _normalize_text(text: str | None) -> str:
        normalized = _NON_WORD_RE.sub(" ", (text or "").lower())
        return _MULTI_SPACE_RE.sub(" ", normalized).strip()

    def _candidate_dedupe_key(self, candidate: ExtractedTodoCandidate) -> str:
        raw = "|".join(
            [
                self._normalize_text(candidate.name),
                candidate.due.isoformat() if candidate.due else "",
                self._normalize_text(candidate.source_text),
            ]
        )
        return hashlib.sha1(raw.encode("utf-8"), usedforsecurity=False).hexdigest()

    def _evict_expired(self, now_ts: float) -> None:
        for key, expires_at in list(self._cache.items()):
            if expires_at <= now_ts:
                self._cache.pop(key, None)

    def _evict_overflow(self) -> None:
        while len(self._cache) > self._max_cache_size:
            self._cache.popitem(last=False)

    async def integrate(
        self,
        *,
        context: TodoIntentContext,
        gate_decision: IntentGateDecision,
        candidates: list[ExtractedTodoCandidate],
    ) -> list[TodoIntegrationResult]:
        _ = context
        _ = gate_decision
        if not candidates:
            return [
                TodoIntegrationResult(
                    action=IntegrationAction.SKIPPED,
                    reason="no_candidates",
                )
            ]

        now_ts = get_utc_now().timestamp()
        self._evict_expired(now_ts)

        results: list[TodoIntegrationResult] = []
        for candidate in candidates:
            dedupe_key = self._candidate_dedupe_key(candidate)
            expires_at = self._cache.get(dedupe_key)
            if expires_at and expires_at > now_ts:
                self._cache.move_to_end(dedupe_key, last=True)
                results.append(
                    TodoIntegrationResult(
                        action=IntegrationAction.SKIPPED,
                        dedupe_key=dedupe_key,
                        reason="duplicate_in_memory_window",
                    )
                )
                continue

            self._cache[dedupe_key] = now_ts + self._dedupe_window_seconds
            self._cache.move_to_end(dedupe_key, last=True)
            self._evict_overflow()
            results.append(
                TodoIntegrationResult(
                    action=IntegrationAction.CREATED,
                    dedupe_key=dedupe_key,
                    reason="memory_only_preview",
                )
            )

        return results
