"""Plan execution state models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class StepResult:
    step_id: str
    status: str
    on_fail: str
    completed_at: float
