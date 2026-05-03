import random

from drts_analyzer.models import Task
from drts_analyzer.simulator import run_simulation


def test_simulator_is_deterministic_with_same_seed():
    tasks = (Task(id="tau1", C=1, BCET=1, D=3, T=4), Task(id="tau2", C=1, BCET=1, D=4, T=5))
    a = run_simulation(tasks, algorithm="DM", horizon=40, rng=random.Random(42))
    b = run_simulation(tasks, algorithm="DM", horizon=40, rng=random.Random(42))
    assert a.max_response == b.max_response
    assert a.deadline_misses == b.deadline_misses


def test_wcets_only_schedulable_no_misses():
    tasks = (Task(id="a", C=1, BCET=1, D=4, T=4), Task(id="b", C=1, BCET=1, D=5, T=5))
    r = run_simulation(tasks, "DM", 200, random.Random(1))
    assert r.deadline_misses == 0


def test_uses_deadline_not_period():
    tasks = (Task(id="a", C=1, BCET=1, D=2, T=5),)
    r = run_simulation(tasks, "EDF", 30, random.Random(1))
    assert r.deadline_misses == 0
