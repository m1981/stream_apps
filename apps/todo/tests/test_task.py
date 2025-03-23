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

class TestTaskSplitting:
    @pytest.fixture
    def splittable_task(self):
        constraints = TaskConstraints(
            zone_type=ZoneType.DEEP,
            energy_level=EnergyLevel.HIGH,
            is_splittable=True,
            min_chunk_duration=30,
            max_split_count=3,
            required_buffer=15,
            dependencies=[]
        )
        return Task(
            id="task1",
            title="Splittable Task",
            duration=120,
            due_date=datetime.now() + timedelta(days=1),
            priority=1,
            project_id="proj1",
            constraints=constraints
        )

    def test_split_task_into_chunks(self, splittable_task):
        chunks = splittable_task.split(chunk_sizes=[45, 45, 30])
        assert len(chunks) == 3
        assert all(chunk.duration >= splittable_task.constraints.min_chunk_duration for chunk in chunks)
        assert sum(chunk.duration for chunk in chunks) == splittable_task.duration

    def test_respects_max_split_count(self, splittable_task):
        with pytest.raises(ValueError, match="Exceeds maximum split count"):
            splittable_task.split(chunk_sizes=[30, 30, 30, 30])

    def test_maintains_task_properties_in_chunks(self, splittable_task):
        chunks = splittable_task.split(chunk_sizes=[60, 60])
        for chunk in chunks:
            assert chunk.constraints.zone_type == splittable_task.constraints.zone_type
            assert chunk.constraints.energy_level == splittable_task.constraints.energy_level
            assert chunk.project_id == splittable_task.project_id

    def test_enforces_minimum_chunk_duration(self, splittable_task):
        with pytest.raises(ValueError, match="All chunks must be at least"):
            splittable_task.split(chunk_sizes=[20, 50, 50])

    def test_validates_total_duration(self, splittable_task):
        with pytest.raises(ValueError, match="Sum of chunk sizes"):
            splittable_task.split(chunk_sizes=[50, 50, 50])  # Exceeds original duration

    def test_creates_sequential_dependencies(self, splittable_task):
        chunks = splittable_task.split(chunk_sizes=[40, 40, 40])
        assert not chunks[0].constraints.dependencies  # First chunk has no dependencies
        assert chunks[1].constraints.dependencies == [f"{splittable_task.id}_chunk_1"]
        assert chunks[2].constraints.dependencies == [f"{splittable_task.id}_chunk_2"]

    def test_prevents_splitting_non_splittable_task(self, splittable_task):
        splittable_task.constraints.is_splittable = False
        with pytest.raises(ValueError, match="Task is not splittable"):
            splittable_task.split(chunk_sizes=[60, 60])

    def test_chunks_are_not_splittable(self, splittable_task):
        chunks = splittable_task.split(chunk_sizes=[60, 60])
        for chunk in chunks:
            assert not chunk.constraints.is_splittable
            assert chunk.constraints.max_split_count == 1
