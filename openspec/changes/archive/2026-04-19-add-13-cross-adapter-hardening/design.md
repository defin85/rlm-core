## Context

Even with a second adapter, shared systems often still carry hidden assumptions from the first migration target. This final hardening slice is intended to flush those assumptions out and stabilize the repository as a multilingual core.

## Decisions

- Cross-adapter hardening is its own change rather than a side effect of the second-adapter work.
- Capability differences are documented and tested explicitly.
- Shared product semantics take priority over adapter-specific convenience shortcuts.

## Risks / Trade-offs

- Hardening work can look like cleanup and be deferred.
  - Mitigation: keep it as a named roadmap change with explicit acceptance criteria.
