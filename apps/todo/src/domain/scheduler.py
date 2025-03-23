from abc import ABC, abstractmethod
from typing import List, Protocol
from datetime import datetime

from .task import Task
from .timeblock import Event, TimeBlockZone

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

class SchedulingStrategy(ABC):
    @abstractmethod
    def schedule(self, 
                tasks: List[Task],
                zones: List[TimeBlockZone],
                existing_events: List[Event]) -> List[Event]:
        pass

class Scheduler:
    def __init__(self,
                 task_repo: TaskRepository,
                 calendar_repo: CalendarRepository,
                 strategy: SchedulingStrategy):
        self.task_repo = task_repo
        self.calendar_repo = calendar_repo
        self.strategy = strategy
    
    def schedule_tasks(self, planning_horizon: int) -> None:
        """Main scheduling orchestration"""
        # Implementation here...
        pass
