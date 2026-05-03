from pathlib import Path

from drts_analyzer.analyzer import analyze_csv_folder


def _write_csv(path: Path, rows: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(rows) + "\n")


def _mk(base: Path, dist: str, util: str, name: str, period2: int = 5):
    _write_csv(base / f"{dist}/1-core/25-task/0-jitter/{util}/{name}.csv", [
        "TaskID,Jitter,BCET,WCET,Period,Deadline,PE",
        "t1,0,1,1,2,2,0",
        f"t2,0,1,1,{period2},{period2},0",
    ])


def test_sampling_limits_and_sorted(tmp_path: Path):
    for i in [2, 0, 1]:
        _mk(tmp_path, "unifast-utilDist", "0.60-util", f"u_{i}")
    out = tmp_path / "out"
    analyze_csv_folder(tmp_path, out, runs=0, seed=1, max_hyperperiod=1000, samples_per_util=2)
    lines = (out / "taskset_summary.csv").read_text().splitlines()
    body = "\n".join(lines[1:])
    assert "u_0.csv" in body and "u_1.csv" in body
    assert "u_2.csv" not in body


def test_util_and_distribution_filters(tmp_path: Path):
    _mk(tmp_path, "unifast-utilDist", "0.30-util", "a")
    _mk(tmp_path, "automotive-utilDist", "0.30-util", "b")
    _mk(tmp_path, "unifast-utilDist", "0.50-util", "c")
    out = tmp_path / "out"
    analyze_csv_folder(tmp_path, out, runs=0, seed=1, max_hyperperiod=1000, util_levels=["0.30"], distributions=["unifast-utilDist"])
    text = (out / "taskset_summary.csv").read_text()
    assert "a.csv" in text
    assert "b.csv" not in text
    assert "c.csv" not in text


def test_skip_edf_but_dm_runs_and_horizon_bound(tmp_path: Path):
    _mk(tmp_path, "unifast-utilDist", "0.60-util", "big", period2=99991)
    out = tmp_path / "out"
    analyze_csv_folder(tmp_path, out, runs=1, seed=1, max_hyperperiod=1000, simulation_horizon=10)
    text = (out / "taskset_summary.csv").read_text()
    assert "skipped_hyperperiod_too_large" in text
    assert ",ok,skipped_hyperperiod_too_large,ok," in text
    assert ",10" in text


def test_batch_continues_after_failure(tmp_path: Path):
    _mk(tmp_path, "unifast-utilDist", "0.10-util", "good")
    bad = tmp_path / "unifast-utilDist/1-core/25-task/0-jitter/0.10-util/bad.csv"
    _write_csv(bad, ["TaskID,Jitter,BCET,WCET,Period,Deadline,PE", "x,1,1,1,2,2,0"])
    out = tmp_path / "out"
    analyze_csv_folder(tmp_path, out, runs=0, seed=1, max_hyperperiod=1000)
    text = (out / "taskset_summary.csv").read_text()
    assert "failed_validation" in text
    assert "ok" in text
