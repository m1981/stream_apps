from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import pytest
from src.domain.task import Task, TaskConstraints, ZoneType, EnergyLevel
from src.domain.scheduling.strategies import SequenceBasedStrategy
from src.domain.timeblock import TimeBlockZone
from src.domain.scheduler import Scheduler

@pytest.fixture
def work_day_zones():
    start_time = datetime(2024, 1, 1, 9)  # 9 AM
    return [
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

@pytest.fixture
def scheduler(work_day_zones):
    task_repo = Mock()
    calendar_repo = Mock()
    strategy = SequenceBasedStrategy()
    
    # Configure mock behavior
    calendar_repo.get_events.return_value = []
    calendar_repo.get_zones.return_value = work_day_zones
    task_repo.get_tasks.return_value = []
    
    return Scheduler(
        task_repo=task_repo,
        calendar_repo=calendar_repo,
        strategy=strategy
    )

def test_reschedule_splits_tasks_when_necessary(scheduler, work_day_zones):
    """
    When: No continuous block available
    Then: Splittable tasks should be split
    And: Split chunks should respect minimum duration
    """
    # Define a fixed reference date for testing
    reference_date = datetime(2024, 1, 1)
    
    # Create a mock datetime object
    mock_datetime = Mock(wraps=datetime)
    mock_datetime.now.return_value = reference_date
    
    # Create patches for all relevant modules
    patches = [
        patch('src.domain.scheduling.strategies.datetime', mock_datetime),
        patch('src.domain.scheduler.datetime', mock_datetime),
        patch('src.domain.timeblock.datetime', mock_datetime)
    ]
    
    # Apply all patches
    for p in patches:
        p.start()
    
    try:
        # Given: A task that's too long for single block
        task = Task(
            id="splittable",
            title="Splittable Task",
            duration=240,  # 4 hours total
            due_date=reference_date + timedelta(days=2),
            project_id="proj1",
            sequence_number=1,
            constraints=TaskConstraints(
                zone_type=ZoneType.DEEP,
                energy_level=EnergyLevel.HIGH,
                is_splittable=True,
                min_chunk_duration=60,  # 1 hour minimum
                max_split_count=4,
                required_buffer=15,
                dependencies=[]
            )
        )

        # Define fixed zones for testing
        test_zones = [
            TimeBlockZone(
                start=reference_date.replace(hour=9),  # Jan 1, 9 AM
                end=reference_date.replace(hour=13),   # Jan 1, 1 PM
                zone_type=ZoneType.DEEP,
                energy_level=EnergyLevel.HIGH,
                min_duration=30,
                buffer_required=15,
                events=[]
            ),
            TimeBlockZone(
                start=(reference_date + timedelta(days=1)).replace(hour=9),  # Jan 2, 9 AM
                end=(reference_date + timedelta(days=1)).replace(hour=13),   # Jan 2, 1 PM
                zone_type=ZoneType.DEEP,
                energy_level=EnergyLevel.HIGH,
                min_duration=30,
                buffer_required=15,
                events=[]
            )
        ]

        # Override the calendar repository's get_zones
        scheduler.calendar_repo.get_zones.return_value = test_zones

        # When: Scheduling the task
        result = scheduler.reschedule([task])
        
        # Debug output before assertions
        print("\nAvailable zones:")
        for zone in test_zones:
            print(f"Zone: {zone.start} - {zone.end}")
        
        print("\nScheduled events:")
        for event in result:
            print(f"Event {event.id}: {event.start} - {event.end}")
        
        # Then: Task should be split into valid chunks
        split_events = [e for e in result if e.id.startswith("splittable")]
        assert len(split_events) > 1, "Task should be split into multiple chunks"
        
        # And: Each chunk should respect minimum duration
        for event in split_events:
            chunk_duration = (event.end - event.start).total_seconds() / 60
            assert chunk_duration >= 60, f"Chunk {event.id} duration ({chunk_duration} min) is less than minimum (60 min)"
        
        # And: Total duration should match original task
        total_duration = sum((e.end - e.start).total_seconds() / 60 for e in split_events)
        assert total_duration == 240, f"Total duration ({total_duration} min) should match original task (240 min)"

        # And: Each chunk should be in a valid DEEP zone
        available_zones = scheduler.calendar_repo.get_zones()
        for event in split_events:
            scheduled_zone = next(
                (z for z in available_zones if z.start <= event.start < z.end),
                None
            )
            assert scheduled_zone is not None, f"Event {event.id} ({event.start} - {event.end}) not in any zone"
            assert scheduled_zone.zone_type == ZoneType.DEEP, f"Event {event.id} in wrong zone type"
            assert scheduled_zone.energy_level == EnergyLevel.HIGH, f"Event {event.id} in wrong energy level"

        # And: Chunks should be properly sequenced with buffers
        sorted_events = sorted(split_events, key=lambda e: e.start)
        for i in range(len(sorted_events) - 1):
            current = sorted_events[i]
            next_event = sorted_events[i + 1]
            
            # Check for same-day events
            if current.start.date() == next_event.start.date():
                buffer = (next_event.start - current.end).total_seconds() / 60
                assert buffer >= 15, f"Buffer between {current.id} and {next_event.id} is {buffer} minutes"

        # Final debug output
        print("\nScheduled chunks:")
        for event in sorted_events:
            print(f"- {event.id}: {event.start.strftime('%Y-%m-%d %H:%M')} - {event.end.strftime('%H:%M')}")

    finally:
        # Clean up all patches
        for p in patches:
            p.stop()





def test_reschedule_handles_energy_level_changes(scheduler, work_day_zones):
    """
    When: Energy levels change throughout day
    Then: Tasks should be scheduled in appropriate energy zones
    And: Tasks should respect energy level constraints
    """
    # Given: Two tasks with different energy requirements
    high_energy_task = Task(
        id="high_energy",
        title="Complex Analysis",
        duration=120,  # 2 hours
        due_date=datetime.now() + timedelta(days=1),
        project_id="proj1",
        sequence_number=1,
        constraints=TaskConstraints(
            zone_type=ZoneType.DEEP,
            energy_level=EnergyLevel.HIGH,
            is_splittable=True,
            min_chunk_duration=60,
            max_split_count=2,
            required_buffer=15,
            dependencies=[]
        )
    )
    
    low_energy_task = Task(
        id="low_energy",
        title="Review Documents",
        duration=90,  # 1.5 hours
        due_date=datetime.now() + timedelta(days=1),
        project_id="proj1",
        sequence_number=2,
        constraints=TaskConstraints(
            zone_type=ZoneType.LIGHT,
            energy_level=EnergyLevel.LOW,
            is_splittable=False,
            min_chunk_duration=90,
            max_split_count=1,
            required_buffer=15,
            dependencies=[]
        )
    )
    
    # When: Scheduling both tasks
    result = scheduler.reschedule([high_energy_task, low_energy_task])
    
    # Then: Tasks should be scheduled in appropriate energy zones
    high_energy_events = [e for e in result if e.id.startswith("high_energy")]
    low_energy_events = [e for e in result if e.id.startswith("low_energy")]
    
    # High energy task should be in morning (DEEP) zone
    for event in high_energy_events:
        scheduled_zone = next(z for z in work_day_zones 
                            if z.start <= event.start < z.end)
        assert scheduled_zone.zone_type == ZoneType.DEEP
        assert scheduled_zone.energy_level == EnergyLevel.HIGH
        
    # Low energy task should be in afternoon (LIGHT) zone
    for event in low_energy_events:
        scheduled_zone = next(z for z in work_day_zones 
                            if z.start <= event.start < z.end)
        assert scheduled_zone.zone_type == ZoneType.LIGHT
        assert scheduled_zone.energy_level == EnergyLevel.MEDIUM
    
    # And: Buffer requirements should be maintained
    all_events = sorted(result, key=lambda x: x.start)
    for i in range(len(all_events) - 1):
        buffer = (all_events[i + 1].start - all_events[i].end).total_seconds() / 60
        assert buffer >= 15  # Required buffer

def test_multi_day_zone_transitions():
    """
    When: Creating zones across multiple days
    Then: Zone transitions should maintain energy patterns
    And: Zone types should be consistent across days
    """
    # Given: Base day zones template
    start_time = datetime(2024, 1, 1, 9)  # 9 AM
    base_zones = [
        TimeBlockZone(
            start=start_time,  # 9 AM
            end=start_time + timedelta(hours=3),   # 12 PM
            zone_type=ZoneType.DEEP,
            energy_level=EnergyLevel.HIGH,
            min_duration=30,
            buffer_required=15,
            events=[]
        ),
        TimeBlockZone(
            start=start_time + timedelta(hours=4),  # 1 PM
            end=start_time + timedelta(hours=8),    # 5 PM
            zone_type=ZoneType.LIGHT,
            energy_level=EnergyLevel.MEDIUM,
            min_duration=30,
            buffer_required=15,
            events=[]
        )
    ]

    # When: Creating multi-day zones
    strategy = SequenceBasedStrategy()
    multi_day_zones = strategy._create_multi_day_zones(base_zones, days=3)

    # Then: Should have correct number of zones
    assert len(multi_day_zones) == len(base_zones) * 3

    # And: Zone types and energy levels should be consistent across days
    for day in range(3):
        day_offset = len(base_zones) * day
        
        # Check morning DEEP zone
        morning_zone = multi_day_zones[day_offset]
        assert morning_zone.zone_type == ZoneType.DEEP
        assert morning_zone.energy_level == EnergyLevel.HIGH
        assert morning_zone.start == start_time + timedelta(days=day)
        
        # Check afternoon LIGHT zone
        afternoon_zone = multi_day_zones[day_offset + 1]
        assert afternoon_zone.zone_type == ZoneType.LIGHT
        assert afternoon_zone.energy_level == EnergyLevel.MEDIUM
        assert afternoon_zone.start == start_time + timedelta(days=day, hours=4)
