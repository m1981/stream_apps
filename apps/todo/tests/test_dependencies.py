import pytest
from datetime import datetime, timedelta
from src.domain.task import Task, TaskConstraints, ZoneType, EnergyLevel
from src.domain.scheduler import Scheduler, SchedulingStrategy
from src.domain.timeblock import TimeBlockZone, Event, TimeBlockType

class DependencyAwareStrategy(SchedulingStrategy):
    def schedule(self, tasks, zones, existing_events):
        # Sort tasks based on dependencies
        scheduled = []
        scheduled_ids = set()
        remaining_tasks = tasks.copy()
        
        while remaining_tasks:
            # Find tasks with satisfied dependencies
            available = [
                task for task in remaining_tasks
                if all(dep in scheduled_ids for dep in task.constraints.dependencies)
            ]
            
            if not available:
                if remaining_tasks:
                    raise ValueError("Circular dependency detected")
                break
                
            # Schedule the first available task
            task = available[0]
            current_time = zones[0].start if zones else datetime.now()
            if scheduled:
                current_time = scheduled[-1].end + timedelta(minutes=task.constraints.required_buffer)
                
            event = Event(
                id=task.id,
                start=current_time,
                end=current_time + timedelta(minutes=task.duration),
                title=task.title,
                type=TimeBlockType.MANAGED
            )
            
            scheduled.append(event)
            scheduled_ids.add(task.id)
            remaining_tasks.remove(task)
            
        return scheduled

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
            sequence_number=1,  # Changed from priority
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
            sequence_number=2,  # Changed from priority
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
            sequence_number=3,  # Changed from priority
            project_id="test",
            constraints=TaskConstraints(
                **{**default_constraints.__dict__, "dependencies": ["task2"]}
            )
        )

        strategy = DependencyAwareStrategy()
        events = strategy.schedule([task3, task1, task2], [TimeBlockZone(
            start=datetime.now(),
            end=datetime.now() + timedelta(hours=4),
            zone_type=ZoneType.DEEP,
            energy_level=EnergyLevel.HIGH,
            min_duration=30,
            buffer_required=15,
            events=[]
        )], [])
        
        # Verify correct ordering
        task1_event = next(e for e in events if e.id == "task1")
        task2_event = next(e for e in events if e.id == "task2")
        task3_event = next(e for e in events if e.id == "task3")
        
        assert task1_event.end <= task2_event.start
        assert task2_event.end <= task3_event.start

    def test_detects_circular_dependencies(self, default_constraints):
        task1 = Task(
            id="task1",
            title="Task 1",
            duration=60,
            due_date=datetime.now() + timedelta(days=1),
            sequence_number=1,  # Changed from priority
            project_id="test",
            constraints=TaskConstraints(
                **{**default_constraints.__dict__, "dependencies": ["task2"]}
            )
        )

        task2 = Task(
            id="task2",
            title="Task 2",
            duration=60,
            due_date=datetime.now() + timedelta(days=1),
            sequence_number=2,  # Changed from priority
            project_id="test",
            constraints=TaskConstraints(
                **{**default_constraints.__dict__, "dependencies": ["task1"]}
            )
        )

        strategy = DependencyAwareStrategy()
        with pytest.raises(ValueError, match="Circular dependency detected"):
            strategy.schedule([task1, task2], [TimeBlockZone(
                start=datetime.now(),
                end=datetime.now() + timedelta(hours=4),
                zone_type=ZoneType.DEEP,
                energy_level=EnergyLevel.HIGH,
                min_duration=30,
                buffer_required=15,
                events=[]
            )], [])
