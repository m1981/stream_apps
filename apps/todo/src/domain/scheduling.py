from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from .task import Task
from .timeblock import TimeBlock, TimeBlockZone, Event

@dataclass
class SchedulingConflict:
    task: Task
    conflicting_events: List[Event]
    proposed_start: datetime
    message: str

class ConflictDetector:
    """Service for detecting scheduling conflicts"""
    
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