## ADDED Requirements

### Requirement: Core-owned workspace resolution
The system SHALL provide a core-owned workspace resolution layer that supports both direct filesystem paths and registry-backed workspace/project identifiers.

#### Scenario: Start a session by direct path
- **WHEN** a caller provides a direct repository path without using any registry entry
- **THEN** the runtime resolves the workspace without requiring adapter-specific registry logic
- **AND** adapter selection happens after workspace resolution

#### Scenario: Start a session by registered workspace
- **WHEN** a caller provides a registered workspace or project identifier
- **THEN** the runtime resolves the identifier through a core-owned registry abstraction
- **AND** the resolved workspace is passed into the adapter lifecycle using the same downstream contract as direct-path execution

### Requirement: Core-owned index lifecycle orchestration
The system SHALL expose index lifecycle operations through a core-owned orchestration layer with stable semantics for build, update, drop, info, and status/check behaviors.

#### Scenario: Build an index through the shared lifecycle API
- **WHEN** a caller requests an index build for a workspace
- **THEN** the core lifecycle layer owns request validation, job orchestration, locking, and status reporting
- **AND** it delegates language-specific build execution to the selected adapter

#### Scenario: Report unsupported lifecycle features
- **WHEN** a caller requests a lifecycle action that the selected adapter does not support
- **THEN** the core lifecycle layer returns a consistent unsupported-capability result
- **AND** it does not require the adapter to emulate unsupported behavior

### Requirement: Adapter-owned index implementation
The system SHALL require each adapter to own its language-specific repository detection, index build/read implementation, helper registration, and adapter-specific schema extensions.

#### Scenario: Build a BSL index
- **WHEN** the BSL adapter is selected for a workspace
- **THEN** BSL parsing, extraction, indexed helper enablement, and BSL-specific schema extensions are handled by the adapter
- **AND** the shared core does not need BSL-specific parsing rules to orchestrate the lifecycle

#### Scenario: Add an adapter with different indexing capabilities
- **WHEN** a new adapter supports only a subset of the indexed feature set
- **THEN** the adapter declares its capabilities explicitly
- **AND** the core lifecycle uses those capabilities instead of assuming BSL-level feature parity

### Requirement: Optional registry mode
The system SHALL treat registry-backed operation as optional rather than mandatory for repository analysis.

#### Scenario: Run without any registry entries
- **WHEN** no workspace or project has been registered
- **THEN** the runtime still supports path-based session and index workflows
- **AND** callers are not forced to populate a registry before using the system
