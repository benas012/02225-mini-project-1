from __future__ import annotations

import csv
import random
import sys
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
        edf_misses += edf_stats.deadline_misses
        dm_preemptions += dm_stats.preemptions
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


def _discover_csv_files(input_root: Path, distributions: set[str] | None, util_levels: set[str] | None) -> dict[tuple[str, str], list[Path]]:
    grouped: dict[tuple[str, str], list[Path]] = defaultdict(list)
    for csv_file in input_root.rglob("*.csv"):
        rel = csv_file.relative_to(input_root)
        if csv_file.name == ".DS_Store" or len(rel.parts) < 5:
            continue
        distribution = rel.parts[0]
        util_folder = rel.parts[4]
        if distributions and distribution not in distributions:
            continue
        if util_levels and util_folder not in util_levels:
            continue
        grouped[(distribution, util_folder)].append(csv_file)

    for key in grouped:
        grouped[key] = sorted(grouped[key], key=lambda p: str(p.relative_to(input_root)))
    return grouped


def analyze_csv_folder(input_path: str | Path, output_path: str | Path, runs: int, seed: int, max_hyperperiod: int, verbose: bool = False, samples_per_util: int | None = None, util_levels: list[str] | None = None, distributions: list[str] | None = None, simulation_horizon: int | None = None) -> None:
    input_root = Path(input_path)
    output_root = Path(output_path)
    output_root.mkdir(parents=True, exist_ok=True)

    util_filter = {f"{u}-util" if not str(u).endswith("-util") else str(u) for u in util_levels} if util_levels else None
    distribution_filter = set(distributions) if distributions else None
    grouped = _discover_csv_files(input_root, distribution_filter, util_filter)

    selected: list[tuple[Path, bool, int]] = []
    for _, files in sorted(grouped.items()):
        if samples_per_util is None:
            chosen = files
        else:
            chosen = files[:samples_per_util]
        for idx, path in enumerate(chosen):
            selected.append((path, True, idx))

    summary_rows: list[dict[str, object]] = []
    detail_rows: list[dict[str, object]] = []

    for index, (csv_file, sampled, sample_index) in enumerate(selected, start=1):
        print(f"[{index}/{len(selected)}] Processing {csv_file.relative_to(input_root)}", file=sys.stderr)
        metadata = parse_taskset_metadata(csv_file, input_root)
        common = {
            "taskset_name": "",
            "source_file": str(csv_file),
            **metadata,
            "sampled": sampled,
            "sample_index_within_group": sample_index,
            "skipped_reason": "",
        }
        try:
            task_set = load_csv_task_set(csv_file, input_root)
            tasks = task_set.tasks
            hyperperiod = lcm([task.T for task in tasks])
            dm = dm_wcrts(tasks)
            dm_schedulable = all(dm[t.id] <= t.D for t in tasks)
            dm_status = "ok"

            edf: dict[str, int] = {}
            edf_status = "ok"
            if hyperperiod > max_hyperperiod:
                print(f"Skipping EDF analytical WCRT because hyperperiod {hyperperiod} > max {max_hyperperiod}", file=sys.stderr)
                edf_status = "skipped_hyperperiod_too_large"
            else:
                edf = edf_wcrts(tasks)

            jobs_in_hyperperiod = sum(hyperperiod // task.T for task in tasks)
            effective_horizon = simulation_horizon if simulation_horizon is not None else min(hyperperiod, max_hyperperiod)

            dm_max_sim_response = edf_max_sim_response = 0
            dm_misses = edf_misses = dm_preemptions = edf_preemptions = 0
            dm_sim_max_by_task = {t.id: 0 for t in tasks}
            edf_sim_max_by_task = {t.id: 0 for t in tasks}
            simulation_status = "ok"
            if runs == 0:
                simulation_status = "simulation_disabled"
            else:
                for run in range(runs):
                    dm_stats = run_simulation(tasks, "DM", effective_horizon, random.Random(seed + run))
                    edf_stats = run_simulation(tasks, "EDF", effective_horizon, random.Random(seed + run))
                    dm_misses += dm_stats.deadline_misses
                    edf_misses += edf_stats.deadline_misses
                    dm_preemptions += dm_stats.preemptions
                    edf_preemptions += edf_stats.preemptions
                    for t in tasks:
                        dm_sim_max_by_task[t.id] = max(dm_sim_max_by_task[t.id], dm_stats.max_response[t.id])
                        edf_sim_max_by_task[t.id] = max(edf_sim_max_by_task[t.id], edf_stats.max_response[t.id])
                dm_max_sim_response = max(dm_sim_max_by_task.values())
                edf_max_sim_response = max(edf_sim_max_by_task.values())

            edf_schedulable = all(edf[t.id] <= t.D for t in tasks) if edf else ""
            status = "ok" if (dm_status == "ok" or edf_status == "ok" or simulation_status == "ok") else "skipped_hyperperiod_too_large"
            skipped_reason = "skipped_hyperperiod_too_large" if edf_status == "skipped_hyperperiod_too_large" else ""
            summary_rows.append({**common, "taskset_name": task_set.name, "actual_utilization": task_set.utilization, "hyperperiod": hyperperiod, "number_of_tasks": len(tasks), "number_of_jobs_in_hyperperiod": jobs_in_hyperperiod, "dm_schedulable": dm_schedulable, "edf_schedulable": edf_schedulable, "dm_max_wcrt": max(dm.values()), "edf_max_wcrt": max(edf.values()) if edf else "", "dm_max_sim_response_time": dm_max_sim_response, "edf_max_sim_response_time": edf_max_sim_response, "dm_deadline_misses_sim": dm_misses, "edf_deadline_misses_sim": edf_misses, "dm_preemptions_sim": dm_preemptions, "edf_preemptions_sim": edf_preemptions, "dm_status": dm_status, "edf_status": edf_status, "simulation_status": simulation_status, "status": status, "skipped_reason": skipped_reason, "error_message": "", "simulation_horizon_used": effective_horizon})
        except Exception as exc:  # noqa: BLE001
            summary_rows.append({**common, "actual_utilization": "", "hyperperiod": "", "number_of_tasks": "", "number_of_jobs_in_hyperperiod": "", "dm_schedulable": "", "edf_schedulable": "", "dm_max_wcrt": "", "edf_max_wcrt": "", "dm_max_sim_response_time": "", "edf_max_sim_response_time": "", "dm_deadline_misses_sim": "", "edf_deadline_misses_sim": "", "dm_preemptions_sim": "", "edf_preemptions_sim": "", "dm_status": "failed_validation", "edf_status": "failed_validation", "simulation_status": "failed_validation", "status": "failed_validation", "skipped_reason": "", "error_message": str(exc), "simulation_horizon_used": ""})

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
