from datetime import datetime
from src.domain.task import Task, TaskConstraints, ZoneType, EnergyLevel
from src.domain.timeblock import TimeBlockZone
from src.domain.conflict import ConflictDetector

def test_zone_transition_conflicts():
    """
    Test detection of conflicts when tasks cross time block zone boundaries.
    
    Scenario:
    ---------
    Given:
    - A 3-hour task (180 minutes) that requires:
        * DEEP work zone
        * HIGH energy level
        * Non-splittable (must be scheduled as single block)
        * 15-minute buffer requirement
    
    - Two adjacent time zones:
        Zone 1 (DEEP/HIGH):
            * 10:00 AM - 12:00 PM
            * DEEP work, HIGH energy
            * 30-min minimum duration
            * 15-min buffer required
            
        Zone 2 (LIGHT/MEDIUM):
            * 12:00 PM - 2:00 PM
            * LIGHT work, MEDIUM energy
            * 30-min minimum duration
            * 15-min buffer required
    
    Test Cases:
    -----------
    1. Incompatible Zone Transition:
       - Start task at 11:00 AM (in Zone 1)
       - Task would cross into Zone 2 at 12:00 PM
       - Expected: Conflict detected due to incompatible zone types (DEEP → LIGHT)
       
    2. Compatible Zone Transition:
       - Change Zone 2 to match Zone 1 (DEEP/HIGH)
       - Start task at 11:00 AM
       - Expected: No conflict detected as zones are compatible
    
    Business Rules Verified:
    -----------------------
    1. Tasks cannot transition between zones with different types
    2. Tasks cannot transition between zones with different energy levels
    3. Tasks can span multiple zones if zones are compatible
    4. Zone transitions are properly detected and validated
    
    Edge Cases Covered:
    ------------------
    - Task spanning exactly across zone boundary
    - Zone compatibility checking for both type and energy level
    - Proper detection of transition points
    """
    
    # Given: A task that spans multiple zones
    task = Task(
        id="cross_zone_task",
        title="Cross Zone Task",
        duration=180,  # 3 hours
        due_date=datetime(2024, 1, 1, 17),
        project_id="proj1",
        sequence_number=1,
        constraints=TaskConstraints(
            zone_type=ZoneType.DEEP,
            energy_level=EnergyLevel.HIGH,
            is_splittable=False,
            min_chunk_duration=180,
            max_split_count=1,
            required_buffer=15,
            dependencies=[]
        )
    )
    
    # And: Two adjacent zones with different types
    zone1 = TimeBlockZone(
        start=datetime(2024, 1, 1, 10),  # 10 AM
        end=datetime(2024, 1, 1, 12),    # 12 PM
        zone_type=ZoneType.DEEP,
        energy_level=EnergyLevel.HIGH,
        min_duration=30,
        buffer_required=15,
        events=[]
    )
    
    zone2 = TimeBlockZone(
        start=datetime(2024, 1, 1, 12),  # 12 PM
        end=datetime(2024, 1, 1, 14),    # 2 PM
        zone_type=ZoneType.LIGHT,
        energy_level=EnergyLevel.MEDIUM,
        min_duration=30,
        buffer_required=15,
        events=[]
    )
    
    # When: Checking for conflicts with incompatible zones
    conflict = ConflictDetector.find_zone_transition_conflicts(
        task,
        datetime(2024, 1, 1, 11),  # Start at 11 AM
        [zone1, zone2]
    )
    
    # Then: Should detect incompatible zone transition
    assert conflict is not None, "Should detect conflict for incompatible zone transition"
    assert "Incompatible zone transition" in conflict.message, \
           "Conflict message should indicate zone incompatibility"
    assert conflict.start_zone == zone1, "Start zone should be Zone 1"
    assert conflict.end_zone == zone2, "End zone should be Zone 2"
    
    # When: Zones have same type and energy level
    zone2.zone_type = ZoneType.DEEP
    zone2.energy_level = EnergyLevel.HIGH
    
    conflict = ConflictDetector.find_zone_transition_conflicts(
        task,
        datetime(2024, 1, 1, 11),  # Start at 11 AM
        [zone1, zone2]
    )
    
    # Then: Should not detect conflict for compatible zones
    assert conflict is None, "Should not detect conflict when zones are compatible"