import pytest
from datetime import datetime, timedelta
from src.domain.scheduling import ConflictDetector, SchedulingConflict
from src.domain.timeblock import TimeBlockZone, Event, TimeBlockType
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
