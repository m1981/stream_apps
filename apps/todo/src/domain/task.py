from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, List

class EnergyLevel(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class ZoneType(Enum):
    DEEP = "deep"
    LIGHT = "light"
    ADMIN = "admin"

@dataclass
class TaskConstraints:
    zone_type: ZoneType
    energy_level: EnergyLevel
    is_splittable: bool
    min_chunk_duration: int  # minutes
    max_split_count: int
    required_buffer: int     # minutes
    dependencies: List[str]  # task IDs

    def validate(self) -> List[str]:
        errors = []

        if self.min_chunk_duration <= 0:
            errors.append("Minimum chunk duration must be positive")

        if self.max_split_count < 1:
            errors.append("Maximum split count must be at least 1")

        if self.required_buffer < 0:
            errors.append("Required buffer cannot be negative")

        if self.is_splittable and self.max_split_count == 1:
            errors.append("Splittable tasks must allow at least 2 splits")

        return errors

@dataclass
class Task:
    id: str
    title: str
    duration: int           # minutes
    due_date: datetime
    priority: int
    project_id: str
    constraints: TaskConstraints

    def validate(self) -> List[str]:
        errors = []

        if self.duration <= 0:
            errors.append("Task duration must be positive")

        if self.priority < 1:
            errors.append("Priority must be positive")

        if not self.title.strip():
            errors.append("Title cannot be empty")

        # Check if due date is in the past
        if self.due_date < datetime.now():
            errors.append("Due date cannot be in the past")

        # Validate constraints
        errors.extend(self.constraints.validate())

        # Validate splitting constraints
        if self.constraints.is_splittable:
            min_total_duration = self.constraints.min_chunk_duration * self.constraints.max_split_count
            if min_total_duration > self.duration:
                errors.append(
                    f"Total minimum chunk duration ({min_total_duration} min) "
                    f"exceeds task duration ({self.duration} min)"
                )

        return errors

    def get_minimum_duration(self) -> int:
        return (self.constraints.min_chunk_duration
                if self.constraints.is_splittable
                else self.duration)