# adapter-selection Specification

## Purpose
TBD - created by archiving change add-03-adapter-spi-and-selection. Update Purpose after archive.
## Requirements
### Requirement: Runtime-selected adapters
The system SHALL select language adapters through a runtime-owned adapter registry and explicit adapter contract.

#### Scenario: Start a session for a repository with a matching adapter
- **WHEN** a caller starts a session for a repository path
- **THEN** the runtime evaluates available adapters against that workspace
- **AND** it selects the matching adapter through the shared SPI rather than through hardcoded language branches

### Requirement: Explicit adapter capabilities
The system SHALL require adapters to declare supported capabilities explicitly.

#### Scenario: Inspect adapter support for an indexed feature
- **WHEN** the runtime or caller needs to know whether an adapter supports a lifecycle or indexed feature
- **THEN** capability availability is determined through the adapter declaration
- **AND** unsupported behavior is not inferred or silently assumed

