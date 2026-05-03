from __future__ import annotations

import argparse
import json
import sys

from .analyzer import analyze_csv_folder, analyze_task_set
from .utils import load_task_sets


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="drts_analyzer")
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze = subparsers.add_parser("analyze", help="Analyze periodic real-time task sets")
    analyze.add_argument("--input", required=True, help="Path to JSON task-set input file")
    analyze.add_argument("--runs", type=int, default=100, help="Number of stochastic simulation runs")
    analyze.add_argument("--seed", type=int, default=42, help="Random seed")
    analyze.add_argument("--horizon", type=int, default=None, help="Optional simulation horizon")
    analyze.add_argument("--verbose", action="store_true", help="Print progress for each task set")
    analyze_csv = subparsers.add_parser("analyze-csv-folder", help="Analyze all CSV task sets under a folder")
    analyze_csv.add_argument("--input", required=True, help="Input folder containing CSV task sets")
    analyze_csv.add_argument("--output", required=True, help="Output folder for result CSV files")
    analyze_csv.add_argument("--runs", type=int, default=100, help="Number of stochastic simulation runs")
    analyze_csv.add_argument("--seed", type=int, default=42, help="Random seed")
    analyze_csv.add_argument("--max-hyperperiod", type=int, default=10_000_000, help="Maximum hyperperiod allowed for analysis")
    analyze_csv.add_argument("--verbose", action="store_true", help="Print progress for each CSV task set")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "analyze":
        task_sets = load_task_sets(args.input)
        output: dict[str, object] = {"task_sets": []}
        for index, task_set in enumerate(task_sets, start=1):
            if args.verbose:
                print(f"[analyze] Running task set {index}/{len(task_sets)}: {task_set.name}", file=sys.stderr)
            rows = analyze_task_set(task_set, runs=args.runs, seed=args.seed, horizon=args.horizon)
            output["task_sets"].append({"name": task_set.name, "results": rows})
        print(json.dumps(output, indent=2))
        return 0

    if args.command == "analyze-csv-folder":
        analyze_csv_folder(
            input_path=args.input,
            output_path=args.output,
            runs=args.runs,
            seed=args.seed,
            max_hyperperiod=args.max_hyperperiod,
            verbose=args.verbose,
        )
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
