from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Optional

from .task import ZoneType, EnergyLevel

class TimeBlockType(Enum):
    FIXED = "fixed"
    MANAGED = "managed"
    ZONE = "zone"

@dataclass
class Event:
    id: str
    start:  datetime
    end: datetime
    title: str
    type: TimeBlockType

@dataclass
class TimeBlock:
    start: datetime
    end: datetime
    type: TimeBlockType
    events: List[Event] = field(default_factory=list)

    def is_available(self, start: datetime, duration: int) -> bool:
        if start < self.start or start + timedelta(minutes=duration) > self.end:
            return False
        return len(self.get_conflicts(start, duration)) == 0

    def get_conflicts(self, start: datetime, duration: int) -> List[Event]:
        end = start + timedelta(minutes=duration)
        return [
            event for event in self.events
            if (start < event.end and end > event.start)
        ]

@dataclass
class TimeBlockZone:
    start: datetime
    end: datetime
    zone_type: ZoneType
    energy_level: EnergyLevel
    min_duration: int  # in minutes
    buffer_required: int  # in minutes
    type: TimeBlockType = TimeBlockType.ZONE
    events: List[Event] = field(default_factory=list)

    def is_available(self, start: datetime, duration: int) -> bool:
        # Check if duration meets minimum requirement
        if duration < self.min_duration:
            return False
            
        # Check time bounds and conflicts
        if start < self.start or start + timedelta(minutes=duration) > self.end:
            return False
        return len(self.get_conflicts(start, duration)) == 0

    def get_conflicts(self, start: datetime, duration: int) -> List[Event]:
        # Basic time conflicts
        end = start + timedelta(minutes=duration)
        conflicts = [
            event for event in self.events
            if (start < event.end and end > event.start)
        ]
        
        # Check for buffer violations
        if self.buffer_required > 0:
            buffer_start = start - timedelta(minutes=self.buffer_required)
            buffer_end = start + timedelta(minutes=duration + self.buffer_required)
            
            buffer_conflicts = [
                event for event in self.events
                if (buffer_start < event.end and buffer_end > event.start)
                and event not in conflicts
            ]
            
            conflicts.extend(buffer_conflicts)
            
        return conflicts
