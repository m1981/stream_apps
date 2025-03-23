class TestRescheduling:
    def test_reschedules_on_priority_change(self):
        task = Task(id="task1", priority=2)
        scheduler.schedule_tasks([task])
        
        # Change priority
        task.priority = 1
        events = scheduler.reschedule_tasks([task])
        assert events[0].start < original_start  # Got better time slot

    def test_handles_new_calendar_conflicts(self):
        # Test rescheduling when new fixed events are added
        pass

    def test_maintains_dependencies_during_reschedule(self):
        # Test that dependency order is preserved during rescheduling
        pass