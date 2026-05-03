from __future__ import annotations

import math
import random
from dataclasses import dataclass

from .dm_analysis import dm_priority_order
from .models import Task


@dataclass
class Job:
    task: Task
    release: int
    absolute_deadline: int
    remaining: float
    job_index: int


@dataclass
class SimulationStats:
    max_response: dict[str, float]
    deadline_misses: int
    preemptions: int


def _pick_job(jobs: list[Job], algorithm: str) -> Job:
    if algorithm == "DM":
        priorities = {task.id: idx for idx, task in enumerate(dm_priority_order(tuple({job.task for job in jobs})))}
        return min(jobs, key=lambda job: (priorities[job.task.id], job.absolute_deadline, job.release, job.task.id, job.job_index))
    if algorithm == "EDF":
        return min(jobs, key=lambda job: (job.absolute_deadline, job.release, job.task.id, job.job_index))
    raise ValueError(f"Unsupported algorithm: {algorithm}")


def _sample_execution(task: Task, rng: random.Random) -> float:
    if task.BCET == task.C:
        return task.C
    return rng.randint(task.BCET, task.C)


def run_simulation(tasks: tuple[Task, ...], algorithm: str, horizon: int, rng: random.Random) -> SimulationStats:
    ready: list[Job] = []
    max_response = {task.id: 0.0 for task in tasks}
    deadline_misses = 0
    preemptions = 0
    current_time = 0
    next_release = {task.id: 0 for task in tasks}
    running_job: Job | None = None
    release_index = {task.id: 0 for task in tasks}

    while current_time < horizon:
        for task in tasks:
            while next_release[task.id] <= current_time and next_release[task.id] < horizon:
                r = next_release[task.id]
                ready.append(Job(task=task, release=r, absolute_deadline=r + task.D, remaining=_sample_execution(task, rng), job_index=release_index[task.id]))
                next_release[task.id] += task.T
                release_index[task.id] += 1

        active = [job for job in ready if job.remaining > 0]
        if not active:
            nearest_release = min(next_release.values())
            if nearest_release >= horizon:
                break
            current_time = nearest_release
            continue

        next_job = _pick_job(active, algorithm)
        if running_job is not None and running_job is not next_job and running_job.remaining > 0:
            preemptions += 1
        running_job = next_job

        completion_time = current_time + running_job.remaining
        nearest_release = min(next_release.values())
        next_event_time = min(completion_time, nearest_release, horizon)
        executed = max(0.0, next_event_time - current_time)
        running_job.remaining -= executed
        current_time = next_event_time

        if running_job.remaining <= 1e-12:
            finish_time = current_time
            if finish_time > running_job.absolute_deadline:
                deadline_misses += 1
            response_time = finish_time - running_job.release
            max_response[running_job.task.id] = max(max_response[running_job.task.id], response_time)
            ready.remove(running_job)
            running_job = None

    return SimulationStats(max_response=max_response, deadline_misses=deadline_misses, preemptions=preemptions)
