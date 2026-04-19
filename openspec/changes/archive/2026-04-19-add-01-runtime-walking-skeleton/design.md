## Context

The first implementation slice must prove that `rlm-core` can run the essential RLM loop before layering adapter and index complexity on top.

## Decisions

- The first slice targets only path-based execution.
- The runtime owns session creation, execution dispatch, and teardown.
- The sandbox namespace is persistent within a session to preserve the upstream usage model.

## Risks / Trade-offs

- A minimal runtime may look too bare compared to the final target.
  - Mitigation: treat this slice as a proof of orchestration, not a feature-complete product surface.
