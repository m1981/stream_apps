from abc import ABC, abstractmethod
from typing import List
from ..task import Task
from ..timeblock import TimeBlockZone, Event

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