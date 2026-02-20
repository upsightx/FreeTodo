from __future__ import annotations

import json
import re
from datetime import datetime
from typing import TYPE_CHECKING

from lifetrace.llm.llm_client import LLMClient
from lifetrace.schemas.perception_todo_intent import ExtractedTodoCandidate
from lifetrace.util.prompt_loader import get_prompt
from lifetrace.util.settings import settings

if TYPE_CHECKING:
    from lifetrace.schemas.perception_todo_intent import TodoIntentContext


class TodoIntentExtractor:
    """Todo intent extractor powered by LLM text generation."""

    _JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)

    def __init__(
        self,
        *,
        llm_client: LLMClient | None = None,
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 800,
        prompt_category: str = "perception_todo_intent_extraction",
    ):
        self._llm_client = llm_client or LLMClient()
        self._model = (model or "").strip()
        self._temperature = float(temperature)
        self._max_tokens = max(64, int(max_tokens))
        self._prompt_category = prompt_category

    @staticmethod
    def _load_from_settings() -> dict:
        cfg = settings.get("perception.todo_intent.extractor", {}) or {}
        if not isinstance(cfg, dict):
            cfg = {}
        return cfg

    @staticmethod
    def _to_datetime(value: object) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        text = str(value).strip()
        if not text:
            return None
        normalized = text.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(normalized)
        except Exception:
            return None

    @staticmethod
    def _to_confidence(value: object) -> float:
        try:
            val = float(value)
        except Exception:
            return 0.0
        if val < 0:
            return 0.0
        if val > 1:
            return 1.0
        return val

    @staticmethod
    def _to_tags(value: object) -> list[str]:
        if not isinstance(value, list):
            return []
        tags: list[str] = []
        for item in value:
            text = str(item).strip()
            if text:
                tags.append(text)
        return tags

    @classmethod
    def _parse_json(cls, text: str) -> dict:
        raw = (text or "").strip()
        if raw.startswith("```json"):
            raw = raw[7:]
        if raw.startswith("```"):
            raw = raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()
        if not raw:
            return {}

        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            pass

        match = cls._JSON_BLOCK_RE.search(raw)
        if not match:
            return {}
        try:
            parsed = json.loads(match.group(0))
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}

    def _to_candidates(self, payload: dict) -> list[ExtractedTodoCandidate]:
        todos_raw = payload.get("todos")
        if not isinstance(todos_raw, list):
            return []

        out: list[ExtractedTodoCandidate] = []
        for item in todos_raw:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or item.get("title") or "").strip()
            if not name:
                continue
            out.append(
                ExtractedTodoCandidate(
                    name=name,
                    description=str(item.get("description")).strip()
                    if item.get("description") is not None
                    else None,
                    start_time=self._to_datetime(item.get("start_time")),
                    due=self._to_datetime(item.get("due")),
                    deadline=self._to_datetime(item.get("deadline")),
                    time_zone=str(item.get("time_zone")).strip()
                    if item.get("time_zone") is not None
                    else None,
                    priority=str(item.get("priority") or "none").strip().lower() or "none",
                    tags=self._to_tags(item.get("tags")),
                    confidence=self._to_confidence(item.get("confidence")),
                    source_text=str(item.get("source_text")).strip()
                    if item.get("source_text") is not None
                    else None,
                )
            )
        return out

    async def extract(
        self,
        context: TodoIntentContext,
        *,
        strict_json: bool = False,
    ) -> list[ExtractedTodoCandidate]:
        cfg = self._load_from_settings()
        llm_client = self._llm_client
        if not llm_client.is_available():
            return []

        model = (
            str(cfg.get("model", "")).strip()
            or self._model
            or str(settings.get("llm.todo_extraction_model", "")).strip()
            or llm_client.model
        )
        temperature = float(cfg.get("temperature", self._temperature))
        max_tokens = int(cfg.get("max_tokens", self._max_tokens))
        prompt_category = str(cfg.get("prompt_category", self._prompt_category))

        merged_text = (context.merged_text or "").strip()
        if not merged_text:
            return []

        system_prompt = get_prompt(prompt_category, "system_assistant")
        user_prompt = get_prompt(
            prompt_category,
            "user_prompt",
            text=merged_text,
            source_set=", ".join([source.value for source in context.source_set]) or "unknown",
            app_name=str(context.metadata.get("app_name") or ""),
            window_title=str(context.metadata.get("window_title") or ""),
            speaker=str(context.metadata.get("speaker") or ""),
            strict_json="true" if strict_json else "false",
        )
        if strict_json:
            user_prompt = (
                f"{user_prompt}\n\n仅返回严格 JSON，不要包含任何解释、前后缀或 markdown 代码块。"
            )

        if not system_prompt or not user_prompt:
            raise ValueError("missing_extractor_prompt")

        result_text = llm_client.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            model=model,
            max_tokens=max_tokens,
            log_meta={
                "endpoint": "perception_todo_intent_extract",
                "feature_type": "perception",
                "response_type": "extract",
                "user_query": merged_text,
                "context_id": context.context_id,
            },
        )
        payload = self._parse_json(result_text)
        if not payload:
            raise ValueError("extractor_unparseable_response")
        return self._to_candidates(payload)
