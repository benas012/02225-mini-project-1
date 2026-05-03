import random

from drts_analyzer.edf_analysis import edf_analyze
from drts_analyzer.models import Task
from drts_analyzer.simulator import run_simulation


def test_simulator_is_deterministic_with_same_seed():
    tasks = (Task(id="tau1", C=1, BCET=1, D=3, T=4), Task(id="tau2", C=1, BCET=1, D=4, T=5))
    a = run_simulation(tasks, algorithm="DM", horizon=40, rng=random.Random(42))
    b = run_simulation(tasks, algorithm="DM", horizon=40, rng=random.Random(42))
    assert a.max_response == b.max_response
    assert a.deadline_misses == b.deadline_misses


def test_schedulable_no_miss_wcets_and_random():
    tasks = (Task(id="a", C=1, BCET=1, D=4, T=4), Task(id="b", C=1, BCET=1, D=5, T=5))
    h = edf_analyze(tasks)["hyperperiod"]
    assert run_simulation(tasks, "DM", h, random.Random(1), execution_policy="wcet").deadline_misses == 0
    assert run_simulation(tasks, "EDF", h, random.Random(1), execution_policy="wcet").deadline_misses == 0
    assert run_simulation(tasks, "DM", h, random.Random(1), execution_policy="random").deadline_misses == 0
    assert run_simulation(tasks, "EDF", h, random.Random(1), execution_policy="random").deadline_misses == 0


def test_deadline_equality_not_miss_and_horizon_no_false_miss():
    tasks = (Task(id="a", C=2, BCET=2, D=2, T=5),)
    r = run_simulation(tasks, "EDF", 2, random.Random(1), execution_policy="wcet")
    assert r.deadline_misses == 0
    r2 = run_simulation(tasks, "EDF", 1, random.Random(1), execution_policy="wcet", drain_after_horizon=True)
    assert r2.deadline_misses == 0


def test_non_draining_horizon_stops_active_job_at_boundary():
    tasks = (Task(id="a", C=5, BCET=5, D=10, T=20),)
    non_draining = run_simulation(tasks, "EDF", 3, random.Random(1), execution_policy="wcet", drain_after_horizon=False)
    draining = run_simulation(tasks, "EDF", 3, random.Random(1), execution_policy="wcet", drain_after_horizon=True)

    assert non_draining.max_response["a"] == 0.0
    assert non_draining.incomplete_jobs_ignored == 1
    assert draining.max_response["a"] == 5
    assert draining.incomplete_jobs_ignored == 0
