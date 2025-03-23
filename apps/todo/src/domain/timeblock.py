from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional

class TimeBlock(ABC):
    @abstractmethod
    def is_available(self, start: datetime, duration: int) -> bool:
        pass

    @abstractmethod
    def get_conflicts(self, start: datetime, duration: int) -> List['Event']:
        pass

class TimeBlockZone:
    def __init__(self, 
                 zone_type: ZoneType,
                 start_time: datetime,
                 end_time: datetime,
                 energy_level: EnergyLevel,
                 min_duration: int,
                 buffer_required: int):
        self.zone_type = zone_type
        self.start_time = start_time
        self.end_time = end_time
        self.energy_level = energy_level
        self.min_duration = min_duration
        self.buffer_required = buffer_required