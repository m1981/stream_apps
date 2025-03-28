from datetime import datetime, timedelta
import pytest
from src.domain.splitting import SplitStrategy, SplitMetrics, ChunkPlacement
from src.domain.task import Task, TaskConstraints, ZoneType, EnergyLevel
from src.domain.timeblock import TimeBlockZone, Event, TimeBlockType

@pytest.fixture
def strategy():
    return SplitStrategy()

@pytest.fixture
def work_week_zones():
    """Creates a week of work zones with realistic patterns"""
    zones = []
    start_date = datetime(2024, 1, 1)  # Monday
    
    for day in range(5):  # Monday to Friday
        day_start = start_date + timedelta(days=day)
        
        # Morning DEEP work zone (9 AM - 12 PM)
        zones.append(TimeBlockZone(
            start=day_start.replace(hour=9),
            end=day_start.replace(hour=12),
            zone_type=ZoneType.DEEP,
            energy_level=EnergyLevel.HIGH,
            min_duration=30,
            buffer_required=15,
            events=[]
        ))
        
        # Afternoon LIGHT work zone (1 PM - 5 PM)
        zones.append(TimeBlockZone(
            start=day_start.replace(hour=13),
            end=day_start.replace(hour=17),
            zone_type=ZoneType.LIGHT,
            energy_level=EnergyLevel.MEDIUM,
            min_duration=30,
            buffer_required=15,
            events=[]
        ))
    
    return zones

def test_optimal_split_calculation(strategy, work_week_zones):
    """
    Test optimal split calculation based on zone patterns.
    
    Scenario:
    - 6-hour task (360 minutes)
    - Available zones: 5 days of morning DEEP work (3 hours each)
    - Task constraints: min 60 minutes per chunk, max 4 splits
    
    Expected:
    - Should split into 3 chunks of 120 minutes each
    - Should utilize morning DEEP work zones
    - Should minimize context switches
    """
    # Given
    total_duration = 360  # 6 hours
    min_chunk_duration = 60  # 1 hour minimum
    max_splits = 4
    
    # When
    metrics = strategy.calculate_optimal_split(
        total_duration=total_duration,
        available_zones=work_week_zones,
        min_chunk_duration=min_chunk_duration,
        max_splits=max_splits
    )
    
    # Then
    assert metrics is not None
    assert metrics.optimal_chunk_count == 3
    assert metrics.chunk_duration == 120  # 2 hours per chunk
    assert metrics.zone_utilization >= 0.8  # Should utilize zones efficiently

def test_zone_pattern_analysis(strategy, work_week_zones):
    """
    Test zone pattern analysis for optimal chunk placement.
    
    Scenario:
    - Analyze 5 days of zones
    - Morning DEEP work and afternoon LIGHT work pattern
    - Looking for optimal DEEP work placements
    
    Expected:
    - Should identify morning DEEP work pattern
    - Should suggest placements that minimize energy cost
    - Should account for buffer requirements
    """
    # Given
    days_ahead = 5
    
    # When
    placements = strategy.analyze_zone_patterns(
        zones=work_week_zones,
        days_ahead=days_ahead
    )
    
    # Then
    assert len(placements) > 0
    
    # Verify placements are in DEEP work zones
    morning_deep_zones = [
        p for p in placements 
        if p.start_time.hour == 9 and p.duration == 180  # 3 hours
    ]
    assert len(morning_deep_zones) == 5  # One for each day
    
    # Verify energy cost optimization
    for placement in morning_deep_zones:
        assert placement.energy_cost <= 0.8  # High energy time slots
        assert placement.context_switches == 0  # No switches within zone

def test_split_with_existing_events(strategy, work_week_zones):
    """
    Test split optimization with existing events in zones.
    
    Scenario:
    - 4-hour task (240 minutes)
    - Some zones have existing events
    - Need to find optimal split around events
    
    Expected:
    - Should avoid conflicts with existing events
    - Should maintain minimum chunk duration
    - Should optimize for fewer splits when possible
    """
    # Given
    existing_event = Event(
        id="existing1",
        start=work_week_zones[0].start + timedelta(minutes=60),
        end=work_week_zones[0].start + timedelta(minutes=120),
        title="Existing Meeting",
        type=TimeBlockType.FIXED,
        buffer_required=15
    )
    work_week_zones[0].events.append(existing_event)
    
    total_duration = 240  # 4 hours
    min_chunk_duration = 60  # 1 hour minimum
    max_splits = 3
    
    # When
    metrics = strategy.calculate_optimal_split(
        total_duration=total_duration,
        available_zones=work_week_zones,
        min_chunk_duration=min_chunk_duration,
        max_splits=max_splits
    )
    
    # Then
    assert metrics is not None
    assert metrics.optimal_chunk_count <= 3
    assert metrics.chunk_duration >= min_chunk_duration
    assert metrics.total_buffer_time >= existing_event.buffer_required * 2

def test_energy_level_optimization(strategy, work_week_zones):
    """
    Test split optimization based on energy levels.
    
    Scenario:
    - 6-hour HIGH energy task
    - Mix of HIGH and MEDIUM energy zones
    - Need to optimize for energy level matching
    
    Expected:
    - Should prefer HIGH energy zones
    - Should minimize energy level transitions
    - Should consider cumulative energy cost
    """
    # Given
    task = Task(
        id="high_energy_task",
        title="High Energy Task",
        duration=360,  # 6 hours
        due_date=datetime(2024, 1, 5),
        project_id="proj1",
        sequence_number=1,
        constraints=TaskConstraints(
            zone_type=ZoneType.DEEP,
            energy_level=EnergyLevel.HIGH,
            is_splittable=True,
            min_chunk_duration=60,
            max_split_count=4,
            required_buffer=15,
            dependencies=[]
        )
    )
    
    # When
    placements = strategy.analyze_zone_patterns(
        zones=work_week_zones,
        days_ahead=5
    )
    
    # Then
    high_energy_placements = [p for p in placements if p.energy_cost <= 0.7]
    assert len(high_energy_placements) >= 3  # Should find at least 3 good slots
    
    # Verify energy optimization
    total_energy_cost = sum(p.energy_cost for p in high_energy_placements[:3])
    assert total_energy_cost <= 2.1  # Average 0.7 per chunk