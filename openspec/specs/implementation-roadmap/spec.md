# implementation-roadmap Specification

## Purpose
TBD - created by archiving change define-implementation-roadmap. Update Purpose after archive.
## Requirements
### Requirement: Implementation work must follow a staged roadmap
The repository SHALL maintain an explicit staged implementation roadmap for delivering the `rlm-core` runtime, lifecycle services, adapters, and public product surface.

#### Scenario: Plan implementation work after architecture setup
- **WHEN** the repository has project context and core/adapter boundary decisions but not yet an implementation sequence
- **THEN** it defines an ordered roadmap of future changes
- **AND** the roadmap records the intended dependency order between foundational runtime, lifecycle, adapter, and hardening work

### Requirement: Foundational runtime work must precede adapter-specific hardening
The repository SHALL sequence foundational runtime and lifecycle changes before production adapter hardening and multilingual validation.

#### Scenario: Evaluate whether to start a later implementation change
- **WHEN** a later roadmap item depends on runtime, adapter SPI, or lifecycle services that are not yet established
- **THEN** the later item is treated as blocked by the earlier foundational changes
- **AND** the roadmap does not treat advanced adapter or public API work as independent of those prerequisites

