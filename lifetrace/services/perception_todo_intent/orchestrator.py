from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from lifetrace.llm.llm_client import LLMClient
from lifetrace.services.perception_todo_intent.dedupe import (
    TTLDedupeCache,
    build_context_anchor,
    build_exact_key,
    canonicalize_text,
)
from lifetrace.services.perception_todo_intent.extractor import TodoIntentExtractor
from lifetrace.services.perception_todo_intent.gate import TodoIntentGate
from lifetrace.services.perception_todo_intent.integration import TodoIntentIntegration
from lifetrace.services.perception_todo_intent.normalizer import normalize_candidates

if TYPE_CHECKING:
    from lifetrace.schemas.perception_todo_intent import TodoIntentContext


class TodoIntentOrchestrator:
    def __init__(self, config: dict[str, object] | None = None):
        cfg = dict(config or {})
        self._mode = str(cfg.get("mode") or "draft")
        self._window_seconds = int(cfg.get("window_seconds", 20))
        self._max_todos_per_context = int(cfg.get("max_todos_per_context", 5))

        pre_gate_cfg = dict(cfg.get("pre_gate_dedupe") or {})
        self._pre_gate_dedupe_enabled = bool(pre_gate_cfg.get("enabled", True))
        self._pre_gate_dedupe = TTLDedupeCache(
            ttl_seconds=int(pre_gate_cfg.get("exact_window_seconds", 90)),
            max_size=int(pre_gate_cfg.get("max_cache_size", 5000)),
        )

        llm_client = LLMClient()
        self._gate = TodoIntentGate(llm_client, dict(cfg.get("gate") or {}))
        self._extractor = TodoIntentExtractor(
            llm_client,
            {
                **dict(cfg.get("extractor") or {}),
                "max_todos_per_context": self._max_todos_per_context,
            },
        )
        self._integration = TodoIntentIntegration(
            mode=self._mode,
            config=dict(cfg.get("integration") or {}),
        )

    async def process_context(self, context: TodoIntentContext) -> dict[str, Any]:
        dedupe_hit, dedupe_key = self._run_pre_gate_dedupe(context)
        if dedupe_hit:
            return {
                "context_id": context.context_id,
                "dedupe_hit": True,
                "dedupe_key": dedupe_key,
                "gate_should_extract": False,
                "gate_reason": "pre_gate_dedupe_hit",
                "todos": [],
                "integration_results": [],
            }

        gate_decision = await self._gate.decide(context)
        if not gate_decision.should_extract:
            return {
                "context_id": context.context_id,
                "dedupe_hit": False,
                "dedupe_key": dedupe_key,
                "gate_should_extract": False,
                "gate_reason": gate_decision.reason,
                "todos": [],
                "integration_results": [],
            }

        extracted = await self._extractor.extract(context)
        normalized = normalize_candidates(
            candidates=extracted,
            context=context,
            max_todos_per_context=self._max_todos_per_context,
        )
        integration_results = await asyncio.to_thread(
            self._integration.integrate,
            context=context,
            candidates=normalized,
        )
        return {
            "context_id": context.context_id,
            "dedupe_hit": False,
            "dedupe_key": dedupe_key,
            "gate_should_extract": True,
            "gate_reason": gate_decision.reason,
            "todos": [item.model_dump() for item in normalized],
            "integration_results": [item.model_dump() for item in integration_results],
        }

    def _run_pre_gate_dedupe(self, context: TodoIntentContext) -> tuple[bool, str | None]:
        if not self._pre_gate_dedupe_enabled:
            return False, None

        canonical_text = canonicalize_text(context.merged_text)
        if not canonical_text:
            return False, None

        dedupe_key = build_exact_key(
            canonical_text=canonical_text,
            context_anchor=build_context_anchor(context.metadata),
            event_time=context.time_window.end,
            bucket_seconds=self._window_seconds,
        )
        first_event_id = context.events[0].event_id if context.events else None
        hit = self._pre_gate_dedupe.check_and_mark(
            dedupe_key,
            first_event_id=first_event_id,
            now=context.time_window.end,
        )
        return hit, dedupe_key
