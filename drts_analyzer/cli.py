from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from pathlib import Path

from .analyzer import analyze_csv_folder, analyze_task_set, diagnose_results
from .dm_analysis import dm_priority_order, dm_wcrts
from .edf_analysis import edf_analyze
from .simulator import run_simulation
from .utils import load_csv_task_set, load_task_sets


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="drts_analyzer")
    subparsers = parser.add_subparsers(dest="command", required=True)
    analyze = subparsers.add_parser("analyze")
    analyze.add_argument("--input", required=True)
    analyze.add_argument("--runs", type=int, default=100)
    analyze.add_argument("--seed", type=int, default=42)
    analyze.add_argument("--horizon", type=int, default=None)
    analyze.add_argument("--verbose", action="store_true")
    analyze_csv = subparsers.add_parser("analyze-csv-folder")
    analyze_csv.add_argument("--input", required=True); analyze_csv.add_argument("--output", required=True)
    analyze_csv.add_argument("--runs", type=int, default=100); analyze_csv.add_argument("--seed", type=int, default=42)
    analyze_csv.add_argument("--max-hyperperiod", type=int, default=10_000_000); analyze_csv.add_argument("--samples-per-util", type=int, default=None)
    analyze_csv.add_argument("--util-levels", nargs="*", default=None); analyze_csv.add_argument("--distributions", nargs="*", default=None)
    analyze_csv.add_argument("--simulation-horizon", type=int, default=None); analyze_csv.add_argument("--verbose", action="store_true")
    d = subparsers.add_parser("diagnose-results"); d.add_argument("--summary", required=True); d.add_argument("--details", required=True); d.add_argument("--output", required=True)
    dbg = subparsers.add_parser("debug-taskset")
    dbg.add_argument("--input", required=True); dbg.add_argument("--runs", type=int, default=1); dbg.add_argument("--seed", type=int, default=42); dbg.add_argument("--trace-edf", action="store_true")
    fs = subparsers.add_parser("find-suspicious")
    fs.add_argument("--summary", required=True); fs.add_argument("--details", required=True); fs.add_argument("--limit", type=int, default=20)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "debug-taskset":
        ts = load_csv_task_set(args.input, Path(args.input).parent)
        print("TaskID,BCET,WCET,Period,Deadline,utilization")
        for t in ts.tasks: print(f"{t.id},{t.BCET},{t.C},{t.T},{t.D},{t.utilization:.6f}")
        dm = dm_wcrts(ts.tasks); order = [t.id for t in dm_priority_order(ts.tasks)]
        print("\nDM priority order:", order)
        print("DM WCRT:", dm); print("DM sched per task:", {t.id: dm[t.id] <= t.D for t in ts.tasks}); print("DM schedulable:", all(dm[t.id] <= t.D for t in ts.tasks))
        edf = edf_analyze(ts.tasks, trace=args.trace_edf)
        print("\nEDF hyperperiod:", edf['hyperperiod']); print("EDF num jobs:", edf['num_jobs']); print("EDF WCRT:", edf['wcrt']); print("EDF sched per task:", edf['per_task_schedulable']); print("EDF schedulable:", edf['schedulable']); print("EDF first miss:", edf['first_miss'])
        for alg in ("DM", "EDF"):
            sim = run_simulation(ts.tasks, alg, edf['hyperperiod'], random.Random(args.seed), execution_policy="random")
            print(f"\nSim {alg}: horizon={edf['hyperperiod']} execution-time policy=random misses={sim.deadline_misses} first_miss={sim.first_miss}")
        if args.trace_edf:
            print("\nstart,end,task_id,job_index,release_time,absolute_deadline,remaining_before,remaining_after")
            for x in edf["trace"]: print(f"{x['start']},{x['end']},{x['task_id']},{x['job_index']},{x['release_time']},{x['absolute_deadline']},{x['remaining_before']},{x['remaining_after']}")
        return 0
    if args.command == "find-suspicious":
        rows = list(csv.DictReader(Path(args.summary).open()))
        filt = [r["source_file"] for r in rows if (r.get("dm_schedulable") == "True" and r.get("edf_schedulable") == "False") or (r.get("dm_schedulable") == "True" and int(r.get("dm_deadline_misses_sim") or 0) > 0) or (r.get("edf_schedulable") == "True" and int(r.get("edf_deadline_misses_sim") or 0) > 0)]
        for p in filt[: args.limit]: print(p)
        return 0
    if args.command == "analyze":
        task_sets = load_task_sets(args.input); output = {"task_sets": []}
        for index, task_set in enumerate(task_sets, start=1):
            if args.verbose: print(f"[analyze] Running task set {index}/{len(task_sets)}: {task_set.name}", file=sys.stderr)
            output["task_sets"].append({"name": task_set.name, "results": analyze_task_set(task_set, runs=args.runs, seed=args.seed, horizon=args.horizon)})
        print(json.dumps(output, indent=2)); return 0
    if args.command == "diagnose-results": diagnose_results(args.summary, args.details, args.output); return 0
    if args.command == "analyze-csv-folder":
        analyze_csv_folder(args.input, args.output, args.runs, args.seed, args.max_hyperperiod, args.verbose, args.samples_per_util, args.util_levels, args.distributions, args.simulation_horizon); return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
