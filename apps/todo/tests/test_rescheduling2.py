import pytest
from datetime import datetime, timedelta
from src.domain.task import Task, TaskConstraints, ZoneType, EnergyLevel
from src.domain.scheduler import Scheduler
from src.domain.timeblock import TimeBlockZone, Event, TimeBlockType

class TestRescheduling:
    @pytest.fixture
    def work_day_zones(self):
        """Typical work day time blocks"""
        now = datetime.now().replace(hour=8, minute=0, second=0, microsecond=0)
        return [
            TimeBlockZone(  # Morning deep work
                start=now,
                end=now + timedelta(hours=4),
                zone_type=ZoneType.DEEP,
                energy_level=EnergyLevel.HIGH,
                min_duration=120,
                buffer_required=15,
                events=[]
            ),
            TimeBlockZone(  # Afternoon light work
                start=now + timedelta(hours=5),
                end=now + timedelta(hours=9),
                zone_type=ZoneType.LIGHT,
                energy_level=EnergyLevel.MEDIUM,
                min_duration=30,
                buffer_required=10,
                events=[]
            )
        ]

    def test_reschedule_on_task_duration_change(self, work_day_zones):
        """
        When: Task duration is updated
        Then: Only affected task and its dependents should be rescheduled
        And: Other tasks should maintain their original schedule
        """
        # Initial schedule
        write_task = Task(id="write", duration=60, zone_type=ZoneType.DEEP)
        review_task = Task(id="review", duration=30, zone_type=ZoneType.LIGHT,
                           dependencies=["write"])
        email_task = Task(id="email", duration=30, zone_type=ZoneType.LIGHT)

        scheduler = Scheduler()
        original_schedule = scheduler.schedule_tasks([write_task, review_task, email_task])

        # Change duration and reschedule
        write_task.duration = 90
        new_schedule = scheduler.reschedule(affected_task_ids=["write"])

        # Verify email_task time unchanged
        original_email = next(e for e in original_schedule if e.id == "email")
        new_email = next(e for e in new_schedule if e.id == "email")
        assert original_email.start == new_email.start

        # Verify review_task rescheduled after write_task
        new_write = next(e for e in new_schedule if e.id == "write")
        new_review = next(e for e in new_schedule if e.id == "review")
        assert new_review.start >= new_write.end + timedelta(minutes=15)

    def test_reschedule_preserves_zone_integrity(self, work_day_zones):
        """
        When: Task is rescheduled
        Then: Zone type constraints must be maintained
        And: Energy level requirements must be respected
        """
        deep_task = Task(
            id="deep_work",
            duration=60,
            zone_type=ZoneType.DEEP,
            energy_level=EnergyLevel.HIGH
        )

        scheduler = Scheduler()
        new_schedule = scheduler.reschedule([deep_task])

        deep_event = next(e for e in new_schedule if e.id == "deep_work")
        scheduled_zone = next(z for z in work_day_zones
                              if z.start <= deep_event.start <= z.end)

        assert scheduled_zone.zone_type == ZoneType.DEEP
        assert scheduled_zone.energy_level == EnergyLevel.HIGH

    def test_reschedule_maintains_project_sequence(self):
        """
        When: Task in project sequence is rescheduled
        Then: Project task sequence should be maintained
        """
        tasks = [
            Task(id="step1", project_id="proj1", sequence_number=1),
            Task(id="step2", project_id="proj1", sequence_number=2),
            Task(id="step3", project_id="proj1", sequence_number=3)
        ]

        scheduler = Scheduler()
        new_schedule = scheduler.reschedule([tasks[1]])  # Reschedule middle task

        scheduled_ids = [e.id for e in new_schedule]
        assert scheduled_ids.index("step1") < scheduled_ids.index("step2")
        assert scheduled_ids.index("step2") < scheduled_ids.index("step3")

    def test_reschedule_handles_buffer_requirements(self, work_day_zones):
        """
        When: Tasks are rescheduled
        Then: Required buffer times must be maintained
        And: Zone transition buffers must be respected
        """
        tasks = [
            Task(id="task1", duration=60, buffer_required=15),
            Task(id="task2", duration=60, buffer_required=30)
        ]

        scheduler = Scheduler()
        schedule = scheduler.reschedule(tasks)

        task1_event = next(e for e in schedule if e.id == "task1")
        task2_event = next(e for e in schedule if e.id == "task2")

        buffer_time = (task2_event.start - task1_event.end).total_seconds() / 60
        assert buffer_time >= 30  # Larger buffer should be used

    def test_reschedule_handles_partial_day_availability(self):
        """
        When: Calendar has fixed events
        Then: Tasks should be rescheduled around fixed events
        And: No overlap should occur
        """
        fixed_event = Event(
            id="meeting",
            start=datetime.now().replace(hour=10),
            end=datetime.now().replace(hour=11),
            type=TimeBlockType.FIXED
        )

        task = Task(id="work", duration=120)

        scheduler = Scheduler()
        schedule = scheduler.reschedule([task], fixed_events=[fixed_event])

        work_event = next(e for e in schedule if e.id == "work")
        assert not (work_event.start < fixed_event.end and
                    work_event.end > fixed_event.start)

    def test_reschedule_splits_tasks_when_necessary(self):
        """
        When: No continuous block available
        Then: Splittable tasks should be split
        And: Split chunks should respect minimum duration
        """
        task = Task(
            id="splittable",
            duration=240,
            is_splittable=True,
            min_chunk_duration=60,
            max_split_count=4
        )

        fixed_events = [
            Event(id="meeting1", start=datetime.now().replace(hour=9),
                  end=datetime.now().replace(hour=10)),
            Event(id="meeting2", start=datetime.now().replace(hour=14),
                  end=datetime.now().replace(hour=15))
        ]

        scheduler = Scheduler()
        schedule = scheduler.reschedule([task], fixed_events=fixed_events)

        split_events = [e for e in schedule if e.id.startswith("splittable")]
        assert len(split_events) > 1
        assert all(e.end - e.start >= timedelta(minutes=60)
                   for e in split_events)

    def test_reschedule_handles_energy_level_changes(self, work_day_zones):
        """
        When: Energy levels change throughout day
        Then: Tasks should be scheduled in appropriate energy zones
        """
        high_energy_task = Task(
            id="complex",
            duration=60,
            energy_level=EnergyLevel.HIGH
        )

        scheduler = Scheduler()
        schedule = scheduler.reschedule([high_energy_task])

        task_event = next(e for e in schedule if e.id == "complex")
        scheduled_zone = next(z for z in work_day_zones
                              if z.start <= task_event.start <= z.end)

        assert scheduled_zone.energy_level == EnergyLevel.HIGH