## ADDED Requirements

### Requirement: Stable external API surface
The system SHALL expose a stable external API surface for runtime and index lifecycle operations after the foundational runtime and first adapter slices are in place.

#### Scenario: Use runtime and lifecycle tools through the public surface
- **WHEN** a caller interacts with the system through the public MCP or CLI surface
- **THEN** the call routes through the shared runtime and lifecycle services
- **AND** behavior remains consistent across adapters apart from explicitly declared capability differences
