from __future__ import annotations

import math

from .models import Task


def dm_priority_order(tasks: tuple[Task, ...]) -> tuple[Task, ...]:
    return tuple(sorted(tasks, key=lambda task: (task.D, task.T, task.id)))


def dm_wcrt(task: Task, higher_priority_tasks: tuple[Task, ...], limit: int | None = None) -> int:
    response = task.C
    while True:
        interference = sum(math.ceil(response / hp.T) * hp.C for hp in higher_priority_tasks)
        next_response = task.C + interference
        if next_response == response:
            return next_response
        if limit is not None and next_response > limit:
            return next_response
        response = next_response


def dm_wcrts(tasks: tuple[Task, ...]) -> dict[str, int]:
    ordered = dm_priority_order(tasks)
    result: dict[str, int] = {}
    for index, task in enumerate(ordered):
        result[task.id] = dm_wcrt(task, ordered[:index], limit=task.D)
    return result
