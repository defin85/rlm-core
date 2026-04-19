## ADDED Requirements

### Requirement: Minimal runtime loop
The system SHALL provide a minimal runtime loop that supports starting a session, executing code in a persistent sandbox, and ending the session.

#### Scenario: Explore a repository through a persistent session
- **WHEN** a caller starts a session for a repository path and executes multiple code snippets
- **THEN** the runtime preserves sandbox state across execute calls
- **AND** the session can be explicitly closed to release resources
