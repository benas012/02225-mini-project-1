from drts_analyzer.dm_analysis import dm_wcrts
from drts_analyzer.edf_analysis import edf_wcrts
from drts_analyzer.models import Task


def test_edf_single_task_wcrt():
    tasks = (Task(id="tau1", C=1, BCET=1, D=5, T=5),)
    assert edf_wcrts(tasks)["tau1"] == 1


def test_edf_two_tasks_schedulable():
    tasks = (Task(id="tau1", C=1, BCET=1, D=4, T=4), Task(id="tau2", C=1, BCET=1, D=5, T=5))
    res = edf_wcrts(tasks)
    assert res["tau1"] <= 4
    assert res["tau2"] <= 5


def test_dm_schedulable_implies_edf_schedulable_small_case():
    tasks = (Task(id="a", C=1, BCET=1, D=3, T=3), Task(id="b", C=1, BCET=1, D=4, T=5))
    dm = dm_wcrts(tasks)
    assert all(dm[t.id] <= t.D for t in tasks)
    edf = edf_wcrts(tasks)
    assert all(edf[t.id] <= t.D for t in tasks)


def test_edf_tie_deadline_case():
    tasks = (Task(id="tau1", C=1, BCET=1, D=4, T=4), Task(id="tau2", C=1, BCET=1, D=4, T=4))
    edf = edf_wcrts(tasks)
    assert edf["tau1"] <= 4
    assert edf["tau2"] <= 4
