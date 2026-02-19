from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime
from typing import TYPE_CHECKING, Any

from lifetrace.schemas.perception_todo_intent import ExtractedTodoCandidate, TodoIntentContext
from lifetrace.util.logging_config import get_logger
from lifetrace.util.time_utils import to_utc

if TYPE_CHECKING:
    from lifetrace.llm.llm_client import LLMClient

logger = get_logger()

_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)
_PRIORITY_SET = {"high", "medium", "low", "none"}

_EXTRACT_SYSTEM_PROMPT = (
    "Extract actionable todos from text. Return strict JSON with shape: "
    '{"todos": [{"name": str, "description": str|null, "start_time": str|null, '
    '"due": str|null, "deadline": str|null, "priority": "high|medium|low|none", '
    '"tags": [str], "confidence": number, "source_text": str}]}. '
    "Only include actionable items."
)

_EXTRACT_USER_PROMPT_TEMPLATE = "Extract todos from this merged context:\n{text}"


class TodoIntentExtractor:
    def __init__(self, llm_client: LLMClient, config: dict[str, object] | None = None):
        cfg = dict(config or {})
        self._llm_client = llm_client
        self._model = str(cfg.get("model") or "").strip()
        self._temperature = float(cfg.get("temperature", 0.2))
        self._max_tokens = int(cfg.get("max_tokens", 800))
        self._max_todos_per_context = int(cfg.get("max_todos_per_context", 5))

    async def extract(self, context: TodoIntentContext) -> list[ExtractedTodoCandidate]:
        text = (context.merged_text or "").strip()
        if not text:
            return []
        if not self._llm_client.is_available():
            logger.info("todo intent extractor skipped: llm_unavailable")
            return []

        try:
            raw = await asyncio.to_thread(self._request_extract, text)
        except Exception as exc:  # pragma: no cover - defensive path
            logger.warning(f"todo intent extractor request failed: {exc}")
            return []

        payload = self._parse_payload(raw)
        todos_raw = payload.get("todos")
        if not isinstance(todos_raw, list):
            return []

        output: list[ExtractedTodoCandidate] = []
        for item in todos_raw:
            candidate = self._coerce_candidate(item)
            if candidate is None:
                continue
            output.append(candidate)
            if len(output) >= max(1, self._max_todos_per_context):
                break
        return output

    def _request_extract(self, text: str) -> str:
        self._llm_client._initialize_client()
        client = self._llm_client._get_client()
        response = client.chat.completions.create(
            model=self._model or self._llm_client.model,
            messages=[
                {"role": "system", "content": _EXTRACT_SYSTEM_PROMPT},
                {"role": "user", "content": _EXTRACT_USER_PROMPT_TEMPLATE.format(text=text)},
            ],
            temperature=self._temperature,
            max_tokens=self._max_tokens,
        )
        return (response.choices[0].message.content or "").strip()

    def _parse_payload(self, raw: str) -> dict[str, Any]:
        clean = (raw or "").strip()
        if clean.startswith("```json"):
            clean = clean[7:]
        if clean.startswith("```"):
            clean = clean[3:]
        if clean.endswith("```"):
            clean = clean[:-3]
        clean = clean.strip()

        if not clean:
            return {}

        for candidate in (clean, self._extract_json_object(clean)):
            if not candidate:
                continue
            parsed = self._try_json_loads(candidate)
            if isinstance(parsed, dict):
                return parsed
            if isinstance(parsed, list):
                return {"todos": parsed}
        return {}

    def _extract_json_object(self, text: str) -> str | None:
        match = _JSON_RE.search(text)
        return match.group(0) if match else None

    def _try_json_loads(self, text: str) -> Any:
        try:
            return json.loads(text)
        except Exception:
            return None

    def _coerce_candidate(self, item: Any) -> ExtractedTodoCandidate | None:
        if not isinstance(item, dict):
            return None

        name = str(item.get("name") or item.get("title") or "").strip()
        if not name:
            return None

        tags = self._coerce_tags(item.get("tags"))
        confidence = self._clamp_confidence(item.get("confidence"))
        priority = self._coerce_priority(item.get("priority"))

        source_text = str(item.get("source_text") or item.get("evidence") or name).strip()
        return ExtractedTodoCandidate(
            name=name,
            description=self._coerce_optional_str(item.get("description")),
            start_time=self._parse_datetime(item.get("start_time")),
            due=self._parse_datetime(item.get("due")),
            deadline=self._parse_datetime(item.get("deadline")),
            time_zone=self._coerce_optional_str(item.get("time_zone")),
            priority=priority,
            tags=tags,
            confidence=confidence,
            source_text=source_text,
        )

    def _coerce_tags(self, value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        output: list[str] = []
        for item in value:
            tag = str(item or "").strip()
            if not tag:
                continue
            output.append(tag[:32])
        return output

    def _coerce_priority(self, value: Any) -> str:
        normalized = str(value or "none").strip().lower()
        return normalized if normalized in _PRIORITY_SET else "none"

    def _coerce_optional_str(self, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def _clamp_confidence(self, value: Any) -> float:
        try:
            conf = float(value)
        except (TypeError, ValueError):
            return 0.0
        if conf < 0:
            return 0.0
        if conf > 1:
            return 1.0
        return conf

    def _parse_datetime(self, value: Any) -> datetime | None:
        if value is None:
            return None
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
