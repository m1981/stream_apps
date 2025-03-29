## Commands:

@STATUS-ANALYSIS [@STATUS, @SPEC]
1. Compare current implementation status in @STATUS against @SPEC requirements
2. Identify gaps and incomplete features
3. Update @STATUS based on step 3 if not aligned with @SPEC
4. Update @SPEC based on step 3 if not aligned with @STATUS

## Reference:
@SPEC - located in spec.md
@STATUS - Implementation status located in status.md


## @TWIN - Test Writing Instructions
When writing tests, follow the Gherkin (Given-When-Then) model to clearly express business requirements:
```
Feature: [Feature being tested]

Scenario: [Specific scenario being tested]
  Given preconditions and setup]
  When [actions performed]
  Then [expected outcomes]
  And [additional assertions if needed]
```


## @PRINCE Principles

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






