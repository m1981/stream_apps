import pytest
from datetime import datetime, timedelta
from src.domain.task import Task, TaskConstraints, ZoneType, EnergyLevel
from src.domain.scheduler import Scheduler, SchedulingStrategy

class DependencyAwareStrategy(SchedulingStrategy):
    def schedule(self, tasks, zones, existing_events):
        # Simple implementation for testing
        events = []
        current_time = zones[0].start if zones else datetime.now()
        
        # Sort tasks by dependencies
        scheduled_tasks = set()
        while tasks:
            # Find task with satisfied dependencies
            schedulable = next(
                (t for t in tasks if all(d in scheduled_tasks for d in t.constraints.dependencies)),
                None
            )
            if not schedulable:
                raise ValueError("Circular dependency detected")
                
            event = Event(
                id=f"evt_{schedulable.id}",
                task_id=schedulable.id,
                start=current_time,
                end=current_time + timedelta(minutes=schedulable.duration),
                title=schedulable.title
            )
            events.append(event)
            scheduled_tasks.add(schedulable.id)
            tasks.remove(schedulable)
            current_time = event.end + timedelta(minutes=schedulable.constraints.required_buffer)
        
        return events

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

class TestTaskDependencies:
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

    def test_respects_task_dependencies(self, default_constraints):
        task1 = Task(
            id="task1",
            title="Task 1",
            duration=60,
            due_date=datetime.now() + timedelta(days=1),
            priority=1,
            project_id="test",
            constraints=TaskConstraints(
                **{**default_constraints.__dict__, "dependencies": []}
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
                **{**default_constraints.__dict__, "dependencies": ["task1"]}
            )
        )

        task3 = Task(
            id="task3",
            title="Task 3",
            duration=60,
            due_date=datetime.now() + timedelta(days=1),
            priority=1,
            project_id="test",
            constraints=TaskConstraints(
                **{**default_constraints.__dict__, "dependencies": ["task2"]}
            )
        )

        scheduler = Scheduler(MockTaskRepository(), MockCalendarRepository(),
                            DependencyAwareStrategy())
        events = scheduler.schedule_tasks([task3, task1, task2])
        
        # Verify correct ordering
        task1_event = next(e for e in events if e.task_id == "task1")
        task2_event = next(e for e in events if e.task_id == "task2")
        task3_event = next(e for e in events if e.task_id == "task3")
        
        assert task1_event.end <= task2_event.start
        assert task2_event.end <= task3_event.start

    def test_detects_circular_dependencies(self):
        task1 = Task(id="task1", dependencies=["task2"])
        task2 = Task(id="task2", dependencies=["task1"])
        
        with pytest.raises(ValueError, match="Circular dependency detected"):
            scheduler.validate_dependencies([task1, task2])