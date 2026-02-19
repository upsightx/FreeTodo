from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from lifetrace.schemas.perception_todo_intent import IntentGateDecision, TodoIntentContext
from lifetrace.services.audio_extraction.gate import coerce_gate_decision, parse_gate_response
from lifetrace.util.logging_config import get_logger
from lifetrace.util.prompt_loader import get_prompt

if TYPE_CHECKING:
    from lifetrace.llm.llm_client import LLMClient

logger = get_logger()

_GATE_SYSTEM_PROMPT = (
    "You are a todo-intent gate. Decide if the text should be sent to a structured todo extractor. "
    'Return strict JSON: {"should_extract": boolean, "reason": string}.'
)
_GATE_USER_PROMPT_TEMPLATE = (
    "Decide if this context likely contains actionable todos.\nText:\n{text}"
)


class TodoIntentGate:
    def __init__(self, llm_client: LLMClient, config: dict[str, object] | None = None):
        cfg = dict(config or {})
        self._llm_client = llm_client
        self._enabled = bool(cfg.get("enabled", True))
        self._model = str(cfg.get("model") or "").strip()
        self._temperature = float(cfg.get("temperature", 0.0))
        self._max_tokens = int(cfg.get("max_tokens", 160))
        self._min_text_length = int(cfg.get("min_text_length", 8))

    async def decide(self, context: TodoIntentContext) -> IntentGateDecision:
        text = (context.merged_text or "").strip()
        early = self._early_decision(text)
        if early is not None:
            return early

        raw, error_reason = await self._call_gate_llm(text)
        if error_reason:
            return IntentGateDecision(should_extract=True, reason=error_reason)

        data = parse_gate_response(raw)
        return self._decision_from_data(data)

    def _request_gate(self, text: str) -> str:
        system_prompt = (
            get_prompt("perception_todo_intent", "gate_system_assistant") or _GATE_SYSTEM_PROMPT
        )
        user_prompt_template = (
            get_prompt("perception_todo_intent", "gate_user_prompt")
            or _GATE_USER_PROMPT_TEMPLATE
        )
        user_prompt = self._render_user_prompt(user_prompt_template, text)

        self._llm_client._initialize_client()
        client = self._llm_client._get_client()
        response = client.chat.completions.create(
            model=self._model or self._llm_client.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=self._temperature,
            max_tokens=self._max_tokens,
        )
        return (response.choices[0].message.content or "").strip()

    def _sanitize_data(self, data: dict[str, Any]) -> dict[str, object]:
        output: dict[str, object] = {}
        for key, value in data.items():
            if isinstance(value, str | int | float | bool) or value is None:
                output[key] = value
        return output

    def _early_decision(self, text: str) -> IntentGateDecision | None:
        if not text:
            return IntentGateDecision(should_extract=False, reason="empty_text")
        if len(text) < max(0, self._min_text_length):
            return IntentGateDecision(should_extract=False, reason="too_short")
        if not self._enabled:
            return IntentGateDecision(should_extract=True, reason="disabled")
        if not self._llm_client.is_available():
            return IntentGateDecision(should_extract=True, reason="llm_unavailable")
        return None

    async def _call_gate_llm(self, text: str) -> tuple[str, str | None]:
        try:
            raw = await asyncio.to_thread(self._request_gate, text)
        except Exception as exc:  # pragma: no cover - defensive path
            logger.warning(f"todo intent gate failed, fallback extract=true: {exc}")
            return "", "error"
        return raw, None

    def _decision_from_data(self, data: object) -> IntentGateDecision:
        if not isinstance(data, dict):
            return IntentGateDecision(should_extract=True, reason="unparseable")

        decision = coerce_gate_decision(data)
        if isinstance(decision, bool):
            reason = str(data.get("reason") or "ok")
            return IntentGateDecision(
                should_extract=decision,
                reason=reason,
                data=self._sanitize_data(data),
            )
        return IntentGateDecision(
            should_extract=True,
            reason="unknown_format",
            data=self._sanitize_data(data),
        )

    def _render_user_prompt(self, prompt_template: str, text: str) -> str:
        try:
            return prompt_template.format(text=text)
        except Exception:
            return _GATE_USER_PROMPT_TEMPLATE.format(text=text)
