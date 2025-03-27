import pytest
from datetime import datetime, timedelta
from src.domain.task import Task, TaskConstraints, ZoneType, EnergyLevel
from src.domain.scheduler import Scheduler
from src.domain.timeblock import TimeBlockZone, Event, TimeBlockType
from src.domain.scheduling.strategies import SequenceBasedStrategy

def test_schedule_dependent_tasks_different_zones():
    # ARRANGE
    start_time = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
    
    # Create both DEEP and LIGHT zones
    zones = [
        TimeBlockZone(
            start=start_time,
            end=start_time + timedelta(hours=4),
            zone_type=ZoneType.DEEP,
            energy_level=EnergyLevel.HIGH,
            min_duration=30,
            buffer_required=15,
            events=[]
        ),
        TimeBlockZone(
            start=start_time + timedelta(hours=4),
            end=start_time + timedelta(hours=8),
            zone_type=ZoneType.LIGHT,
            energy_level=EnergyLevel.MEDIUM,
            min_duration=30,
            buffer_required=15,
            events=[]
        )
    ]
    
    write_task = Task(
        id="write",
        title="Write Document",
        duration=90,
        due_date=start_time + timedelta(days=1),
        project_id="proj1",
        sequence_number=1,
        constraints=TaskConstraints(
            zone_type=ZoneType.DEEP,
            energy_level=EnergyLevel.HIGH,
            is_splittable=False,
            min_chunk_duration=30,
            max_split_count=1,
            required_buffer=15,
            dependencies=[]
        )
    )
    
    review_task = Task(
        id="review",
        title="Review Document",
        duration=30,
        due_date=start_time + timedelta(days=1),
        project_id="proj1",
        sequence_number=2,
        constraints=TaskConstraints(
            zone_type=ZoneType.LIGHT,
            energy_level=EnergyLevel.MEDIUM,
            is_splittable=False,
            min_chunk_duration=30,
            max_split_count=1,
            required_buffer=15,
            dependencies=["write"]
        )
    )
    
    strategy = SequenceBasedStrategy()
    
    # ACT
    scheduled_events = strategy.schedule([write_task, review_task], zones, [])
    
    # ASSERT
    assert len(scheduled_events) == 2, "Both tasks should be scheduled"
    
    write_event = next(e for e in scheduled_events if e.id == "write")
    review_event = next(e for e in scheduled_events if e.id == "review")
    
    # Verify correct zone assignment
    assert write_event.start.hour == 9, "Write task should start in DEEP zone"
    assert review_event.start.hour == 13, "Review task should start in LIGHT zone"
    
    # Verify sequence
    assert write_event.end <= review_event.start, "Review should start after write completes"
    
    # Verify buffer time
    buffer_time = (review_event.start - write_event.end).total_seconds() / 60
    assert buffer_time >= 15, "Should maintain minimum buffer time"