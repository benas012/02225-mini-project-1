from pathlib import Path

from drts_analyzer.analyzer import analyze_csv_folder, analyze_task_set
from drts_analyzer.models import Task, TaskSet


def _write_csv(path: Path, rows: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(rows) + "\n")


def test_analyze_task_set_returns_per_task_results():
    task_set = TaskSet(
        name="example",
        tasks=(
            Task(id="tau1", C=1, BCET=1, D=3, T=4),
            Task(id="tau2", C=1, BCET=1, D=4, T=5),
        ),
    )

    rows = analyze_task_set(task_set, runs=1, seed=42)

    assert [row["task_id"] for row in rows] == ["tau1", "tau2"]
    assert rows[0]["DM_WCRT"] == 1
    assert rows[1]["DM_WCRT"] == 2
    assert all(row["EDF_schedulable"] for row in rows)
    assert all("DM_max_sim" in row and "EDF_max_sim" in row for row in rows)


def test_analyze_csv_folder_writes_task_details(tmp_path: Path):
    csv_file = tmp_path / "unifast-utilDist/1-core/25-task/0-jitter/0.60-util/u_0.csv"
    _write_csv(
        csv_file,
        [
            "TaskID,Jitter,BCET,WCET,Period,Deadline,PE",
            "t1,0,1,1,4,3,0",
            "t2,0,1,1,5,4,0",
        ],
    )
    out = tmp_path / "out"

    analyze_csv_folder(tmp_path, out, runs=1, seed=1, max_hyperperiod=1000)

    details = (out / "task_details.csv").read_text()
    assert "task_id" in details
    assert "t1" in details
    assert "DM_WCRT" in details
    assert "EDF_WCRT" in details
