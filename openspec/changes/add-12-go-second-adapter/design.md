## Context

The second adapter is the real test of whether `rlm-core` is multilingual or merely a BSL migration shell.

## Decisions

- The second adapter is planned as Go unless a later focused change revises that decision.
- Go-specific tooling remains adapter-owned and optional from the core's perspective.
- The purpose of this slice is architectural proof, not immediate parity with every future BSL capability.

## Risks / Trade-offs

- External Go tooling can add environment complexity.
  - Mitigation: keep toolchain integration behind adapter-owned boundaries and capability declarations.
