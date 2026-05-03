from __future__ import annotations

import csv
import json
import math
import re
from pathlib import Path

from .models import Task, TaskSet

_REQUIRED_COLUMNS = {"TaskID", "Jitter", "BCET", "WCET", "Period", "Deadline", "PE"}


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


def parse_taskset_metadata(csv_file: str | Path, input_root: str | Path) -> dict[str, object]:
    csv_path = Path(csv_file)
    root = Path(input_root)
    relative = csv_path.relative_to(root)
    parts = relative.parts

    distribution = parts[0] if len(parts) > 0 else ""
    core_count = parts[1] if len(parts) > 1 else ""
    task_count = parts[2] if len(parts) > 2 else ""
    jitter_group = parts[3] if len(parts) > 3 else ""
    util_group = parts[4] if len(parts) > 4 else ""

    target_utilization = None
    match = re.match(r"^(\d+(?:\.\d+)?)-util$", util_group)
    if match:
        target_utilization = float(match.group(1))

    return {
        "distribution": distribution,
        "core_count": core_count,
        "task_count": task_count,
        "jitter_group": jitter_group,
        "target_utilization": target_utilization,
        "csv_file_name": csv_path.name,
    }


def load_csv_task_set(csv_file: str | Path, input_root: str | Path) -> TaskSet:
    csv_path = Path(csv_file)
    with csv_path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        columns = set(reader.fieldnames or [])
        missing = sorted(_REQUIRED_COLUMNS - columns)
        if missing:
            raise ValueError(f"Missing required columns: {', '.join(missing)}")

        tasks: list[Task] = []
        for row_num, row in enumerate(reader, start=2):
            try:
                jitter = int(row["Jitter"])
                bcet = int(row["BCET"])
                wcet = int(row["WCET"])
                period = int(row["Period"])
                deadline = int(row["Deadline"])
                pe = int(row["PE"])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Row {row_num}: non-integer field value") from exc

            if wcet <= 0:
                raise ValueError(f"Row {row_num}: WCET must be > 0")
            if period <= 0:
                raise ValueError(f"Row {row_num}: Period must be > 0")
            if deadline <= 0:
                raise ValueError(f"Row {row_num}: Deadline must be > 0")
            if bcet < 0:
                raise ValueError(f"Row {row_num}: BCET must be >= 0")
            if bcet > wcet:
                raise ValueError(f"Row {row_num}: BCET must be <= WCET")
            if not (wcet <= deadline <= period):
                raise ValueError(f"Row {row_num}: expected WCET <= Deadline <= Period")
            if jitter != 0:
                raise ValueError(f"Row {row_num}: Jitter must be 0 for synchronous model")
            if pe != 0:
                raise ValueError(f"Row {row_num}: PE must be 0 for single-core model")

            tasks.append(Task(id=row["TaskID"], C=wcet, BCET=bcet, D=deadline, T=period))

    if not tasks:
        raise ValueError("CSV file contains no tasks")

    rel_no_suffix = Path(csv_path).relative_to(Path(input_root)).with_suffix("")
    return TaskSet(name=str(rel_no_suffix), tasks=tuple(tasks))
