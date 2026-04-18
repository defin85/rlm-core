## ADDED Requirements

### Requirement: Non-BSL adapter validation
The system SHALL validate the shared core architecture through a second real adapter that is materially different from BSL.

#### Scenario: Use a Go repository through the shared runtime
- **WHEN** a caller analyzes a Go repository through the shared runtime
- **THEN** the Go adapter integrates through the same adapter SPI and lifecycle contracts as the BSL adapter
- **AND** the shared core does not require BSL-specific assumptions to support that workflow
