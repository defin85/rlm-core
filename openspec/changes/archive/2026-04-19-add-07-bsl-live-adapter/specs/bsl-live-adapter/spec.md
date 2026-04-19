## ADDED Requirements

### Requirement: BSL adapter supports live analysis
The system SHALL provide a BSL adapter that supports repository detection and useful live filesystem-based analysis through the shared runtime.

#### Scenario: Analyze a BSL repository before any prebuilt index exists
- **WHEN** a caller starts a session on a BSL repository that has no prebuilt index
- **THEN** the BSL adapter is selected through the adapter SPI
- **AND** the caller can use BSL-specific helpers for meaningful repository exploration through live analysis
