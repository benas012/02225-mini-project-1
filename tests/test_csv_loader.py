from pathlib import Path

from drts_analyzer.analyzer import analyze_csv_folder
from drts_analyzer.utils import load_csv_task_set, parse_taskset_metadata


def _write_csv(path: Path, rows: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(rows) + "\n")


def test_accepts_integer_like_floats(tmp_path: Path):
    csv_file = tmp_path / "a.csv"
    _write_csv(csv_file, ["TaskID,Jitter,BCET,WCET,Period,Deadline,PE", "t1,0.0,0.0,1.0,10.0,10.0,0.0"])
    ts = load_csv_task_set(csv_file, tmp_path)
    assert ts.tasks[0].T == 10


def test_validation_rules(tmp_path: Path):
    bad_rows = [
        "t1,0,1,0,10,10,0",
        "t1,0,2,1,10,10,0",
        "t1,0,1,5,10,4,0",
        "t1,0,1,5,4,5,0",
        "t1,1,1,1,10,10,0",
        "t1,0,1,1,10,10,1",
    ]
    for row in bad_rows:
        csv_file = tmp_path / "b.csv"
        _write_csv(csv_file, ["TaskID,Jitter,BCET,WCET,Period,Deadline,PE", row])
        try:
            load_csv_task_set(csv_file, tmp_path)
            assert False
        except ValueError:
            pass


def test_missing_columns_rejected(tmp_path: Path):
    csv_file = tmp_path / "m.csv"
    _write_csv(csv_file, ["TaskID,BCET,WCET,Period,Deadline,PE", "t1,0,1,10,10,0"])
    try:
        load_csv_task_set(csv_file, tmp_path)
        assert False
    except ValueError as exc:
        assert "Missing required columns" in str(exc)


def test_parse_metadata_from_path(tmp_path: Path):
    csv_file = tmp_path / "tasksets/uniform-discrete-perDist/1-core/25-task/0-jitter/0.60-util/uniform-discrete_0.csv"
    _write_csv(csv_file, ["TaskID,Jitter,BCET,WCET,Period,Deadline,PE", "t1,0,1,1,5,5,0"])
    metadata = parse_taskset_metadata(csv_file, tmp_path / "tasksets")
    assert metadata["distribution"] == "uniform-discrete-perDist"
    assert metadata["target_utilization"] == 0.60
    assert metadata["task_count"] == "25-task"
    assert metadata["jitter_group"] == "0-jitter"
    assert metadata["core_count"] == "1-core"


def test_parse_metadata_from_nested_generated_path(tmp_path: Path):
    csv_file = tmp_path / "tasksets/automotive-utilDist/automotive-perDist/1-core/25-task/0-jitter/0.60-util/tasksets/automotive_0.csv"
    _write_csv(csv_file, ["TaskID,Jitter,BCET,WCET,Period,Deadline,PE", "t1,0,1,1,5,5,0"])
    metadata = parse_taskset_metadata(csv_file, tmp_path / "tasksets")
    assert metadata["distribution"] == "automotive-utilDist"
    assert metadata["period_distribution"] == "automotive-perDist"
    assert metadata["core_count"] == "1-core"
    assert metadata["task_count"] == "25-task"
    assert metadata["jitter_group"] == "0-jitter"
    assert metadata["target_utilization"] == 0.60


def test_target_util_depth_independent(tmp_path: Path):
    csv_file = tmp_path / "x/y/z/1.00-util/f.csv"
    _write_csv(csv_file, ["TaskID,Jitter,BCET,WCET,Period,Deadline,PE", "t1,0,1,1,5,5,0"])
    m = parse_taskset_metadata(csv_file, tmp_path)
    assert m["target_utilization"] == 1.0
