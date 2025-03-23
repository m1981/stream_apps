import pytest
from datetime import datetime, timedelta
from src.domain.task import Task, TaskConstraints, ZoneType, EnergyLevel
from src.domain.scheduler import Scheduler
from src.domain.strategies import BufferAwareStrategy

class MockTaskRepository:
    def get_tasks(self):
        return []
    
    def mark_scheduled(self, task_id):
        pass

class MockCalendarRepository:
    def get_events(self, start, end):
        return []
    
    def create_event(self, event):
        return "new_event_id"
    
    def remove_managed_events(self):
        pass

class TestBufferManagement:
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

    def test_maintains_buffer_between_different_zone_types(self, default_constraints):
        deep_constraints = TaskConstraints(
            zone_type=ZoneType.DEEP,
            energy_level=EnergyLevel.HIGH,
            is_splittable=False,
            min_chunk_duration=30,
            max_split_count=1,
            required_buffer=15,
            dependencies=[]
        )
        
        light_constraints = TaskConstraints(
            zone_type=ZoneType.LIGHT,
            energy_level=EnergyLevel.MEDIUM,
            is_splittable=False,
            min_chunk_duration=30,
            max_split_count=1,
            required_buffer=15,
            dependencies=[]
        )

        deep_task = Task(
            id="deep",
            title="Deep Task",
            duration=60,
            due_date=datetime.now() + timedelta(days=1),
            priority=1,
            project_id="test",
            constraints=deep_constraints
        )

        light_task = Task(
            id="light",
            title="Light Task",
            duration=60,
            due_date=datetime.now() + timedelta(days=1),
            priority=1,
            project_id="test",
            constraints=light_constraints
        )
        
        scheduler = Scheduler(MockTaskRepository(), MockCalendarRepository(),
                            BufferAwareStrategy())
        events = scheduler.schedule_tasks([deep_task, light_task])
        
        # Verify minimum transition buffer between different zones
        deep_event = next(e for e in events if e.task_id == "deep")
        light_event = next(e for e in events if e.task_id == "light")
        buffer = (light_event.start - deep_event.end).minutes
        assert buffer >= 30  # Transition buffer

    def test_respects_task_specific_buffer_requirements(self, default_constraints):
        task1 = Task(
            id="task1",
            title="Task 1",
            duration=60,
            due_date=datetime.now() + timedelta(days=1),
            priority=1,
            project_id="test",
            constraints=TaskConstraints(
                **{**default_constraints.__dict__, "required_buffer": 15}
            )
        )

        task2 = Task(
            id="task2",
            title="Task 2",
            duration=60,
            due_date=datetime.now() + timedelta(days=1),
            priority=1,
            project_id="test",
            constraints=TaskConstraints(
                **{**default_constraints.__dict__, "required_buffer": 30}
            )
        )
        
        scheduler = Scheduler(MockTaskRepository(), MockCalendarRepository(),
                            BufferAwareStrategy())
        events = scheduler.schedule_tasks([task1, task2])
        buffer = (events[1].start - events[0].end).minutes
        assert buffer >= 30  # Uses larger buffer requirement