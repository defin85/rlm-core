## ADDED Requirements

### Requirement: Advanced BSL analysis remains adapter-owned
The system SHALL expose advanced BSL analysis capabilities as adapter-owned extensions rather than shared-core behavior.

#### Scenario: Use an advanced BSL-specific analysis capability
- **WHEN** a caller invokes a BSL capability that depends on BSL-specific metadata, parsing, or indexed enrichments
- **THEN** that behavior is supplied by the BSL adapter extension layer
- **AND** the shared core remains responsible only for generic orchestration and capability routing
