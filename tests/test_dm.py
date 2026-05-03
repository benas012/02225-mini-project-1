from drts_analyzer.dm_analysis import dm_priority_order, dm_wcrts
from drts_analyzer.models import Task


def test_dm_priority_order_uses_deadline():
    tasks = (
        Task(id="t1", C=1, BCET=1, D=5, T=5),
        Task(id="t2", C=1, BCET=1, D=3, T=6),
    )
    ordered = dm_priority_order(tasks)
    assert [task.id for task in ordered] == ["t2", "t1"]


def test_dm_wcrt_small_example():
    tasks = (
        Task(id="tau1", C=1, BCET=1, D=3, T=4),
        Task(id="tau2", C=1, BCET=1, D=4, T=5),
    )
    results = dm_wcrts(tasks)
    assert results["tau1"] == 1
    assert results["tau2"] == 2


def test_dm_wcrt_project_example_and_deadline_edge():
    tasks = (
        Task(id="tau1", C=1, BCET=1, D=3, T=5),
        Task(id="tau2", C=2, BCET=1, D=7, T=10),
    )
    results = dm_wcrts(tasks)
    assert results["tau1"] == 1
    assert results["tau2"] == 3
    assert results["tau1"] <= 3 and results["tau2"] <= 7


def test_dm_unschedulable_when_response_exceeds_deadline():
    tasks = (
        Task(id="a", C=2, BCET=1, D=2, T=3),
        Task(id="b", C=3, BCET=1, D=3, T=5),
    )
    r = dm_wcrts(tasks)
    assert r["b"] > 3
