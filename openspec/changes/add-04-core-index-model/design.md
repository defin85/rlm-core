## Context

The shared core needs an index model, but it should be small enough to stay multilingual and stable across adapters.

## Decisions

- The core owns only generic entities.
- Adapter-specific metadata lives in adapter extensions rather than the core schema.
- The index model is defined before lifecycle orchestration so lifecycle logic has a stable target.

## Risks / Trade-offs

- A generic model can become too weak for real workflows.
  - Mitigation: keep adapter extension hooks explicit instead of overstuffing the shared schema.
