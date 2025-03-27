from typing import List, Tuple
from datetime import datetime, timedelta
from ..task import Task
from ..timeblock import TimeBlockZone, Event, TimeBlockType
from ..conflict import ConflictDetector
from .base import SchedulingStrategy

class SequenceBasedStrategy(SchedulingStrategy):
    def schedule(self, tasks: List[Task], zones: List[TimeBlockZone], existing_events: List[Event]) -> List[Event]:
        if not zones:
            return []
            
        events = existing_events.copy()  # Include existing events
        scheduled_task_ids = set()
        remaining_tasks = tasks.copy()
        
        # Create multi-day zones based on planning horizon
        all_zones = self._create_multi_day_zones(zones, days=7)
        
        while remaining_tasks:
            available_tasks = [
                task for task in remaining_tasks
                if all(dep in scheduled_task_ids for dep in task.constraints.dependencies)
            ]
            
            if not available_tasks:
                if remaining_tasks:
                    print(f"DEBUG: Dependency deadlock detected")
                break
                
            available_tasks.sort(key=lambda t: (t.due_date, t.project_id, t.sequence_number))
            task = available_tasks[0]
            
            # Always try splitting for splittable tasks
            if task.constraints.is_splittable:
                scheduled = self._try_schedule_split_task(task, all_zones, events, scheduled_task_ids)
            else:
                scheduled = self._try_schedule_task(task, all_zones, events, scheduled_task_ids)
            
            if scheduled:
                remaining_tasks.remove(task)
            else:
                print(f"DEBUG: Failed to schedule task {task.id} in any zone")
                break
                
        return [e for e in events if e.type == TimeBlockType.MANAGED]

    def _find_available_slots(self, zone: TimeBlockZone, events: List[Event], 
                            min_duration: int) -> List[Tuple[datetime, datetime]]:
        """Find available time slots in a zone"""
        slots = []
        current = zone.start
        
        # Get events that overlap with this zone
        zone_events = [e for e in events if e.end > zone.start and e.start < zone.end]
        zone_events.sort(key=lambda e: e.start)
        
        for event in zone_events:
            if (event.start - current).total_seconds() / 60 >= min_duration:
                slots.append((current, event.start))
            current = max(current, event.end)
            
        if (zone.end - current).total_seconds() / 60 >= min_duration:
            slots.append((current, zone.end))
            
        return slots

    def _try_schedule_split_task(self, task: Task, zones: List[TimeBlockZone], 
                                events: List[Event], scheduled_task_ids: set) -> bool:
        """Try to schedule task by splitting it into smaller chunks"""
        remaining_duration = task.duration
        chunk_count = 0
        task_events = []
        
        while remaining_duration > 0 and chunk_count < task.constraints.max_split_count:
            scheduled_chunk = False
            
            for zone in zones:
                if zone.zone_type != task.constraints.zone_type:
                    continue
                    
                # Find available slots in this zone
                available_slots = self._find_available_slots(
                    zone, events, task.constraints.min_chunk_duration
                )
                
                for slot_start, slot_end in available_slots:
                    # Calculate chunk duration
                    available_duration = (slot_end - slot_start).total_seconds() / 60
                    chunk_duration = min(
                        remaining_duration,
                        available_duration,
                        120  # Maximum 2 hours per chunk for better splitting
                    )
                    
                    if chunk_duration >= task.constraints.min_chunk_duration:
                        chunk_id = f"{task.id}_chunk_{chunk_count + 1}"
                        event = Event(
                            id=chunk_id,
                            start=slot_start,
                            end=slot_start + timedelta(minutes=chunk_duration),
                            title=f"{task.title} (Part {chunk_count + 1})",
                            type=TimeBlockType.MANAGED
                        )
                        task_events.append(event)
                        remaining_duration -= chunk_duration
                        chunk_count += 1
                        scheduled_chunk = True
                        break
                
                if scheduled_chunk:
                    break
            
            if not scheduled_chunk:
                return False
        
        if remaining_duration <= 0:
            events.extend(task_events)
            for event in task_events:
                scheduled_task_ids.add(event.id)
            return True
            
        return False

    def _try_schedule_task(self, task: Task, zones: List[TimeBlockZone], 
                          events: List[Event], scheduled_task_ids: set) -> bool:
        """Try to schedule task as a single block"""
        for zone in zones:
            if zone.zone_type != task.constraints.zone_type:
                continue
                
            # Calculate required buffer based on previous event
            if events:
                last_event = events[-1]
                # Use the maximum buffer requirement between consecutive tasks
                required_buffer = max(
                    task.constraints.required_buffer,
                    # Try to get previous task's buffer requirement
                    getattr(last_event, 'buffer_required', 0)
                )
                current_time = max(
                    zone.start,
                    last_event.end + timedelta(minutes=required_buffer)
                )
            else:
                current_time = zone.start
            
            if current_time + timedelta(minutes=task.duration) <= zone.end:
                conflict = ConflictDetector.find_conflicts(task, current_time, zone)
                if not conflict:
                    event = Event(
                        id=task.id,
                        start=current_time,
                        end=current_time + timedelta(minutes=task.duration),
                        title=task.title,
                        type=TimeBlockType.MANAGED,
                        buffer_required=task.constraints.required_buffer  # Store buffer requirement
                    )
                    events.append(event)
                    scheduled_task_ids.add(task.id)
                    return True
        return False

    def _create_multi_day_zones(self, base_zones: List[TimeBlockZone], days: int) -> List[TimeBlockZone]:
        """Create zones for multiple days based on base zones"""
        all_zones = []
        for day in range(days):
            for zone in base_zones:
                next_day = zone.start + timedelta(days=day)
                new_zone = TimeBlockZone(
                    start=datetime.combine(next_day.date(), zone.start.time()),
                    end=datetime.combine(next_day.date(), zone.end.time()),
                    zone_type=zone.zone_type,
                    energy_level=zone.energy_level,
                    min_duration=zone.min_duration,
                    buffer_required=zone.buffer_required,
                    type=zone.type,
                    events=[]
                )
                all_zones.append(new_zone)
        return all_zones