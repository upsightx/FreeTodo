"""Plan Runner - execution and rollback."""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import TYPE_CHECKING, Any

from lifetrace.llm.agno_plan.plan_actions import CompletedStep, PlanActionExecutor
from lifetrace.llm.agno_plan.plan_chat import PlanChatExecutor
from lifetrace.llm.agno_plan.plan_graph import topo_levels
from lifetrace.llm.agno_plan.plan_state import StepResult
from lifetrace.llm.agno_plan.plan_status import (
    RUN_STATUS_CANCELLED,
    RUN_STATUS_COMPLETED,
    RUN_STATUS_FAILED,
    RUN_STATUS_RUNNING,
    STEP_STATUS_FAILED,
    STEP_STATUS_SKIPPED,
    STEP_STATUS_SUCCESS,
)
from lifetrace.llm.agno_plan.plan_step_executor import PlanStepExecutor
from lifetrace.llm.llm_client import LLMClient
from lifetrace.repositories.sql_todo_repository import SqlTodoRepository
from lifetrace.storage.database import db_base
from lifetrace.util.logging_config import get_logger
from lifetrace.util.time_utils import get_utc_now

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Callable

    from lifetrace.schemas.agent_plan import PlanSpec, PlanStep
    from lifetrace.storage.agent_plan_manager import AgentPlanManager

logger = get_logger()

PLAN_EVENT_PREFIX = "\n[PLAN_EVENT:"
PLAN_EVENT_SUFFIX = "]\n"


class PlanRunner:
    """Plan Runner"""

    def __init__(
        self,
        plan_manager: AgentPlanManager,
        llm_client: LLMClient | None = None,
        workspace_path: str | None = None,
    ) -> None:
        self.plan_manager = plan_manager
        self.llm_client = llm_client or LLMClient()
        self.chat_executor = PlanChatExecutor(db_base)
        todo_repo = SqlTodoRepository(db_base)
        self.actions = PlanActionExecutor(
            plan_manager,
            todo_repo,
            workspace_path=workspace_path,
        )
        self.step_executor = PlanStepExecutor(
            plan_manager=plan_manager,
            actions=self.actions,
            llm_client=self.llm_client,
            chat_executor=self.chat_executor,
        )

    def format_event(self, payload: dict[str, Any]) -> str:
        return f"{PLAN_EVENT_PREFIX}{json.dumps(payload, ensure_ascii=False)}{PLAN_EVENT_SUFFIX}"

    def validate_plan(self, plan: PlanSpec) -> None:
        step_ids = {step.step_id for step in plan.steps}
        if len(step_ids) != len(plan.steps):
            raise ValueError("duplicate step_id detected")
        for step in plan.steps:
            for dep in step.depends_on:
                if dep not in step_ids:
                    raise ValueError(f"missing dependency: {dep}")
        topo_levels(plan.steps)

    async def run_plan_stream(
        self,
        *,
        plan: PlanSpec,
        session_id: str | None = None,
        run_id: str | None = None,
        resume: bool = False,
    ) -> AsyncGenerator[str, None]:
        """Run plan and stream events."""
        event_queue: asyncio.Queue[str | None] = asyncio.Queue()

        async def emit(payload: dict[str, Any]) -> None:
            await event_queue.put(self.format_event(payload))

        runner_task = asyncio.create_task(
            self._run_plan(
                plan=plan,
                session_id=session_id,
                run_id=run_id,
                resume=resume,
                emit=emit,
            )
        )

        while True:
            if runner_task.done() and event_queue.empty():
                break
            payload = await event_queue.get()
            if payload is None:
                break
            yield payload

        try:
            await runner_task
        except Exception as exc:
            logger.error("Plan stream failed: %s", exc)

    async def _run_plan(
        self,
        *,
        plan: PlanSpec,
        session_id: str | None,
        run_id: str | None,
        resume: bool,
        emit: Callable[[dict[str, Any]], Any],
    ) -> None:
        run_id, session_id = self._ensure_run(plan, session_id, run_id, resume)
        try:
            self.validate_plan(plan)
        except Exception as exc:
            await self._finalize_failure(
                plan,
                run_id,
                exc,
                [],
                emit,
                session_id=session_id,
            )
            return

        await emit(
            {
                "type": "plan_started",
                "plan_id": plan.plan_id,
                "run_id": run_id,
                "session_id": session_id,
                "timestamp": get_utc_now().isoformat(),
            }
        )

        completed_ids, completed_steps = self._load_resume_state(run_id, resume)

        try:
            for level in topo_levels(plan.steps):
                if await self._handle_cancel(plan, run_id, emit, session_id=session_id):
                    return
                results = await self._execute_level(
                    level,
                    plan,
                    run_id,
                    completed_ids,
                    emit,
                    session_id=session_id,
                )
                completed_steps, completed_ids = self._collect_results(
                    results, completed_steps, completed_ids
                )

            await self._finalize_success(
                plan,
                run_id,
                emit,
                session_id=session_id,
            )
        except Exception as exc:
            await self._finalize_failure(
                plan, run_id, exc, completed_steps, emit, session_id=session_id
            )

    def _ensure_run(
        self,
        plan: PlanSpec,
        session_id: str | None,
        run_id: str | None,
        resume: bool,
    ) -> tuple[str, str | None]:
        if resume and run_id:
            run_info = self.plan_manager.get_run(run_id)
            if not run_info:
                raise ValueError("run_id not found")
            if run_info["status"] in (RUN_STATUS_COMPLETED, RUN_STATUS_CANCELLED):
                raise ValueError("run already finished")
            session_id = self.chat_executor.ensure_session(
                session_id or run_info.get("session_id"),
                plan,
                run_id,
            )
            self.plan_manager.update_run(
                run_id,
                status=RUN_STATUS_RUNNING,
                error=None,
                ended_at=None,
                cancel_requested=False,
                session_id=session_id,
            )
            return run_id, session_id

        new_run_id = f"run_{uuid.uuid4().hex[:12]}"
        session_id = self.chat_executor.ensure_session(session_id, plan, new_run_id)
        run_info = self.plan_manager.create_run(
            run_id=new_run_id,
            plan_id=plan.plan_id,
            status=RUN_STATUS_RUNNING,
            session_id=session_id,
        )
        if not run_info:
            raise RuntimeError("failed to create run")
        return new_run_id, session_id

    def _load_resume_state(self, run_id: str, resume: bool) -> tuple[set[str], list[StepResult]]:
        if not resume:
            return set(), []
        completed_steps: list[StepResult] = []
        completed_ids: set[str] = set()
        for step in self.plan_manager.list_steps(run_id):
            if step["status"] not in (STEP_STATUS_SUCCESS, STEP_STATUS_SKIPPED):
                continue
            completed_ids.add(step["step_id"])
            completed_steps.append(
                StepResult(
                    step_id=step["step_id"],
                    status=step["status"],
                    on_fail="skip",
                    completed_at=step["ended_at"].timestamp() if step["ended_at"] else 0.0,
                )
            )
        return completed_ids, completed_steps

    async def _handle_cancel(
        self,
        plan: PlanSpec,
        run_id: str,
        emit: Callable[[dict[str, Any]], Any],
        *,
        session_id: str | None = None,
    ) -> bool:
        if not self._is_cancel_requested(run_id):
            return False
        self.plan_manager.update_run(
            run_id,
            status=RUN_STATUS_CANCELLED,
            ended_at=get_utc_now(),
        )
        await emit(
            {
                "type": "plan_cancelled",
                "plan_id": plan.plan_id,
                "run_id": run_id,
                "session_id": session_id,
                "timestamp": get_utc_now().isoformat(),
            }
        )
        return True

    async def _execute_level(
        self,
        level: list[PlanStep],
        plan: PlanSpec,
        run_id: str,
        completed_ids: set[str],
        emit: Callable[[dict[str, Any]], Any],
        *,
        session_id: str | None = None,
    ) -> list[StepResult | None]:
        tasks: list[asyncio.Task[StepResult | None]] = []
        for step in level:
            if step.step_id in completed_ids:
                continue
            tasks.append(
                asyncio.create_task(
                    self.step_executor.execute_step(step, plan, run_id, emit, session_id=session_id)
                )
            )
        if not tasks:
            return []
        return await asyncio.gather(*tasks)

    def _collect_results(
        self,
        results: list[StepResult | None],
        completed_steps: list[StepResult],
        completed_ids: set[str],
    ) -> tuple[list[StepResult], set[str]]:
        for result in results:
            if result is None:
                continue
            if result.status in (STEP_STATUS_SUCCESS, STEP_STATUS_SKIPPED):
                completed_steps.append(result)
                completed_ids.add(result.step_id)
                continue
            if result.status == STEP_STATUS_FAILED and result.on_fail != "skip":
                raise RuntimeError(f"step_failed:{result.step_id}")
        return completed_steps, completed_ids

    async def _finalize_success(
        self,
        plan: PlanSpec,
        run_id: str,
        emit: Callable[[dict[str, Any]], Any],
        *,
        session_id: str | None = None,
    ) -> None:
        self.plan_manager.update_run(
            run_id,
            status=RUN_STATUS_COMPLETED,
            ended_at=get_utc_now(),
        )
        await emit(
            {
                "type": "plan_completed",
                "plan_id": plan.plan_id,
                "run_id": run_id,
                "session_id": session_id,
                "timestamp": get_utc_now().isoformat(),
            }
        )

    async def _finalize_failure(
        self,
        plan: PlanSpec,
        run_id: str,
        exc: Exception,
        completed_steps: list[StepResult],
        emit: Callable[[dict[str, Any]], Any],
        *,
        session_id: str | None = None,
    ) -> None:
        logger.error("Plan execution failed: %s", exc)
        self.plan_manager.update_run(
            run_id,
            status=RUN_STATUS_FAILED,
            error=str(exc),
            ended_at=get_utc_now(),
        )
        await emit(
            {
                "type": "plan_failed",
                "plan_id": plan.plan_id,
                "run_id": run_id,
                "session_id": session_id,
                "error": str(exc),
                "timestamp": get_utc_now().isoformat(),
            }
        )
        rollback_steps = [
            CompletedStep(step_id=step.step_id, completed_at=step.completed_at)
            for step in completed_steps
            if step.status in (STEP_STATUS_SUCCESS, STEP_STATUS_SKIPPED)
        ]
        await self.actions.rollback(run_id, rollback_steps, emit)

    def _is_cancel_requested(self, run_id: str) -> bool:
        run = self.plan_manager.get_run(run_id)
        return bool(run and run.get("cancel_requested"))
