# @SPEC Specification
Task Scheduling System: Todoist to Google Calendar Integration

## Overview
This system is designed to bridge the gap between task management (Todoist) and time management (Google Calendar) by intelligently scheduling tasks into appropriate time blocks while respecting existing commitments. The core purpose is to transform a list of tasks into a realistic, time-blocked schedule that optimizes productivity through strategic time allocation.

## Problem Statement
Knowledge workers often struggle with two parallel systems:
1. Task Management (What needs to be done?) - Managed in Todoist
2. Time Management (When will it be done?) - Managed in Google Calendar

This disconnect leads to:
- Overcommitment
- Poor time allocation
- Ineffective use of peak productivity hours
- Difficulty in balancing deep work with routine tasks

## Solution
Our system automatically schedules Todoist tasks into Google Calendar using intelligent time blocking, considering:
- Natural energy levels throughout the day
- Task complexity and focus requirements
- Existing calendar commitments
- The need for different types of work zones

## Key Features
1. Automated scheduling within a 3-4 week horizon
2. Respect for existing calendar commitments
3. Intelligent time zone blocking
4. Rescheduling capability when priorities change
5. Clear distinction between system-managed and fixed events

Let me enhance the definitions by incorporating time blocking zones, which is an important concept for effective scheduling:

## Core Terms
1. `Task` - An item from Todoist that needs to be scheduled
2. `Event` - A time block in Google Calendar
3. `Managed Event` - An event created by our system (identified by special marker)
4. `Fixed Event` - Existing calendar events not managed by our system
5. `Planning Horizon` - The 3-4 week period for scheduling
6. `Time Block Zone` - A predefined time period for specific types of work
7. `Scheduling Window` - Available slots within appropriate Time Block Zones
8. `Task Sequence` - The natural ordering of tasks within a Todoist project, reflecting logical workflow and implicit dependencies

## Time Block Zones

1. `Deep Work Zone`:
    - Purpose: Focused, complex tasks requiring sustained attention
    - Time Range: Typically morning hours (e.g., 8:00-12:00)
    - Energy Level: High
    - Minimum Duration: 2 hours
    - Interruption Policy: None
    - Buffer Requirement: 15 minutes between tasks

2. `Light Work Zone`:
    - Purpose: Routine, less demanding tasks
    - Time Range: Typically afternoon (e.g., 13:00-17:00)
    - Energy Level: Medium
    - Minimum Duration: 30 minutes
    - Interruption Policy: Limited
    - Buffer Requirement: 10 minutes between tasks

3. `Admin  Zone`:
    - Purpose: Emails, planning, quick tasks
    - Time Range: Day start/end (e.g., 17:00-18:00)
    - Energy Level: Low
    - Duration: 30-60 minutes
    - Interruption Policy: Flexible
    - Buffer Requirement: 5 minutes between tasks

## Task Properties

1. `Basic Properties`:
    - Duration (estimated time)
    - Due date (from Todoist)
    - Sequence number (position in Todoist project)
    - Project (from Todoist)

2. `Zone Requirements`:
    - Required Zone Type (Deep/Light/Admin)
    - Is Splittable (can be broken into smaller chunks)
    - Minimum Chunk Duration
    - Maximum Split Count
    - Energy Level Required (High/Medium/Low)

3. `Scheduling Constraints`:
    - Preferred Time Block Zone
    - Dependencies (tasks that must be completed first)
    - Maximum Split Count (for splittable tasks)
    - Required Buffer Time

## Scheduling Rules

1. `Task Sequence Resolution`:
    - Maintain project task sequence from Todoist as primary ordering
    - Use due dates for cross-project scheduling
    - Consider dependencies before sequence
    - Tasks within same project maintain Todoist order
    - Cross-project tasks interleave based on due dates

2. `Zone Matching`:
    - Tasks must be scheduled in compatible Time Block Zones
    - Energy level requirements must match zone characteristics
    - Respect minimum duration constraints

3. `Task Splitting`:
    - Only split tasks marked as splittable
    - Respect minimum chunk duration
    - Don't exceed maximum split count
    - Maintain task sequence when split

4. `Buffer Management`:
    - Insert required buffer time between tasks
    - Adjust buffers based on zone type
    - Account for transition time between different zones

## Core Operations

1. `Sync`:
    - Fetch tasks from Todoist
    - Fetch events from Google Calendar
    - Validate task properties
    - Identify fixed vs managed events

2. `Clean`:
    - Remove all managed events
    - Preserve fixed events
    - Update task status

3. `Schedule`:
    - Apply scheduling rules
    - Create managed events
    - Respect zone constraints
    - Handle task splitting

4. `Reschedule`:
    - Execute Clean operation
    - Re-run Schedule operation
    - Maintain task relationships
    - Update all affected events

## System Boundaries

### Error Handling Boundaries
1. `External Service Interactions`:
    - Retry Limits: Maximum 3 attempts for external API calls
    - API Timeouts: Maximum 30 second wait for external services
    - Circuit Breaker: Disable service after 5 consecutive failures

2. `Data Validation`:
    - Reject invalid task properties immediately
    - Validate all incoming API data before processing
    - Return detailed validation errors

3. `Conflict Resolution`:
    - System will fail-fast on scheduling conflicts
    - No automatic conflict resolution
    - User must manually resolve scheduling conflicts
    - Calendar sync conflicts abort operation

### User Interaction Boundaries

1. `In Scope`:
    - Single user task management
    - Basic task property updates
    - Schedule viewing and confirmation
    - Manual rescheduling triggers
    - Basic error notifications

2. `Out of Scope`:
    - Multi-user collaboration
    - Complex task patterns
    - Real-time updates
    - Mobile notifications
    - Automated conflict resolution
    - Task templates
    - Recurring task patterns

