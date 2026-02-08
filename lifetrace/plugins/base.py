"""Base interfaces for backend plugin runtime."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import FastAPI

    from lifetrace.plugins.models import PluginState


class BackendPlugin(ABC):
    """Abstract backend plugin contract."""

    id: str
    name: str
    version: str
    source: str = "builtin"

    @abstractmethod
    def list_states(self) -> dict[str, PluginState]:
        """Return plugin states before registration."""

    @abstractmethod
    def register(self, app: FastAPI) -> list[str]:
        """Register plugin routes/services and return active plugin ids."""
