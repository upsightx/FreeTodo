from __future__ import annotations

from datetime import datetime

from lifetrace.schemas.perception_todo_intent import (
    ExtractedTodoCandidate,
    TodoIntegrationResult,
    TodoIntentContext,
)
from lifetrace.services.perception_todo_intent.dedupe import TTLDedupeCache, canonicalize_text
from lifetrace.storage import todo_mgr
from lifetrace.util.logging_config import get_logger
from lifetrace.util.time_utils import to_utc

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
        self._update_time_tolerance_seconds = int(cfg.get("update_time_tolerance_seconds", 7200))
        self._lookup_limit = int(cfg.get("lookup_limit", 500))

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

            existing = self._find_existing_todo(candidate)
            if (
                existing is not None
                and candidate.confidence >= self._update_confidence_threshold
                and self._update_existing_todo(existing, context, candidate)
            ):
                results.append(
                    TodoIntegrationResult(
                        action="updated",
                        todo_id=int(existing.get("id") or 0) or None,
                        dedupe_key=dedupe_key or None,
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

    def _find_existing_todo(self, candidate: ExtractedTodoCandidate) -> dict[str, object] | None:
        candidate_name = canonicalize_text(candidate.name)
        if not candidate_name:
            return None

        candidate_due = self._candidate_due(candidate)
        fallback_name_only: dict[str, object] | None = None

        for todo in self._list_existing_todos():
            todo_name = canonicalize_text(str(todo.get("name") or ""))
            if todo_name != candidate_name:
                continue

            existing_due = self._existing_due(todo)
            if self._is_due_compatible(candidate_due, existing_due):
                return todo
            if candidate_due is None or existing_due is None:
                fallback_name_only = todo

        return fallback_name_only

    def _update_existing_todo(
        self,
        existing: dict[str, object],
        context: TodoIntentContext,
        candidate: ExtractedTodoCandidate,
    ) -> bool:
        todo_id = int(existing.get("id") or 0)
        if todo_id <= 0:
            return False

        update_payload = self._build_update_payload(existing, context, candidate)
        if not update_payload:
            return True
        try:
            return bool(todo_mgr.update_todo(todo_id, **update_payload))
        except Exception as exc:  # pragma: no cover - defensive path
            logger.warning(f"todo intent integration update failed: {exc}")
            return False

    def _build_update_payload(
        self,
        existing: dict[str, object],
        context: TodoIntentContext,
        candidate: ExtractedTodoCandidate,
    ) -> dict[str, object]:
        payload: dict[str, object] = {}

        existing_description = str(existing.get("description") or "").strip()
        merged_description = self._merge_text(existing_description, candidate.description)
        if merged_description != existing_description:
            payload["description"] = merged_description or None

        existing_notes = str(existing.get("user_notes") or "").strip()
        merged_notes = self._merge_text(existing_notes, self._build_user_notes(context, candidate))
        if merged_notes != existing_notes:
            payload["user_notes"] = merged_notes or None

        tags = self._merge_tags(existing.get("tags"), candidate.tags)
        if tags:
            payload["tags"] = tags

        existing_priority = str(existing.get("priority") or "none").strip().lower()
        if existing_priority == "none" and candidate.priority != "none":
            payload["priority"] = candidate.priority

        candidate_due = self._candidate_due(candidate)
        existing_due = self._existing_due(existing)
        if candidate_due is not None and existing_due is None:
            payload["due"] = candidate_due
            payload["deadline"] = candidate_due
            payload["start_time"] = candidate.start_time or candidate_due
            if candidate.time_zone:
                payload["time_zone"] = candidate.time_zone

        return payload

    def _merge_tags(self, existing: object, new_tags: list[str]) -> list[str]:
        output: list[str] = []
        seen: set[str] = set()

        existing_tags = existing if isinstance(existing, list) else []
        for raw in [*existing_tags, *new_tags, "auto_extract"]:
            tag = str(raw or "").strip()
            if not tag:
                continue
            if tag in seen:
                continue
            seen.add(tag)
            output.append(tag)

        return output

    def _merge_text(self, existing: str, new_content: str | None) -> str:
        new_text = str(new_content or "").strip()
        if not new_text:
            return existing
        if not existing:
            return new_text
        if new_text in existing:
            return existing
        return f"{existing}\n{new_text}"

    def _list_existing_todos(self) -> list[dict[str, object]]:
        todos: list[dict[str, object]] = []
        for status in ("active", "draft"):
            try:
                rows = todo_mgr.list_todos(limit=self._lookup_limit, offset=0, status=status)
            except Exception:
                rows = []
            for row in rows:
                if isinstance(row, dict):
                    todos.append(row)
        return todos

    def _candidate_due(self, candidate: ExtractedTodoCandidate) -> datetime | None:
        return self._coerce_datetime(candidate.due or candidate.deadline)

    def _existing_due(self, existing: dict[str, object]) -> datetime | None:
        return self._coerce_datetime(existing.get("due") or existing.get("deadline"))

    def _is_due_compatible(self, left: datetime | None, right: datetime | None) -> bool:
        if left is None and right is None:
            return True
        if left is None or right is None:
            return False
        delta = abs((left - right).total_seconds())
        return delta <= float(self._update_time_tolerance_seconds)

    def _coerce_datetime(self, value: object) -> datetime | None:
        if isinstance(value, datetime):
            return to_utc(value)
        if not isinstance(value, str):
            return None

        raw = value.strip()
        if not raw:
            return None
        if raw.endswith("Z"):
            raw = f"{raw[:-1]}+00:00"
        try:
            return to_utc(datetime.fromisoformat(raw))
        except ValueError:
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
