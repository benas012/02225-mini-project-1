from __future__ import annotations

from dataclasses import dataclass

from .models import Task
from .utils import lcm


@dataclass
class _Job:
    task_id: str
    release: int
    absolute_deadline: int
    remaining: int
    job_index: int


def _priority_key(job: _Job) -> tuple[int, int, str, int]:
    return (job.absolute_deadline, job.release, job.task_id, job.job_index)


def edf_wcrts(tasks: tuple[Task, ...]) -> dict[str, int]:
    hyperperiod = lcm([task.T for task in tasks])
    releases: dict[int, list[_Job]] = {}
    for task in tasks:
        count = hyperperiod // task.T
        for k in range(count):
            r = k * task.T
            releases.setdefault(r, []).append(_Job(task.id, r, r + task.D, task.C, k))

    ready: list[_Job] = []
    wcrt = {task.id: 0 for task in tasks}
    current_time = 0

    while current_time < hyperperiod or ready:
        for job in releases.pop(current_time, []):
            ready.append(job)

        active = [j for j in ready if j.remaining > 0]
        if not active:
            if not releases:
                break
            current_time = min(releases.keys())
            continue

        best = min(active, key=_priority_key)
        next_release = min(releases.keys()) if releases else hyperperiod
        step = min(best.remaining, max(1, next_release - current_time))
        best.remaining -= step
        current_time += step
        if best.remaining == 0:
            finish = current_time
            wcrt[best.task_id] = max(wcrt[best.task_id], finish - best.release)
            ready.remove(best)

    return wcrt
