import pytest
from datetime import datetime, timedelta
from src.domain.timeblock import TimeBlock, TimeBlockZone, TimeBlockType, Event
from src.domain.task import ZoneType, EnergyLevel

class TestTimeBlockAvailability:
    @pytest.fixture
    def time_block(self):
        start = datetime.now().replace(hour=9, minute=0)
        end = start + timedelta(hours=4)
        return TimeBlock(start, end, TimeBlockType.ZONE)

    def test_detects_basic_availability(self, time_block):
        start = time_block.start + timedelta(minutes=30)
        assert time_block.is_available(start, 60) == True

    def test_detects_out_of_bounds(self, time_block):
        start = time_block.start - timedelta(minutes=30)
        assert time_block.is_available(start, 60) == False

    def test_detects_conflicts(self, time_block):
        event = Event(
            id="evt1",
            start=time_block.start + timedelta(minutes=30),
            end=time_block.start + timedelta(minutes=90),
            title="Existing Meeting",
            type=TimeBlockType.FIXED
        )
        time_block.events.append(event)
        
        start = time_block.start + timedelta(minutes=45)
        conflicts = time_block.get_conflicts(start, 30)
        assert len(conflicts) == 1
        assert conflicts[0].id == "evt1"

class TestTimeBlockZone:
    @pytest.fixture
    def deep_work_zone(self):
        start = datetime.now().replace(hour=9, minute=0)
        end = start + timedelta(hours=4)
        return TimeBlockZone(
            start=start,
            end=end,
            zone_type=ZoneType.DEEP,
            energy_level=EnergyLevel.HIGH,
            min_duration=120,
            buffer_required=15,
            events=[]
        )

    def test_enforces_minimum_duration(self, deep_work_zone):
        start = deep_work_zone.start + timedelta(minutes=30)
        assert deep_work_zone.is_available(start, 60) == False

    def test_respects_buffer_requirements(self, deep_work_zone):
        event = Event(
            id="evt1",
            start=deep_work_zone.start + timedelta(minutes=60),
            end=deep_work_zone.start + timedelta(minutes=120),
            title="Existing Task",
            type=TimeBlockType.MANAGED
        )
        deep_work_zone.events.append(event)
        
        # Try to schedule right after the event
        start = event.end
        conflicts = deep_work_zone.get_conflicts(start, 60)
        assert len(conflicts) == 1  # Should conflict due to buffer requirement
