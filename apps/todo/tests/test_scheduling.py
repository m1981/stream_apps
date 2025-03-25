import dataclasses
import pytest
from datetime import datetime, timedelta
from typing import List
from src.domain.scheduling.strategies import SequenceBasedStrategy
from src.domain.scheduling.base import SchedulingStrategy
from src.domain.scheduler import Scheduler
from src.domain.conflict import ConflictDetector
from src.domain.task import Task, TaskConstraints, EnergyLevel, ZoneType
from src.domain.timeblock import TimeBlock, TimeBlockZone, TimeBlockType, Event

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
        events=[],
        type=TimeBlockType.MANAGED  # Added type
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
            project_id="proj1",
            sequence_number=1,  # Changed from priority
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
            events=[],
            type=TimeBlockType.MANAGED  # Added type
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
            ],
            type=TimeBlockType.MANAGED  # Added type
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
            events=[existing_event],
            type=TimeBlockType.MANAGED  # Added type
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
            events=[existing_event],
            type=TimeBlockType.MANAGED  # Added type
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
            events=[],
            type=TimeBlockType.MANAGED  # Added type
        )
        
        system_design_task = Task(
            id="arch_design",
            title="System Architecture Design",
            duration=120,  # 2 hours
            due_date=datetime.now() + timedelta(days=1),
            project_id="proj1",
            sequence_number=1,
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
            type=TimeBlockType.MANAGED,  # Added missing type parameter
            events=[]
        )
        
        code_review_task = Task(
            id="quick_review",
            title="Quick Code Review",
            duration=15,  # 15 minutes
            due_date=datetime.now() + timedelta(days=1),
            project_id="proj1",
            sequence_number=1,
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
        Tests that find_available_slot correctly scans through time in 15-minute increments
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
            type=TimeBlockType.MANAGED,  # Added type
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
            type=TimeBlockType.MANAGED,  # Added type
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
            sequence_number=1,  # Changed from priority
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
            sequence_number=1,  # Changed from priority
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

    def test_respects_buffer_requirements(self):
        """
        Tests that scheduling respects buffer time requirements between tasks
        """
        # Arrange
        start_time = datetime.now().replace(hour=9, minute=0)
        time_block = TimeBlockZone(
            start=start_time,
            end=start_time + timedelta(hours=4),
            zone_type=ZoneType.DEEP,
            energy_level=EnergyLevel.HIGH,
            min_duration=30,
            buffer_required=15,
            type=TimeBlockType.MANAGED,
            events=[
                Event(
                    id="existing_event",
                    start=start_time,
                    end=start_time + timedelta(hours=2),  # 9:00 - 11:00
                    title="Existing Meeting",
                    type=TimeBlockType.FIXED
                )
            ]
        )

        task = Task(
            id="task1",
            title="New Task",
            duration=60,
            due_date=start_time + timedelta(days=1),
            sequence_number=1,
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
        # The first available slot should be after the existing event (11:00)
        # plus the required buffer time (15 minutes)
        expected_slot = start_time + timedelta(hours=2, minutes=15)  # 11:15 AM
        assert available_slot == expected_slot

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
    def sequence_tasks(self, default_constraints):
        """
        Simulates a real project workflow for writing a blog post,
        with tasks in natural Todoist sequence
        """
        now = datetime.now()
        return [
            Task(
                id="research",
                title="Research blog topic",
                duration=60,
                due_date=now + timedelta(days=5),
                project_id="blog_post",
                sequence_number=1,
                constraints=default_constraints
            ),
            Task(
                id="outline",
                title="Create content outline",
                duration=30,
                due_date=now + timedelta(days=5),
                project_id="blog_post",
                sequence_number=2,
                constraints=default_constraints
            ),
            Task(
                id="draft",
                title="Write first draft",
                duration=120,
                due_date=now + timedelta(days=5),
                project_id="blog_post",
                sequence_number=3,
                constraints=default_constraints
            ),
            Task(
                id="review",
                title="Technical review",
                duration=45,
                due_date=now + timedelta(days=5),
                project_id="blog_post",
                sequence_number=4,
                constraints=default_constraints
            )
        ]

    def test_respects_project_sequence(self, sequence_tasks, deep_work_zone):
        """Tests that tasks are scheduled in their natural project sequence"""
        # Initialize scheduler with sequence tasks
        task_repo = MockTaskRepository(tasks=sequence_tasks)
        calendar_repo = MockCalendarRepository()
        strategy = SequenceBasedStrategy()
        
        scheduler = Scheduler(task_repo, calendar_repo, strategy)
        events = scheduler.schedule_tasks(planning_horizon=7)
        
        # Verify events are scheduled in sequence
        assert len(events) == 4, "All tasks should be scheduled"
        
        # Check sequence order is maintained
        scheduled_ids = [event.id for event in events]
        expected_sequence = ['research', 'outline', 'draft', 'review']
        assert scheduled_ids == expected_sequence, "Tasks should be scheduled in project sequence order"
        
        # Verify each task starts after the previous one ends
        for i in range(1, len(events)):
            assert events[i].start >= events[i-1].end, \
                f"Task {events[i].id} should start after {events[i-1].id} ends"

    def test_cross_project_scheduling(self, default_constraints):
        """
        Tests scheduling tasks from multiple projects with different due dates,
        simulating parallel work on blog post and client project
        """
        now = datetime.now()
        
        blog_tasks = [
            Task(
                id="blog_research",
                title="Research blog topic",
                duration=60,
                due_date=now + timedelta(days=5),
                project_id="blog_post",
                sequence_number=1,
                constraints=default_constraints
            ),
            Task(
                id="blog_write",
                title="Write blog post",
                duration=120,
                due_date=now + timedelta(days=5),
                project_id="blog_post",
                sequence_number=2,
                constraints=default_constraints
            )
        ]
        
        client_tasks = [
            Task(
                id="client_spec",
                title="Write specification",
                duration=90,
                due_date=now + timedelta(days=2),  # Earlier due date
                project_id="client_project",
                sequence_number=1,
                constraints=default_constraints
            ),
            Task(
                id="client_review",
                title="Client review meeting",
                duration=60,
                due_date=now + timedelta(days=2),
                project_id="client_project",
                sequence_number=2,
                constraints=default_constraints
            )
        ]
        
        task_repo = MockTaskRepository(tasks=blog_tasks + client_tasks)
        calendar_repo = MockCalendarRepository()
        strategy = SequenceBasedStrategy()
        
        scheduler = Scheduler(task_repo, calendar_repo, strategy)
        events = scheduler.schedule_tasks(planning_horizon=7)
        
        # Verify client project tasks (earlier due date) are scheduled first
        scheduled_ids = [event.id for event in events]
        assert scheduled_ids.index('client_spec') < scheduled_ids.index('blog_research'), \
            "Client tasks with earlier due date should be scheduled before blog tasks"
        
        # Verify sequence within each project is maintained
        assert scheduled_ids.index('client_spec') < scheduled_ids.index('client_review'), \
            "Client project sequence should be maintained"
        assert scheduled_ids.index('blog_research') < scheduled_ids.index('blog_write'), \
            "Blog project sequence should be maintained"

    def test_handles_dependent_project_tasks(self, default_constraints):
        """
        Tests scheduling with dependencies across projects,
        simulating a website launch with content and technical tasks
        """
        now = datetime.now()
        
        # Content project tasks
        content_constraints = dataclasses.replace(
            default_constraints,
            dependencies=[]
        )
        content_tasks = [
            Task(
                id="content_write",
                title="Write website content",
                duration=120,
                due_date=now + timedelta(days=3),
                project_id="content",
                sequence_number=1,
                constraints=content_constraints
            ),
            Task(
                id="content_review",
                title="Review content",
                duration=60,
                due_date=now + timedelta(days=3),
                project_id="content",
                sequence_number=2,
                constraints=content_constraints
            )
        ]
        
        # Technical project tasks depending on content
        tech_constraints = dataclasses.replace(
            default_constraints,
            dependencies=["content_write", "content_review"]
        )
        tech_tasks = [
            Task(
                id="tech_implement",
                title="Implement website",
                duration=180,
                due_date=now + timedelta(days=5),
                project_id="technical",
                sequence_number=1,
                constraints=tech_constraints
            ),
            Task(
                id="tech_deploy",
                title="Deploy website",
                duration=60,
                due_date=now + timedelta(days=5),
                project_id="technical",
                sequence_number=2,
                constraints=tech_constraints
            )
        ]
        
        task_repo = MockTaskRepository(tasks=content_tasks + tech_tasks)
        calendar_repo = MockCalendarRepository()
        strategy = SequenceBasedStrategy()
        
        scheduler = Scheduler(task_repo, calendar_repo, strategy)
        events = scheduler.schedule_tasks(planning_horizon=7)
        
        # Verify content tasks are scheduled before technical tasks
        scheduled_ids = [event.id for event in events]
        assert scheduled_ids.index('content_write') < scheduled_ids.index('tech_implement'), \
            "Content tasks should be scheduled before dependent technical tasks"
        
        # Verify sequence within projects is maintained
        assert scheduled_ids.index('content_write') < scheduled_ids.index('content_review'), \
            "Content project sequence should be maintained"
        assert scheduled_ids.index('tech_implement') < scheduled_ids.index('tech_deploy'), \
            "Technical project sequence should be maintained"

    # Priority-based tests removed
