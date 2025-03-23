from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional, Set
from enum import Enum

from .task import EnergyLevel, ZoneType

class TimeBlockType(Enum):
    FIXED = "fixed"        # External calendar events
    MANAGED = "managed"    # System-managed task blocks
    ZONE = "zone"         # Time block zones

@dataclass
class Event:
    id: str
    start: datetime
    end: datetime
    title: str
    type: TimeBlockType
    description: Optional[str] = None

class TimeBlock:
    """Represents a block of time that can be checked for availability"""
    
    def __init__(self, 
                 start: datetime,
                 end: datetime,
                 block_type: TimeBlockType,
                 events: Optional[List[Event]] = None):
        if start >= end:
            raise ValueError("Start time must be before end time")
        
        self.start = start
        self.end = end
        self.block_type = block_type
        self.events = events or []

    def duration_minutes(self) -> int:
        """Calculate duration in minutes"""
        return int((self.end - self.start).total_seconds() / 60)

    def is_available(self, start: datetime, duration: int) -> bool:
        if start < self.start or start >= self.end:
            return False
            
        end_time = start + timedelta(minutes=duration)
        if end_time > self.end:
            return False

        return len(self.get_conflicts(start, duration)) == 0

    def get_conflicts(self, start: datetime, duration: int) -> List[Event]:
        end_time = start + timedelta(minutes=duration)
        conflicts = []
        
        for event in self.events:
            # Check if event overlaps with proposed time
            if (event.start < end_time and event.end > start):
                conflicts.append(event)
                
        return conflicts

class TimeBlockZone(TimeBlock):
    """Represents a zone for specific type of work with energy level requirements"""
    
    def __init__(self,
                 start: datetime,
                 end: datetime,
                 zone_type: ZoneType,
                 energy_level: EnergyLevel,
                 min_duration: int,
                 buffer_required: int,
                 events: Optional[List[Event]] = None):
        super().__init__(start, end, TimeBlockType.ZONE, events)
        
        if min_duration <= 0:
            raise ValueError("Minimum duration must be positive")
        if buffer_required < 0:
            raise ValueError("Buffer time cannot be negative")
            
        self.zone_type = zone_type
        self.energy_level = energy_level
        self.min_duration = min_duration
        self.buffer_required = buffer_required

    def is_available(self, start: datetime, duration: int) -> bool:
        if duration < self.min_duration:
            return False
            
        # Add buffer time to check availability
        total_duration = duration + (2 * self.buffer_required)
        buffer_start = start - timedelta(minutes=self.buffer_required)
        
        return super().is_available(buffer_start, total_duration)

    def get_conflicts(self, start: datetime, duration: int) -> List[Event]:

        # Check conflicts including buffer periods
        buffer_start = start - timedelta(minutes=self.buffer_required)
        total_duration = duration + (2 * self.buffer_required)
        
        return super().get_conflicts(buffer_start, total_duration)