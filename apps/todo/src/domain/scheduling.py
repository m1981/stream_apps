from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Optional

from .task import Task, ZoneType, EnergyLevel

class TimeBlockType(Enum):
    FIXED = "fixed"
    MANAGED = "managed"

@dataclass
class Event:
    id: str
    start: datetime
    end: datetime
    title: str
    type: TimeBlockType

@dataclass
class TimeBlock:
    start: datetime
    end: datetime
    type: TimeBlockType
    events: List[Event]

    def get_conflicts(self, start_time: datetime, duration: int) -> List[Event]:
        """
        Find any events that conflict with the proposed time slot.
        
        Args:
            start_time: Proposed start time for new event
            duration: Duration in minutes
            
        Returns:
            List of conflicting events, empty if no conflicts
        """
        end_time = start_time + timedelta(minutes=duration)
        return [
            event for event in self.events
            if (start_time < event.end and end_time > event.start)
        ]

@dataclass
class TimeBlockZone(TimeBlock):
    zone_type: ZoneType
    energy_level: EnergyLevel
    min_duration: int
    buffer_required: int
    events: List[Event]

class SchedulingStrategy(ABC):
    """
    Abstract base class for implementing different scheduling strategies.
    Strategies determine how tasks are assigned to available time blocks.
    """
    
    @abstractmethod
    def schedule(self, tasks: List[Task], zones: List[TimeBlockZone], existing_events: List[Event]) -> List[Event]:
        """
        Schedule tasks into available time blocks according to strategy rules.
        
        Args:
            tasks: List of tasks to be scheduled
            zones: List of available time block zones
            existing_events: List of existing calendar events to work around
            
        Returns:
            List of newly created events representing scheduled tasks
        """
        pass

"""
Scheduling conflict detection and resolution system.

Domain Context:
- Validates task placement in time blocks
- Detects conflicts with existing events
- Ensures zone and energy level compatibility
- Manages buffer requirements between tasks

Business Rules:
- Tasks can only be scheduled in compatible zones
- Energy levels must match between task and zone
- Minimum duration constraints must be respected
- Buffer time must be maintained between tasks
- No overlapping with existing events

Architecture:
- ConflictDetector is a stateless service
- SchedulingConflict represents validation failures
- Conflict detection is separate from resolution
"""

@dataclass
class SchedulingConflict:
    task: Task
    conflicting_events: List[Event]
    proposed_start: datetime
    message: str

class ConflictDetector:
    """
    Detects scheduling conflicts for tasks based on:
    - Time slot availability
    - Zone type compatibility (DEEP/LIGHT/ADMIN)
    - Energy level requirements
    """

    @staticmethod
    def find_conflicts(
        task: Task,
        proposed_start: datetime,
        time_block: TimeBlock
    ) -> Optional[SchedulingConflict]:
        # Basic time block availability
        conflicts = time_block.get_conflicts(proposed_start, task.duration)
        if conflicts:
            return SchedulingConflict(
                task=task,
                conflicting_events=conflicts,
                proposed_start=proposed_start,
                message="Time slot has conflicting events"
            )
            
        # Check zone constraints if applicable
        if isinstance(time_block, TimeBlockZone):
            if time_block.zone_type != task.constraints.zone_type:
                return SchedulingConflict(
                    task=task,
                    conflicting_events=[],
                    proposed_start=proposed_start,
                    message=f"Task requires {task.constraints.zone_type.value} zone"
                )
                
            if time_block.energy_level != task.constraints.energy_level:
                return SchedulingConflict(
                    task=task,
                    conflicting_events=[],
                    proposed_start=proposed_start,
                    message=f"Task requires {task.constraints.energy_level.value} energy level"
                )
                
            if task.get_minimum_duration() < time_block.min_duration:
                return SchedulingConflict(
                    task=task,
                    conflicting_events=[],
                    proposed_start=proposed_start,
                    message=f"Task duration below zone minimum ({time_block.min_duration} min)"
                )
        
        return None

    @staticmethod
    def find_available_slot(
        task: Task,
        time_block: TimeBlock,
        start_from: datetime
    ) -> Optional[datetime]:
        current_time = max(start_from, time_block.start)
        end_time = min(task.due_date, time_block.end)
        
        while current_time < end_time:
            if not ConflictDetector.find_conflicts(task, current_time, time_block):
                return current_time
            current_time += timedelta(minutes=15)  # 15-minute increments
            
        return None