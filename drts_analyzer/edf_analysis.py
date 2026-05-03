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
    finish_time: int | None = None


def _priority_key(job: _Job) -> tuple[int, int, str, int]:
    return (job.absolute_deadline, job.release, job.task_id, job.job_index)


def edf_analyze(tasks: tuple[Task, ...], trace: bool = False) -> dict[str, object]:
    hyperperiod = lcm([task.T for task in tasks])
    jobs: list[_Job] = []
    for task in tasks:
        for k in range(hyperperiod // task.T):
            r = k * task.T
            jobs.append(_Job(task.id, r, r + task.D, task.C, k))

    jobs.sort(key=lambda j: (j.release, j.task_id, j.job_index))
    ready: list[_Job] = []
    i = 0
    current_time = 0
    wcrt = {task.id: 0 for task in tasks}
    first_miss = None
    intervals: list[dict[str, int | str]] = []

    while i < len(jobs) or ready:
        while i < len(jobs) and jobs[i].release <= current_time:
            ready.append(jobs[i])
            i += 1

        if not ready:
            if i >= len(jobs):
                break
            current_time = jobs[i].release
            continue

        ready.sort(key=_priority_key)
        running = ready[0]
        next_release = jobs[i].release if i < len(jobs) else None
        run_until = current_time + running.remaining
        if next_release is not None:
            run_until = min(run_until, next_release)
        before = running.remaining
        running.remaining -= run_until - current_time
        if trace:
            intervals.append({"start": current_time, "end": run_until, "task_id": running.task_id, "job_index": running.job_index, "release_time": running.release, "absolute_deadline": running.absolute_deadline, "remaining_before": before, "remaining_after": running.remaining})
        current_time = run_until
        if running.remaining == 0:
            running.finish_time = current_time
            rt = running.finish_time - running.release
            wcrt[running.task_id] = max(wcrt[running.task_id], rt)
            if running.finish_time > running.absolute_deadline and first_miss is None:
                first_miss = {
                    "task_id": running.task_id,
                    "job_index": running.job_index,
                    "release_time": running.release,
                    "absolute_deadline": running.absolute_deadline,
                    "finish_time": running.finish_time,
                    "response_time": rt,
                    "remaining_time": 0,
                }
            ready.pop(0)

    per_task = {t.id: wcrt[t.id] <= t.D for t in tasks}
    return {
        "hyperperiod": hyperperiod,
        "num_jobs": len(jobs),
        "wcrt": wcrt,
        "per_task_schedulable": per_task,
        "schedulable": all(per_task.values()),
        "first_miss": first_miss,
        "trace": intervals,
    }


def edf_wcrts(tasks: tuple[Task, ...]) -> dict[str, int]:
    return edf_analyze(tasks)["wcrt"]
