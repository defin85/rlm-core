## ADDED Requirements

### Requirement: Shared generic index entities
The system SHALL define a shared generic index model for core-owned repository entities.

#### Scenario: Persist generic repository structure
- **WHEN** an adapter emits generic repository information into the shared index
- **THEN** the index can represent files, symbols, definitions, references, calls, imports, and diagnostics
- **AND** those entities do not require language-specific fields to remain valid
