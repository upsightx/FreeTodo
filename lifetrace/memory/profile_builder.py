"""L4 ProfileBuilder — incremental user-profile maintenance.

Runs on a periodic schedule (default: every hour).  Collects the latest L2
event summaries since the last update, compares them against the existing
profile, and asks an LLM whether and how the profile should be updated.
The profile is stored as ``profile_L4/user_profile.md``.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from lifetrace.util.time_utils import get_local_now, local_today_str, local_yesterday_str

from lifetrace.util.logging_config import get_logger

if TYPE_CHECKING:
    from pathlib import Path

    from lifetrace.llm.llm_client import LLMClient

logger = get_logger()

PROFILE_SYSTEM_PROMPT = (
    "你是一个用户画像维护助手。根据最近发生的事件，判断是否需要更新用户画像。\n"
    "如果需要更新，输出完整的更新后画像（Markdown 格式）。\n"
    "如果不需要更新（事件太琐碎、没有新信息），只输出：NO_UPDATE"
)

PROFILE_USER_TEMPLATE = """当前用户画像：
{current_profile}

最近发生的事件摘要（{time_range}）：
{recent_events}

请判断：
1. 这些新事件是否揭示了用户的新特征、新习惯、新关系、新状态？
2. 如果是，请输出完整的更新后用户画像（保留未变化的部分，修改/新增有变化的部分）
3. 如果这些事件没有带来任何新的用户洞察，直接输出 NO_UPDATE

画像应包含以下分区（按需填写，没有信息的分区可以省略）：
- 基本信息（身份、角色）
- 工作模式（作息、工具偏好）
- 当前重点（近期主要在做什么）
- 社交关系（常联系的人、关系描述）
- 偏好与习惯
- 近期状态（情绪、压力等可观察的状态）
"""

DEFAULT_PROFILE = """# 用户画像

> 最后更新：{date}
> 状态：初始化，等待数据积累

（画像将在积累足够的观察数据后自动生成）
"""


class ProfileBuilder:
    """L4: maintain ``profile_L4/user_profile.md`` via hourly incremental updates.

    Each update cycle:
    1. Reads the current profile from ``profile_L4/user_profile.md``.
    2. Collects L2 event summaries from ``events_L2/`` since the last update.
    3. Asks LLM whether the profile should change.
    4. If yes, writes the updated profile back.
    """

    def __init__(
        self,
        memory_dir: Path,
        llm_client: LLMClient,
        *,
        model: str | None = None,
    ):
        self._memory_dir = memory_dir
        self._profile_dir = memory_dir / "profile_L4"
        self._profile_dir.mkdir(parents=True, exist_ok=True)
        self._profile_file = self._profile_dir / "user_profile.md"
        self._events_dir = memory_dir / "events_L2"
        self._llm = llm_client
        self._model = model

        self._last_update: datetime | None = None
        self._stats = {"checks": 0, "updates": 0, "skipped": 0, "errors": 0}

    def get_stats(self) -> dict:
        stats = dict(self._stats)
        stats["last_update"] = self._last_update.isoformat() if self._last_update else None
        return stats

    def read_profile(self) -> str:
        """Return current profile content."""
        if self._profile_file.exists():
            return self._profile_file.read_text(encoding="utf-8")
        return ""

    async def update(self) -> bool:
        """Run one update cycle.  Returns True if the profile was changed."""
        self._stats["checks"] += 1

        current_profile = self.read_profile()
        if not current_profile:
            today = local_today_str()
            current_profile = DEFAULT_PROFILE.format(date=today)
            self._profile_file.write_text(current_profile, encoding="utf-8")

        recent = self._collect_recent_events()
        if not recent.strip():
            self._stats["skipped"] += 1
            logger.debug("ProfileBuilder: no recent events, skipping update")
            return False

        time_range = self._time_range_label()

        prompt = PROFILE_USER_TEMPLATE.format(
            current_profile=current_profile,
            recent_events=recent,
            time_range=time_range,
        )
        messages: list[dict[str, str]] = [
            {"role": "system", "content": PROFILE_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        try:
            resp = await asyncio.to_thread(
                self._llm.chat,
                messages,
                0.3,
                self._model,
                4096,
                log_usage=True,
                log_meta={"endpoint": "memory_profile", "feature_type": "memory_profile"},
            )
        except Exception:
            logger.exception("ProfileBuilder LLM call failed")
            self._stats["errors"] += 1
            return False

        if not resp or "NO_UPDATE" in resp.strip().upper():
            self._stats["skipped"] += 1
            self._last_update = get_local_now()
            logger.debug("ProfileBuilder: LLM said no update needed")
            return False

        updated = self._ensure_header(resp.strip())
        self._profile_file.write_text(updated, encoding="utf-8")
        self._last_update = get_local_now()
        self._stats["updates"] += 1
        logger.info("ProfileBuilder: profile updated (%d chars)", len(updated))
        return True

    def _collect_recent_events(self) -> str:
        """Gather L2 event summaries from today's events file.

        If a last_update timestamp exists, tries to extract only events that
        appear after that time.  Falls back to returning the full day's events
        if parsing is uncertain.
        """
        today = local_today_str()
        events_file = self._events_dir / f"{today}.md"

        parts: list[str] = []
        if events_file.exists():
            parts.append(events_file.read_text(encoding="utf-8"))

        yesterday = local_yesterday_str()
        yesterday_file = self._events_dir / f"{yesterday}.md"
        if yesterday_file.exists() and self._last_update is None:
            parts.append(yesterday_file.read_text(encoding="utf-8"))

        return "\n\n---\n\n".join(parts)

    def _time_range_label(self) -> str:
        if self._last_update:
            return f"自 {self._last_update.strftime('%Y-%m-%d %H:%M')} 以来"
        return "最近（首次运行）"

    @staticmethod
    def _ensure_header(content: str) -> str:
        """Make sure the profile starts with an H1 and has an update timestamp."""
        now_str = get_local_now().strftime("%Y-%m-%d %H:%M")
        if not content.startswith("# "):
            content = f"# 用户画像\n\n{content}"
        marker = "> 最后更新："
        if marker not in content:
            lines = content.split("\n", 1)
            rest = lines[1] if len(lines) > 1 else ""
            content = f"{lines[0]}\n\n> 最后更新：{now_str}\n{rest}"
        else:
            import re  # noqa: PLC0415

            content = re.sub(
                r"> 最后更新：.*",
                f"> 最后更新：{now_str}",
                content,
                count=1,
            )
        return content
