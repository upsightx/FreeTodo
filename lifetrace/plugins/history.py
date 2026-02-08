"""Persistent plugin operation history storage."""

from __future__ import annotations

import json
import threading
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from lifetrace.util import base_paths
from lifetrace.util.settings import settings


@dataclass
class PluginTaskRecord:
    """One persisted plugin operation task."""

    task_id: str
    plugin_id: str
    action: str
    status: str
    created_at: str
    updated_at: str
    progress: int | None
    message: str
    error_code: str | None
    details: dict[str, Any]

    def to_payload(self) -> dict[str, Any]:
        """Serialize for API response."""
        return {
            "task_id": self.task_id,
            "plugin_id": self.plugin_id,
            "action": self.action,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "progress": self.progress,
            "message": self.message,
            "error_code": self.error_code,
            "details": self.details,
        }

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> PluginTaskRecord:
        """Build task from persisted payload."""
        raw_details = payload.get("details")
        details = raw_details if isinstance(raw_details, dict) else {}
        return cls(
            task_id=str(payload.get("task_id") or ""),
            plugin_id=str(payload.get("plugin_id") or ""),
            action=str(payload.get("action") or ""),
            status=str(payload.get("status") or "unknown"),
            created_at=str(payload.get("created_at") or ""),
            updated_at=str(payload.get("updated_at") or ""),
            progress=payload.get("progress") if isinstance(payload.get("progress"), int) else None,
            message=str(payload.get("message") or ""),
            error_code=str(payload.get("error_code")) if payload.get("error_code") else None,
            details=details,
        )


class PluginTaskHistoryStore:
    """JSON-backed task history for plugin operations."""

    def __init__(self, max_records: int = 300) -> None:
        self._max_records = max_records
        self._lock = threading.Lock()

    def create_task(
        self,
        *,
        plugin_id: str,
        action: str,
        message: str,
        status: str = "running",
        progress: int | None = 0,
        details: dict[str, Any] | None = None,
    ) -> PluginTaskRecord:
        """Create and persist a new plugin operation task."""
        now = datetime.now(tz=UTC).isoformat()
        task = PluginTaskRecord(
            task_id=uuid.uuid4().hex,
            plugin_id=plugin_id,
            action=action,
            status=status,
            created_at=now,
            updated_at=now,
            progress=progress,
            message=message,
            error_code=None,
            details=details or {},
        )
        with self._lock:
            tasks = self._load_tasks()
            tasks.append(task)
            self._save_tasks(self._trim(tasks))
        return task

    def update_task(
        self,
        *,
        task_id: str,
        status: str,
        message: str,
        progress: int | None = None,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> PluginTaskRecord | None:
        """Update one task and persist."""
        with self._lock:
            tasks = self._load_tasks()
            for task in tasks:
                if task.task_id != task_id:
                    continue
                task.status = status
                task.message = message
                task.progress = progress
                task.error_code = error_code
                task.updated_at = datetime.now(tz=UTC).isoformat()
                if details:
                    merged = dict(task.details)
                    merged.update(details)
                    task.details = merged
                self._save_tasks(self._trim(tasks))
                return task
            return None

    def list_tasks(
        self, *, plugin_id: str | None = None, limit: int = 50
    ) -> list[PluginTaskRecord]:
        """List task history in reverse-chronological order."""
        with self._lock:
            tasks = self._load_tasks()
        if plugin_id:
            tasks = [task for task in tasks if task.plugin_id == plugin_id]
        tasks = sorted(tasks, key=lambda item: item.updated_at, reverse=True)
        return tasks[: max(limit, 1)]

    def get_task(self, task_id: str) -> PluginTaskRecord | None:
        """Get one task by id."""
        with self._lock:
            tasks = self._load_tasks()
        for task in tasks:
            if task.task_id == task_id:
                return task
        return None

    def _history_file(self) -> Path:
        configured_file = str(settings.get("plugins.history_file", "plugins/history.json"))
        history_path = Path(configured_file)
        if not history_path.is_absolute():
            history_path = base_paths.get_user_data_dir() / history_path
        history_path.parent.mkdir(parents=True, exist_ok=True)
        return history_path

    def _load_tasks(self) -> list[PluginTaskRecord]:
        history_file = self._history_file()
        if not history_file.exists():
            return []
        try:
            payload = json.loads(history_file.read_text(encoding="utf-8"))
        except Exception:
            return []
        if not isinstance(payload, list):
            return []
        return [PluginTaskRecord.from_payload(item) for item in payload if isinstance(item, dict)]

    def _save_tasks(self, tasks: list[PluginTaskRecord]) -> None:
        history_file = self._history_file()
        payload = [task.to_payload() for task in tasks]
        history_file.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _trim(self, tasks: list[PluginTaskRecord]) -> list[PluginTaskRecord]:
        if len(tasks) <= self._max_records:
            return tasks
        return tasks[-self._max_records :]
