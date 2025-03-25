from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional

from .task import Task
from .scheduling import TimeBlock, TimeBlockZone, Event

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
    - Buffer requirements
    """

    @staticmethod
    def find_conflicts(
        task: Task,
        proposed_start: datetime,
        time_block: TimeBlock
    ) -> Optional[SchedulingConflict]:
        proposed_end = proposed_start + timedelta(minutes=task.duration)
        required_buffer = max(
            task.constraints.required_buffer,
            time_block.buffer_required if isinstance(time_block, TimeBlockZone) else 0
        )

        # Calculate the total duration including buffer
        total_duration = task.duration + (2 * required_buffer)  # Buffer before and after
        buffer_start = proposed_start - timedelta(minutes=required_buffer)
        
        # Get all events that could affect buffer requirements
        all_conflicts = time_block.get_conflicts(buffer_start, total_duration)
        
        # Check basic time slot availability
        direct_conflicts = [
            event for event in all_conflicts
            if (event.start < proposed_end and event.end > proposed_start)
        ]
        if direct_conflicts:
            return SchedulingConflict(
                task=task,
                conflicting_events=direct_conflicts,
                proposed_start=proposed_start,
                message="Time slot has conflicting events"
            )

        # Check buffer violations
        buffer_conflicts = [
            event for event in all_conflicts
            if (
                # Check if event ends too close to our start
                (event.end <= proposed_start and 
                 (proposed_start - event.end).total_seconds() / 60 < required_buffer) or
                # Check if event starts too close to our end
                (event.start >= proposed_end and 
                 (event.start - proposed_end).total_seconds() / 60 < required_buffer)
            )
        ]
        if buffer_conflicts:
            return SchedulingConflict(
                task=task,
                conflicting_events=buffer_conflicts,
                proposed_start=proposed_start,
                message=f"Buffer requirement of {required_buffer} minutes not met"
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
                
            if task.duration < time_block.min_duration:
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
        
        # Get required buffer
        required_buffer = max(
            task.constraints.required_buffer,
            time_block.buffer_required if isinstance(time_block, TimeBlockZone) else 0
        )

        # Get all events in the time block
        all_events = time_block.events
        if all_events:
            # If there are events and we're starting at the block start,
            # adjust start time to include buffer after previous event if needed
            last_event_before = max(
                (e for e in all_events if e.end <= current_time),
                key=lambda e: e.end,
                default=None
            )
            if last_event_before:
                min_start = last_event_before.end + timedelta(minutes=required_buffer)
                current_time = max(current_time, min_start)
        
        while current_time < end_time:
            if not ConflictDetector.find_conflicts(task, current_time, time_block):
                return current_time
            current_time += timedelta(minutes=15)  # 15-minute increments
            
        return None