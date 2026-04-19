## Context

Registry-backed operation is useful for managed and remote workflows, but it must remain optional so the lightweight direct-path flow is preserved.

## Decisions

- The registry is core-owned and shared across adapters.
- Path-only operation remains a first-class execution path.
- Registry mutation policy is centralized rather than adapter-specific.

## Risks / Trade-offs

- Registry support increases lifecycle complexity and test matrix size.
  - Mitigation: require both path-only and registry-backed acceptance tests for relevant workflows.
