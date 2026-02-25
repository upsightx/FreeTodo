"""Memory Reader — file-based retrieval engine (time + keyword search)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from lifetrace.memory.models import MemoryLevel, MemorySearchResult

if TYPE_CHECKING:
    from pathlib import Path
from lifetrace.util.logging_config import get_logger

logger = get_logger()


class MemoryReader:
    """File-based memory retrieval engine.

    Supports:
    - Date-based lookup (raw / events files)
    - Keyword search across recent days
    - Listing available dates
    """

    def __init__(self, memory_dir: Path):
        self._memory_dir = memory_dir
        self._raw_dir = memory_dir / "raw"
        self._events_dir = memory_dir / "events"

    def read_by_date(self, date_str: str, level: str = "events") -> str | None:
        """Read memory file for a given date.

        Prefers the compressed *events* file (L1); falls back to *raw* (L0).
        """
        if level == "events":
            events_file = self._events_dir / f"{date_str}.md"
            if events_file.exists():
                return events_file.read_text(encoding="utf-8")

        raw_file = self._raw_dir / f"{date_str}.md"
        if raw_file.exists():
            return raw_file.read_text(encoding="utf-8")
        return None

    def search_keyword(
        self,
        keyword: str,
        days: int = 7,
        max_results: int = 10,
    ) -> list[MemorySearchResult]:
        """Search recent files for *keyword* (case-insensitive)."""
        results: list[MemorySearchResult] = []
        today = datetime.now(tz=UTC)

        for i in range(days):
            date = today - timedelta(days=i)
            date_str = date.strftime("%Y-%m-%d")

            for subdir_name, level in (
                ("events", MemoryLevel.EVENT),
                ("raw", MemoryLevel.RAW),
            ):
                file_path = self._memory_dir / subdir_name / f"{date_str}.md"
                if not file_path.exists():
                    continue

                content = file_path.read_text(encoding="utf-8")
                if keyword.lower() not in content.lower():
                    continue

                snippets = self._extract_matching_sections(content, keyword)
                for snippet in snippets:
                    results.append(
                        MemorySearchResult(
                            level=level,
                            date=date_str,
                            snippet=snippet,
                            file_path=str(file_path),
                        )
                    )
                    if len(results) >= max_results:
                        return results
        return results

    def list_available_dates(self) -> list[str]:
        """Return all dates that have at least one memory file, newest first."""
        dates: set[str] = set()
        for subdir in (self._raw_dir, self._events_dir):
            if subdir.exists():
                for f in subdir.glob("*.md"):
                    dates.add(f.stem)
        return sorted(dates, reverse=True)

    def get_raw_content(self, date_str: str) -> str | None:
        """Read raw L0 file for a given date."""
        raw_file = self._raw_dir / f"{date_str}.md"
        if raw_file.exists():
            return raw_file.read_text(encoding="utf-8")
        return None

    def _extract_matching_sections(
        self,
        content: str,
        keyword: str,
        context_lines: int = 5,
    ) -> list[str]:
        """Extract text snippets containing *keyword* with surrounding context."""
        lines = content.split("\n")
        keyword_lower = keyword.lower()
        snippets: list[str] = []
        seen_ranges: list[tuple[int, int]] = []

        for i, line in enumerate(lines):
            if keyword_lower not in line.lower():
                continue
            start = max(0, i - context_lines)
            end = min(len(lines), i + context_lines + 1)

            if any(s <= i <= e for s, e in seen_ranges):
                continue
            seen_ranges.append((start, end))
            snippets.append("\n".join(lines[start:end]))

        return snippets
