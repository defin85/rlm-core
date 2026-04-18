## ADDED Requirements

### Requirement: Shared lifecycle orchestration
The system SHALL expose index lifecycle operations through a core-owned lifecycle service.

#### Scenario: Build an index in path-only mode
- **WHEN** a caller requests an index build for a direct repository path
- **THEN** the core lifecycle service validates the request, acquires lifecycle ownership, and tracks job status
- **AND** language-specific build execution is delegated through the selected adapter

### Requirement: Consistent unsupported-capability behavior
The system SHALL return consistent unsupported-capability results for lifecycle actions an adapter does not implement.

#### Scenario: Request an unsupported update flow
- **WHEN** a caller requests an incremental update for an adapter that only supports full rebuilds
- **THEN** the lifecycle service returns a consistent unsupported-capability outcome
- **AND** it does not require the adapter to emulate unsupported behavior
