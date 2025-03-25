import pytest
from datetime import datetime, timedelta
from typing import List
from src.domain.task import Task, TaskConstraints, ZoneType, EnergyLevel
from src.domain.scheduler import Scheduler, SchedulingStrategy
from src.domain.timeblock import TimeBlockZone, Event, TimeBlockType

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

class SequenceBasedStrategy(SchedulingStrategy):
    def schedule(self, tasks: List[Task], zones: List[TimeBlockZone], existing_events: List[Event]) -> List[Event]:
        events = []
        sorted_tasks = sorted(tasks, key=lambda t: (t.sequence_number, t.due_date))
        
        for task in sorted_tasks:
            # Find appropriate zone
            suitable_zone = next(
                (zone for zone in zones 
                 if zone.zone_type == task.constraints.zone_type 
                 and zone.energy_level == task.constraints.energy_level),
                None
            )
            
            if not suitable_zone:
                continue
            
            # Find earliest available slot
            current_time = suitable_zone.start
            event_created = False
            
            while current_time < suitable_zone.end and not event_created:
                conflicts = suitable_zone.get_conflicts(current_time, task.duration)
                if not conflicts:
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

class TestRescheduling:
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
    def deep_work_zone(self):
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

    def test_reschedules_on_sequence_change(self, default_constraints, deep_work_zone):
        start_time = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
        
        task = Task(
            id="task1",
            title="Task 1",
            duration=60,
            due_date=datetime.now() + timedelta(days=1),
            project_id="test",
            sequence_number=2,
            constraints=default_constraints
        )
        
        # Initialize scheduler with mocked repositories and fixed time zone
        zone = TimeBlockZone(
            start=start_time,
            end=start_time + timedelta(hours=4),
            zone_type=ZoneType.DEEP,
            energy_level=EnergyLevel.HIGH,
            min_duration=30,
            buffer_required=15,
            events=[]
        )
        
        scheduler = Scheduler(
            task_repo=MockTaskRepository(tasks=[task]),
            calendar_repo=MockCalendarRepository(),
            strategy=SequenceBasedStrategy()
        )
        
        # Initial scheduling
        initial_events = scheduler.schedule_tasks(planning_horizon=7)
        assert initial_events is not None, "Events should not be None"
        assert len(initial_events) > 0, "No events were scheduled"
        original_start = initial_events[0].start
        
        # Change sequence and reschedule
        task.sequence_number = 1  # Earlier in sequence
        new_events = scheduler.schedule_tasks(planning_horizon=7)
        assert len(new_events) > 0, "No events were scheduled after sequence change"
        
        # Compare only up to minutes for scheduling comparison
        original_start_normalized = original_start.replace(second=0, microsecond=0)
        new_start_normalized = new_events[0].start.replace(second=0, microsecond=0)
        assert new_start_normalized <= original_start_normalized, "Task with earlier sequence should get same or better time slot"

    def test_handles_new_calendar_conflicts(self):
        # Test rescheduling when new fixed events are added
        pass

    def test_maintains_dependencies_during_reschedule(self):
        # Test that dependency order is preserved during rescheduling
        pass