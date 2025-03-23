import pytest
from datetime import datetime, timedelta
from src.domain.task import Task, TaskConstraints, EnergyLevel, ZoneType

class TestTaskValidation:
    @pytest.fixture
    def valid_constraints(self):
        return TaskConstraints(
            zone_type=ZoneType.DEEP,
            energy_level=EnergyLevel.HIGH,
            is_splittable=True,
            min_chunk_duration=30,
            max_split_count=2,
            required_buffer=15,
            dependencies=[]
        )

    @pytest.fixture
    def valid_task(self, valid_constraints):
        return Task(
            id="task1",
            title="Important Task",
            duration=120,
            due_date=datetime.now() + timedelta(days=1),
            priority=1,
            project_id="proj1",
            constraints=valid_constraints
        )

    def test_valid_task_passes_validation(self, valid_task):
        assert valid_task.validate() == []

    def test_rejects_negative_duration(self, valid_task):
        valid_task.duration = -30
        errors = valid_task.validate()
        assert "Task duration must be positive" in errors

    def test_rejects_past_due_date(self, valid_task):
        valid_task.due_date = datetime.now() - timedelta(days=1)
        errors = valid_task.validate()
        assert "Due date cannot be in the past" in errors

    def test_validates_splitting_constraints(self, valid_task):
        valid_task.duration = 40
        valid_task.constraints.min_chunk_duration = 30
        valid_task.constraints.max_split_count = 2
        errors = valid_task.validate()
        assert "Total minimum chunk duration (60 min) exceeds task duration (40 min)" in errors