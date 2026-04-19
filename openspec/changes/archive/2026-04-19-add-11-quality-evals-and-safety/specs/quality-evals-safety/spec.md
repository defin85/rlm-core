## ADDED Requirements

### Requirement: Measurable quality and safety gates
The system SHALL maintain measurable quality and safety gates for runtime, lifecycle, and adapter behavior.

#### Scenario: Validate a release candidate against runtime claims
- **WHEN** the repository evaluates a release candidate or substantial change
- **THEN** it can run repeatable quality, benchmark, and safety checks
- **AND** those checks cover sandbox behavior, lifecycle regressions, and representative adapter workflows
