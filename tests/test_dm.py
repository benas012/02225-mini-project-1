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
