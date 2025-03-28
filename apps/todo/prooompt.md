# AI Implementation Procedure

Reference Tags:
@STATUS - Implementation status (in Readme.md)
@SPEC - System specifications
@PRINCE - Architecture principles
@TWIN - Test writing guidelines
@DEVCON - Development constraints
@REF_IP - Implementation plan

Follow these steps sequentially, using reference tags for context:

1. STATUS ANALYSIS [@STATUS, @SPEC]
- Compare current implementation status in @STATUS against @SPEC requirements
- Identify gaps and incomplete features
- Output a concise status report focusing on missing core functionality

2. PRIORITY SELECTION [@STATUS, @PRINCE, @REF_IP]
- Based on @STATUS analysis, identify next highest-priority item from @REF_IP
- Consider dependencies between components
- Justify selection based on @PRINCE architecture principles

3. DOMAIN MODEL VERIFICATION [@PRINCE, @SPEC]
- For selected feature, verify required domain entities exist in @SPEC
- Check alignment with @PRINCE principles
- List any missing domain entities or relationships
- Provide domain model suggestions using standard DDD patterns

4. TEST DEVELOPMENT [@TWIN, @SPEC, @DEVCON]
- Following @TWIN guidelines, write tests for the selected feature
- Structure using Given-When-Then format from @TWIN
- Focus on business requirements from @SPEC
- Include edge cases and validation scenarios

5. IMPLEMENTATION [@PRINCE, @DEVCON]
- Implement minimum code needed to make tests pass
- Follow @PRINCE architectural principles
- Maintain clean architecture boundaries
- Document key business rules in comments

Output Format:
1. Status Report: [concise gap analysis]
2. Selected Priority: [feature] because [reasoning]
3. Domain Model Needs: [entities/relationships]
4. Test Implementation: [code]
5. Feature Implementation: [code]

# AI Commands Quick Reference

## Basic Commands
STATUS - Show current implementation status
NEXT   - Analyze and suggest next priority item
SPEC   - Show system specifications
TEST   - Get test writing guidelines
IMPL   - Get implementation guidelines
ARCH   - Show architecture principles
PLAN   - Show implementation plan

## Analysis Commands
GAP    - Analyze gaps between STATUS and SPEC
VERIFY - Verify current implementation against PRINCE
CHECK  - Run full status analysis (STATUS + GAP + NEXT)

## Implementation Commands
DO     - Execute full implementation cycle for next feature:
        1. Status analysis
        2. Priority selection
        3. Domain verification
        4. Test development
        5. Implementation

## Command Combinations
STATUS + NEXT  - Show status and next priority
SPEC + TEST    - Show specifications and test guidelines
GAP + PLAN     - Show gaps and implementation plan

Example usage:
"STATUS" - Shows current status
"NEXT" - Suggests next priority item
"DO" - Starts full implementation cycle
