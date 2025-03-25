"""
Task sequencing logic for natural ordering.

Domain Context:
- Maintains task order from Todoist projects
- Handles implicit dependencies from sequence
- Provides ordering utilities for scheduler

Business Rules:
- Tasks within same project maintain Todoist order
- Cross-project tasks can interleave based on due dates
- Explicit dependencies override sequence when needed
"""
from dataclasses import dataclass
from typing import List, Dict
from datetime import datetime

@dataclass
class TaskSequence:
    project_id: str
    sequence_number: int  # Position in Todoist
    due_date: datetime

class SequenceManager:
    def order_tasks(self, tasks: List[Task]) -> List[Task]:
        """Orders tasks respecting project sequence and dependencies"""
        # Group by project
        project_tasks: Dict[str, List[Task]] = {}
        for task in tasks:
            if task.project_id not in project_tasks:
                project_tasks[task.project_id] = []
            project_tasks[task.project_id].append(task)
            
        # Sort within projects
        for project_id in project_tasks:
            project_tasks[project_id].sort(
                key=lambda t: t.sequence_number
            )
            
        # Merge projects considering due dates
        return self._merge_project_sequences(project_tasks)

    def _merge_project_sequences(
        self, 
        project_tasks: Dict[str, List[Task]]
    ) -> List[Task]:
        """Merges multiple project sequences intelligently"""
        # Implementation here
        pass