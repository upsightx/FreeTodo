"""L1 Compressor — raw daily Markdown → structured event summaries via LLM."""

from __future__ import annotations

from datetime import UTC
from typing import TYPE_CHECKING

from lifetrace.util.logging_config import get_logger

if TYPE_CHECKING:
    from pathlib import Path

    from lifetrace.llm.llm_client import LLMClient

logger = get_logger()

COMPRESS_SYSTEM_PROMPT = (
    "你是一个个人记忆管理助手，擅长从原始感知记录中提取有意义的事件并生成结构化摘要。"
)

COMPRESS_USER_TEMPLATE = """以下是 {date_str} 的原始感知记录。
请提取所有有意义的事件，生成结构化 Markdown 摘要。

要求：
1. 每个事件包含：标题、时间范围、参与人、来源、摘要、待办（如果有）、标签
2. 合并时间相近且主题相关的碎片记录为一个事件
3. 忽略无意义的噪声数据（重复内容、无信息量的片段）
4. 输出格式严格遵循下方示例

输出格式示例：
```
# {date_str} 事件摘要

## Event: 与导师微信沟通论文进展
- **时间**: 09:17 - 09:25
- **参与人**: 张教授
- **来源**: 微信（屏幕感知 + 麦克风）
- **摘要**: 导师询问论文进展，回复实验数据正在整理中
- **待办**: 下午完成实验数据初步分析
- **标签**: #论文项目 #张教授
```

原始记录：
{raw_content}"""


class MemoryCompressor:
    """L0 raw → L1 event summaries via LLM."""

    MIN_RAW_LENGTH = 50

    def __init__(self, memory_dir: Path, llm_client: LLMClient):
        self._memory_dir = memory_dir
        self._raw_dir = memory_dir / "raw"
        self._events_dir = memory_dir / "events"
        self._events_dir.mkdir(parents=True, exist_ok=True)
        self._llm = llm_client

    async def compress_day(self, date_str: str) -> Path | None:
        """Compress the L0 file for *date_str* into an L1 event summary.

        Returns the path to the generated events file, or ``None`` if nothing
        was produced (missing/too-short raw file, LLM failure, etc.).
        """
        raw_file = self._raw_dir / f"{date_str}.md"
        if not raw_file.exists():
            logger.debug("No raw file for %s, skipping compression", date_str)
            return None

        raw_content = raw_file.read_text(encoding="utf-8")
        if len(raw_content.strip()) < self.MIN_RAW_LENGTH:
            logger.debug("Raw file for %s too short, skipping compression", date_str)
            return None

        prompt = COMPRESS_USER_TEMPLATE.format(date_str=date_str, raw_content=raw_content)
        messages: list[dict[str, str]] = [
            {"role": "system", "content": COMPRESS_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        try:
            summary = self._llm.chat(
                messages,
                temperature=0.3,
                log_meta={
                    "endpoint": "memory_compress",
                    "feature_type": "memory_compression",
                },
            )
        except Exception:
            logger.exception("LLM compression failed for %s", date_str)
            return None

        if not summary or not summary.strip():
            logger.warning("LLM returned empty summary for %s", date_str)
            return None

        events_file = self._events_dir / f"{date_str}.md"
        events_file.write_text(summary, encoding="utf-8")
        logger.info("Compressed %s → %s (%d chars)", raw_file.name, events_file.name, len(summary))
        return events_file

    async def compress_yesterday(self) -> Path | None:
        """Convenience: compress yesterday's raw file."""
        from datetime import datetime, timedelta  # noqa: PLC0415

        yesterday = (datetime.now(tz=UTC) - timedelta(days=1)).strftime("%Y-%m-%d")
        return await self.compress_day(yesterday)

    def is_compressed(self, date_str: str) -> bool:
        """Check whether an events file already exists for *date_str*."""
        return (self._events_dir / f"{date_str}.md").exists()
