from __future__ import annotations

from lifetrace.schemas.perception_todo_intent import (
    ExtractedTodoCandidate,
    TodoIntegrationResult,
    TodoIntentContext,
)
from lifetrace.services.perception_todo_intent.dedupe import TTLDedupeCache
from lifetrace.storage import todo_mgr
from lifetrace.util.logging_config import get_logger

logger = get_logger()

_INTEGRATION_MODES = {"draft", "active", "review_queue"}


class TodoIntentIntegration:
    def __init__(
        self,
        *,
        mode: str,
        config: dict[str, object] | None = None,
    ):
        cfg = dict(config or {})
        normalized_mode = (mode or "draft").strip().lower()
        self._mode = normalized_mode if normalized_mode in _INTEGRATION_MODES else "draft"
        self._create_confidence_threshold = float(cfg.get("create_confidence_threshold", 0.7))
        self._update_confidence_threshold = float(cfg.get("update_confidence_threshold", 0.75))
        _ = self._update_confidence_threshold

        post_window_seconds = int(cfg.get("post_extract_dedupe_window_seconds", 600))
        self._post_dedupe = TTLDedupeCache(
            ttl_seconds=post_window_seconds,
            max_size=5000,
        )

    def integrate(
        self,
        *,
        context: TodoIntentContext,
        candidates: list[ExtractedTodoCandidate],
    ) -> list[TodoIntegrationResult]:
        results: list[TodoIntegrationResult] = []

        for candidate in candidates:
            dedupe_key = candidate.dedupe_key or ""
            if dedupe_key and self._post_dedupe.check_and_mark(dedupe_key):
                results.append(
                    TodoIntegrationResult(
                        action="skipped",
                        dedupe_key=dedupe_key,
                        reason="post_extract_dedupe_hit",
                    )
                )
                continue

            if self._mode == "review_queue":
                results.append(
                    TodoIntegrationResult(
                        action="queued_review",
                        dedupe_key=dedupe_key or None,
                        reason="review_queue_mode",
                    )
                )
                continue

            status = self._resolve_status(candidate)
            todo_id = self._create_todo(
                context=context,
                candidate=candidate,
                status=status,
            )
            if todo_id is None:
                results.append(
                    TodoIntegrationResult(
                        action="skipped",
                        dedupe_key=dedupe_key or None,
                        reason="create_failed",
                    )
                )
                continue

            results.append(
                TodoIntegrationResult(
                    action="created",
                    todo_id=todo_id,
                    dedupe_key=dedupe_key or None,
                )
            )

        return results

    def _resolve_status(self, candidate: ExtractedTodoCandidate) -> str:
        if self._mode == "draft":
            return "draft"
        if candidate.confidence >= self._create_confidence_threshold:
            return "active"
        return "draft"

    def _create_todo(
        self,
        *,
        context: TodoIntentContext,
        candidate: ExtractedTodoCandidate,
        status: str,
    ) -> int | None:
        due = candidate.due or candidate.deadline
        user_notes = self._build_user_notes(context, candidate)
        try:
            return todo_mgr.create_todo(
                name=candidate.name,
                description=candidate.description,
                user_notes=user_notes,
                start_time=candidate.start_time,
                due=due,
                deadline=due,
                time_zone=candidate.time_zone,
                status=status,
                priority=candidate.priority,
                tags=candidate.tags or ["auto_extract"],
            )
        except Exception as exc:  # pragma: no cover - defensive path
            logger.warning(f"todo intent integration create failed: {exc}")
            return None

    def _build_user_notes(
        self, context: TodoIntentContext, candidate: ExtractedTodoCandidate
    ) -> str:
        lines = [
            "source: perception.todo_intent",
            f"context_id: {context.context_id}",
        ]
        if candidate.source_event_ids:
            lines.append(f"source_event_ids: {','.join(candidate.source_event_ids)}")
        if candidate.source_text:
            lines.append(f"source_text: {candidate.source_text}")
        return "\n".join(lines)
