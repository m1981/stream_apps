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
            
        print("\nStarting scheduling process:")
        print(f"Total tasks to schedule: {len(tasks)}")
        print(f"Available zones: {len(zones)}")
        print(f"Existing events: {len(existing_events)}")
            
        events = existing_events.copy()  # Include existing events
        scheduled_task_ids = set()
        remaining_tasks = tasks.copy()
        
        # Create multi-day zones based on planning horizon
        all_zones = self._create_multi_day_zones(zones, days=7)
        print(f"\nCreated {len(all_zones)} multi-day zones")
        
        while remaining_tasks:
            available_tasks = [
                task for task in remaining_tasks
                if all(dep in scheduled_task_ids for dep in task.constraints.dependencies)
            ]
            
            print(f"\nRemaining tasks: {len(remaining_tasks)}")
            print(f"Available tasks: {len(available_tasks)}")
            print(f"Scheduled task IDs: {scheduled_task_ids}")
            
            if not available_tasks:
                if remaining_tasks:
                    print(f"DEBUG: Dependency deadlock detected")
                    print(f"Remaining tasks: {[t.id for t in remaining_tasks]}")
                    print(f"Their dependencies: {[t.constraints.dependencies for t in remaining_tasks]}")
                break
                
            available_tasks.sort(key=lambda t: (t.due_date, t.project_id, t.sequence_number))
            task = available_tasks[0]
            
            print(f"\nAttempting to schedule task: {task.id}")
            print(f"Task zone type: {task.constraints.zone_type}")
            print(f"Task duration: {task.duration}")
            print(f"Dependencies: {task.constraints.dependencies}")
            
            # Always try splitting for splittable tasks
            if task.constraints.is_splittable:
                print(f"Attempting to split task {task.id}")
                scheduled = self._try_schedule_split_task(task, all_zones, events, scheduled_task_ids)
            else:
                print(f"Attempting to schedule task {task.id} as single block")
                scheduled = self._try_schedule_task(task, all_zones, events, scheduled_task_ids)
            
            if scheduled:
                print(f"Successfully scheduled task {task.id}")
                remaining_tasks.remove(task)
            else:
                print(f"\nFailed to schedule task {task.id}")
                print("Available zones:")
                for zone in all_zones:
                    print(f"- Zone: {zone.zone_type}, Time: {zone.start}-{zone.end}")
                print("Current events:")
                for event in events:
                    print(f"- Event: {event.id}, Time: {event.start}-{event.end}")
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
                            type=TimeBlockType.MANAGED,
                            buffer_required=task.constraints.required_buffer
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
        print(f"\nTrying to schedule task {task.id} in available zones")
        
        for zone in zones:
            if zone.zone_type != task.constraints.zone_type:
                print(f"Skipping zone - type mismatch: {zone.zone_type} != {task.constraints.zone_type}")
                continue
                
            print(f"Checking zone: {zone.zone_type} ({zone.start} - {zone.end})")
            
            # Calculate required buffer based on previous event
            if events:
                last_event = events[-1]
                required_buffer = max(
                    task.constraints.required_buffer,
                    last_event.buffer_required
                )
                current_time = max(
                    zone.start,
                    last_event.end + timedelta(minutes=required_buffer)
                )
                print(f"Last event ends at {last_event.end}, using buffer {required_buffer}")
                print(f"Calculated start time: {current_time}")
            else:
                current_time = zone.start
                print(f"No previous events, starting at zone start: {current_time}")
        
            if current_time + timedelta(minutes=task.duration) <= zone.end:
                conflict = ConflictDetector.find_conflicts(task, current_time, zone)
                if not conflict:
                    print(f"Found valid slot at {current_time}")
                    event = Event(
                        id=task.id,
                        start=current_time,
                        end=current_time + timedelta(minutes=task.duration),
                        title=task.title,
                        type=TimeBlockType.MANAGED,
                        buffer_required=task.constraints.required_buffer
                    )
                    events.append(event)
                    scheduled_task_ids.add(task.id)
                    return True
                else:
                    print(f"Conflict detected: {conflict.message}")
            else:
                print(f"Not enough time in zone: need {task.duration} minutes")
                
        print(f"No suitable zone found for task {task.id}")
        return False

    def _create_multi_day_zones(self, zones: List[TimeBlockZone], days: int) -> List[TimeBlockZone]:
        """Create zones for multiple days based on the template zones"""
        multi_day_zones = []
        for day in range(days):
            day_offset = timedelta(days=day)
            for zone in zones:  # Iterate through ALL zones
                new_zone = TimeBlockZone(
                    zone_type=zone.zone_type,
                    start=zone.start + day_offset,
                    end=zone.end + day_offset,
                    energy_level=zone.energy_level,
                    min_duration=zone.min_duration,
                    buffer_required=zone.buffer_required,
                    events=zone.events.copy() if zone.events else []
                )
                multi_day_zones.append(new_zone)
        return multi_day_zones
