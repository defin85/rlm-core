# workspace-registry Specification

## Purpose
TBD - created by archiving change add-06-workspace-registry. Update Purpose after archive.
## Requirements
### Requirement: Optional named workspace resolution
The system SHALL support named workspace or project resolution through a core-owned registry while preserving path-only operation.

#### Scenario: Resolve a registered workspace for runtime or lifecycle use
- **WHEN** a caller refers to a registered workspace by name
- **THEN** the runtime resolves that workspace through the core-owned registry
- **AND** downstream execution uses the same lifecycle contracts as direct-path operation

#### Scenario: Operate with no registry entries
- **WHEN** the registry is empty or unused
- **THEN** callers can still use direct repository paths for runtime and index lifecycle operations
- **AND** registry population is not required to use the system

