## ADDED Requirements

### Requirement: BSL adapter supports prebuilt indexing
The system SHALL support a BSL prebuilt index through adapter-owned build/read logic orchestrated by the shared core lifecycle service.

#### Scenario: Build and use a BSL prebuilt index
- **WHEN** a caller requests a BSL index build through the shared lifecycle API
- **THEN** the core lifecycle service orchestrates the request and the BSL adapter performs language-specific index work
- **AND** subsequent BSL helper flows can use indexed acceleration when that index is available
