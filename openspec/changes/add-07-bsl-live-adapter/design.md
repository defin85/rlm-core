## Context

BSL is the migration anchor for `rlm-core`, but the adapter should first prove the live-analysis path before index migration complexity is introduced.

## Decisions

- Live BSL analysis is introduced before prebuilt BSL indexing.
- The adapter must register helpers through the shared SPI rather than by wiring directly into the runtime.
- The first helper set should focus on navigation and targeted code reading rather than every advanced BSL feature.

## Risks / Trade-offs

- Live-only analysis may be slower on large repositories.
  - Mitigation: treat this slice as the semantic migration baseline and add indexed acceleration in the next change.
