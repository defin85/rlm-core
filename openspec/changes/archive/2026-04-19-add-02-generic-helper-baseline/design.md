## Context

Generic helpers are the smallest useful surface for repository analysis and should exist before language adapters add specialized capabilities.

## Decisions

- The baseline helper set is language-agnostic.
- Helpers are injected by the runtime, not by any one adapter.
- Output formatting favors compact, intentional summaries over uncontrolled file dumps.

## Risks / Trade-offs

- A helper set that is too small may force premature adapter work.
  - Mitigation: include the proven upstream exploration primitives first, then expand only when justified by real workflows.
