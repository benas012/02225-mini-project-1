from __future__ import annotations

import csv
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

from .dm_analysis import dm_wcrts
from .edf_analysis import edf_wcrts
from .models import TaskSet
from .simulator import run_simulation
from .utils import lcm, load_csv_task_set, parse_taskset_metadata


def analyze_task_set(task_set: TaskSet, runs: int, seed: int, horizon: int | None = None) -> list[dict[str, object]]:
    return []


def _discover_csv_files(input_root: Path, distributions: set[str] | None, util_levels: set[str] | None) -> dict[tuple[str, str], list[Path]]:
    grouped: dict[tuple[str, str], list[Path]] = defaultdict(list)
    for csv_file in input_root.rglob("*.csv"):
        rel = csv_file.relative_to(input_root)
        if csv_file.name == ".DS_Store" or len(rel.parts) < 2:
            continue
        distribution = rel.parts[0]
        util_folder = next((p for p in rel.parts if p.endswith("-util")), "")
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
    grouped = _discover_csv_files(input_root, set(distributions) if distributions else None, util_filter)

    selected = [p for _, files in sorted(grouped.items()) for p in (files[:samples_per_util] if samples_per_util else files)]
    summary_rows: list[dict[str, object]] = []
    for index, csv_file in enumerate(selected, start=1):
        print(f"[{index}/{len(selected)}] Processing {csv_file.relative_to(input_root)}", file=sys.stderr)
        metadata = parse_taskset_metadata(csv_file, input_root)
        common = {"taskset_name": "", "source_file": str(csv_file), **metadata, "warnings": "", "error_message": ""}
        try:
            task_set = load_csv_task_set(csv_file, input_root)
            tasks = task_set.tasks
            hyperperiod = lcm([t.T for t in tasks])
            dm = dm_wcrts(tasks)
            dm_sched = all(dm[t.id] <= t.D for t in tasks)
            dm_status = "ok"
            if hyperperiod <= max_hyperperiod:
                edf = edf_wcrts(tasks)
                edf_status = "ok"
                edf_sched = all(edf[t.id] <= t.D for t in tasks)
            else:
                edf = {}
                edf_status = "skipped_hyperperiod_too_large"
                edf_sched = ""
            effective_horizon = simulation_horizon if simulation_horizon is not None else min(hyperperiod, max_hyperperiod)
            dm_misses = edf_misses = 0
            simulation_status = "simulation_disabled" if runs == 0 else "ok"
            if runs > 0:
                for run in range(runs):
                    dm_misses += run_simulation(tasks, "DM", effective_horizon, random.Random(seed + run)).deadline_misses
                    edf_misses += run_simulation(tasks, "EDF", effective_horizon, random.Random(seed + run)).deadline_misses
            warnings = []
            if dm_sched and edf_sched is False:
                warnings.append("edf_worse_than_dm_check_failed")
            if dm_sched and dm_misses > 0:
                warnings.append("dm_sim_miss_despite_analytical_schedulable")
            if edf_sched is True and edf_misses > 0:
                warnings.append("edf_sim_miss_despite_analytical_schedulable")
            summary_rows.append({**common, "taskset_name": task_set.name, "actual_utilization": task_set.utilization, "hyperperiod": hyperperiod, "number_of_tasks": len(tasks), "dm_schedulable": dm_sched, "edf_schedulable": edf_sched, "dm_deadline_misses_sim": dm_misses, "edf_deadline_misses_sim": edf_misses, "dm_status": dm_status, "edf_status": edf_status, "simulation_status": simulation_status, "status": "ok", "simulation_horizon_used": effective_horizon, "warnings": ";".join(warnings)})
        except Exception as exc:  # noqa: BLE001
            summary_rows.append({**common, "actual_utilization": "", "hyperperiod": "", "number_of_tasks": "", "dm_schedulable": "", "edf_schedulable": "", "dm_deadline_misses_sim": "", "edf_deadline_misses_sim": "", "dm_status": "failed_validation", "edf_status": "failed_validation", "simulation_status": "failed_validation", "status": "failed_validation", "simulation_horizon_used": "", "error_message": str(exc)})
    _write_csv(output_root / "taskset_summary.csv", summary_rows)
    _write_csv(output_root / "task_details.csv", [])


def diagnose_results(summary_path: str | Path, details_path: str | Path, output_path: str | Path) -> None:
    rows = list(csv.DictReader(Path(summary_path).open()))
    status = Counter(r.get("status", "") for r in rows)
    dist = Counter(r.get("distribution", "") for r in rows)
    util = Counter(r.get("target_utilization", "") for r in rows)
    errors = Counter(r.get("error_message", "") for r in rows if r.get("status") == "failed_validation")
    combos = Counter((r.get("dm_schedulable"), r.get("edf_schedulable")) for r in rows)
    suspicious = [r for r in rows if (r.get("dm_schedulable") == "True" and r.get("edf_schedulable") == "False") or (r.get("dm_schedulable") == "True" and int(r.get("dm_deadline_misses_sim") or 0) > 0) or (r.get("target_utilization") in ("", "None")) or (r.get("status") == "failed_validation")][:20]

    out = ["# Diagnostics Report", f"- total task sets: {len(rows)}", "## Count by status"]
    out += [f"- {k}: {v}" for k, v in status.items()]
    out += ["## Count by distribution"] + [f"- {k}: {v}" for k, v in dist.items()]
    out += ["## Count by target_utilization"] + [f"- {k}: {v}" for k, v in util.items()]
    out += ["## Validation failures by error"] + [f"- {k}: {v}" for k, v in errors.items()]
    out += ["## DM/EDF combination counts", f"- DM true EDF false: {combos.get(('True','False'),0)}", f"- EDF true DM false: {combos.get(('False','True'),0)}", f"- both true: {combos.get(('True','True'),0)}", f"- both false: {combos.get(('False','False'),0)}"]
    out += ["## Top 20 suspicious rows", "|source_file|status|dm|edf|dm_miss|edf_miss|target_utilization|error|", "|---|---|---|---|---|---|---|---|"]
    for r in suspicious:
        out.append(f"|{r.get('source_file','')}|{r.get('status','')}|{r.get('dm_schedulable','')}|{r.get('edf_schedulable','')}|{r.get('dm_deadline_misses_sim','')}|{r.get('edf_deadline_misses_sim','')}|{r.get('target_utilization','')}|{r.get('error_message','')}|")
    Path(output_path).write_text("\n".join(out) + "\n")


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        path.write_text("")
        return
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
