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

"""
Domain model for Tasks in the intelligent time-blocking system.

Domain Context:
- Tasks represent work items that need to be scheduled into specific time zones
- Each task has specific zone and energy requirements that constrain when it can be scheduled
- Tasks can optionally be split into smaller chunks to fit available time slots
- Tasks maintain dependencies to ensure correct execution order

Business Rules:
- Tasks must be scheduled in compatible time zones (DEEP/LIGHT/ADMIN)
- Tasks require specific energy levels (HIGH/MEDIUM/LOW)
- Splittable tasks must respect minimum chunk duration
- Split tasks create a dependency chain (chunk2 depends on chunk1)
- Buffer time must be maintained between tasks
- Tasks cannot be scheduled in the past

Architecture:
- Task is an immutable domain entity
- TaskConstraints encapsulates all scheduling rules
- Task splitting creates new Task instances
- Validation rules are self-contained within the Task
"""

@dataclass
class TaskConstraints:
    """
    Encapsulates all scheduling constraints for a task.
    
    Business Rules:
    - zone_type determines valid time blocks (DEEP/LIGHT/ADMIN)
    - energy_level must match time block's energy level
    - if splittable:
        - chunks must be >= min_chunk_duration
        - total chunks must not exceed max_split_count
        - total of minimum chunks must not exceed task duration
    - required_buffer ensures spacing between tasks
    - dependencies enforce task execution order
    """
    zone_type: ZoneType
    energy_level: EnergyLevel
    is_splittable: bool
    min_chunk_duration: int  # in minutes
    max_split_count: int
    required_buffer: int  # in minutes
    dependencies: List[str]  # task IDs

@dataclass
class Task:
    """
    Core domain entity representing a schedulable unit of work.
    
    System Constraints:
    - Task duration must be positive
    - Due date must be in the future
    - If splittable, total minimum chunk duration must not exceed task duration
    - Split tasks inherit most constraints but cannot be split further
    - Split tasks maintain sequential dependencies
    
    Usage:
    1. Task validation:
        task.validate() -> List[str]  # Returns validation errors
    
    2. Getting minimum schedulable duration:
        min_duration = task.get_minimum_duration()
    
    3. Splitting task:
        chunks = task.split([30, 30, 30])  # Creates 3 dependent chunks
    """
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
        Business rules:
        - Sum of chunks must equal original duration
        - Each chunk inherits zone and energy constraints
        - Chunks are sequentially dependent
        - First chunk inherits original dependencies
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
            # Set up dependencies for this chunk
            chunk_dependencies = []
            if i == 1:
                # First chunk inherits original task's dependencies
                chunk_dependencies = self.constraints.dependencies.copy()
            else:
                # Other chunks depend on the previous chunk
                chunk_dependencies = [f"{self.id}_chunk_{i-1}"]

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
                    dependencies=chunk_dependencies  # Use the prepared dependencies
                )
            )
            chunks.append(chunk)
            
        return chunks
