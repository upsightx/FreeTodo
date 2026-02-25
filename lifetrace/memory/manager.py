"""Memory Manager — lifecycle management for the memory module."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from lifetrace.memory.compressor import MemoryCompressor
from lifetrace.memory.reader import MemoryReader
from lifetrace.memory.writer import MemoryWriter
from lifetrace.util.base_paths import get_user_data_dir
from lifetrace.util.logging_config import get_logger

if TYPE_CHECKING:
    from lifetrace.perception.stream import PerceptionStream

logger = get_logger()


class MemoryManager:
    """Manage Memory module lifecycle: writer + compressor + reader."""

    def __init__(self, config: dict | None = None):
        config = dict(config or {})
        memory_base = config.get("memory_dir")
        if memory_base:
            self._memory_dir = Path(memory_base)
        else:
            self._memory_dir = get_user_data_dir() / "memory"

        self._memory_dir.mkdir(parents=True, exist_ok=True)

        self.writer = MemoryWriter(self._memory_dir)
        self.reader = MemoryReader(self._memory_dir)
        self.compressor: MemoryCompressor | None = None

        self._config = config
        self._subscribed = False

        if config.get("auto_compress", True):
            self._init_compressor()

    def _init_compressor(self) -> None:
        try:
            from lifetrace.llm.llm_client import LLMClient  # noqa: PLC0415

            llm = LLMClient()
            if llm.is_available():
                self.compressor = MemoryCompressor(self._memory_dir, llm)
                logger.info("MemoryCompressor initialized")
            else:
                logger.warning("LLM not available — MemoryCompressor disabled")
        except Exception:
            logger.exception("Failed to initialize MemoryCompressor")

    async def start(self, perception_stream: PerceptionStream | None = None) -> None:
        """Start the memory module, optionally subscribing to perception stream."""
        if perception_stream and not self._subscribed:
            perception_stream.subscribe(self.writer.on_event)
            self._subscribed = True
            logger.info("MemoryWriter subscribed to PerceptionStream")

    async def stop(self, perception_stream: PerceptionStream | None = None) -> None:
        """Stop the memory module, unsubscribing from perception stream."""
        if perception_stream and self._subscribed:
            perception_stream.unsubscribe(self.writer.on_event)
            self._subscribed = False
            logger.info("MemoryWriter unsubscribed from PerceptionStream")

    def get_status(self) -> dict:
        return {
            "memory_dir": str(self._memory_dir),
            "subscribed": self._subscribed,
            "compressor_available": self.compressor is not None,
            "writer": self.writer.get_stats(),
            "available_dates": self.reader.list_available_dates()[:10],
        }

    @property
    def memory_dir(self) -> Path:
        return self._memory_dir


# ---------------------------------------------------------------------------
# Singleton access pattern (mirrors perception/manager.py)
# ---------------------------------------------------------------------------

_manager: MemoryManager | None = None


async def init_memory_manager(
    config: dict | None = None,
    perception_stream: PerceptionStream | None = None,
) -> MemoryManager:
    global _manager  # noqa: PLW0603
    if _manager is None:
        _manager = MemoryManager(config=config)
        await _manager.start(perception_stream)
    return _manager


async def shutdown_memory_manager() -> None:
    global _manager  # noqa: PLW0603
    if _manager is None:
        return
    await _manager.stop()
    _manager = None


def get_memory_manager() -> MemoryManager:
    if _manager is None:
        raise RuntimeError(
            "MemoryManager not initialized. Call init_memory_manager() at startup."
        )
    return _manager


def try_get_memory_manager() -> MemoryManager | None:
    return _manager
