## Context

Public API design should happen after the first real adapter proves the internal runtime and lifecycle contracts.

## Decisions

- The public surface wraps core runtime and lifecycle services rather than bypassing them.
- MCP and CLI semantics should align where they describe the same lifecycle operations.
- Capability differences are surfaced explicitly instead of being hidden behind adapter-specific command variations.

## Risks / Trade-offs

- Stabilizing the public surface too early could freeze weak abstractions.
  - Mitigation: sequence this change after the first production-grade adapter slice.
