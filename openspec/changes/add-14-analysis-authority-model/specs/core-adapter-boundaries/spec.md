## ADDED Requirements

### Requirement: Adapter-owned analysis providers
The system SHALL allow adapters to declare optional analysis providers beyond helper registration and index lifecycle hooks.

#### Scenario: Integrate a semantic backend without moving language semantics into core
- **WHEN** an adapter adds compiler, type-checker, language-server, or official toolchain-backed analysis
- **THEN** backend selection, configuration, and execution remain adapter-owned
- **AND** the shared core exposes that provider through adapter-neutral contracts instead of reimplementing language semantics itself
