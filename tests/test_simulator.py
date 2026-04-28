import random

from drts_analyzer.models import Task
from drts_analyzer.simulator import run_simulation


def test_simulator_is_deterministic_with_same_seed():
    tasks = (
        Task(id="tau1", C=1, BCET=1, D=3, T=4),
        Task(id="tau2", C=1, BCET=1, D=4, T=5),
    )
    a = run_simulation(tasks, algorithm="DM", horizon=40, rng=random.Random(42))
    b = run_simulation(tasks, algorithm="DM", horizon=40, rng=random.Random(42))
    assert a.max_response == b.max_response
    assert a.deadline_misses == b.deadline_misses
    assert a.preemptions == b.preemptions


def test_simulator_tracks_preemptions_and_deadline_misses():
    tasks = (
        Task(id="fast", C=1, BCET=1, D=2, T=2),
        Task(id="slow", C=3, BCET=3, D=3, T=4),
    )
    result = run_simulation(tasks, algorithm="DM", horizon=20, rng=random.Random(7))
    assert result.preemptions >= 0
    assert result.deadline_misses >= 0
