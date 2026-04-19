## Context

Lifecycle orchestration is a runtime concern and must remain stable regardless of how individual adapters implement their indexes.

## Decisions

- Lifecycle semantics are owned by the core.
- Adapters are called through lifecycle hooks rather than owning their own external lifecycle APIs.
- Background orchestration and locking are part of the lifecycle contract, not optional adapter behaviors.

## Risks / Trade-offs

- Background orchestration can become complex before real adapters exist.
  - Mitigation: prove the path-only baseline first and keep the initial job model simple.
