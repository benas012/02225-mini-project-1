import random

from drts_analyzer.dm_analysis import dm_wcrts
from drts_analyzer.edf_analysis import edf_analyze, edf_wcrts
from drts_analyzer.models import Task


def test_edf_single_task_wcrt():
    tasks = (Task(id="tau1", C=1, BCET=1, D=5, T=5),)
    assert edf_wcrts(tasks)["tau1"] == 1


def test_edf_two_tasks_schedulable_and_equal_deadline_tie():
    tasks = (Task(id="tau1", C=1, BCET=1, D=4, T=4), Task(id="tau2", C=1, BCET=1, D=5, T=5))
    assert edf_analyze(tasks)["schedulable"] is True
    tie = (Task(id="a", C=1, BCET=1, D=4, T=4), Task(id="b", C=1, BCET=1, D=4, T=4))
    t = edf_analyze(tie)
    assert t["schedulable"] is True
    assert t["first_miss"] is None


def test_edf_dm_consistency_random_small():
    rng = random.Random(123)
    for _ in range(100):
        n = rng.randint(1, 4)
        tasks = []
        for i in range(n):
            T = rng.randint(2, 10)
            D = rng.randint(1, T)
            C = rng.randint(1, D)
            tasks.append(Task(id=f"t{i}", C=C, BCET=rng.randint(0, C), D=D, T=T))
        ts = tuple(tasks)
        if sum(t.C / t.T for t in ts) > 1:
            continue
        dm = dm_wcrts(ts)
        if all(dm[t.id] <= t.D for t in ts):
            edf = edf_analyze(ts, trace=True)
            assert edf["schedulable"], f"failed taskset={ts} trace={edf['trace'][:40]}"
