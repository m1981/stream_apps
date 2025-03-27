import pytest
from datetime import datetime, timedelta
from src.domain.task import Task, TaskConstraints, ZoneType, EnergyLevel
from src.domain.scheduler import Scheduler
from src.domain.timeblock import TimeBlockZone, Event, TimeBlockType
from src.domain.scheduling import SequenceBasedStrategy
from unittest.mock import Mock
from src.domain.scheduling.strategies import SequenceBasedStrategy

class TestRescheduling:
    @pytest.fixture
    def work_day_zones(self):
        """Create zones covering a work day with different energy levels"""
        now = datetime.now().replace(hour=9, minute=0)
        return [
            TimeBlockZone(
                start=now,
                end=now + timedelta(hours=4),
                zone_type=ZoneType.DEEP,
                energy_level=EnergyLevel.HIGH,
                min_duration=30,
                buffer_required=15,
                events=[]
            ),
            TimeBlockZone(
                start=now + timedelta(hours=4),
                end=now + timedelta(hours=8),
                zone_type=ZoneType.LIGHT,
                energy_level=EnergyLevel.MEDIUM,
                min_duration=30,
                buffer_required=10,
                events=[]
            )
        ]

    @pytest.fixture
    def mock_task_repo(self):
        class MockTaskRepository:
            def get_tasks(self):
                return []
            
            def mark_scheduled(self, task_id):
                pass
        return MockTaskRepository()

    @pytest.fixture
    def mock_calendar_repo(self):
        class MockCalendarRepository:
            def get_events(self, start, end):
                return []
            
            def create_event(self, event):
                return "new_event_id"
            
            def remove_managed_events(self):
                pass
        return MockCalendarRepository()

    @pytest.fixture
    def scheduler(self, mock_task_repo, mock_calendar_repo):
        return Scheduler(
            task_repo=mock_task_repo,
            calendar_repo=mock_calendar_repo,
            strategy=SequenceBasedStrategy()
        )

    def test_reschedule_on_task_duration_change(self, work_day_zones):
        """
        When: Task duration is updated
        Then: Only affected task and its dependents should be rescheduled
        And: Other tasks should maintain their original schedule
        """
        # Initial schedule
        write_task = Task(id="write", duration=60, zone_type=ZoneType.DEEP)
        review_task = Task(id="review", duration=30, zone_type=ZoneType.LIGHT,
                           dependencies=["write"])
        email_task = Task(id="email", duration=30, zone_type=ZoneType.LIGHT)

        scheduler = Scheduler()
        original_schedule = scheduler.schedule_tasks([write_task, review_task, email_task])

        # Change duration and reschedule
        write_task.duration = 90
        new_schedule = scheduler.reschedule(affected_task_ids=["write"])

        # Verify email_task time unchanged
        original_email = next(e for e in original_schedule if e.id == "email")
        new_email = next(e for e in new_schedule if e.id == "email")
        assert original_email.start == new_email.start

        # Verify review_task rescheduled after write_task
        new_write = next(e for e in new_schedule if e.id == "write")
        new_review = next(e for e in new_schedule if e.id == "review")
        assert new_review.start >= new_write.end + timedelta(minutes=15)

    def test_reschedule_preserves_zone_integrity(self, work_day_zones):
        """
        When: Task is rescheduled
        Then: Zone type constraints must be maintained
        And: Energy level requirements must be respected
        """
        deep_task = Task(
            id="deep_work",
            duration=60,
            zone_type=ZoneType.DEEP,
            energy_level=EnergyLevel.HIGH
        )

        scheduler = Scheduler()
        new_schedule = scheduler.reschedule([deep_task])

        deep_event = next(e for e in new_schedule if e.id == "deep_work")
        scheduled_zone = next(z for z in work_day_zones
                              if z.start <= deep_event.start <= z.end)

        assert scheduled_zone.zone_type == ZoneType.DEEP
        assert scheduled_zone.energy_level == EnergyLevel.HIGH

    def test_reschedule_maintains_project_sequence(self):
        """
        When: Tasks in project sequence are rescheduled
        Then: Project task sequence should be maintained
        
        Visual representation of expected schedule:
        
        Timeline    Task
        9:00 AM     step1  (sequence=1) -------|
        10:00 AM    step2  (sequence=2)    -------|
        11:00 AM    step3  (sequence=3)        -------|
        """
        # Create mock repositories
        task_repo = Mock()
        calendar_repo = Mock()
        strategy = SequenceBasedStrategy()
        
        # Create work day zone
        morning_zone = TimeBlockZone(
            start=datetime.now().replace(hour=9),
            end=datetime.now().replace(hour=12),
            zone_type=ZoneType.DEEP,
            energy_level=EnergyLevel.HIGH,
            min_duration=30,
            buffer_required=15,
            type=TimeBlockType.MANAGED,
            events=[]
        )
        
        # Configure mock behavior
        calendar_repo.get_events.return_value = []
        calendar_repo.get_zones.return_value = [morning_zone]
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

    def test_reschedule_handles_buffer_requirements(self, work_day_zones):
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

    def test_reschedule_handles_partial_day_availability(self):
        """
        When: Calendar has fixed events
        Then: Tasks should be rescheduled around fixed events
        And: No overlap should occur
        """
        # Create mock repositories
        task_repo = Mock()
        calendar_repo = Mock()
        
        # Create strategy
        strategy = SequenceBasedStrategy()
        
        # Create fixed event
        fixed_event = Event(
            id="meeting",
            title="Daily Standup",
            start=datetime.now().replace(hour=10),
            end=datetime.now().replace(hour=11),
            type=TimeBlockType.FIXED
        )

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
        
        # Create work day zones
        morning_zone = TimeBlockZone(
            start=datetime.now().replace(hour=9),
            end=datetime.now().replace(hour=12),
            zone_type=ZoneType.DEEP,
            energy_level=EnergyLevel.HIGH,
            min_duration=30,
            buffer_required=15,
            type=TimeBlockType.MANAGED,
            events=[]
        )
        
        # Mock the zones in the calendar repository
        calendar_repo.get_zones.return_value = [morning_zone]

        schedule = scheduler.reschedule([task], fixed_events=[fixed_event])

        work_event = next(e for e in schedule if e.id == "work")
        assert not (work_event.start < fixed_event.end and
                    work_event.end > fixed_event.start)

    def test_reschedule_splits_tasks_when_necessary(self, scheduler, work_day_zones):
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
                zone_type=ZoneType.DEEP,
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

    def test_reschedule_handles_energy_level_changes(self, scheduler, work_day_zones):
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
                return super().schedule(tasks, work_day_zones, existing_events)

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
