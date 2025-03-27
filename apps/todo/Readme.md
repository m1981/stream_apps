# Specification (SPEC)
Task Scheduling System: Todoist to Google Calendar Integration

## Development Constraints  (DEVCON)

We are great fans of TDD technique so we first write tests to fulfill business requirements and then move to implementation.
1. Read REF_SP
2. Read business logic comments in core files
3. Read existing test cases
4. Write tests first. Follow best TDD and DDD principles. Refer to business logic. When lack of business logic ask user questions.
5. Provide implementation

### Test Writing Instructions
When writing tests, follow the Gherkin (Given-When-Then) model to clearly express business requirements:

```gherkin
Feature: [Feature being tested]

Scenario: [Specific scenario being tested]
  Given [preconditions and setup]
  When [actions performed]
  Then [expected outcomes]
  And [additional assertions if needed]
```

Translate these Gherkin scenarios into actual test code using the Arrange-Act-Assert pattern while maintaining the business language and intent of the requirements.

## Principles (PRINCE)

1. Domain-Driven Design (DDD) Principles
- Clear bounded context for task scheduling domain
- Rich domain models (`Task`, `TimeBlockZone`, `Event`)
- Value objects and entities properly separated
- Domain logic encapsulated within entities (e.g., `Task.split()`)
- Ubiquitous language consistently used throughout (reflected in comments and naming)

2. SOLID Principles
- Single Responsibility: Each class has one clear purpose (e.g., `ConflictDetector`, `SequenceManager`)
- Open/Closed: Strategy pattern for scheduling algorithms allows extension
- Liskov Substitution: Clean inheritance hierarchy (e.g., `SchedulingStrategy`)
- Interface Segregation: Protocols for repositories define minimal interfaces
- Dependency Inversion: High-level modules depend on abstractions (`TaskRepository`, `CalendarRepository`)

3. Clean Architecture
- Clear separation of concerns:
   - Domain layer (`task.py`, `timeblock.py`)
   - Application services (`scheduler.py`)
   - Infrastructure interfaces (repository protocols)
- Domain models independent of external concerns
- Business rules centralized in domain entities
- Infrastructure dependencies isolated via protocols

4. Design Patterns
- Strategy Pattern: `SchedulingStrategy` for different scheduling algorithms
- Repository Pattern: `TaskRepository` and `CalendarRepository`
- Factory Pattern: Task creation and splitting
- Command Pattern: Scheduling operations

5. Immutability and Value Objects
- Tasks are immutable (using `@dataclass`)
- Splitting creates new instances rather than modifying
- Clear value objects for constraints and configurations

6. Testability
- Dependency injection enables easy mocking
- Clear separation allows unit testing of business logic
- Test fixtures demonstrate intended usage
- Comprehensive test coverage approach

The architecture shows mature understanding of:
- Separation of concerns
- Business domain isolation
- External service adaptation
- Testing best practices

This is a well-structured enterprise application following established patterns while maintaining pragmatic simplicity.

For AI: Each implementation file has comments that provide:
* Domain context
* Business rules
* Architectural decisions
* System constraints

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



# Implementation Plan (REF_IP)

1. Implementation (Start with the simplest useful behavior)

1.1. Task & TimeBlock Core Logic
- Implement basic Task validation rules
- Implement TimeBlock availability checking
- Write tests for time conflicts detection
- Implement basic time zone constraints

1.2. Basic Scheduling Algorithm
- Start with simplest SchedulingStrategy implementation
- Focus on single-day, non-splitting tasks first
- Write tests for basic scheduling scenarios
- Implement conflict detection

2. Infrastructure Layer (External Services Integration)
   2.1. TodoistAdapter Implementation
   - Write integration tests for Todoist API
   - Implement task fetching and mapping to domain model
   - Handle error cases and API limits
   - Add task status updates

2.2. GoogleCalendarAdapter Implementation
- Write integration tests for Google Calendar API
- Implement event fetching and mapping
- Add event creation and deletion
- Handle calendar sync conflicts

3. Scheduling Features
   3.1. Task Splitting Logic
- Implement tests for splittable tasks
- Add logic for minimum chunk duration
- Handle maximum split count
- Test various splitting scenarios

3.2. Time Block Zones
- Implement zone matching algorithm
- Add energy level matching
- Handle buffer times between tasks
- Test zone constraints

4. Optimization and Edge Cases
   4.1. Sequence Handling
   - Implement sequence-based scheduling
   - Add due date considerations
   - Handle task dependencies
   - Test sequence conflicts

4.2. Rescheduling Logic
- Implement clean operation
- Add incremental rescheduling
- Handle failed schedules
- Test rescheduling scenarios

5. Integration and Testing

5.1. Integration Tests
- Write end-to-end tests
- Test full scheduling workflow
- Add performance tests
- Test error recovery

5.2. System Testing
- Test with real Todoist data
- Test with real Calendar data
- Measure scheduling performance
- Document edge cases