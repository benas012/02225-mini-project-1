from __future__ import annotations

import math

from .models import Task


def edf_wcrt(task: Task, all_tasks: tuple[Task, ...], limit: int = 10_000) -> int:
    """Conservative EDF response-time upper bound using all-task interference."""
    response = task.C
    others = tuple(t for t in all_tasks if t.id != task.id)
    while True:
        interference = sum(math.ceil(response / other.T) * other.C for other in others)
        next_response = task.C + interference
        if next_response == response:
            return next_response
        if next_response > limit:
            return next_response
        response = next_response


def edf_wcrts(tasks: tuple[Task, ...]) -> dict[str, int]:
    return {task.id: edf_wcrt(task, tasks) for task in tasks}
