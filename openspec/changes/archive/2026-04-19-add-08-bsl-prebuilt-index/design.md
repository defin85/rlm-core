## Context

The BSL adapter should move from pure live analysis to indexed acceleration without breaking the core-owned lifecycle design.

## Decisions

- The BSL index implementation remains adapter-owned.
- Build and status semantics are exposed only through the shared core lifecycle service.
- The first indexed helper set targets the workflows that most improve latency and context efficiency.

## Risks / Trade-offs

- BSL index migration is likely one of the largest slices in the roadmap.
  - Mitigation: keep advanced enrichments out of this change and move them to the next one.
