## ADDED Requirements

### Requirement: Sessions expose analysis authority profiles
The system SHALL expose a machine-readable analysis authority profile for each session and selected adapter so callers can understand the trust level of available analysis workflows before invoking helper logic.

#### Scenario: Start a session on a heuristic-only adapter
- **WHEN** a caller starts a session on an adapter that only supports textual or heuristic analysis
- **THEN** the session metadata includes the declared authority levels and backend kinds available for that adapter
- **AND** the caller can distinguish heuristic analysis from semantic or authoritative analysis without inferring it from helper names alone

### Requirement: Analysis claims distinguish possible from resolved results
The system SHALL require helpers that report structural or semantic relationships such as callers, callees, references, implementations, or type resolution to distinguish approximate claims from resolved claims.

#### Scenario: Return a heuristic call relationship
- **WHEN** a helper reports a relationship without a semantic or authoritative backend proving it
- **THEN** the result marks that relationship as possible or heuristic
- **AND** it does not present the relationship as resolved truth

#### Scenario: Return a resolved semantic relationship
- **WHEN** a helper reports a relationship backed by a declared semantic or authoritative provider
- **THEN** the result marks that relationship as resolved
- **AND** it carries provider provenance sufficient to audit the claim

### Requirement: Analysis provenance is explicit
The system SHALL attach backend provenance and freshness metadata to analysis results that make structural or semantic claims.

#### Scenario: Return an indexed analysis result
- **WHEN** a helper or provider serves an answer from an indexed or cached backend
- **THEN** the result includes backend identity and freshness or staleness metadata
- **AND** the caller can tell whether the answer came from live analysis or a persisted snapshot
