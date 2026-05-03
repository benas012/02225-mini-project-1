from pathlib import Path

from drts_analyzer.analyzer import analyze_csv_folder
from drts_analyzer.utils import load_csv_task_set, parse_taskset_metadata


def _write_csv(path: Path, rows: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(rows) + "\n")


def test_load_valid_csv_task_set(tmp_path: Path):
    csv_file = tmp_path / "uniform-discrete-perDist/1-core/25-task/0-jitter/0.60-util/uniform-discrete_0.csv"
    _write_csv(
        csv_file,
        [
            "TaskID,Jitter,BCET,WCET,Period,Deadline,PE",
            "t1,0,1,2,10,10,0",
            "t2,0,1,1,5,5,0",
        ],
    )

    task_set = load_csv_task_set(csv_file, tmp_path)
    assert task_set.name == "uniform-discrete-perDist/1-core/25-task/0-jitter/0.60-util/uniform-discrete_0"
    assert len(task_set.tasks) == 2


def test_reject_missing_columns(tmp_path: Path):
    csv_file = tmp_path / "a.csv"
    _write_csv(csv_file, ["TaskID,WCET,Period,Deadline", "t1,2,10,10"])
    try:
        load_csv_task_set(csv_file, tmp_path)
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "Missing required columns" in str(exc)


def test_reject_non_zero_jitter(tmp_path: Path):
    csv_file = tmp_path / "a.csv"
    _write_csv(csv_file, ["TaskID,Jitter,BCET,WCET,Period,Deadline,PE", "t1,1,1,2,10,10,0"])
    try:
        load_csv_task_set(csv_file, tmp_path)
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "Jitter must be 0" in str(exc)


def test_reject_non_zero_pe(tmp_path: Path):
    csv_file = tmp_path / "a.csv"
    _write_csv(csv_file, ["TaskID,Jitter,BCET,WCET,Period,Deadline,PE", "t1,0,1,2,10,10,1"])
    try:
        load_csv_task_set(csv_file, tmp_path)
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "PE must be 0" in str(exc)


def test_reject_wcet_greater_than_deadline(tmp_path: Path):
    csv_file = tmp_path / "a.csv"
    _write_csv(csv_file, ["TaskID,Jitter,BCET,WCET,Period,Deadline,PE", "t1,0,1,11,12,10,0"])
    try:
        load_csv_task_set(csv_file, tmp_path)
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "WCET <= Deadline <= Period" in str(exc)


def test_parse_metadata_from_path(tmp_path: Path):
    csv_file = tmp_path / "automotive-utilDist/1-core/25-task/0-jitter/0.20-util/automotive_1.csv"
    _write_csv(csv_file, ["TaskID,Jitter,BCET,WCET,Period,Deadline,PE", "t1,0,1,1,5,5,0"])
    metadata = parse_taskset_metadata(csv_file, tmp_path)
    assert metadata["distribution"] == "automotive-utilDist"
    assert metadata["core_count"] == "1-core"
    assert metadata["task_count"] == "25-task"
    assert metadata["jitter_group"] == "0-jitter"
    assert metadata["target_utilization"] == 0.20


def test_batch_continues_after_bad_csv(tmp_path: Path):
    good = tmp_path / "unifast-utilDist/1-core/25-task/0-jitter/0.10-util/u_0.csv"
    bad = tmp_path / "unifast-utilDist/1-core/25-task/0-jitter/0.20-util/u_1.csv"
    _write_csv(good, ["TaskID,Jitter,BCET,WCET,Period,Deadline,PE", "t1,0,1,1,10,10,0"])
    _write_csv(bad, ["TaskID,Jitter,BCET,WCET,Period,Deadline,PE", "t1,1,1,1,10,10,0"])

    output_dir = tmp_path / "results"
    analyze_csv_folder(tmp_path, output_dir, runs=0, seed=42, max_hyperperiod=10_000)

    summary = (output_dir / "taskset_summary.csv").read_text()
    assert "status" in summary
    assert "failed" in summary
    assert "ok" in summary


def test_gitignore_contains_tasksets_and_results():
    gitignore = Path(".gitignore").read_text()
    assert "tasksets/" in gitignore
    assert "results/" in gitignore
    assert "*.log" in gitignore
