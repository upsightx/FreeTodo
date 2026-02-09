"""音频相关的 LLM 工具函数。"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from lifetrace.llm.llm_client import LLMClient
else:
    LLMClient = Any
from lifetrace.util.logging_config import get_logger
from lifetrace.util.prompt_loader import get_prompt
from lifetrace.util.token_usage_logger import log_token_usage

logger = get_logger()

_CODE_BLOCK_MIN_LINES = 2


async def optimize_transcription_text(llm_client: LLMClient, text: str) -> str:
    """使用 LLM 优化转录文本。"""
    try:
        if not llm_client.is_available():
            logger.warning("LLM客户端不可用，跳过文本优化")
            return text

        system_prompt = get_prompt("transcription_optimization", "system_assistant")
        user_prompt = get_prompt("transcription_optimization", "user_prompt", text=text)

        if not system_prompt or not user_prompt:
            logger.warning("无法加载优化提示词，使用默认提示词")
            system_prompt = "你是一个专业的文本优化助手，擅长优化语音转录文本。"
            user_prompt = (
                "请优化以下语音转录文本，使其更加流畅、准确、易读。\n\n"
                f"转录文本：\n{text}\n\n只返回优化后的文本，不要其他内容。"
            )

        llm_client._initialize_client()
        openai_client = llm_client._get_client()
        response = cast(
            "Any",
            openai_client.chat.completions.create(
                model=llm_client.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
            ),
        )

        optimized_text = (response.choices[0].message.content or "").strip()
        usage = getattr(response, "usage", None)
        if usage:
            log_token_usage(
                model=llm_client.model,
                input_tokens=usage.prompt_tokens,
                output_tokens=usage.completion_tokens,
                endpoint="audio_transcription_optimization",
                user_query=text[:200],
                response_type="transcription_optimization",
                feature_type="audio_transcription",
            )

        if optimized_text.startswith("```"):
            lines = optimized_text.split("\n")
            if lines[0].startswith("```") and len(lines) > _CODE_BLOCK_MIN_LINES:
                optimized_text = "\n".join(lines[1:-1]).strip()
            else:
                optimized_text = optimized_text.strip()

        return optimized_text
    except Exception as e:
        logger.error(f"优化转录文本失败: {e}")
        return text
