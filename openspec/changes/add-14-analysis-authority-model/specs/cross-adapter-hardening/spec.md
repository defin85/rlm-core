## MODIFIED Requirements

### Requirement: Cross-adapter behavior is explicit and hardened
The system SHALL expose cross-adapter behavior through explicit capability handling, analysis-authority signaling, and shared semantics rather than first-adapter assumptions.

#### Scenario: Compare supported behavior across adapters
- **WHEN** callers interact with adapters that differ in supported features or trust levels
- **THEN** capability and authority differences are surfaced explicitly through shared runtime and lifecycle semantics
- **AND** unsupported or heuristic-only behavior is handled consistently rather than by adapter-specific surprises
