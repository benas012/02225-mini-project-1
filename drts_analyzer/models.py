from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Task:
    id: str
    C: int
    BCET: int
    D: int
    T: int

    def __post_init__(self) -> None:
        if min(self.C, self.BCET, self.D, self.T) <= 0:
            raise ValueError("Task parameters must be positive integers")
        if self.BCET > self.C:
            raise ValueError("BCET must be <= C")
        if not (self.C <= self.D <= self.T):
            raise ValueError("Expected constrained deadline: C <= D <= T")

    @property
    def utilization(self) -> float:
        return self.C / self.T


@dataclass(frozen=True)
class TaskSet:
    name: str
    tasks: tuple[Task, ...]

    @property
    def utilization(self) -> float:
        return sum(task.utilization for task in self.tasks)
