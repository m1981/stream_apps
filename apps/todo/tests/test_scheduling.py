import pytest
from datetime import datetime, timedelta
from src.domain.scheduling import ConflictDetector, SchedulingConflict
from src.domain.timeblock import TimeBlockZone
from src.domain.task import Task, TaskConstraints, ZoneType, EnergyLevel

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
        scheduler = Scheduler(MockTaskRepository(), MockCalendarRepository(), 
                            PriorityBasedStrategy())
        events = scheduler.schedule_tasks(priority_tasks, [deep_work_zone])
        
        # Verify high priority task gets preferred time slot
        assert events[0].task_id == "high"
        assert events[0].start == deep_work_zone.start

    def test_handles_priority_conflicts_with_due_dates(self):
        # Test when lower priority task has earlier due date
        pass
