import pytest
from datetime import datetime, timedelta
from typing import List
from src.domain.task import Task, TaskConstraints, ZoneType, EnergyLevel
from src.domain.scheduler import Scheduler
from src.domain.timeblock import TimeBlockZone, Event, TimeBlockType
from src.domain.scheduling import SequenceBasedStrategy
from unittest.mock import Mock

@pytest.fixture
def work_day_zones():
    start_time = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
    return [
        TimeBlockZone(
            zone_type=ZoneType.DEEP,
            start=start_time,
            end=start_time + timedelta(hours=4),  # 9:00 - 13:00
            energy_level=EnergyLevel.HIGH,
            min_duration=30,
            buffer_required=15,
            events=[]
        ),
        TimeBlockZone(
            zone_type=ZoneType.LIGHT,
            start=start_time + timedelta(hours=4),
            end=start_time + timedelta(hours=8),  # 13:00 - 17:00
            energy_level=EnergyLevel.MEDIUM,
            min_duration=30,
            buffer_required=15,
            events=[]
        )
    ]

def test_reschedule_maintains_relative_task_order(work_day_zones):
    """
    When: Multiple tasks are rescheduled
    Then: Their relative order should be maintained
    """
    # Create mock repositories and strategy
    task_repo = Mock()
    calendar_repo = Mock()
    strategy = SequenceBasedStrategy()

    # Configure mock behavior
    calendar_repo.get_events.return_value = []
    calendar_repo.get_zones.return_value = work_day_zones
    task_repo.get_tasks.return_value = []

    # Create tasks with sequential order
    task1 = Task(
        id="task1",
        title="First Task",
        duration=60,
        due_date=datetime.now() + timedelta(days=1),
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

    task2 = Task(
        id="task2",
        title="Second Task",
        duration=60,
        due_date=datetime.now() + timedelta(days=1),
        project_id="proj1",
        sequence_number=2,
        constraints=TaskConstraints(
            zone_type=ZoneType.DEEP,
            energy_level=EnergyLevel.HIGH,
            is_splittable=False,
            min_chunk_duration=30,
            max_split_count=1,
            required_buffer=15,
            dependencies=["task1"]
        )
    )

    # Create scheduler
    scheduler = Scheduler(
        task_repo=task_repo,
        calendar_repo=calendar_repo,
        strategy=strategy
    )

    # Reschedule tasks
    schedule = scheduler.reschedule([task1, task2])

    # Get scheduled events
    event1 = next(e for e in schedule if e.id == "task1")
    event2 = next(e for e in schedule if e.id == "task2")

    # Verify order
    assert event1.start < event2.start, "Task1 should be scheduled before Task2"
    
    # Verify buffer
    buffer_time = (event2.start - event1.end).total_seconds() / 60
    assert buffer_time >= 15, "Buffer between tasks should be at least 15 minutes"
