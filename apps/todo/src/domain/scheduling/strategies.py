from typing import List
from datetime import datetime, timedelta
from ..task import Task
from ..timeblock import TimeBlockZone, Event, TimeBlockType
from ..conflict import ConflictDetector
from .base import SchedulingStrategy

class SequenceBasedStrategy(SchedulingStrategy):
    def schedule(self, tasks: List[Task], zones: List[TimeBlockZone], existing_events: List[Event]) -> List[Event]:
        if not zones:
            return []
            
        events = []
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
            scheduled = False
            
            for zone in all_zones:
                if zone.zone_type != task.constraints.zone_type:
                    continue
                    
                current_time = max(
                    zone.start,
                    events[-1].end + timedelta(minutes=task.constraints.required_buffer) if events else zone.start
                )
                
                if current_time + timedelta(minutes=task.duration) <= zone.end:
                    conflict = ConflictDetector.find_conflicts(task, current_time, zone)
                    if not conflict:
                        event = Event(
                            id=task.id,
                            start=current_time,
                            end=current_time + timedelta(minutes=task.duration),
                            title=task.title,
                            type=TimeBlockType.MANAGED
                        )
                        events.append(event)
                        scheduled_task_ids.add(task.id)
                        scheduled = True
                        break
            
            if scheduled:
                remaining_tasks.remove(task)
            else:
                print(f"DEBUG: Failed to schedule task {task.id} in any zone")
                break
                
        return events

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