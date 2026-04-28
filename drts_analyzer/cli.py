from __future__ import annotations

import argparse
import json

from .analyzer import analyze_task_set
from .utils import load_task_sets


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="drts_analyzer")
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze = subparsers.add_parser("analyze", help="Analyze periodic real-time task sets")
    analyze.add_argument("--input", required=True, help="Path to JSON task-set input file")
    analyze.add_argument("--runs", type=int, default=100, help="Number of stochastic simulation runs")
    analyze.add_argument("--seed", type=int, default=42, help="Random seed")
    analyze.add_argument("--horizon", type=int, default=None, help="Optional simulation horizon")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "analyze":
        task_sets = load_task_sets(args.input)
        output: dict[str, object] = {"task_sets": []}
        for task_set in task_sets:
            rows = analyze_task_set(task_set, runs=args.runs, seed=args.seed, horizon=args.horizon)
            output["task_sets"].append({"name": task_set.name, "results": rows})
        print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
