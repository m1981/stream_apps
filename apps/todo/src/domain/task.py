from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List, Optional

class ZoneType(Enum):
    DEEP = "deep"
    LIGHT = "light"
    ADMIN = "admin"

class EnergyLevel(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

@dataclass
class TaskConstraints:
    zone_type: ZoneType
    energy_level: EnergyLevel
    is_splittable: bool
    min_chunk_duration: int  # in minutes
    max_split_count: int
    required_buffer: int  # in minutes
    dependencies: List[str]  # task IDs

@dataclass
class Task:
    id: str
    title: str
    duration: int  # in minutes
    due_date: datetime
    priority: int
    project_id: str
    constraints: TaskConstraints

    def validate(self) -> List[str]:
        errors = []
        
        if self.duration <= 0:
            errors.append("Task duration must be positive")
            
        if self.due_date < datetime.now():
            errors.append("Due date cannot be in the past")
            
        if self.constraints.is_splittable:
            total_min_duration = self.constraints.min_chunk_duration * self.constraints.max_split_count
            if total_min_duration > self.duration:
                errors.append(
                    f"Total minimum chunk duration ({total_min_duration} min) "
                    f"exceeds task duration ({self.duration} min)"
                )
                
        return errors

    def get_minimum_duration(self) -> int:
        """Returns the minimum duration needed for a single block of this task"""
        if self.constraints.is_splittable:
            return self.constraints.min_chunk_duration
        return self.duration

    def split(self, chunk_sizes: List[int]) -> List['Task']:
        """
        Split the task into multiple chunks with specified durations.
        
        Args:
            chunk_sizes: List of durations in minutes for each chunk
            
        Returns:
            List of new Task objects representing the chunks
            
        Raises:
            ValueError: If splitting violates task constraints
        """
        # Validate split parameters
        if len(chunk_sizes) > self.constraints.max_split_count:
            raise ValueError(f"Exceeds maximum split count of {self.constraints.max_split_count}")
            
        if sum(chunk_sizes) != self.duration:
            raise ValueError(f"Sum of chunk sizes ({sum(chunk_sizes)}) must equal task duration ({self.duration})")
            
        if any(size < self.constraints.min_chunk_duration for size in chunk_sizes):
            raise ValueError(f"All chunks must be at least {self.constraints.min_chunk_duration} minutes")
            
        if not self.constraints.is_splittable:
            raise ValueError("Task is not splittable")

        # Create chunks
        chunks = []
        for i, size in enumerate(chunk_sizes, 1):
            chunk = Task(
                id=f"{self.id}_chunk_{i}",
                title=f"{self.title} (Part {i}/{len(chunk_sizes)})",
                duration=size,
                due_date=self.due_date,
                priority=self.priority,
                project_id=self.project_id,
                constraints=TaskConstraints(
                    zone_type=self.constraints.zone_type,
                    energy_level=self.constraints.energy_level,
                    is_splittable=False,  # Chunks cannot be split further
                    min_chunk_duration=self.constraints.min_chunk_duration,
                    max_split_count=1,
                    required_buffer=self.constraints.required_buffer,
                    dependencies=[f"{self.id}_chunk_{i-1}"] if i > 1 else []  # Chain dependencies
                )
            )
            chunks.append(chunk)
            
        return chunks
