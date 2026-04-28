from drts_analyzer.edf_analysis import edf_wcrts
from drts_analyzer.models import Task


def test_edf_wcrt_is_at_least_execution_time():
    tasks = (
        Task(id="tau1", C=1, BCET=1, D=3, T=4),
        Task(id="tau2", C=2, BCET=1, D=5, T=7),
    )
    results = edf_wcrts(tasks)
    assert results["tau1"] >= 1
    assert results["tau2"] >= 2


def test_edf_wcrt_stable_for_single_task():
    tasks = (Task(id="tau1", C=2, BCET=1, D=5, T=5),)
    results = edf_wcrts(tasks)
    assert results["tau1"] == 2
