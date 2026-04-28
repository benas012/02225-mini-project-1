from __future__ import annotations

import random
from collections import defaultdict

from .dm_analysis import dm_wcrts
from .edf_analysis import edf_wcrts
from .models import TaskSet
from .simulator import run_simulation
from .utils import lcm


def analyze_task_set(task_set: TaskSet, runs: int, seed: int, horizon: int | None = None) -> list[dict[str, object]]:
    tasks = task_set.tasks
    dm = dm_wcrts(tasks)
    edf = edf_wcrts(tasks)

    if horizon is None:
        horizon = lcm([task.T for task in tasks])

    dm_sim_max = defaultdict(int)
    edf_sim_max = defaultdict(int)
    dm_misses = dm_preemptions = 0
    edf_misses = edf_preemptions = 0

    for run in range(runs):
        dm_rng = random.Random(seed + run)
        edf_rng = random.Random(seed + run)
        dm_stats = run_simulation(tasks, "DM", horizon, dm_rng)
        edf_stats = run_simulation(tasks, "EDF", horizon, edf_rng)
        for task in tasks:
            dm_sim_max[task.id] = max(dm_sim_max[task.id], dm_stats.max_response[task.id])
            edf_sim_max[task.id] = max(edf_sim_max[task.id], edf_stats.max_response[task.id])
        dm_misses += dm_stats.deadline_misses
        dm_preemptions += dm_stats.preemptions
        edf_misses += edf_stats.deadline_misses
        edf_preemptions += edf_stats.preemptions

    rows: list[dict[str, object]] = []
    for task in tasks:
        rows.append(
            {
                "task_id": task.id,
                "C": task.C,
                "BCET": task.BCET,
                "D": task.D,
                "T": task.T,
                "U_i": round(task.utilization, 5),
                "DM_WCRT": dm[task.id],
                "DM_schedulable": dm[task.id] <= task.D,
                "EDF_WCRT": edf[task.id],
                "EDF_schedulable": edf[task.id] <= task.D,
                "DM_max_sim": dm_sim_max[task.id],
                "EDF_max_sim": edf_sim_max[task.id],
                "analytical_minus_sim_gap": max(dm[task.id], edf[task.id]) - max(dm_sim_max[task.id], edf_sim_max[task.id]),
                "deadline_misses": {"DM": dm_misses, "EDF": edf_misses},
                "preemptions": {"DM": dm_preemptions, "EDF": edf_preemptions},
            }
        )
    return rows
