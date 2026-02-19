from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

from lifetrace.services.perception_todo_intent.dedupe import canonicalize_text

if TYPE_CHECKING:
    from lifetrace.schemas.perception_todo_intent import ExtractedTodoCandidate, TodoIntentContext


def normalize_candidates(
    *,
    candidates: list[ExtractedTodoCandidate],
    context: TodoIntentContext,
    max_todos_per_context: int,
) -> list[ExtractedTodoCandidate]:
    normalized: list[ExtractedTodoCandidate] = []
    seen_keys: set[str] = set()
    max_count = max(1, int(max_todos_per_context))

    for candidate in candidates:
        updated = _normalize_single(candidate, context)
        key = _build_candidate_dedupe_key(updated)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        updated.dedupe_key = key
        normalized.append(updated)
        if len(normalized) >= max_count:
            break

    return normalized


def _normalize_single(
    candidate: ExtractedTodoCandidate,
    context: TodoIntentContext,
) -> ExtractedTodoCandidate:
    if candidate.due is None and candidate.deadline is not None:
        candidate.due = candidate.deadline
    if candidate.deadline is None and candidate.due is not None:
        candidate.deadline = candidate.due

    candidate.priority = _normalize_priority(candidate.priority)
    candidate.confidence = _clamp_confidence(candidate.confidence)
    if not candidate.source_text:
        candidate.source_text = candidate.name

    if not candidate.source_event_ids:
        candidate.source_event_ids = _match_source_event_ids(candidate.source_text, context)
    return candidate


def _normalize_priority(value: str) -> str:
    normalized = (value or "none").strip().lower()
    if normalized in {"high", "medium", "low", "none"}:
        return normalized
    return "none"


def _clamp_confidence(value: float) -> float:
    if value < 0:
        return 0.0
    if value > 1:
        return 1.0
    return value


def _match_source_event_ids(source_text: str, context: TodoIntentContext) -> list[str]:
    source_canonical = canonicalize_text(source_text)
    if not source_canonical:
        return [event.event_id for event in context.events[-1:]]

    matched: list[str] = []
    for event in context.events:
        event_text = canonicalize_text(event.content_text)
        if not event_text:
            continue
        if source_canonical in event_text or event_text in source_canonical:
            matched.append(event.event_id)

    if matched:
        return matched
    return [event.event_id for event in context.events[-1:]]


def _build_candidate_dedupe_key(candidate: ExtractedTodoCandidate) -> str:
    when = candidate.due or candidate.deadline or candidate.start_time
    time_text = when.isoformat() if when is not None else ""
    raw = "|".join(
        [
            canonicalize_text(candidate.name),
            time_text,
            canonicalize_text(candidate.source_text),
        ]
    )
    return hashlib.md5(raw.encode("utf-8"), usedforsecurity=False).hexdigest()
