import pytest
from datetime import datetime, timedelta
from src.domain.scheduling import ConflictDetector, SchedulingConflict
from src.domain.timeblock import TimeBlock, TimeBlockZone, TimeBlockType, Event
from src.domain.task import Task, TaskConstraints, ZoneType, EnergyLevel
from src.domain.scheduler import Scheduler, SchedulingStrategy
from typing import List

class MockTaskRepository:
    def __init__(self, tasks=None):
        self.tasks = tasks or []
    
    def get_tasks(self):
        return self.tasks
    
    def mark_scheduled(self, task_id):
        pass

class MockCalendarRepository:
    def get_events(self, start, end):
        return []
    
    def create_event(self, event):
        return "new_event_id"
    
    def remove_managed_events(self):
        pass

class PriorityBasedStrategy(SchedulingStrategy):
    def schedule(self, tasks: List[Task], zones: List[TimeBlockZone], existing_events: List[Event]) -> List[Event]:
        events = []
        # Fix: Sort by priority (1 is highest) and then by due date
        sorted_tasks = sorted(tasks, key=lambda t: (t.priority, t.due_date))  # Remove negative priority
        
        for task in sorted_tasks:
            suitable_zone = next(
                (zone for zone in zones 
                 if zone.zone_type == task.constraints.zone_type 
                 and zone.energy_level == task.constraints.energy_level),
                None
            )
            
            if not suitable_zone:
                continue
                
            current_time = suitable_zone.start
            event_created = False
            
            while current_time < suitable_zone.end and not event_created:
                conflict = ConflictDetector.find_conflicts(task, current_time, suitable_zone)
                if not conflict:
                    event = Event(
                        id=task.id,
                        start=current_time,
                        end=current_time + timedelta(minutes=task.duration),
                        title=task.title,
                        type=TimeBlockType.MANAGED
                    )
                    events.append(event)
                    event_created = True
                current_time += timedelta(minutes=15)
                
        return events

@pytest.fixture
def deep_work_zone():
    start = datetime.now().replace(hour=9, minute=0)
    return TimeBlockZone(
        start=start,
        end=start + timedelta(hours=4),
        zone_type=ZoneType.DEEP,
        energy_level=EnergyLevel.HIGH,
        min_duration=120,
        buffer_required=15,
        events=[]
    )

class TestConflictDetection:
    @pytest.fixture
    def deep_work_task(self):
        constraints = TaskConstraints(
            zone_type=ZoneType.DEEP,
            energy_level=EnergyLevel.HIGH,
            is_splittable=False,
            min_chunk_duration=120,
            max_split_count=1,
            required_buffer=15,
            dependencies=[]
        )
        return Task(
            id="task1",
            title="Deep Work Task",
            duration=120,
            due_date=datetime.now() + timedelta(days=1),
            priority=1,
            project_id="proj1",
            constraints=constraints
        )

    def test_detects_zone_type_mismatch(self, deep_work_task):
        light_zone = TimeBlockZone(
            start=datetime.now(),
            end=datetime.now() + timedelta(hours=4),
            zone_type=ZoneType.LIGHT,
            energy_level=EnergyLevel.MEDIUM,
            min_duration=30,
            buffer_required=10,
            events=[]
        )
        
        conflict = ConflictDetector.find_conflicts(
            deep_work_task,
            light_zone.start,
            light_zone
        )
        assert conflict is not None
        assert "Task requires deep zone" in conflict.message

    def test_finds_available_slot(self, deep_work_zone, deep_work_task):
        slot = ConflictDetector.find_available_slot(
            deep_work_task,
            deep_work_zone,
            deep_work_zone.start
        )
        assert slot is not None
        assert slot >= deep_work_zone.start

    def test_detects_direct_time_conflict(self, deep_work_task):
        """
        Tests that a direct time overlap with an existing event is detected as a conflict
        """
        # Arrange
        start_time = datetime.now().replace(hour=9, minute=0)
        zone = TimeBlockZone(
            start=start_time,
            end=start_time + timedelta(hours=4),
            zone_type=ZoneType.DEEP,
            energy_level=EnergyLevel.HIGH,
            min_duration=30,
            buffer_required=15,
            events=[
                Event(
                    id="existing_event",
                    start=start_time + timedelta(minutes=30),
                    end=start_time + timedelta(minutes=90),
                    title="Existing Meeting",
                    type=TimeBlockType.FIXED
                )
            ]
        )
        
        proposed_start = start_time + timedelta(minutes=60)  # Right in the middle of existing event
        
        # Act
        conflict = ConflictDetector.find_conflicts(deep_work_task, proposed_start, zone)
        
        # Assert
        assert conflict is not None
        assert conflict.task == deep_work_task
        assert len(conflict.conflicting_events) == 1
        assert conflict.conflicting_events[0].id == "existing_event"
        assert conflict.message == "Time slot has conflicting events"
        assert conflict.proposed_start == proposed_start

    def test_detects_partial_overlap_at_start(self, deep_work_task):
        """
        Tests that partial overlap at the start of an existing event is detected as a conflict
        """
        # Arrange
        start_time = datetime.now().replace(hour=9, minute=0)
        existing_event = Event(
            id="existing_event",
            start=start_time + timedelta(minutes=60),
            end=start_time + timedelta(minutes=120),
            title="Existing Meeting",
            type=TimeBlockType.FIXED
        )
        
        zone = TimeBlockZone(
            start=start_time,
            end=start_time + timedelta(hours=4),
            zone_type=ZoneType.DEEP,
            energy_level=EnergyLevel.HIGH,
            min_duration=30,
            buffer_required=15,
            events=[existing_event]
        )
        
        proposed_start = existing_event.start - timedelta(minutes=30)  # Overlaps with start
        
        # Act
        conflict = ConflictDetector.find_conflicts(deep_work_task, proposed_start, zone)
        
        # Assert
        assert conflict is not None
        assert len(conflict.conflicting_events) == 1
        assert conflict.conflicting_events[0] == existing_event

    def test_detects_partial_overlap_at_end(self, deep_work_task):
        """
        Tests that partial overlap at the end of an existing event is detected as a conflict
        """
        # Arrange
        start_time = datetime.now().replace(hour=9, minute=0)
        existing_event = Event(
            id="existing_event",
            start=start_time + timedelta(minutes=60),
            end=start_time + timedelta(minutes=120),
            title="Existing Meeting",
            type=TimeBlockType.FIXED
        )
        
        zone = TimeBlockZone(
            start=start_time,
            end=start_time + timedelta(hours=4),
            zone_type=ZoneType.DEEP,
            energy_level=EnergyLevel.HIGH,
            min_duration=30,
            buffer_required=15,
            events=[existing_event]
        )
        
        proposed_start = existing_event.end - timedelta(minutes=30)  # Overlaps with end
        
        # Act
        conflict = ConflictDetector.find_conflicts(deep_work_task, proposed_start, zone)
        
        # Assert
        assert conflict is not None
        assert len(conflict.conflicting_events) == 1
        assert conflict.conflicting_events[0] == existing_event

    def test_prevent_high_energy_task_in_low_energy_period(self):
        """
        Tests preventing system design work (high energy) 
        from being scheduled in late afternoon (low energy)
        """
        # Arrange
        late_afternoon = datetime.now().replace(hour=16, minute=0)  # 4 PM
        low_energy_zone = TimeBlockZone(
            start=late_afternoon,
            end=late_afternoon + timedelta(hours=3),
            zone_type=ZoneType.DEEP,
            energy_level=EnergyLevel.LOW,
            min_duration=30,
            buffer_required=15,
            events=[]
        )
        
        system_design_task = Task(
            id="arch_design",
            title="System Architecture Design",
            duration=120,  # 2 hours
            due_date=datetime.now() + timedelta(days=1),
            priority=1,
            project_id="proj1",
            constraints=TaskConstraints(
                zone_type=ZoneType.DEEP,
                energy_level=EnergyLevel.HIGH,  # Requires high energy
                is_splittable=False,
                min_chunk_duration=60,
                max_split_count=1,
                required_buffer=15,
                dependencies=[]
            )
        )
        
        # Act
        conflict = ConflictDetector.find_conflicts(
            system_design_task,
            low_energy_zone.start,
            low_energy_zone
        )
        
        # Assert
        assert conflict is not None
        assert conflict.message == f"Task requires {EnergyLevel.HIGH.value} energy level"

    def test_prevent_short_task_in_deep_work_block(self):
        """
        Tests preventing a quick code review (15 min) 
        from being scheduled in a deep work block (2 hour minimum)
        """
        # Arrange
        morning = datetime.now().replace(hour=9, minute=0)
        deep_work_zone = TimeBlockZone(
            start=morning,
            end=morning + timedelta(hours=4),
            zone_type=ZoneType.DEEP,
            energy_level=EnergyLevel.HIGH,
            min_duration=120,  # 2 hour minimum
            buffer_required=15,
            events=[]
        )
        
        code_review_task = Task(
            id="quick_review",
            title="Quick Code Review",
            duration=15,  # 15 minutes
            due_date=datetime.now() + timedelta(days=1),
            priority=2,
            project_id="proj1",
            constraints=TaskConstraints(
                zone_type=ZoneType.DEEP,
                energy_level=EnergyLevel.HIGH,
                is_splittable=False,
                min_chunk_duration=15,
                max_split_count=1,
                required_buffer=5,
                dependencies=[]
            )
        )
        
        # Act
        conflict = ConflictDetector.find_conflicts(
            code_review_task,
            deep_work_zone.start,
            deep_work_zone
        )
        
        # Assert
        assert conflict is not None
        assert conflict.message == f"Task duration below zone minimum (120 min)"

    def test_find_available_slot_scanning_behavior(self):
        """
        Tests how find_available_slot scans through time in 15-minute increments
        until finding an open slot or reaching the end
        """
        # Arrange
        start_time = datetime.now().replace(hour=9, minute=0)  # 9 AM
        end_time = start_time + timedelta(hours=8)  # 5 PM
        
        # Create a time block with two meetings:
        # 1. 9:00 AM - 10:00 AM
        # 2. 10:15 AM - 11:00 AM
        time_block = TimeBlockZone(
            start=start_time,
            end=end_time,
            zone_type=ZoneType.DEEP,
            energy_level=EnergyLevel.HIGH,
            min_duration=30,
            buffer_required=15,
            events=[
                Event(
                    id="meeting1",
                    start=start_time,
                    end=start_time + timedelta(hours=1),
                    title="Morning Meeting",
                    type=TimeBlockType.FIXED
                ),
                Event(
                    id="meeting2",
                    start=start_time + timedelta(hours=1, minutes=15),
                    end=start_time + timedelta(hours=2),
                    title="Team Sync",
                    type=TimeBlockType.FIXED
                )
            ]
        )
        
        # 30-minute task that needs scheduling
        task = Task(
            id="quick_task",
            title="Quick Task",
            duration=30,
            due_date=end_time,
            priority=1,
            project_id="proj1",
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
        
        # Act
        available_slot = ConflictDetector.find_available_slot(
            task,
            time_block,
            start_time
        )
        
        # Assert
        expected_slot = start_time + timedelta(hours=2, minutes=15)  # 11:15 AM
        assert available_slot == expected_slot
        
        # Verify this is actually the first available slot
        # by checking earlier times have conflicts
        earlier_slot = expected_slot - timedelta(minutes=15)
        assert ConflictDetector.find_conflicts(task, earlier_slot, time_block) is not None

    def test_no_available_slot_found(self):
        """
        Tests that find_available_slot returns None when no suitable slot exists
        """
        # Arrange
        start_time = datetime.now().replace(hour=9, minute=0)
        end_time = start_time + timedelta(hours=2)  # Short time block
        
        # Create a fully booked time block with back-to-back meetings
        time_block = TimeBlockZone(
            start=start_time,
            end=end_time,
            zone_type=ZoneType.DEEP,
            energy_level=EnergyLevel.HIGH,
            min_duration=30,
            buffer_required=15,
            events=[
                Event(
                    id="meeting1",
                    start=start_time,
                    end=start_time + timedelta(hours=1),
                    title="Meeting 1",
                    type=TimeBlockType.FIXED
                ),
                Event(
                    id="meeting2",
                    start=start_time + timedelta(hours=1),
                    end=end_time,
                    title="Meeting 2",
                    type=TimeBlockType.FIXED
                )
            ]
        )
        
        task = Task(
            id="task1",
            title="No Room For This",
            duration=60,
            due_date=end_time,
            priority=1,
            project_id="proj1",
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
        
        # Act
        available_slot = ConflictDetector.find_available_slot(
            task,
            time_block,
            start_time
        )
        
        # Assert
        assert available_slot is None

    def test_regular_timeblock_ignores_zone_constraints(self):
        """
        Tests that regular TimeBlock doesn't check zone-specific constraints
        """
        # Arrange
        start_time = datetime.now().replace(hour=9, minute=0)
        
        # Create a regular TimeBlock (not TimeBlockZone)
        regular_block = TimeBlock(
            start=start_time,
            end=start_time + timedelta(hours=4),
            type=TimeBlockType.MANAGED,
            events=[]
        )
        
        # Task with zone constraints that would fail in a TimeBlockZone
        task = Task(
            id="task1",
            title="Short Task",
            duration=15,  # Would be too short for deep work zone
            due_date=start_time + timedelta(hours=4),
            priority=1,
            project_id="proj1",
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
        
        # Act
        conflict = ConflictDetector.find_conflicts(task, start_time, regular_block)
        
        # Assert
        assert conflict is None  # Should pass despite zone constraints

class TestPriorityScheduling:
    @pytest.fixture
    def default_constraints(self):
        return TaskConstraints(
            zone_type=ZoneType.DEEP,
            energy_level=EnergyLevel.HIGH,
            is_splittable=False,
            min_chunk_duration=30,
            max_split_count=1,
            required_buffer=15,
            dependencies=[]
        )

    @pytest.fixture
    def priority_tasks(self, default_constraints):
        return [
            Task(id="high", 
                title="High Priority", 
                duration=60, 
                priority=1,
                due_date=datetime.now() + timedelta(days=1),
                project_id="test_project",
                constraints=default_constraints),
            Task(id="medium", 
                title="Medium Priority", 
                duration=60, 
                priority=2,
                due_date=datetime.now() + timedelta(days=1),
                project_id="test_project",
                constraints=default_constraints),
            Task(id="low", 
                title="Low Priority", 
                duration=60, 
                priority=3,
                due_date=datetime.now() + timedelta(days=1),
                project_id="test_project",
                constraints=default_constraints)
        ]

    def test_schedules_by_priority(self, priority_tasks, deep_work_zone):
        # Initialize scheduler with the priority tasks in the repository
        task_repo = MockTaskRepository(tasks=priority_tasks)
        calendar_repo = MockCalendarRepository()
        strategy = PriorityBasedStrategy()
        
        scheduler = Scheduler(task_repo, calendar_repo, strategy)
        events = scheduler.schedule_tasks(planning_horizon=7)
        
        # Verify high priority task gets preferred time slot
        assert len(events) > 0, "No events were scheduled"
        assert events[0].id == "high", "High priority task should be scheduled first"
        
        # Compare normalized times (removing microseconds)
        event_start = events[0].start.replace(microsecond=0)
        zone_start = deep_work_zone.start.replace(microsecond=0)
        assert event_start == zone_start, "High priority task should get preferred time slot"

    def test_handles_priority_conflicts_with_due_dates(self):
        # Test when lower priority task has earlier due date
        pass
