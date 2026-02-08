"""Data models for backend plugin runtime state."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class PluginKind(StrEnum):
    """Supported backend plugin kinds."""

    BACKEND = "backend"


class PluginStatus(StrEnum):
    """Plugin runtime status."""

    DISCOVERED = "discovered"
    ENABLED = "enabled"
    RUNNING = "running"
    DISABLED = "disabled"
    UNAVAILABLE = "unavailable"
    INSTALLED = "installed"


@dataclass
class PluginState:
    """Runtime state for one backend plugin."""

    id: str
    name: str
    version: str
    kind: PluginKind
    source: str
    enabled: bool
    installed: bool
    available: bool
    status: PluginStatus
    missing_deps: list[str] = field(default_factory=list)


@dataclass
class PluginSnapshot:
    """State snapshot returned by plugin manager."""

    module_states: dict[str, Any]
    plugin_states: dict[str, PluginState]
