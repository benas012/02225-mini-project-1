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
        if self.C <= 0 or self.D <= 0 or self.T <= 0:
            raise ValueError("C, D, and T must be > 0")
        if self.BCET < 0:
            raise ValueError("BCET must be >= 0")
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
