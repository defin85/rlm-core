## Context

`rlm-core` is meant to evolve from the current single-language BSL implementation into a multilingual runtime with shared orchestration and pluggable language adapters. In `rlm-tools-bsl`, the MCP layer, session lifecycle, project registry, index lifecycle, and BSL-specific indexing are colocated in one package. That is workable for a single adapter but does not define a safe extraction boundary for a shared core.

The main open architecture question is where project/workspace registry and index lifecycle management should live as multiple adapters are introduced.

## Goals / Non-Goals

- Goals:
  - Keep one stable runtime and MCP/API surface across languages.
  - Avoid baking BSL-specific index and metadata assumptions into `core`.
  - Avoid duplicating index lifecycle orchestration in every adapter.
  - Support both direct-path execution and registry-backed execution.
- Non-Goals:
  - Define the full generic index schema in this change.
  - Implement cross-language symbol resolution.
  - Require every adapter to support prebuilt indexing or incremental updates.

## Decisions

### Decision: Workspace/project registry lives in core

`core` owns the registry abstraction and any policy around workspace identifiers, human-readable aliases, confirmation metadata, and lookup from external API inputs to canonical filesystem roots.

Rationale:
- Registry lookup is a runtime concern, not a language concern.
- Users should see one consistent workflow whether they target BSL, TypeScript, Go, or another adapter.
- Confirmation and mutation policy should not be reimplemented differently per adapter.

### Decision: Index lifecycle orchestration lives in core

`core` owns the state machine and service surface for `build`, `update`, `drop`, `info`, `check`, locking, background jobs, stale detection, and status reporting.

Rationale:
- These operations define the user-visible lifecycle contract.
- The MCP/API surface should remain stable across languages.
- Locking, job tracking, and orchestration are generic concerns that should not fragment across adapters.

### Decision: Adapters own index implementation and schema extensions

Each adapter owns language-specific detection, parsing, extractors, index builders/readers, helper registration, strategy hints, and any adapter-owned indexed data beyond the generic core entities.

Rationale:
- The parsing and index model for BSL, TypeScript, Go, Rust, and Java will differ materially.
- Adapter-owned extensions prevent the core schema from turning into a union of all language quirks.
- This keeps the core reusable and allows adapters with weaker indexing support to participate without faking unsupported capabilities.

### Decision: Capabilities are explicit

Adapters must declare capabilities such as:
- supports prebuilt index
- supports incremental update
- supports background build
- supports generic entities only
- supports adapter-specific indexed helpers/features

Rationale:
- Not every adapter can support the same lifecycle operations.
- The core must be able to surface consistent API behavior without pretending unsupported features exist.

### Decision: Registry use remains optional

The runtime must continue to work with direct filesystem paths even when no registry entry exists. Registry-backed operation is an additional mode, not a mandatory prerequisite.

Rationale:
- Direct-path operation keeps the lightweight `rlm-tools` workflow intact.
- Registry-backed operation is valuable for managed or remote deployments, but should not become a hard dependency for local exploration.

## Alternatives Considered

### Put both registry and index lifecycle in adapters

Rejected because it would duplicate:
- background job handling
- lifecycle status semantics
- locking
- mutation/confirmation policy
- external API semantics

This would likely produce different behavior across adapters and make the runtime harder to reason about.

### Put both lifecycle and index implementation in core

Rejected because the shared core would accumulate language-specific assumptions and become a disguised BSL-first implementation. That would make future adapters fit poorly or require unnatural abstractions.

## Risks / Trade-offs

- The capability model can become too abstract if it tries to predict every future adapter need.
  - Mitigation: start with the minimum capability set needed for BSL plus one mainstream language.
- Core-owned lifecycle may still leak adapter assumptions if the first migration is BSL-only.
  - Mitigation: keep adapter hooks narrow and validate them against at least one non-BSL adapter design before locking the SPI.
- Optional registry mode increases the number of execution paths to test.
  - Mitigation: treat path-only and registry-backed flows as first-class acceptance paths.

## Migration Plan

1. Define the core contracts for registry, lifecycle orchestration, and adapter capabilities.
2. Extract BSL-specific index logic behind the adapter SPI without changing external behavior.
3. Route existing MCP/API actions through core-owned orchestration services.
4. Add a second adapter or adapter stub to validate that the contracts are not BSL-shaped.

## Open Questions

- Whether the public name should be `ProjectRegistry`, `WorkspaceRegistry`, or a pair of abstractions.
- Whether direct-path indexing metadata and registry-backed indexing metadata should share one persistence backend or only one lifecycle API.
