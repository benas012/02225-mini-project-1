from __future__ import annotations

import csv
import random
from collections import defaultdict
from pathlib import Path

from .dm_analysis import dm_wcrts
from .edf_analysis import edf_wcrts
from .models import TaskSet
from .simulator import run_simulation
from .utils import lcm, load_csv_task_set, parse_taskset_metadata


def analyze_task_set(task_set: TaskSet, runs: int, seed: int, horizon: int | None = None) -> list[dict[str, object]]:
    tasks = task_set.tasks
    dm = dm_wcrts(tasks)
    edf = edf_wcrts(tasks)

    if horizon is None:
        horizon = lcm([task.T for task in tasks])

    dm_sim_max = defaultdict(int)
    edf_sim_max = defaultdict(int)
    dm_misses = dm_preemptions = 0
    edf_misses = edf_preemptions = 0

    for run in range(runs):
        dm_rng = random.Random(seed + run)
        edf_rng = random.Random(seed + run)
        dm_stats = run_simulation(tasks, "DM", horizon, dm_rng)
        edf_stats = run_simulation(tasks, "EDF", horizon, edf_rng)
        for task in tasks:
            dm_sim_max[task.id] = max(dm_sim_max[task.id], dm_stats.max_response[task.id])
            edf_sim_max[task.id] = max(edf_sim_max[task.id], edf_stats.max_response[task.id])
        dm_misses += dm_stats.deadline_misses
        dm_preemptions += dm_stats.preemptions
        edf_misses += edf_stats.deadline_misses
        edf_preemptions += edf_stats.preemptions

    rows: list[dict[str, object]] = []
    for task in tasks:
        rows.append(
            {
                "task_id": task.id,
                "C": task.C,
                "BCET": task.BCET,
                "D": task.D,
                "T": task.T,
                "U_i": round(task.utilization, 5),
                "DM_WCRT": dm[task.id],
                "DM_schedulable": dm[task.id] <= task.D,
                "EDF_WCRT": edf[task.id],
                "EDF_schedulable": edf[task.id] <= task.D,
                "DM_max_sim": dm_sim_max[task.id],
                "EDF_max_sim": edf_sim_max[task.id],
                "analytical_minus_sim_gap": max(dm[task.id], edf[task.id]) - max(dm_sim_max[task.id], edf_sim_max[task.id]),
                "deadline_misses": {"DM": dm_misses, "EDF": edf_misses},
                "preemptions": {"DM": dm_preemptions, "EDF": edf_preemptions},
            }
        )
    return rows


def analyze_csv_folder(input_path: str | Path, output_path: str | Path, runs: int, seed: int, max_hyperperiod: int) -> None:
    input_root = Path(input_path)
    output_root = Path(output_path)
    output_root.mkdir(parents=True, exist_ok=True)

    summary_rows: list[dict[str, object]] = []
    detail_rows: list[dict[str, object]] = []

    for csv_file in sorted(input_root.rglob("*.csv")):
        if csv_file.name == ".DS_Store":
            continue
        metadata = parse_taskset_metadata(csv_file, input_root)
        common = {
            "taskset_name": "",
            "source_file": str(csv_file),
            **metadata,
        }
        try:
            task_set = load_csv_task_set(csv_file, input_root)
            tasks = task_set.tasks
            hyperperiod = lcm([task.T for task in tasks])
            if hyperperiod > max_hyperperiod:
                summary_rows.append(
                    {
                        **common,
                        "taskset_name": task_set.name,
                        "actual_utilization": task_set.utilization,
                        "hyperperiod": hyperperiod,
                        "number_of_tasks": len(tasks),
                        "number_of_jobs_in_hyperperiod": "",
                        "dm_schedulable": "",
                        "edf_schedulable": "",
                        "dm_max_wcrt": "",
                        "edf_max_wcrt": "",
                        "dm_max_sim_response_time": "",
                        "edf_max_sim_response_time": "",
                        "dm_deadline_misses_sim": "",
                        "edf_deadline_misses_sim": "",
                        "dm_preemptions_sim": "",
                        "edf_preemptions_sim": "",
                        "status": "skipped_hyperperiod_too_large",
                        "error_message": f"Hyperperiod {hyperperiod} exceeds max_hyperperiod {max_hyperperiod}",
                    }
                )
                continue

            dm = dm_wcrts(tasks)
            edf = edf_wcrts(tasks)
            dm_schedulable = all(dm[t.id] <= t.D for t in tasks)
            edf_schedulable = all(edf[t.id] <= t.D for t in tasks)
            jobs_in_hyperperiod = sum(hyperperiod // task.T for task in tasks)

            dm_max_sim_response = edf_max_sim_response = 0
            dm_misses = edf_misses = dm_preemptions = edf_preemptions = 0
            dm_sim_max_by_task = {t.id: 0 for t in tasks}
            edf_sim_max_by_task = {t.id: 0 for t in tasks}

            if runs > 0:
                for run in range(runs):
                    dm_stats = run_simulation(tasks, "DM", hyperperiod, random.Random(seed + run))
                    edf_stats = run_simulation(tasks, "EDF", hyperperiod, random.Random(seed + run))
                    dm_misses += dm_stats.deadline_misses
                    edf_misses += edf_stats.deadline_misses
                    dm_preemptions += dm_stats.preemptions
                    edf_preemptions += edf_stats.preemptions
                    for t in tasks:
                        dm_sim_max_by_task[t.id] = max(dm_sim_max_by_task[t.id], dm_stats.max_response[t.id])
                        edf_sim_max_by_task[t.id] = max(edf_sim_max_by_task[t.id], edf_stats.max_response[t.id])
                dm_max_sim_response = max(dm_sim_max_by_task.values())
                edf_max_sim_response = max(edf_sim_max_by_task.values())

            summary_rows.append(
                {
                    **common,
                    "taskset_name": task_set.name,
                    "actual_utilization": task_set.utilization,
                    "hyperperiod": hyperperiod,
                    "number_of_tasks": len(tasks),
                    "number_of_jobs_in_hyperperiod": jobs_in_hyperperiod,
                    "dm_schedulable": dm_schedulable,
                    "edf_schedulable": edf_schedulable,
                    "dm_max_wcrt": max(dm.values()),
                    "edf_max_wcrt": max(edf.values()),
                    "dm_max_sim_response_time": dm_max_sim_response,
                    "edf_max_sim_response_time": edf_max_sim_response,
                    "dm_deadline_misses_sim": dm_misses,
                    "edf_deadline_misses_sim": edf_misses,
                    "dm_preemptions_sim": dm_preemptions,
                    "edf_preemptions_sim": edf_preemptions,
                    "status": "ok",
                    "error_message": "",
                }
            )

            for t in tasks:
                dm_sim = dm_sim_max_by_task[t.id]
                edf_sim = edf_sim_max_by_task[t.id]
                detail_rows.append(
                    {
                        "taskset_name": task_set.name,
                        "source_file": str(csv_file),
                        "task_id": t.id,
                        "BCET": t.BCET,
                        "WCET": t.C,
                        "Period": t.T,
                        "Deadline": t.D,
                        "utilization": t.utilization,
                        "DM_WCRT": dm[t.id],
                        "DM_schedulable": dm[t.id] <= t.D,
                        "EDF_WCRT": edf[t.id],
                        "EDF_schedulable": edf[t.id] <= t.D,
                        "DM_max_sim_response_time": dm_sim,
                        "EDF_max_sim_response_time": edf_sim,
                        "DM_analytical_minus_sim_gap": dm[t.id] - dm_sim,
                        "EDF_analytical_minus_sim_gap": edf[t.id] - edf_sim,
                    }
                )
        except Exception as exc:  # noqa: BLE001
            summary_rows.append(
                {
                    **common,
                    "actual_utilization": "",
                    "hyperperiod": "",
                    "number_of_tasks": "",
                    "number_of_jobs_in_hyperperiod": "",
                    "dm_schedulable": "",
                    "edf_schedulable": "",
                    "dm_max_wcrt": "",
                    "edf_max_wcrt": "",
                    "dm_max_sim_response_time": "",
                    "edf_max_sim_response_time": "",
                    "dm_deadline_misses_sim": "",
                    "edf_deadline_misses_sim": "",
                    "dm_preemptions_sim": "",
                    "edf_preemptions_sim": "",
                    "status": "failed",
                    "error_message": str(exc),
                }
            )

    _write_csv(output_root / "taskset_summary.csv", summary_rows)
    _write_csv(output_root / "task_details.csv", detail_rows)


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        path.write_text("")
        return
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
