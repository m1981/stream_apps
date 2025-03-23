from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, List

class EnergyLevel(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class ZoneType(Enum):
    DEEP = "deep"
    LIGHT = "light"
    ADMIN = "admin"

@dataclass
class TaskConstraints:
    zone_type: ZoneType
    energy_level: EnergyLevel
    is_splittable: bool
    min_chunk_duration: int  # minutes
    max_split_count: int
    required_buffer: int     # minutes
    dependencies: List[str]  # task IDs

@dataclass
class Task:
    id: str
    title: str
    duration: int           # minutes
    due_date: datetime
    priority: int
    project_id: str
    constraints: TaskConstraints