"""Base interfaces for backend plugin runtime."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

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

    def list_third_party_states(self) -> Mapping[str, PluginState]:
        """Return third-party plugin states managed by this plugin source."""
        return {}

    @abstractmethod
    def register(self, app: FastAPI) -> list[str]:
        """Register plugin routes/services and return active plugin ids."""
