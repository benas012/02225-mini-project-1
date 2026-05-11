from __future__ import annotations

import csv
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


def parse_taskset_metadata(csv_file: str | Path, input_root: str | Path) -> dict[str, object]:
    csv_path = Path(csv_file)
    root = Path(input_root)
    relative = csv_path.relative_to(root)
    parts = relative.parts
    target_utilization = None
    for part in parts:
        match = re.match(r"^([0-9]+(?:\.[0-9]+)?)-util$", part)
        if match:
            target_utilization = float(match.group(1))
            break
    core_count = next((p for p in parts if p.endswith("-core")), "")
    task_count = next((p for p in parts if p.endswith("-task")), "")
    jitter_group = next((p for p in parts if p.endswith("-jitter")), "")
    period_distribution = ""
    if len(parts) > 1 and not parts[1].endswith(("-core", "-task", "-jitter", "-util")):
        period_distribution = parts[1]

    return {
        "distribution": parts[0] if len(parts) > 0 else "",
        "period_distribution": period_distribution,
        "core_count": core_count,
        "task_count": task_count,
        "jitter_group": jitter_group,
        "target_utilization": target_utilization,
        "csv_file_name": csv_path.name,
    }


def _parse_numeric(row: dict[str, str], column: str, row_num: int, allow_float: bool = False) -> int | float:
    raw = row[column]
    try:
        value = float(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Row {row_num}: non-numeric value for {column}: {raw}") from exc
    if not math.isfinite(value):
        raise ValueError(f"Row {row_num}: non-finite value for {column}: {raw}")
    if allow_float:
        return value
    if value.is_integer():
        return int(value)
    raise ValueError(f"non-integer time value not supported: column {column} row {row_num} value {raw}")


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
            jitter = _parse_numeric(row, "Jitter", row_num)
            bcet = _parse_numeric(row, "BCET", row_num)
            wcet = _parse_numeric(row, "WCET", row_num)
            period = _parse_numeric(row, "Period", row_num)
            deadline = _parse_numeric(row, "Deadline", row_num)
            pe = _parse_numeric(row, "PE", row_num)

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
            if wcet > deadline:
                raise ValueError(f"Row {row_num}: WCET must be <= Deadline")
            if deadline > period:
                raise ValueError(f"Row {row_num}: Deadline must be <= Period")
            if jitter != 0:
                raise ValueError(f"Row {row_num}: Jitter must be 0 for synchronous model")
            if pe != 0:
                raise ValueError(f"Row {row_num}: PE must be 0 for single-core model")

            tasks.append(Task(id=row["TaskID"], C=wcet, BCET=bcet, D=deadline, T=period))

    if not tasks:
        raise ValueError("CSV file contains no tasks")

    rel_no_suffix = Path(csv_path).relative_to(Path(input_root)).with_suffix("")
    return TaskSet(name=str(rel_no_suffix), tasks=tuple(tasks))
