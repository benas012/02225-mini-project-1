from __future__ import annotations

import random
from dataclasses import dataclass

from .dm_analysis import dm_priority_order
from .models import Task


@dataclass
class Job:
    task: Task
    release: int
    absolute_deadline: int
    remaining: int
    started: bool = False


@dataclass
class SimulationStats:
    max_response: dict[str, int]
    deadline_misses: int
    preemptions: int


def _pick_job(jobs: list[Job], algorithm: str) -> Job:
    if algorithm == "DM":
        priorities = {task.id: idx for idx, task in enumerate(dm_priority_order(tuple(job.task for job in jobs)))}
        return min(jobs, key=lambda job: (priorities[job.task.id], job.absolute_deadline, job.release))
    if algorithm == "EDF":
        return min(jobs, key=lambda job: (job.absolute_deadline, job.release, job.task.id))
    raise ValueError(f"Unsupported algorithm: {algorithm}")


def run_simulation(
    tasks: tuple[Task, ...],
    algorithm: str,
    horizon: int,
    rng: random.Random,
) -> SimulationStats:
    ready: list[Job] = []
    max_response = {task.id: 0 for task in tasks}
    deadline_misses = 0
    preemptions = 0
    running_job: Job | None = None

    for tick in range(horizon):
        for task in tasks:
            if tick % task.T == 0:
                execution_time = rng.randint(task.BCET, task.C)
                ready.append(
                    Job(
                        task=task,
                        release=tick,
                        absolute_deadline=tick + task.D,
                        remaining=execution_time,
                    )
                )

        late_jobs = [job for job in ready if tick >= job.absolute_deadline and job.remaining > 0]
        deadline_misses += len(late_jobs)

        if ready:
            next_job = _pick_job([job for job in ready if job.remaining > 0], algorithm)
            if running_job is not None and running_job is not next_job and running_job.remaining > 0:
                preemptions += 1
            running_job = next_job
            running_job.started = True
            running_job.remaining -= 1
            if running_job.remaining == 0:
                response_time = tick + 1 - running_job.release
                max_response[running_job.task.id] = max(max_response[running_job.task.id], response_time)
                ready.remove(running_job)
                running_job = None

        ready = [job for job in ready if job.remaining > 0]

    return SimulationStats(max_response=max_response, deadline_misses=deadline_misses, preemptions=preemptions)
