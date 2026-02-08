"""Plan step execution helpers."""

from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING, Any

from lifetrace.llm.agno_plan.plan_state import StepResult
from lifetrace.llm.agno_plan.plan_status import (
    STEP_STATUS_FAILED,
    STEP_STATUS_RUNNING,
    STEP_STATUS_SKIPPED,
    STEP_STATUS_SUCCESS,
)
from lifetrace.storage.agent_plan_manager import AgentPlanStepPayload
from lifetrace.util.time_utils import get_utc_now

if TYPE_CHECKING:
    from collections.abc import Callable

    from lifetrace.llm.agno_plan.plan_actions import PlanActionExecutor
    from lifetrace.llm.agno_plan.plan_chat import PlanChatExecutor
    from lifetrace.llm.llm_client import LLMClient
    from lifetrace.schemas.agent_plan import PlanSpec, PlanStep
    from lifetrace.storage.agent_plan_manager import AgentPlanManager


class PlanStepExecutor:
    """Execute a single plan step with retries and events."""

    def __init__(
        self,
        *,
        plan_manager: AgentPlanManager,
        actions: PlanActionExecutor,
        llm_client: LLMClient,
        chat_executor: PlanChatExecutor,
    ) -> None:
        self.plan_manager = plan_manager
        self.actions = actions
        self.llm_client = llm_client
        self.chat_executor = chat_executor

    async def execute_step(
        self,
        step: PlanStep,
        plan: PlanSpec,
        run_id: str,
        emit: Callable[[dict[str, Any]], Any],
        *,
        session_id: str | None = None,
    ) -> StepResult:
        retry_policy = step.retry
        max_retries = retry_policy.max_retries if retry_policy else 0
        backoff_ms = retry_policy.backoff_ms if retry_policy else 0

        is_side_effect = self.actions.is_side_effect(step)
        start_time = get_utc_now()
        self.plan_manager.upsert_step(
            AgentPlanStepPayload(
                run_id=run_id,
                step_id=step.step_id,
                step_name=step.name,
                status=STEP_STATUS_RUNNING,
                retry_count=0,
                input_json=json.dumps(step.inputs, ensure_ascii=False),
                started_at=start_time,
                is_side_effect=is_side_effect,
                rollback_required=self.actions.requires_rollback(step),
            )
        )
        await emit(
            {
                "type": "step_started",
                "plan_id": plan.plan_id,
                "run_id": run_id,
                "step_id": step.step_id,
                "session_id": session_id,
                "status": STEP_STATUS_RUNNING,
                "timestamp": start_time.isoformat(),
            }
        )

        attempt = 0
        last_error: str | None = None
        while attempt <= max_retries:
            attempt += 1
            try:
                output = await self._execute_step_logic(
                    step,
                    run_id,
                    plan=plan,
                    emit=emit,
                    session_id=session_id,
                )
                end_time = get_utc_now()
                self.plan_manager.upsert_step(
                    AgentPlanStepPayload(
                        run_id=run_id,
                        step_id=step.step_id,
                        step_name=step.name,
                        status=STEP_STATUS_SUCCESS,
                        retry_count=attempt - 1,
                        output_json=json.dumps(output, ensure_ascii=False),
                        ended_at=end_time,
                        is_side_effect=is_side_effect,
                        rollback_required=self.actions.requires_rollback(step),
                    )
                )
                await emit(
                    {
                        "type": "step_completed",
                        "plan_id": plan.plan_id,
                        "run_id": run_id,
                        "step_id": step.step_id,
                        "session_id": session_id,
                        "status": STEP_STATUS_SUCCESS,
                        "timestamp": end_time.isoformat(),
                    }
                )
                return StepResult(
                    step_id=step.step_id,
                    status=STEP_STATUS_SUCCESS,
                    on_fail=step.on_fail,
                    completed_at=end_time.timestamp(),
                )
            except Exception as exc:
                last_error = str(exc)
                if attempt <= max_retries:
                    await emit(
                        {
                            "type": "step_retry",
                            "plan_id": plan.plan_id,
                            "run_id": run_id,
                            "step_id": step.step_id,
                            "session_id": session_id,
                            "retry_count": attempt,
                        }
                    )
                    if backoff_ms:
                        await asyncio.sleep(backoff_ms / 1000)
                    continue

                end_time = get_utc_now()
                self.plan_manager.upsert_step(
                    AgentPlanStepPayload(
                        run_id=run_id,
                        step_id=step.step_id,
                        step_name=step.name,
                        status=STEP_STATUS_FAILED,
                        retry_count=attempt - 1,
                        error=last_error,
                        ended_at=end_time,
                        is_side_effect=is_side_effect,
                        rollback_required=self.actions.requires_rollback(step),
                    )
                )
                await emit(
                    {
                        "type": "step_failed",
                        "plan_id": plan.plan_id,
                        "run_id": run_id,
                        "step_id": step.step_id,
                        "session_id": session_id,
                        "status": STEP_STATUS_FAILED,
                        "error": last_error,
                        "timestamp": end_time.isoformat(),
                    }
                )

                if step.on_fail == "skip":
                    return StepResult(
                        step_id=step.step_id,
                        status=STEP_STATUS_SKIPPED,
                        on_fail=step.on_fail,
                        completed_at=end_time.timestamp(),
                    )

                return StepResult(
                    step_id=step.step_id,
                    status=STEP_STATUS_FAILED,
                    on_fail=step.on_fail,
                    completed_at=end_time.timestamp(),
                )

        raise RuntimeError(last_error or "step_failed")

    async def _execute_step_logic(
        self,
        step: PlanStep,
        run_id: str,
        *,
        plan: PlanSpec,
        emit: Callable[[dict[str, Any]], Any],
        session_id: str | None,
    ) -> dict[str, Any]:
        if self.chat_executor.should_use_agent(step):
            return await self.chat_executor.execute_step(
                step,
                plan=plan,
                run_id=run_id,
                session_id=session_id,
                emit=emit,
            )
        if step.type == "tool":
            return self.actions.execute_tool(step, run_id)
        if step.type == "llm":
            return await self._execute_llm(step)
        if step.type == "condition":
            return self._execute_condition(step)
        raise ValueError(f"unsupported step type: {step.type}")

    async def _execute_llm(self, step: PlanStep) -> dict[str, Any]:
        messages = step.inputs.get("messages")
        if not messages:
            prompt = step.inputs.get("prompt") or ""
            system_prompt = step.inputs.get("system_prompt")
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
        response = self.llm_client.chat(messages=messages, temperature=0.2)
        return {"content": response}

    def _execute_condition(self, step: PlanStep) -> dict[str, Any]:
        value = step.inputs.get("value")
        if isinstance(value, bool):
            return {"value": value}
        expression = step.inputs.get("expression")
        if isinstance(expression, bool):
            return {"value": expression}
        return {"value": False}
