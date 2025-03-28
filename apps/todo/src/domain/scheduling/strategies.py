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

    def _find_available_slots_with_duration(self, zone: TimeBlockZone, events: List[Event], 
                                          min_duration: int, required_buffer: int) -> List[Tuple[datetime, datetime]]:
        """Find available time slots in a zone that can fit the specified duration"""
        slots = []
        current = zone.start
        
        # Get events that overlap with this zone
        zone_events = [e for e in events if e.end > zone.start and e.start < zone.end]
        zone_events.sort(key=lambda e: e.start)
        
        if not zone_events:
            duration_minutes = (zone.end - zone.start).total_seconds() / 60
            if duration_minutes >= min_duration:
                slots.append((zone.start, zone.end))
            return slots
        
        # Check slot before first event
        first_slot_duration = (zone_events[0].start - current).total_seconds() / 60
        if first_slot_duration >= min_duration:
            slots.append((current, zone_events[0].start))
        
        # Check slots between events
        for i in range(len(zone_events) - 1):
            current_event = zone_events[i]
            next_event = zone_events[i + 1]
            
            # Add required buffer after current event
            slot_start = current_event.end + timedelta(minutes=required_buffer)
            slot_duration = (next_event.start - slot_start).total_seconds() / 60
            
            if slot_duration >= min_duration:
                slots.append((slot_start, next_event.start))
        
        # Check final slot
        last_event = zone_events[-1]
        final_start = last_event.end + timedelta(minutes=required_buffer)
        final_duration = (zone.end - final_start).total_seconds() / 60
        
        if final_duration >= min_duration:
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
        
        # Calculate optimal chunk size
        optimal_chunk_size = max(
            min(task.duration // 2, 120),  # Try to split into 2 chunks, max 120 mins each
            task.constraints.min_chunk_duration  # But respect minimum chunk duration
        )
        
        print(f"Calculated optimal chunk size: {optimal_chunk_size} minutes")
        
        while remaining_duration > 0 and chunk_count < task.constraints.max_split_count:
            chunk_duration = min(remaining_duration, optimal_chunk_size)
            
            print(f"\nAttempting to schedule chunk {chunk_count + 1}")
            print(f"Chunk duration: {chunk_duration} minutes")
            print(f"Remaining duration: {remaining_duration} minutes")
            
            chunk_scheduled = False
            for zone in sorted_zones:
                if zone.zone_type != task.constraints.zone_type:
                    continue
                
                slots = self._find_available_slots_with_duration(
                    zone, current_events, chunk_duration, task.constraints.required_buffer
                )
                
                if slots:
                    slot_start, slot_end = slots[0]
                    chunk_id = f"{task.id}_chunk_{chunk_count + 1}"
                    event = Event(
                        id=chunk_id,
                        start=slot_start,
                        end=slot_start + timedelta(minutes=chunk_duration),
                        title=f"{task.title} (Part {chunk_count + 1})",
                        type=TimeBlockType.MANAGED,
                        buffer_required=task.constraints.required_buffer
                    )
                    
                    print(f"Scheduled chunk {chunk_count + 1}: {event.start} - {event.end}")
                    
                    current_events.append(event)
                    task_events.append(event)
                    remaining_duration -= chunk_duration
                    chunk_count += 1
                    chunk_scheduled = True
                    break
                
            if not chunk_scheduled:
                print(f"Failed to schedule chunk {chunk_count + 1}")
                return False
        
        print(f"\nFinal scheduling result:")
        print(f"Total chunks created: {len(task_events)}")
        print(f"Remaining duration: {remaining_duration}")
        for idx, event in enumerate(task_events, 1):
            print(f"Chunk {idx}: {event.start} - {event.end} "
                  f"({(event.end - event.start).total_seconds() / 60} minutes)")
        
        if remaining_duration <= 0:
            events.extend(task_events)
            scheduled_task_ids.add(task.id)
            return True
        
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
