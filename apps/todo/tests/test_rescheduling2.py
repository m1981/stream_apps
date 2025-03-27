
import pytest
from datetime import datetime, timedelta
from typing import List
from src.domain.task import Task, TaskConstraints, ZoneType, EnergyLevel
from src.domain.scheduler import Scheduler
from src.domain.timeblock import TimeBlockZone, Event, TimeBlockType
from src.domain.scheduling import SequenceBasedStrategy
from unittest.mock import Mock
from src.domain.scheduling.strategies import SequenceBasedStrategy

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

@pytest.fixture
def mock_task_repo():
    class MockTaskRepository:
        def get_tasks(self):
            return []
        
        def mark_scheduled(self, task_id):
            pass
    return MockTaskRepository()

@pytest.fixture
def mock_calendar_repo():
    class MockCalendarRepository:
        def get_events(self, start, end):
            return []
        
        def create_event(self, event):
            return "new_event_id"
        
        def remove_managed_events(self):
            pass
    return MockCalendarRepository()

@pytest.fixture
def scheduler(mock_task_repo, mock_calendar_repo):
    return Scheduler(
        task_repo=mock_task_repo,
        calendar_repo=mock_calendar_repo,
        strategy=SequenceBasedStrategy()
    )

def test_reschedule_on_task_duration_change():
    """
    When: Task duration is updated
    Then: Only affected task and its dependents should be rescheduled
    And: Other tasks should maintain their original schedule
    """
    print("\n=== Test: Reschedule on Task Duration Change ===")
    
    start_time = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
    
    # Create both DEEP and LIGHT zones
    day_zones = [
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

    print("\n=== Debug Point 1: Initial Zones ===")
    for zone in day_zones:
        print(f"Zone: {zone.zone_type}, Time: {zone.start.strftime('%H:%M')}-{zone.end.strftime('%H:%M')}, "
              f"Energy: {zone.energy_level}")

    # Create mock repositories
    task_repo = Mock()
    calendar_repo = Mock()
    
    # Configure mock behavior
    calendar_repo.get_events.return_value = []
    calendar_repo.get_zones.return_value = day_zones
    task_repo.get_tasks.return_value = []

    class TestStrategy(SequenceBasedStrategy):
        def schedule(self, tasks, zones, existing_events):
            print("\n=== Debug Point 2: Strategy Schedule Called ===")
            print(f"Tasks to schedule: {[t.id for t in tasks]}")
            print(f"Initial zones count: {len(zones)}")
            
            # Create multi-day zones while preserving both zone types
            multi_day_zones = []
            for day in range(7):
                day_start = start_time + timedelta(days=day)
                for zone in day_zones:
                    new_zone = TimeBlockZone(
                        start=day_start.replace(hour=zone.start.hour, minute=zone.start.minute),
                        end=day_start.replace(hour=zone.end.hour, minute=zone.end.minute),
                        zone_type=zone.zone_type,
                        energy_level=zone.energy_level,
                        min_duration=zone.min_duration,
                        buffer_required=zone.buffer_required,
                        events=[]
                    )
                    multi_day_zones.append(new_zone)

            print("\n=== Debug Point 3: Multi-day Zones Created ===")
            for i, zone in enumerate(multi_day_zones[:4]):  # Print first 4 zones for brevity
                print(f"Zone {i}: {zone.zone_type}, "
                      f"Time: {zone.start.strftime('%Y-%m-%d %H:%M')}-{zone.end.strftime('%H:%M')}")

            result = super().schedule(tasks, multi_day_zones, existing_events)
            
            print("\n=== Debug Point 4: Schedule Result ===")
            for event in result:
                print(f"Event: {event.id}, "
                      f"Time: {event.start.strftime('%Y-%m-%d %H:%M')}-{event.end.strftime('%H:%M')}")
            
            return result

    # Create scheduler with our custom strategy
    scheduler = Scheduler(
        task_repo=task_repo,
        calendar_repo=calendar_repo,
        strategy=TestStrategy()
    )

    # Create initial task and dependent task
    task1 = Task(
        id="task1",
        title="Initial Task",
        duration=60,  # 1 hour initially
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

    dependent_task = Task(
        id="dependent",
        title="Dependent Task",
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
            dependencies=["task1"]
        )
    )

    print("\n=== Debug Point 5: Initial Tasks Configuration ===")
    print(f"Task 1: {task1.id}, Duration: {task1.duration}, Zone: {task1.constraints.zone_type}")
    print(f"Dependent: {dependent_task.id}, Duration: {dependent_task.duration}, "
          f"Zone: {dependent_task.constraints.zone_type}")

    # Initial schedule
    print("\n=== Debug Point 6: Creating Initial Schedule ===")
    initial_schedule = scheduler.reschedule([task1, dependent_task])
    
    print("\n=== Debug Point 7: Initial Schedule Created ===")
    for event in initial_schedule:
        print(f"Event: {event.id}, Time: {event.start.strftime('%H:%M')}-{event.end.strftime('%H:%M')}")
    
    # Record initial timing of dependent task
    initial_dependent_event = next(e for e in initial_schedule if e.id == "dependent")
    initial_dependent_start = initial_dependent_event.start

    # Update task1 duration
    updated_task1 = Task(
        id="task1",
        title="Initial Task",
        duration=120,  # Updated duration: 2 hours
        due_date=start_time + timedelta(days=1),
        project_id="proj1",
        sequence_number=1,
        constraints=task1.constraints
    )

    print("\n=== Debug Point 8: Rescheduling with Updated Duration ===")
    print(f"Updated Task 1 duration: {updated_task1.duration}")

    # Reschedule with updated duration
    updated_schedule = scheduler.reschedule([updated_task1, dependent_task])

    print("\n=== Debug Point 9: Final Schedule ===")
    for event in updated_schedule:
        print(f"Event: {event.id}, Time: {event.start.strftime('%H:%M')}-{event.end.strftime('%H:%M')}")

    # Verify results
    updated_task1_event = next(e for e in updated_schedule if e.id == "task1")
    updated_dependent_event = next(e for e in updated_schedule if e.id == "dependent")

    # Verify task1 has new duration
    task1_duration = (updated_task1_event.end - updated_task1_event.start).total_seconds() / 60
    print(f"\n=== Debug Point 10: Verification ===")
    print(f"Task1 actual duration: {task1_duration} minutes")
    print(f"Task1 expected duration: {updated_task1.duration} minutes")
    print(f"Dependent task moved: {updated_dependent_event.start != initial_dependent_start}")
    
    assert task1_duration == 120, f"Expected duration 120, got {task1_duration}"

    # Verify dependent task was rescheduled after task1
    assert updated_dependent_event.start > updated_task1_event.end

    # Verify proper buffer between tasks
    buffer_time = (updated_dependent_event.start - updated_task1_event.end).total_seconds() / 60
    print(f"Buffer time between tasks: {buffer_time} minutes")
    assert buffer_time >= 15, f"Expected buffer >= 15 minutes, got {buffer_time} minutes"

def test_reschedule_preserves_zone_integrity(work_day_zones):
    """
    When: Task is rescheduled
    Then: Zone type constraints must be maintained
    And: Energy level requirements must be respected
    """
    # Create mock repositories and strategy
    task_repo = Mock()
    calendar_repo = Mock()
    strategy = SequenceBasedStrategy()

    # Configure mock behavior
    calendar_repo.get_events.return_value = []
    calendar_repo.get_zones.return_value = work_day_zones
    task_repo.get_tasks.return_value = []

    deep_task = Task(
        id="deep_work",
        title="Deep Work Task",
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

    # Create scheduler with all required dependencies
    scheduler = Scheduler(
        task_repo=task_repo,
        calendar_repo=calendar_repo,
        strategy=strategy
    )

    new_schedule = scheduler.reschedule([deep_task])

    deep_event = next(e for e in new_schedule if e.id == "deep_work")
    scheduled_zone = next(z for z in work_day_zones
                          if z.start <= deep_event.start <= z.end)

    assert scheduled_zone.zone_type == ZoneType.DEEP  # Changed from type to zone_type
    assert scheduled_zone.energy_level == EnergyLevel.HIGH

def test_reschedule_maintains_project_sequence():
    """
    When: Tasks in project sequence are rescheduled
    Then: Project task sequence should be maintained
    """
    # Create mock repositories
    task_repo = Mock()
    calendar_repo = Mock()
    strategy = SequenceBasedStrategy()
    
    morning = datetime.now().replace(hour=9, minute=0)
    fixed_events = [
        Event(
            id="meeting1",
            title="Morning Meeting",
            start=morning + timedelta(hours=1),  # 10:00
            end=morning + timedelta(hours=2),    # 11:00
            type=TimeBlockType.FIXED
        ),
        Event(
            id="meeting2",
            title="Afternoon Meeting",
            start=morning + timedelta(hours=3),  # 12:00
            end=morning + timedelta(hours=4),    # 13:00
            type=TimeBlockType.FIXED
        )
    ]

    # Create zones that match the task requirements
    work_day_zones = [
        TimeBlockZone(
            zone_type=ZoneType.DEEP,  # Required positional argument
            start=morning,
            end=morning + timedelta(hours=8),  # 9:00 - 17:00
            energy_level=EnergyLevel.HIGH,
            min_duration=30,
            buffer_required=15,
            type=TimeBlockType.MANAGED,
            events=fixed_events.copy()  # Include fixed events in zone
        )
    ]

    # Configure mock behavior
    calendar_repo.get_events.return_value = []
    calendar_repo.get_zones.return_value = work_day_zones
    task_repo.get_tasks.return_value = []

    base_constraints = TaskConstraints(
        zone_type=ZoneType.DEEP,
        energy_level=EnergyLevel.HIGH,
        is_splittable=False,
        min_chunk_duration=30,
        max_split_count=1,
        required_buffer=15,
        dependencies=[]
    )

    tasks = [
        Task(
            id="step1",
            title="Step 1",
            duration=60,
            due_date=datetime.now() + timedelta(days=1),
            project_id="proj1",
            sequence_number=1,
            constraints=base_constraints
        ),
        Task(
            id="step2",
            title="Step 2",
            duration=60,
            due_date=datetime.now() + timedelta(days=1),
            project_id="proj1",
            sequence_number=2,
            constraints=base_constraints
        ),
        Task(
            id="step3",
            title="Step 3",
            duration=60,
            due_date=datetime.now() + timedelta(days=1),
            project_id="proj1",
            sequence_number=3,
            constraints=base_constraints
        )
    ]

    scheduler = Scheduler(
        task_repo=task_repo,
        calendar_repo=calendar_repo,
        strategy=strategy
    )

    # Reschedule ALL tasks, not just the middle one
    new_schedule = scheduler.reschedule(tasks)

    # Verify sequence
    scheduled_ids = [e.id for e in new_schedule]
    assert len(scheduled_ids) == 3, f"Expected 3 tasks, got {len(scheduled_ids)}"
    assert scheduled_ids == ["step1", "step2", "step3"], f"Incorrect sequence: {scheduled_ids}"

    # Verify timing
    events = sorted(new_schedule, key=lambda e: e.start)
    for i in range(len(events) - 1):
        assert events[i].end <= events[i + 1].start, (
            f"Task {events[i].id} overlaps with {events[i + 1].id}"
        )

def test_reschedule_handles_buffer_requirements(work_day_zones):
    """
    When: Tasks are rescheduled
    Then: Required buffer times must be maintained
    And: Zone transition buffers must be respected
    """
    # Create mock repositories and strategy
    task_repo = Mock()
    calendar_repo = Mock()
    strategy = SequenceBasedStrategy()

    # Configure mock return values
    calendar_repo.get_events.return_value = []
    calendar_repo.get_zones.return_value = work_day_zones
    task_repo.get_tasks.return_value = []

    # Create task constraints
    task1_constraints = TaskConstraints(
        zone_type=ZoneType.DEEP,
        energy_level=EnergyLevel.HIGH,
        is_splittable=False,
        min_chunk_duration=30,
        max_split_count=1,
        required_buffer=15,
        dependencies=[]
    )

    task2_constraints = TaskConstraints(
        zone_type=ZoneType.DEEP,
        energy_level=EnergyLevel.HIGH,
        is_splittable=False,
        min_chunk_duration=30,
        max_split_count=1,
        required_buffer=30,
        dependencies=[]
    )

    # Create tasks with all required arguments
    tasks = [
        Task(
            id="task1",
            title="Task 1",
            duration=60,
            due_date=datetime.now() + timedelta(days=1),
            sequence_number=1,
            project_id="proj1",
            constraints=task1_constraints
        ),
        Task(
            id="task2",
            title="Task 2",
            duration=60,
            due_date=datetime.now() + timedelta(days=1),
            sequence_number=2,
            project_id="proj1",
            constraints=task2_constraints
        )
    ]

    # Create scheduler with dependencies
    scheduler = Scheduler(
        task_repo=task_repo,
        calendar_repo=calendar_repo,
        strategy=strategy
    )

    schedule = scheduler.reschedule(tasks)

    task1_event = next(e for e in schedule if e.id == "task1")
    task2_event = next(e for e in schedule if e.id == "task2")

    buffer_time = (task2_event.start - task1_event.end).total_seconds() / 60
    assert buffer_time >= 30  # Larger buffer should be used

def test_reschedule_handles_partial_day_availability():
    """
    When: Calendar has fixed events
    Then: Tasks should be rescheduled around fixed events
    And: No overlap should occur
    """
    # Create mock repositories
    task_repo = Mock()
    calendar_repo = Mock()
    strategy = SequenceBasedStrategy()
    
    morning = datetime.now().replace(hour=9, minute=0)
    fixed_events = [
        Event(
            id="meeting",
            title="Daily Standup",
            start=morning + timedelta(hours=1),
            end=morning + timedelta(hours=2),
            type=TimeBlockType.FIXED
        )
    ]

    # Create zones that match the task requirements
    work_day_zones = [
        TimeBlockZone(
            zone_type=ZoneType.DEEP,  # Required positional argument
            start=morning,
            end=morning + timedelta(hours=8),  # 9:00 - 17:00
            energy_level=EnergyLevel.HIGH,
            min_duration=30,
            buffer_required=15,
            type=TimeBlockType.MANAGED,
            events=fixed_events.copy()  # Include fixed events in zone
        )
    ]

    # Configure mock behavior
    calendar_repo.get_events.return_value = []
    calendar_repo.get_zones.return_value = work_day_zones
    task_repo.get_tasks.return_value = []

    task = Task(
        id="work",
        title="Work Task",
        duration=120,
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

    # Create scheduler with all required dependencies
    scheduler = Scheduler(
        task_repo=task_repo,
        calendar_repo=calendar_repo,
        strategy=strategy
    )

    schedule = scheduler.reschedule([task], fixed_events=fixed_events)

    work_event = next(e for e in schedule if e.id == "work")
    # Check overlap with each fixed event
    for fixed_event in fixed_events:
        assert not (work_event.start < fixed_event.end and
                   work_event.end > fixed_event.start)

def test_reschedule_splits_tasks_when_necessary(scheduler, work_day_zones):
    """
    When: No continuous block available
    Then: Splittable tasks should be split
    And: Split chunks should respect minimum duration
    """
    # Create a task that's too long to fit in any single available block
    task = Task(
        id="splittable",
        title="Splittable Task",
        duration=240,  # 4 hours total
        due_date=datetime.now() + timedelta(days=1),
        project_id="proj1",
        sequence_number=1,
        constraints=TaskConstraints(
            zone_type=ZoneType.DEEP,
            energy_level=EnergyLevel.HIGH,
            is_splittable=True,
            min_chunk_duration=60,  # 1 hour minimum chunks
            max_split_count=4,
            required_buffer=15,
            dependencies=[]
        )
    )

    # Create fixed events that force splitting
    morning = datetime.now().replace(hour=9, minute=0)
    fixed_events = [
        Event(
            id="meeting1",
            title="Morning Meeting",
            start=morning + timedelta(hours=1),  # 10:00
            end=morning + timedelta(hours=2),    # 11:00
            type=TimeBlockType.FIXED
        ),
        Event(
            id="meeting2",
            title="Afternoon Meeting",
            start=morning + timedelta(hours=3),  # 12:00
            end=morning + timedelta(hours=4),    # 13:00
            type=TimeBlockType.FIXED
        )
    ]

    # Create zones that match the task requirements
    work_day_zones = [
        TimeBlockZone(
            start=morning,
            end=morning + timedelta(hours=8),  # 9:00 - 17:00
            zone_type=ZoneType.DEEP,  # Changed from TimeBlockType.ZONE
            energy_level=EnergyLevel.HIGH,
            min_duration=30,
            buffer_required=15,
            events=fixed_events.copy()  # Include fixed events in zone
        )
    ]

    # Configure scheduler with our test zones
    class TestStrategy(SequenceBasedStrategy):
        def schedule(self, tasks, zones, existing_events):
            return super().schedule(tasks, work_day_zones, existing_events)
    
    scheduler.strategy = TestStrategy()
    schedule = scheduler.reschedule([task], fixed_events=fixed_events)

    # Verify splitting
    split_events = [e for e in schedule if e.id.startswith("splittable")]
    assert len(split_events) > 1  # Should have at least 2 chunks
        
    # Verify chunk durations
    assert all(
        (e.end - e.start).total_seconds() / 60 >= task.constraints.min_chunk_duration 
        for e in split_events
    )
        
    # Verify no overlap with fixed events
    for split_event in split_events:
        for fixed_event in fixed_events:
            assert not (
                split_event.start < fixed_event.end and 
                split_event.end > fixed_event.start
            )

    # Verify total duration matches original task
    total_duration = sum(
        (e.end - e.start).total_seconds() / 60 
        for e in split_events
    )
    assert total_duration == task.duration

def test_reschedule_handles_energy_level_changes(scheduler, work_day_zones):
    """
    When: Energy levels change throughout day
    Then: Tasks should be scheduled in appropriate energy zones
    """
    high_energy_task = Task(
        id="complex",
        title="Complex Task",
        duration=60,
        due_date=datetime.now() + timedelta(days=1),
        project_id="proj1",
        sequence_number=1,
        constraints=TaskConstraints(
            zone_type=ZoneType.DEEP,  # Match with available zone type
            energy_level=EnergyLevel.HIGH,
            is_splittable=False,
            min_chunk_duration=30,
            max_split_count=1,
            required_buffer=15,
            dependencies=[]
        )
    )

    # Create a strategy that uses work_day_zones
    class TestStrategy(SequenceBasedStrategy):
        def schedule(self, tasks, zones, existing_events):
            # Use work_day_zones instead of provided zones
            multi_day_zones = self._create_multi_day_zones(work_day_zones)
            return super().schedule(tasks, multi_day_zones, existing_events)

        def _create_multi_day_zones(self, base_zones: List[TimeBlockZone], days: int = 7) -> List[TimeBlockZone]:
            multi_day_zones = []
            start_date = base_zones[0].start

            for day in range(days):
                day_start = start_date + timedelta(days=day)
                for zone in base_zones:  # This will now include both DEEP and LIGHT zones
                    new_zone = TimeBlockZone(
                        zone_type=zone.zone_type,  # Preserve original zone type
                        start=day_start.replace(hour=zone.start.hour, minute=zone.start.minute),
                        end=day_start.replace(hour=zone.end.hour, minute=zone.end.minute),
                        energy_level=zone.energy_level,
                        min_duration=zone.min_duration,
                        buffer_required=zone.buffer_required,
                        events=[]
                    )
                    multi_day_zones.append(new_zone)
            return multi_day_zones

    scheduler.strategy = TestStrategy()
    schedule = scheduler.reschedule([high_energy_task])

    # Debug output
    print(f"Schedule length: {len(schedule)}")
    print(f"Available zones: {len(work_day_zones)}")
    for zone in work_day_zones:
        print(f"Zone: {zone.zone_type}, Energy: {zone.energy_level}, "
              f"Time: {zone.start}-{zone.end}")

    task_event = next(e for e in schedule if e.id == "complex")
    scheduled_zone = next(z for z in work_day_zones
                          if z.start <= task_event.start <= z.end)

    assert scheduled_zone.energy_level == EnergyLevel.HIGH

def test_schedule_dependent_tasks_different_zones():
    # ARRANGE
    start_time = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
    
    # Create both DEEP and LIGHT zones for a single day
    day_zones = [
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

    # Create a strategy that properly handles both zone types
    class TestStrategy(SequenceBasedStrategy):
        def schedule(self, tasks, zones, existing_events):
            # Create multi-day zones while preserving both zone types
            multi_day_zones = []
            for day in range(7):
                day_start = start_time + timedelta(days=day)
                for zone in day_zones:
                    new_zone = TimeBlockZone(
                        start=day_start.replace(hour=zone.start.hour, minute=zone.start.minute),
                        end=day_start.replace(hour=zone.end.hour, minute=zone.end.minute),
                        zone_type=zone.zone_type,
                        energy_level=zone.energy_level,
                        min_duration=zone.min_duration,
                        buffer_required=zone.buffer_required,
                        events=[]
                    )
                    multi_day_zones.append(new_zone)
            return super().schedule(tasks, multi_day_zones, existing_events)

    # Create mock repositories
    task_repo = Mock()
    calendar_repo = Mock()
    
    # Configure mock behavior
    calendar_repo.get_events.return_value = []
    calendar_repo.get_zones.return_value = day_zones
    task_repo.get_tasks.return_value = []

    # Create scheduler with our custom strategy
    strategy = TestStrategy()
    scheduler = Scheduler(
        task_repo=task_repo,
        calendar_repo=calendar_repo,
        strategy=strategy
    )

    # Create dependent tasks
    task1 = Task(
        id="task1",
        title="Task 1",
        duration=60,
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

    task2 = Task(
        id="task2",
        title="Task 2",
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
            dependencies=["task1"]
        )
    )

    # ACT
    schedule = scheduler.reschedule([task1, task2])

    # ASSERT
    task1_event = next(e for e in schedule if e.id == "task1")
    task2_event = next(e for e in schedule if e.id == "task2")

    # Task 1 should be scheduled in DEEP zone
    assert task1_event.start >= start_time
    assert task1_event.end <= start_time + timedelta(hours=4)
    assert task1_event.start + timedelta(minutes=task1.duration) <= task1_event.end

    # Task 2 should be scheduled in LIGHT zone
    assert task2_event.start >= start_time + timedelta(hours=4)
    assert task2_event.end <= start_time + timedelta(hours=8)
    assert task2_event.start + timedelta(minutes=task2.duration) <= task2_event.end

    # Task 2 should start after Task 1 ends
    assert task2_event.start >= task1_event.end

    # Verify buffers
    buffer_time = (task2_event.start - task1_event.end).total_seconds() / 60
    assert buffer_time >= 15, "Buffer between task1 and task2 should be at least 15 minutes"

def test_write_review_workflow():
    """Test scheduling a writing task followed by a review task"""
    # ARRANGE
    start_time = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
    
    # Create both DEEP and LIGHT zones
    day_zones = [
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

    # Define TestStrategy class
    class TestStrategy(SequenceBasedStrategy):
        def schedule(self, tasks, zones, existing_events):
            # Create multi-day zones while preserving both zone types
            multi_day_zones = []
            for day in range(7):
                day_start = start_time + timedelta(days=day)
                for zone in day_zones:
                    new_zone = TimeBlockZone(
                        start=day_start.replace(hour=zone.start.hour, minute=zone.start.minute),
                        end=day_start.replace(hour=zone.end.hour, minute=zone.end.minute),
                        zone_type=zone.zone_type,
                        energy_level=zone.energy_level,
                        min_duration=zone.min_duration,
                        buffer_required=zone.buffer_required,
                        events=[]
                    )
                    multi_day_zones.append(new_zone)
            return super().schedule(tasks, multi_day_zones, existing_events)

    # Create mock repositories
    task_repo = Mock()
    calendar_repo = Mock()
    
    # Configure mock behavior
    calendar_repo.get_events.return_value = []
    calendar_repo.get_zones.return_value = day_zones
    task_repo.get_tasks.return_value = []

    # Create tasks
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

    # Create scheduler with our custom strategy
    scheduler = Scheduler(
        task_repo=task_repo,
        calendar_repo=calendar_repo,
        strategy=TestStrategy()
    )

    # ACT
    schedule = scheduler.reschedule([write_task, review_task])

    # ASSERT
    write_event = next(e for e in schedule if e.id == "write")
    review_event = next(e for e in schedule if e.id == "review")

    # Debug output
    print("\nScheduled Events:")
    for event in schedule:
        print(f"Event: {event.id}, Time: {event.start.strftime('%H:%M')}-{event.end.strftime('%H:%M')}")

    # Verify write task is in DEEP zone
    assert write_event.start.hour == 9
    assert (write_event.end - write_event.start).total_seconds() / 60 == 90

    # Verify review task is in LIGHT zone
    assert review_event.start.hour >= 13  # Should be in afternoon LIGHT zone
    assert (review_event.end - review_event.start).total_seconds() / 60 == 30

    # Verify sequence
    assert review_event.start > write_event.end
