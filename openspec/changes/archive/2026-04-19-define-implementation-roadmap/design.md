## Context

`rlm-core` is starting from a clean repository with a clear target architecture but without implementation slices. The main risk at this stage is sequencing: the repository can drift into premature generic index design, BSL-shaped core abstractions, or public API stabilization before the runtime and adapter boundaries are proven.

The roadmap should favor vertical slices that prove the architecture incrementally:
- first a working runtime loop
- then adapter selection and core lifecycle
- then one production-grade adapter
- then a second adapter to prove the abstractions are not BSL-specific

## Goals / Non-Goals

- Goals:
  - Provide a realistic, dependency-aware implementation order.
  - Minimize architectural risk and wasted work.
  - Create natural acceptance gates between foundation, first adapter, and multilingual proof.
- Non-Goals:
  - Lock every future change permanently; later proposals may still refine scope.
  - Fully specify each implementation detail in this roadmap artifact.

## Decisions

### Decision: Use sequential `add-0x-*` changes

The implementation roadmap is defined as an ordered set of `add-0x-*` changes, where the prefix encodes intended execution order.

### Decision: Prefer walking skeleton before full index design

The runtime/session/sandbox loop must be proven before broad generic indexing work starts.

### Decision: Prove one production-grade adapter before stabilizing public surface

The first real adapter (BSL) should validate core assumptions before the public MCP/API and CLI surface are considered stable.

### Decision: Require a second adapter before declaring the core truly multilingual

A second adapter is needed to prove that the shared core contracts are not accidentally BSL-shaped.

## Phases and Gates

### Phase 1: Runtime foundation
- `add-01-runtime-walking-skeleton`
- `add-02-generic-helper-baseline`
- `add-03-adapter-spi-and-selection`

Gate:
- A minimal upstream-style exploration loop works end-to-end.
- Adapter selection exists without BSL-specific branching in the runtime.

### Phase 2: Core lifecycle services
- `add-04-core-index-model`
- `add-05-core-index-lifecycle`
- `add-06-workspace-registry`

Gate:
- Core lifecycle services operate in path-only mode and optional registry-backed mode.
- The index service surface exists independently of any one adapter.

### Phase 3: First production-grade adapter
- `add-07-bsl-live-adapter`
- `add-08-bsl-prebuilt-index`
- `add-09-bsl-advanced-analysis`

Gate:
- BSL works as a real adapter rather than a hidden core subsystem.
- The first production vertical slice demonstrates both live analysis and indexed acceleration.

### Phase 4: Stable product surface and quality
- `add-10-public-api-surface`
- `add-11-quality-evals-and-safety`

Gate:
- External API and CLI semantics are stable enough to benchmark and harden.
- Quality, sandbox safety, and context-efficiency claims are measurable.

### Phase 5: Multilingual proof
- `add-12-go-second-adapter`
- `add-13-cross-adapter-hardening`

Gate:
- The core has been validated by at least two materially different adapters.
- Remaining BSL-first assumptions are removed or made explicit.

## Risks / Trade-offs

- A strict sequence can slow down parallel work.
  - Mitigation: allow parallelism only within a phase when shared contracts are already stable.
- BSL migration tasks may still be large enough to require subdivision.
  - Mitigation: treat `add-08` and `add-09` as split candidates if implementation scope expands.
- The chosen second adapter may change as the repository evolves.
  - Mitigation: keep the second-adapter phase explicit so adapter selection can be revised by a focused change if needed.

## Open Questions

- Whether the second adapter should remain Go or be switched to TypeScript if product priorities change.
- Whether `add-10` should expose both MCP and CLI in one change or split if the public surface proves too large.
