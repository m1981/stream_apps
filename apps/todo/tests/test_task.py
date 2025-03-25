import pytest
import dataclasses
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
            project_id="proj1",
            sequence_number=1,  # Changed from priority
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
        return Task(
            id="task1",
            title="Large Task",
            duration=240,  # 4 hours
            due_date=datetime.now() + timedelta(days=1),
            project_id="proj1",
            sequence_number=1,  # Changed from priority
            constraints=TaskConstraints(
                zone_type=ZoneType.DEEP,
                energy_level=EnergyLevel.HIGH,
                is_splittable=True,
                min_chunk_duration=60,  # 1 hour minimum
                max_split_count=4,
                required_buffer=15,
                dependencies=[]
            )
        )

    def test_split_equal_chunks(self, splittable_task):
        """Test splitting task into equal chunks"""
        chunks = splittable_task.split(chunk_sizes=[60, 60, 60, 60])
        assert len(chunks) == 4
        assert all(chunk.duration == 60 for chunk in chunks)
        assert all(chunk.constraints.is_splittable is False for chunk in chunks)

    def test_split_unequal_chunks(self, splittable_task):
        """Test splitting task into unequal chunks"""
        chunks = splittable_task.split(chunk_sizes=[90, 90, 60])
        assert len(chunks) == 3
        assert chunks[0].duration == 90
        assert chunks[1].duration == 90
        assert chunks[2].duration == 60

    def test_split_preserves_metadata(self, splittable_task):
        """Test that split chunks preserve original task metadata"""
        chunks = splittable_task.split(chunk_sizes=[120, 120])
        for i, chunk in enumerate(chunks, 1):
            assert chunk.id == f"{splittable_task.id}_chunk_{i}"
            assert chunk.title == f"{splittable_task.title} (Part {i}/2)"
            assert chunk.due_date == splittable_task.due_date
            assert chunk.sequence_number == splittable_task.sequence_number * 1000 + i  # Updated from priority check
            assert chunk.project_id == splittable_task.project_id
            assert chunk.constraints.zone_type == splittable_task.constraints.zone_type
            assert chunk.constraints.energy_level == splittable_task.constraints.energy_level

    def test_split_creates_dependencies(self, splittable_task):
        """Test that split chunks have correct dependency chain"""
        chunks = splittable_task.split(chunk_sizes=[80, 80, 80])
        assert not chunks[0].constraints.dependencies
        assert chunks[1].constraints.dependencies == [f"{splittable_task.id}_chunk_1"]
        assert chunks[2].constraints.dependencies == [f"{splittable_task.id}_chunk_2"]

    def test_split_validates_chunk_count(self, splittable_task):
        """Test validation of maximum split count"""
        with pytest.raises(ValueError, match="Exceeds maximum split count"):
            splittable_task.split(chunk_sizes=[60, 60, 60, 60, 60])

    def test_split_validates_minimum_duration(self, splittable_task):
        """Test validation of minimum chunk duration"""
        with pytest.raises(ValueError, match="All chunks must be at least"):
            splittable_task.split(chunk_sizes=[45, 45, 150])  # 45 < min_chunk_duration

    def test_split_validates_total_duration(self, splittable_task):
        """Test validation of total duration"""
        with pytest.raises(ValueError, match="Sum of chunk sizes"):
            splittable_task.split(chunk_sizes=[100, 100, 100])  # Sum > original duration

    def test_split_non_splittable_task(self, splittable_task):
        """Test that non-splittable tasks cannot be split"""
        splittable_task.constraints.is_splittable = False
        with pytest.raises(ValueError, match="Task is not splittable"):
            splittable_task.split(chunk_sizes=[120, 120])

    def test_split_chunks_inherit_buffer(self, splittable_task):
        """Test that split chunks inherit buffer requirements"""
        chunks = splittable_task.split(chunk_sizes=[120, 120])
        assert all(chunk.constraints.required_buffer == splittable_task.constraints.required_buffer 
                  for chunk in chunks)

    def test_split_with_existing_dependencies(self):
        """Test splitting task that has existing dependencies"""
        task = Task(
            id="dependent_task",
            title="Dependent Task",
            duration=180,
            due_date=datetime.now() + timedelta(days=1),
            project_id="proj1",
            sequence_number=1,
            constraints=TaskConstraints(
                zone_type=ZoneType.DEEP,
                energy_level=EnergyLevel.HIGH,
                is_splittable=True,
                min_chunk_duration=60,
                max_split_count=3,
                required_buffer=15,
                dependencies=["prerequisite_task"]
            )
        )
        
        chunks = task.split(chunk_sizes=[60, 60, 60])
        # First chunk should inherit original dependencies
        assert "prerequisite_task" in chunks[0].constraints.dependencies
        # Subsequent chunks should depend on previous chunk
        assert chunks[1].constraints.dependencies == [f"{task.id}_chunk_1"]
        assert chunks[2].constraints.dependencies == [f"{task.id}_chunk_2"]

    def test_split_validates_zone_minimum_duration(self):
        """Test splitting respects zone minimum duration"""
        task = Task(
            id="zone_restricted_task",
            title="Zone Restricted Task",
            duration=180,
            due_date=datetime.now() + timedelta(days=1),
            project_id="proj1",
            sequence_number=1,  # Changed from priority
            constraints=TaskConstraints(
                zone_type=ZoneType.DEEP,
                energy_level=EnergyLevel.HIGH,
                is_splittable=True,
                min_chunk_duration=120,  # Deep work minimum
                max_split_count=2,
                required_buffer=15,
                dependencies=[]
            )
        )
        
        with pytest.raises(ValueError, match="All chunks must be at least"):
            task.split(chunk_sizes=[90, 90])  # Below deep work minimum
