from __future__ import annotations

import csv
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

from .dm_analysis import dm_wcrts
from .edf_analysis import edf_analyze
from .models import Task, TaskSet
from .simulator import run_simulation
from .utils import lcm, load_csv_task_set, parse_taskset_metadata


def analyze_task_set(task_set: TaskSet, runs: int, seed: int, horizon: int | None = None) -> list[dict[str, object]]:
    tasks = task_set.tasks
    hyperperiod = lcm([task.T for task in tasks])
    effective_horizon = horizon if horizon is not None else hyperperiod
    dm = dm_wcrts(tasks)
    edf_res = edf_analyze(tasks)
    edf = edf_res["wcrt"]
    sim = _run_simulations(tasks, runs, seed, effective_horizon)

    rows: list[dict[str, object]] = []
    for task in tasks:
        rows.append(
            {
                "task_id": task.id,
                "C": task.C,
                "BCET": task.BCET,
                "D": task.D,
                "T": task.T,
                "U_i": task.utilization,
                "DM_WCRT": dm[task.id],
                "DM_schedulable": dm[task.id] <= task.D,
                "EDF_WCRT": edf[task.id],
                "EDF_schedulable": edf[task.id] <= task.D,
                "DM_max_sim": sim["DM"]["max_response"][task.id],
                "EDF_max_sim": sim["EDF"]["max_response"][task.id],
                "DM_analytical_minus_sim_gap": dm[task.id] - sim["DM"]["max_response"][task.id],
                "EDF_analytical_minus_sim_gap": edf[task.id] - sim["EDF"]["max_response"][task.id],
                "DM_deadline_misses": sim["DM"]["deadline_misses_by_task"][task.id],
                "EDF_deadline_misses": sim["EDF"]["deadline_misses_by_task"][task.id],
                "DM_preemptions": sim["DM"]["preemptions"],
                "EDF_preemptions": sim["EDF"]["preemptions"],
                "simulation_horizon": effective_horizon,
                "simulation_runs": runs,
            }
        )
    return rows


def _run_simulations(tasks: tuple[Task, ...], runs: int, seed: int, horizon: int) -> dict[str, dict[str, object]]:
    result = {
        algorithm: {
            "max_response": {task.id: 0.0 for task in tasks},
            "deadline_misses": 0,
            "deadline_misses_by_task": {task.id: 0 for task in tasks},
            "preemptions": 0,
            "incomplete_jobs_ignored": 0,
        }
        for algorithm in ("DM", "EDF")
    }
    for run in range(runs):
        for algorithm in ("DM", "EDF"):
            stats = run_simulation(tasks, algorithm, horizon, random.Random(seed + run), execution_policy="random")
            result[algorithm]["deadline_misses"] += stats.deadline_misses
            result[algorithm]["preemptions"] += stats.preemptions
            result[algorithm]["incomplete_jobs_ignored"] += stats.incomplete_jobs_ignored
            for task in tasks:
                result[algorithm]["max_response"][task.id] = max(result[algorithm]["max_response"][task.id], stats.max_response[task.id])
                result[algorithm]["deadline_misses_by_task"][task.id] += stats.deadline_misses_by_task[task.id]
    return result


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
    detail_rows: list[dict[str, object]] = []
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
                edf_res = edf_analyze(tasks)
                edf = edf_res["wcrt"]
                edf_status = "ok"
                edf_sched = edf_res["schedulable"]
            else:
                edf = {}
                edf_status = "skipped_hyperperiod_too_large"
                edf_sched = ""
            effective_horizon = simulation_horizon if simulation_horizon is not None else min(hyperperiod, max_hyperperiod)
            simulation_status = "simulation_disabled" if runs == 0 else "ok"
            sim = _run_simulations(tasks, runs, seed, effective_horizon)
            dm_misses = sim["DM"]["deadline_misses"]
            edf_misses = sim["EDF"]["deadline_misses"]
            dm_max_sim_response_time = max(sim["DM"]["max_response"].values(), default=0.0)
            edf_max_sim_response_time = max(sim["EDF"]["max_response"].values(), default=0.0)
            dm_preemptions = sim["DM"]["preemptions"]
            edf_preemptions = sim["EDF"]["preemptions"]
            incomplete = sim["DM"]["incomplete_jobs_ignored"] > 0 or sim["EDF"]["incomplete_jobs_ignored"] > 0
            warnings = []
            if dm_sched and edf_sched is False:
                warnings.append("edf_worse_than_dm_check_failed")
            if dm_sched and dm_misses > 0:
                warnings.append("dm_sim_miss_despite_analytical_schedulable")
            if edf_sched is True and edf_misses > 0:
                warnings.append("edf_sim_miss_despite_analytical_schedulable")
            if hyperperiod > max_hyperperiod:
                warnings.append("hyperperiod_too_large_edf_skipped")
            if runs>0 and incomplete:
                warnings.append("simulation_incomplete_jobs_ignored")
            summary_rows.append({**common, "taskset_name": task_set.name, "actual_utilization": task_set.utilization, "hyperperiod": hyperperiod, "number_of_tasks": len(tasks), "number_of_jobs_in_hyperperiod": sum(hyperperiod // t.T for t in tasks), "dm_schedulable": dm_sched, "edf_schedulable": edf_sched, "dm_deadline_misses_sim": dm_misses, "edf_deadline_misses_sim": edf_misses, "dm_status": dm_status, "edf_status": edf_status, "simulation_status": simulation_status, "dm_max_wcrt": max(dm.values(), default=0), "edf_max_wcrt": max(edf.values(), default=0) if edf else "", "dm_max_sim_response_time": dm_max_sim_response_time, "edf_max_sim_response_time": edf_max_sim_response_time, "dm_preemptions_sim": dm_preemptions, "edf_preemptions_sim": edf_preemptions, "status": "ok", "simulation_horizon_used": effective_horizon, "warnings": ";".join(warnings)})
            for task in tasks:
                detail_rows.append(
                    {
                        **common,
                        "taskset_name": task_set.name,
                        "task_id": task.id,
                        "C": task.C,
                        "BCET": task.BCET,
                        "D": task.D,
                        "T": task.T,
                        "U_i": task.utilization,
                        "DM_WCRT": dm[task.id],
                        "DM_schedulable": dm[task.id] <= task.D,
                        "EDF_WCRT": edf.get(task.id, ""),
                        "EDF_schedulable": (edf[task.id] <= task.D) if edf else "",
                        "DM_max_sim": sim["DM"]["max_response"][task.id],
                        "EDF_max_sim": sim["EDF"]["max_response"][task.id],
                        "DM_analytical_minus_sim_gap": dm[task.id] - sim["DM"]["max_response"][task.id],
                        "EDF_analytical_minus_sim_gap": (edf[task.id] - sim["EDF"]["max_response"][task.id]) if edf else "",
                        "DM_deadline_misses": sim["DM"]["deadline_misses_by_task"][task.id],
                        "EDF_deadline_misses": sim["EDF"]["deadline_misses_by_task"][task.id],
                        "DM_preemptions": dm_preemptions,
                        "EDF_preemptions": edf_preemptions,
                        "simulation_horizon": effective_horizon,
                        "simulation_runs": runs,
                        "status": "ok",
                        "warnings": ";".join(warnings),
                    }
                )
        except Exception as exc:  # noqa: BLE001
            summary_rows.append({**common, "actual_utilization": "", "hyperperiod": "", "number_of_tasks": "", "number_of_jobs_in_hyperperiod": "", "dm_schedulable": "", "edf_schedulable": "", "dm_deadline_misses_sim": "", "edf_deadline_misses_sim": "", "dm_status": "failed_validation", "edf_status": "failed_validation", "simulation_status": "failed_validation", "dm_max_wcrt": "", "edf_max_wcrt": "", "dm_max_sim_response_time": "", "edf_max_sim_response_time": "", "dm_preemptions_sim": "", "edf_preemptions_sim": "", "status": "failed_validation", "simulation_horizon_used": "", "error_message": str(exc)})
    _write_csv(output_root / "taskset_summary.csv", summary_rows)
    _write_csv(output_root / "task_details.csv", detail_rows)


def diagnose_results(summary_path: str | Path, details_path: str | Path, output_path: str | Path) -> None:
    rows = list(csv.DictReader(Path(summary_path).open()))
    status = Counter(r.get("status", "") for r in rows)
    dist = Counter(r.get("distribution", "") for r in rows)
    util = Counter(r.get("target_utilization", "") for r in rows)
    errors = Counter(r.get("error_message", "") for r in rows if r.get("status") == "failed_validation")
    combos = Counter((r.get("dm_schedulable"), r.get("edf_schedulable")) for r in rows)
    warning_counts = Counter()
    for r in rows:
        for w in (r.get("warnings", "") or "").split(";"):
            if w:
                warning_counts[w] += 1
    dm_sched_count = sum(r.get("dm_schedulable") == "True" for r in rows)
    edf_sched_count = sum(r.get("edf_schedulable") == "True" for r in rows)
    sim_miss_despite_analytic = sum((r.get("dm_schedulable") == "True" and int(r.get("dm_deadline_misses_sim") or 0) > 0) or (r.get("edf_schedulable") == "True" and int(r.get("edf_deadline_misses_sim") or 0) > 0) for r in rows)
    missing_target = sum(r.get("target_utilization") in ("", "None") for r in rows)
    suspicious = [r for r in rows if (r.get("dm_schedulable") == "True" and r.get("edf_schedulable") == "False") or (r.get("dm_schedulable") == "True" and int(r.get("dm_deadline_misses_sim") or 0) > 0) or (r.get("target_utilization") in ("", "None")) or (r.get("status") == "failed_validation")][:20]

    out = ["# Diagnostics Report", f"- total task sets: {len(rows)}", "## Count by status"]
    out += [f"- {k}: {v}" for k, v in status.items()]
    out += ["## Count by distribution"] + [f"- {k}: {v}" for k, v in dist.items()]
    out += ["## Count by target_utilization"] + [f"- {k}: {v}" for k, v in util.items()]
    out += ["## Validation failures by error"] + [f"- {k}: {v}" for k, v in errors.items()]
    out += ["## Count by warning"] + [f"- {k}: {v}" for k, v in warning_counts.items()]
    out += ["## Schedulability summary", f"- DM schedulable count: {dm_sched_count}", f"- EDF schedulable count: {edf_sched_count}", f"- DM true EDF false: {combos.get(('True','False'),0)}", f"- EDF true DM false: {combos.get(('False','True'),0)}", f"- simulation misses despite analytical schedulability: {sim_miss_despite_analytic}", f"- missing target_utilization rows: {missing_target}"]
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
