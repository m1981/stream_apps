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
        """Find available time slots in a zone, respecting buffer requirements"""
        slots = []
        current = zone.start
        
        # Get events that overlap with this zone, including fixed events
        zone_events = [
            e for e in events 
            if e.end > zone.start and e.start < zone.end
        ]
        zone_events.sort(key=lambda e: e.start)
        
        if not zone_events:
            if (zone.end - zone.start).total_seconds() / 60 >= min_duration:
                slots.append((zone.start, zone.end))
            return slots
        
        # Check slot before first event
        if (zone_events[0].start - current).total_seconds() / 60 >= min_duration:
            slots.append((current, zone_events[0].start))
        
        # Check slots between events
        for i in range(len(zone_events) - 1):
            current_event = zone_events[i]
            next_event = zone_events[i + 1]
            
            slot_start = current_event.end + timedelta(minutes=current_event.buffer_required)
            if (next_event.start - slot_start).total_seconds() / 60 >= min_duration:
                slots.append((slot_start, next_event.start))
        
        # Check final slot
        last_event = zone_events[-1]
        final_start = last_event.end + timedelta(minutes=last_event.buffer_required)
        if (zone.end - final_start).total_seconds() / 60 >= min_duration:
            slots.append((final_start, zone.end))
        
        return slots

    def _try_schedule_split_task(self, task: Task, zones: List[TimeBlockZone], 
                                events: List[Event], scheduled_task_ids: set) -> bool:
        """Try to schedule task by splitting it into smaller chunks"""
        remaining_duration = task.duration
        chunk_count = 0
        task_events = []
        current_events = events.copy()
        
        print(f"\n=== Starting split scheduling for task: {task.id} ===")
        print(f"Total duration: {task.duration} minutes")
        print(f"Min chunk duration: {task.constraints.min_chunk_duration} minutes")
        print(f"Max split count: {task.constraints.max_split_count}")
        print(f"Buffer required: {task.constraints.required_buffer} minutes")
        
        # Sort zones chronologically
        sorted_zones = sorted(zones, key=lambda z: z.start)
        
        # Try to schedule chunks across multiple zones if needed
        for zone in sorted_zones:
            if remaining_duration <= 0:
                break
            
            if zone.zone_type != task.constraints.zone_type:
                print(f"\nSkipping zone {zone.start} - {zone.end} (incompatible type: {zone.zone_type})")
                continue
            
            print(f"\nTrying zone: {zone.start} - {zone.end}")
            print(f"Zone type: {zone.zone_type}")
            print(f"Remaining duration: {remaining_duration} minutes")
            
            # Find available slots in this zone
            available_slots = self._find_available_slots(
                zone, current_events, task.constraints.min_chunk_duration
            )
            
            for slot_start, slot_end in available_slots:
                if remaining_duration <= 0 or chunk_count >= task.constraints.max_split_count:
                    break
                
                # Calculate chunk duration for this slot
                available_duration = (slot_end - slot_start).total_seconds() / 60
                chunk_duration = min(
                    remaining_duration,
                    available_duration,
                    120  # Maximum 2 hours per chunk
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
                    
                    print(f"Created chunk {chunk_count + 1}:")
                    print(f"Start: {event.start}")
                    print(f"End: {event.end}")
                    print(f"Duration: {chunk_duration} minutes")
                    
                    task_events.append(event)
                    current_events.append(event)
                    remaining_duration -= chunk_duration
                    chunk_count += 1
                    
                    print(f"Remaining duration: {remaining_duration} minutes")
        
        if remaining_duration <= 0:
            print("\nSuccessfully scheduled all chunks")
            events.extend(task_events)
            for event in task_events:
                scheduled_task_ids.add(event.id.split('_chunk_')[0])  # Add base task ID
            return True
        
        print(f"\nFailed to schedule all chunks. Remaining duration: {remaining_duration}")
        return False

    def _try_schedule_chunk_in_zones(self, zones: List[TimeBlockZone], task: Task,
                                    remaining_duration: int, chunk_count: int,
                                    current_events: List[Event],
                                    task_events: List[Event]) -> bool:
        """Try to schedule a single chunk within the given zones"""
        for zone in zones:
            if zone.zone_type != task.constraints.zone_type:
                continue
            
            available_slots = self._find_available_slots(
                zone, current_events, task.constraints.min_chunk_duration
            )
            
            for slot_start, slot_end in available_slots:
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

    def _create_multi_day_zones(self, base_zones: List[TimeBlockZone], days: int = 7) -> List[TimeBlockZone]:
        """Create zones for multiple days based on base zone template"""
        multi_day_zones = []
        start_date = base_zones[0].start

        for day in range(days):
            day_start = start_date + timedelta(days=day)
            for zone in base_zones:
                # Create new zone with same properties but adjusted date
                new_zone = TimeBlockZone(
                    start=day_start.replace(hour=zone.start.hour, minute=zone.start.minute),
                    end=day_start.replace(hour=zone.end.hour, minute=zone.end.minute),
                    zone_type=zone.zone_type,
                    energy_level=zone.energy_level,
                    min_duration=zone.min_duration,
                    buffer_required=zone.buffer_required,
                    events=[]
                )
                multi_day_zones.append(new_zone)
        
        return multi_day_zones
