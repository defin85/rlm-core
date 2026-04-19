## ADDED Requirements

### Requirement: Authority-aware correctness gates
The system SHALL maintain correctness gates that verify analysis claims do not overstate their authority level.

#### Scenario: Validate heuristic and semantic analysis claims
- **WHEN** the repository evaluates a release candidate or substantial change
- **THEN** the quality and safety suite checks that approximate helpers are labeled as approximate
- **AND** resolved claims are only emitted when backed by declared semantic or authoritative providers
- **AND** regressions fail when helpers silently upgrade heuristic results into resolved ones
