"""Plan graph helpers."""

from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lifetrace.schemas.agent_plan import PlanStep


def topo_levels(steps: list[PlanStep]) -> list[list[PlanStep]]:
    """Return plan steps grouped by dependency levels."""
    step_map = {step.step_id: step for step in steps}
    indegree = {step.step_id: 0 for step in steps}
    graph: dict[str, list[str]] = {}

    for step in steps:
        for dep in step.depends_on:
            graph.setdefault(dep, []).append(step.step_id)
            indegree[step.step_id] += 1

    queue = deque([sid for sid, deg in indegree.items() if deg == 0])
    levels: list[list[PlanStep]] = []
    visited = 0
    while queue:
        level_size = len(queue)
        level_steps: list[PlanStep] = []
        for _ in range(level_size):
            sid = queue.popleft()
            visited += 1
            level_steps.append(step_map[sid])
            for neighbor in graph.get(sid, []):
                indegree[neighbor] -= 1
                if indegree[neighbor] == 0:
                    queue.append(neighbor)
        levels.append(level_steps)

    if visited != len(steps):
        raise ValueError("cycle detected in plan")
    return levels
