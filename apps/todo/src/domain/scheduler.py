from typing import List, Protocol
from datetime import datetime, timedelta

from .task import Task
from .timeblock import Event, TimeBlockZone, ZoneType, EnergyLevel
from .scheduling import SchedulingStrategy

"""
Task scheduling orchestration and strategy implementation.

Domain Context:
- Coordinates task scheduling within planning horizon
- Manages interaction between tasks and calendar
- Implements different scheduling strategies
- Handles task repository and calendar integration

Business Rules:
- Tasks are scheduled within defined planning horizon
- Higher priority tasks get preferred slots
- Dependencies must be respected
- Zone matching rules must be followed
- Buffer times must be maintained

Architecture:
- SchedulingStrategy defines scheduling algorithm interface
- TaskRepository abstracts task storage
- CalendarRepository abstracts calendar operations
- Scheduler orchestrates the entire process

System Constraints:
- Planning horizon typically 7-28 days
- Must handle both fixed and managed events
- Must support rescheduling of existing tasks
"""

class TaskRepository(Protocol):
    def get_tasks(self) -> List[Task]:
        pass
    
    def mark_scheduled(self, task_id: str) -> None:
        pass

class CalendarRepository(Protocol):
    def get_events(self, start: datetime, end: datetime) -> List[Event]:
        pass
    
    def create_event(self, event: Event) -> str:
        pass
    
    def remove_managed_events(self) -> None:
        pass

class Scheduler:
    def __init__(self,
                 task_repo: TaskRepository,
                 calendar_repo: CalendarRepository,
                 strategy: SchedulingStrategy):
        self.task_repo = task_repo
        self.calendar_repo = calendar_repo
        self.strategy = strategy
    
    def schedule_tasks(self, planning_horizon: int = 7) -> List[Event]:
        """Schedule tasks within the given planning horizon"""
        # Get tasks to schedule
        tasks = self.task_repo.get_tasks()
        if not tasks:
            return []

        # Calculate planning window
        start = datetime.now().replace(hour=9, minute=0)
        end = start + timedelta(days=planning_horizon)
        
        # Get existing events
        existing_events = self.calendar_repo.get_events(start, end)
        
        # Create default zone if none provided
        zones = [TimeBlockZone(
            start=start,
            end=start + timedelta(hours=4),
            zone_type=ZoneType.DEEP,
            energy_level=EnergyLevel.HIGH,
            min_duration=30,
            buffer_required=15,
            events=[]
        )]
        
        # Use strategy to create schedule
        scheduled_events = self.strategy.schedule(tasks, zones, existing_events)
        
        # Remove existing managed events before creating new ones
        self.calendar_repo.remove_managed_events()
        
        # Create new events in calendar
        for event in scheduled_events:
            self.calendar_repo.create_event(event)
            
        return scheduled_events
