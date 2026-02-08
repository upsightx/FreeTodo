"""Agent plan chat execution helpers."""

from __future__ import annotations

import asyncio
import json
import threading
from typing import TYPE_CHECKING, Any

from lifetrace.llm.agent_service import AgentService
from lifetrace.repositories.sql_chat_repository import SqlChatRepository
from lifetrace.services.chat_service import ChatService
from lifetrace.util.logging_config import get_logger

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Callable

    from lifetrace.schemas.agent_plan import PlanSpec, PlanStep
    from lifetrace.storage.database_base import DatabaseBase

logger = get_logger()


class PlanChatExecutor:
    """Bridge plan execution to Agent chat sessions."""

    def __init__(self, db_base: DatabaseBase) -> None:
        self.chat_service = ChatService(SqlChatRepository(db_base))
        self.agent_service = AgentService()

    def ensure_session(
        self,
        session_id: str | None,
        plan: PlanSpec,
        run_id: str,
    ) -> str | None:
        if not session_id:
            session_id = self.chat_service.generate_session_id()

        chat = self.chat_service.ensure_chat_exists(
            session_id=session_id,
            chat_type="agent_plan",
            title=plan.title,
        )
        if not chat:
            logger.warning("Failed to ensure chat session for plan run %s", run_id)
        else:
            self.chat_service.update_chat_title(session_id, plan.title)
        return session_id

    def should_use_agent(self, step: PlanStep) -> bool:
        if step.type in {"tool"}:
            return False
        if step.type == "condition" and step.inputs == {"value": True}:
            return True
        return step.type == "condition"

    async def execute_step(
        self,
        step: PlanStep,
        *,
        plan: PlanSpec,
        run_id: str,
        session_id: str | None,
        emit: Callable[[dict[str, Any]], Any],
    ) -> dict[str, Any]:
        prompt = self._build_step_prompt(plan, step)
        if session_id:
            self.chat_service.add_message(
                session_id=session_id,
                role="user",
                content=prompt,
                metadata=json.dumps(
                    {"plan_id": plan.plan_id, "run_id": run_id, "step_id": step.step_id},
                    ensure_ascii=False,
                ),
            )
        await emit(
            {
                "type": "chat_message",
                "session_id": session_id,
                "step_id": step.step_id,
                "role": "user",
                "content": prompt,
            }
        )

        assistant_chunks: list[str] = []
        try:
            async for chunk in self._stream_agent_chunks(prompt):
                assistant_chunks.append(chunk)
                await emit(
                    {
                        "type": "chat_chunk",
                        "session_id": session_id,
                        "step_id": step.step_id,
                        "role": "assistant",
                        "content": chunk,
                    }
                )
        except Exception as exc:
            raise RuntimeError(f"agent_step_failed:{step.step_id}:{exc}") from exc

        assistant_content = "".join(assistant_chunks)
        if session_id and assistant_content:
            self.chat_service.add_message(
                session_id=session_id,
                role="assistant",
                content=assistant_content,
                metadata=json.dumps(
                    {"plan_id": plan.plan_id, "run_id": run_id, "step_id": step.step_id},
                    ensure_ascii=False,
                ),
            )
        await emit(
            {
                "type": "chat_message_completed",
                "session_id": session_id,
                "step_id": step.step_id,
                "role": "assistant",
            }
        )
        return {"content": assistant_content}

    async def _stream_agent_chunks(self, prompt: str) -> AsyncGenerator[str, None]:
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[tuple[str, str | None]] = asyncio.Queue()

        def runner() -> None:
            try:
                for chunk in self.agent_service.stream_agent_response(user_query=prompt):
                    loop.call_soon_threadsafe(queue.put_nowait, ("chunk", chunk))
            except Exception as exc:
                loop.call_soon_threadsafe(queue.put_nowait, ("error", str(exc)))
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, ("done", None))

        threading.Thread(target=runner, daemon=True).start()

        while True:
            kind, payload = await queue.get()
            if kind == "chunk" and payload is not None:
                yield payload
            elif kind == "error" and payload is not None:
                raise RuntimeError(payload)
            elif kind == "done":
                break

    def _build_step_prompt(self, plan: PlanSpec, step: PlanStep) -> str:
        return (
            "你正在执行一个计划。\n"
            f"计划标题: {plan.title}\n"
            f"当前步骤: {step.name}\n"
            "请完成该步骤，并输出结果。"
        )
