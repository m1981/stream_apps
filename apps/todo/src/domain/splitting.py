from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional
from .task import Task, ZoneType, EnergyLevel
from .timeblock import TimeBlockZone, Event, TimeBlockType  # Added Event and TimeBlockType

@dataclass
class SplitMetrics:
    """Metrics for optimizing task splitting decisions"""
    optimal_chunk_count: int
    chunk_duration: int
    total_buffer_time: int
    zone_utilization: float  # 0-1 representing zone capacity usage

@dataclass
class ChunkPlacement:
    """Represents a potential placement for a task chunk"""
    start_time: datetime
    duration: int
    zone_id: str
    energy_cost: float  # 0-1 representing energy expenditure
    context_switches: int  # Number of context switches this placement causes

class SplitStrategy:
    """Determines optimal task splitting strategy based on available zones"""
    
    def calculate_optimal_split(
        self,
        total_duration: int,
        available_zones: List[TimeBlockZone],
        min_chunk_duration: int,
        max_splits: int
    ) -> Optional[SplitMetrics]:
        """
        Calculate optimal split configuration based on zone patterns.
        
        Args:
            total_duration: Total task duration in minutes
            available_zones: List of available time block zones
            min_chunk_duration: Minimum duration for each chunk in minutes
            max_splits: Maximum number of splits allowed
        
        Returns:
            SplitMetrics object with optimal splitting configuration or None if no valid split found
        """
        if not available_zones or total_duration <= 0:
            return None
        
        print("\n=== Split Strategy Calculation ===")
        print(f"Total duration: {total_duration} minutes")
        print(f"Min chunk duration: {min_chunk_duration} minutes")
        print(f"Max splits allowed: {max_splits}")
        
        # Calculate optimal chunks based on preferred chunk size
        preferred_chunk_size = 120  # 2 hours
        optimal_chunks = max(1, -(-total_duration // preferred_chunk_size))
        optimal_chunks = min(optimal_chunks, max_splits + 1)
        chunk_duration = -(-total_duration // optimal_chunks)
        
        print(f"\nChunk Calculation:")
        print(f"Optimal chunks: {optimal_chunks}")
        print(f"Chunk duration: {chunk_duration} minutes")
        
        # Calculate buffer times:
        # 1. Between chunks
        between_chunks_buffer = (optimal_chunks - 1) * 15
        # 2. Around existing events (minimum 15 minutes before and after each chunk)
        existing_events_buffer = optimal_chunks * (15 * 2)  # 15 mins before and after each chunk
        total_buffer = between_chunks_buffer + existing_events_buffer
        
        # Get morning DEEP work zones, sorted by start time
        morning_deep_zones = sorted(
            [z for z in available_zones 
             if z.zone_type == ZoneType.DEEP and z.start.hour == 9],
            key=lambda z: z.start
        )
        
        # Calculate usable capacity based on chunk duration
        zones_needed = optimal_chunks
        usable_zone_capacity = zones_needed * chunk_duration  # Only count the time we'll actually use
        
        print(f"\nZone Analysis:")
        print(f"Morning DEEP zones available: {len(morning_deep_zones)}")
        print(f"Zones needed: {zones_needed}")
        print(f"Usable zone capacity: {usable_zone_capacity} minutes")
        
        # Calculate utilization based on actual chunk usage
        zone_utilization = (total_duration / usable_zone_capacity 
                           if usable_zone_capacity > 0 else 0)
        
        print(f"\nUtilization Analysis:")
        print(f"Total required time (task only): {total_duration} minutes")
        print(f"Total buffer time: {total_buffer} minutes")
        print(f"Zone utilization: {zone_utilization:.2f}")
        
        metrics = SplitMetrics(
            optimal_chunk_count=optimal_chunks,
            chunk_duration=chunk_duration,
            total_buffer_time=total_buffer,
            zone_utilization=min(zone_utilization, 1.0)
        )
        
        print(f"\nFinal Metrics:")
        print(f"Chunks: {metrics.optimal_chunk_count}")
        print(f"Duration per chunk: {metrics.chunk_duration} minutes")
        print(f"Buffer time: {metrics.total_buffer_time} minutes")
        print(f"Utilization: {metrics.zone_utilization:.2f}")
        
        return metrics

    def analyze_zone_patterns(
        self,
        zones: List[TimeBlockZone],
        days_ahead: int = 7
    ) -> List[ChunkPlacement]:
        """
        Analyze zone patterns to find optimal chunk placements.
        
        Args:
            zones: List of available time block zones
            days_ahead: Number of days to look ahead for pattern analysis
            
        Returns:
            List of potential chunk placements sorted by optimality
        """
        if not zones:
            return []
            
        placements = []
        
        # Sort zones chronologically
        sorted_zones = sorted(zones, key=lambda z: z.start)
        
        for zone in sorted_zones:
            # Calculate available duration
            available_duration = int((zone.end - zone.start).total_seconds() / 60)
            
            # Calculate energy cost based on zone type and energy level
            energy_cost = 0.5  # Base cost
            if zone.zone_type == ZoneType.DEEP:
                energy_cost = 0.7 if zone.energy_level == EnergyLevel.HIGH else 0.9
            
            # Calculate context switches (simplified version)
            context_switches = 0
            
            placement = ChunkPlacement(
                start_time=zone.start,
                duration=available_duration,
                zone_id=str(id(zone)),  # Using object id as temporary zone id
                energy_cost=energy_cost,
                context_switches=context_switches
            )
            
            placements.append(placement)
        
        # Sort placements by energy cost (lower is better)
        return sorted(placements, key=lambda p: p.energy_cost)