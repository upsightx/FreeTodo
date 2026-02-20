from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from lifetrace.perception.models import SourceType
from lifetrace.schemas.perception_todo_intent import (
    TodoIntentContext,
    TodoIntentOrchestratorStats,
    TodoIntentProcessingRecord,
    TodoIntentProcessingStatus,
)
from lifetrace.services.perception_todo_intent.dedupe import PreGateDedupeCache
from lifetrace.services.perception_todo_intent.extractor import TodoIntentExtractor
from lifetrace.services.perception_todo_intent.gate import TodoIntentGate
from lifetrace.services.perception_todo_intent.integration import TodoIntentIntegrationService
from lifetrace.services.perception_todo_intent.normalizer import TodoIntentPostProcessor
from lifetrace.util.settings import settings
from lifetrace.util.time_utils import get_utc_now

if TYPE_CHECKING:
    from lifetrace.perception.models import PerceptionEvent


class TodoIntentOrchestrator:
    """Orchestrates pre-gate dedupe -> gate -> extract -> integrate."""

    def __init__(
        self,
        *,
        config: dict[str, Any] | None = None,
        dedupe: PreGateDedupeCache | None = None,
        gate: TodoIntentGate | None = None,
        extractor: TodoIntentExtractor | None = None,
        post_processor: TodoIntentPostProcessor | None = None,
        integration: TodoIntentIntegrationService | None = None,
    ):
        cfg = config
        if cfg is None:
            loaded = settings.get("perception.todo_intent", {}) or {}
            cfg = dict(loaded) if isinstance(loaded, dict) else {}
        self._config = cfg

        pre_gate_cfg = cfg.get("pre_gate_dedupe", {})
        if not isinstance(pre_gate_cfg, dict):
            pre_gate_cfg = {}
        gate_cfg = cfg.get("gate", {})
        if not isinstance(gate_cfg, dict):
            gate_cfg = {}
        extractor_cfg = cfg.get("extractor", {})
        if not isinstance(extractor_cfg, dict):
            extractor_cfg = {}
        integration_cfg = cfg.get("integration", {})
        if not isinstance(integration_cfg, dict):
            integration_cfg = {}

        self._max_context_chars = max(200, int(cfg.get("max_context_chars", 2500)))
        self._dedupe_enabled = bool(pre_gate_cfg.get("enabled", True))
        self._dedupe = dedupe or PreGateDedupeCache(
            ttl_seconds=int(pre_gate_cfg.get("exact_window_seconds", 90)),
            max_cache_size=int(pre_gate_cfg.get("max_cache_size", 5000)),
        )
        self._gate = gate or TodoIntentGate(
            min_text_length=int(gate_cfg.get("min_text_length", 8)),
            model=str(gate_cfg.get("model", "")).strip() or None,
            temperature=float(gate_cfg.get("temperature", 0.0)),
            max_tokens=int(gate_cfg.get("max_tokens", 160)),
        )
        self._extractor = extractor or TodoIntentExtractor(
            model=str(extractor_cfg.get("model", "")).strip() or None,
            temperature=float(extractor_cfg.get("temperature", 0.2)),
            max_tokens=int(extractor_cfg.get("max_tokens", 800)),
        )
        self._post_processor = post_processor or TodoIntentPostProcessor(
            max_todos_per_context=int(cfg.get("max_todos_per_context", 5)),
        )
        self._integration = integration or TodoIntentIntegrationService(
            dedupe_window_seconds=int(
                integration_cfg.get("post_extract_dedupe_window_seconds", 600)
            ),
        )
        self._counters: Counter[str] = Counter()

    @staticmethod
    def _source_prefix(source: SourceType) -> str:
        if source in {SourceType.MIC_PC, SourceType.MIC_HARDWARE}:
            return "[音频]"
        if source in {SourceType.OCR_SCREEN, SourceType.OCR_PROACTIVE}:
            return "[OCR]"
        if source == SourceType.USER_INPUT:
            return "[输入]"
        return "[文本]"

    def _build_record(  # noqa: PLR0913
        self,
        *,
        context: TodoIntentContext,
        status: TodoIntentProcessingStatus,
        dedupe_hit: bool = False,
        dedupe_key: str | None = None,
        gate_decision=None,
        candidates=None,
        integration_results=None,
        error: str | None = None,
    ) -> TodoIntentProcessingRecord:
        return TodoIntentProcessingRecord(
            record_id=f"tir_{uuid4().hex}",
            context_id=context.context_id,
            status=status,
            created_at=get_utc_now(),
            event_ids=list(context.event_ids),
            source_set=list(context.source_set),
            merged_text=context.merged_text,
            time_window_start=context.time_window_start,
            time_window_end=context.time_window_end,
            metadata=dict(context.metadata),
            dedupe_hit=dedupe_hit,
            dedupe_key=dedupe_key,
            gate_decision=gate_decision,
            candidates=list(candidates or []),
            integration_results=list(integration_results or []),
            error=error,
        )

    def build_context_from_event(self, event: PerceptionEvent) -> TodoIntentContext:
        text = (event.content_text or "").strip()
        merged_text = f"{self._source_prefix(event.source)} {text}".strip()
        if len(merged_text) > self._max_context_chars:
            merged_text = merged_text[: self._max_context_chars]

        return TodoIntentContext(
            context_id=f"ctx_{uuid4().hex}",
            event_ids=[event.event_id],
            merged_text=merged_text,
            source_set=[event.source],
            time_window_start=event.timestamp,
            time_window_end=event.timestamp,
            metadata=dict(event.metadata or {}),
        )

    async def process_event(self, event: PerceptionEvent) -> TodoIntentProcessingRecord:
        context = self.build_context_from_event(event)
        return await self.process_context(context)

    async def process_context(self, context: TodoIntentContext) -> TodoIntentProcessingRecord:
        self._counters["contexts_total"] += 1
        dedupe_hit = False
        dedupe_key: str | None = None
        if self._dedupe_enabled:
            dedupe_hit, dedupe_key = self._dedupe.check_and_record(context)
        if dedupe_hit:
            self._counters["dedupe_hits"] += 1
            return self._build_record(
                context=context,
                status=TodoIntentProcessingStatus.DEDUPE_HIT,
                dedupe_hit=True,
                dedupe_key=dedupe_key,
            )

        gate_decision = await self._gate.decide(context)
        if not gate_decision.should_extract:
            self._counters["gate_skips"] += 1
            return self._build_record(
                context=context,
                status=TodoIntentProcessingStatus.GATE_SKIPPED,
                dedupe_key=dedupe_key,
                gate_decision=gate_decision,
            )

        try:
            candidates = await self._extractor.extract(context)
        except Exception:
            # Retry once with stricter JSON instruction.
            candidates = await self._extractor.extract(context, strict_json=True)

        normalized = self._post_processor.normalize(candidates, context)
        self._counters["extracted_candidates"] += len(normalized)

        results = await self._integration.integrate(
            context=context,
            gate_decision=gate_decision,
            candidates=normalized,
        )
        self._counters["integrated_total"] += len(results)
        return self._build_record(
            context=context,
            status=(
                TodoIntentProcessingStatus.EXTRACTED
                if normalized
                else TodoIntentProcessingStatus.PROCESSED
            ),
            dedupe_key=dedupe_key,
            gate_decision=gate_decision,
            candidates=normalized,
            integration_results=results,
        )

    def get_stats(self) -> TodoIntentOrchestratorStats:
        return TodoIntentOrchestratorStats(
            contexts_total=int(self._counters.get("contexts_total", 0)),
            dedupe_hits=int(self._counters.get("dedupe_hits", 0)),
            gate_skips=int(self._counters.get("gate_skips", 0)),
            extracted_candidates=int(self._counters.get("extracted_candidates", 0)),
            integrated_total=int(self._counters.get("integrated_total", 0)),
        )
