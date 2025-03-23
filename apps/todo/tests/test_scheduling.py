import pytest
from datetime import datetime, timedelta
from src.domain.scheduling import ConflictDetector, SchedulingConflict
from src.domain.timeblock import TimeBlockZone
from src.domain.task import Task, TaskConstraints, ZoneType, EnergyLevel
class TestConflictDetection:
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