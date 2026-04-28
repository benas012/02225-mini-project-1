from __future__ import annotations

import json
import math
from pathlib import Path

from .models import Task, TaskSet


def lcm(values: list[int]) -> int:
    result = 1
    for value in values:
        result = math.lcm(result, value)
    return result


def load_task_sets(path: str | Path) -> list[TaskSet]:
    data = json.loads(Path(path).read_text())
    task_sets: list[TaskSet] = []
    for raw_set in data["task_sets"]:
        tasks = tuple(Task(**task) for task in raw_set["tasks"])
        task_sets.append(TaskSet(name=raw_set["name"], tasks=tasks))
    return task_sets
