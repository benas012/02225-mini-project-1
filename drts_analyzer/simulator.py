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
    execution_time: int
    job_index: int


@dataclass
class SimulationStats:
    max_response: dict[str, float]
    deadline_misses: int
    preemptions: int
    first_miss: dict[str, object] | None
    incomplete_jobs_ignored: int


def _pick_job(jobs: list[Job], algorithm: str, dm_priorities: dict[str, int]) -> Job:
    if algorithm == "DM":
        return min(jobs, key=lambda job: (dm_priorities[job.task.id], job.absolute_deadline, job.release, job.task.id, job.job_index))
    if algorithm == "EDF":
        return min(jobs, key=lambda job: (job.absolute_deadline, job.release, job.task.id, job.job_index))
    raise ValueError(f"Unsupported algorithm: {algorithm}")


def _sample_execution(task: Task, rng: random.Random, policy: str) -> int:
    if policy == "wcet":
        return task.C
    return rng.randint(task.BCET, task.C)


def run_simulation(tasks: tuple[Task, ...], algorithm: str, horizon: int, rng: random.Random, execution_policy: str = "random", drain_after_horizon: bool = True) -> SimulationStats:
    ready: list[Job] = []
    max_response = {task.id: 0.0 for task in tasks}
    deadline_misses = 0
    preemptions = 0
    current_time = 0
    next_release = {task.id: 0 for task in tasks}
    running_job: Job | None = None
    release_index = {task.id: 0 for task in tasks}
    first_miss = None
    dm_priorities = {task.id: idx for idx, task in enumerate(dm_priority_order(tasks))}

    while True:
        for task in tasks:
            while next_release[task.id] <= current_time and next_release[task.id] < horizon:
                r = next_release[task.id]
                ex = _sample_execution(task, rng, execution_policy)
                ready.append(Job(task=task, release=r, absolute_deadline=r + task.D, remaining=ex, execution_time=ex, job_index=release_index[task.id]))
                next_release[task.id] += task.T
                release_index[task.id] += 1

        active = [job for job in ready if job.remaining > 0]
        if not active:
            nearest_release = min(next_release.values())
            if nearest_release >= horizon or not drain_after_horizon:
                break
            current_time = nearest_release
            continue

        next_job = _pick_job(active, algorithm, dm_priorities)
        if running_job is not None and running_job is not next_job and running_job.remaining > 0:
            preemptions += 1
        running_job = next_job

        completion_time = current_time + running_job.remaining
        nearest_release = min(next_release.values())
        next_event_time = completion_time if (nearest_release >= horizon or not drain_after_horizon) else min(completion_time, nearest_release)
        running_job.remaining -= next_event_time - current_time
        current_time = next_event_time

        if running_job.remaining == 0:
            finish_time = current_time
            if finish_time > running_job.absolute_deadline:
                deadline_misses += 1
                if first_miss is None:
                    first_miss = {"scheduler": algorithm, "task_id": running_job.task.id, "job_index": running_job.job_index, "release_time": running_job.release, "absolute_deadline": running_job.absolute_deadline, "sampled_execution_time": running_job.execution_time, "finish_time": finish_time, "response_time": finish_time - running_job.release}
            max_response[running_job.task.id] = max(max_response[running_job.task.id], finish_time - running_job.release)
            ready.remove(running_job)
            running_job = None

        if current_time >= horizon and all(nr >= horizon for nr in next_release.values()) and not ready:
            break

    incomplete = len([j for j in ready if j.remaining > 0])
    return SimulationStats(max_response=max_response, deadline_misses=deadline_misses, preemptions=preemptions, first_miss=first_miss, incomplete_jobs_ignored=incomplete)
